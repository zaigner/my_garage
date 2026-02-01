import requests
import logging
import base64
from django.conf import settings
from django.db import transaction
from decimal import Decimal
from typing import Dict, Any, Optional, List
from django.core.files.base import ContentFile
from django.utils import timezone
from pymongo.errors import ServerSelectionTimeoutError

from my_garage.models import Vehicle, ServiceRecord, Upgrade, ConditionReport, ValuationHistory
from ..utils.mongo import get_collection

logger = logging.getLogger(__name__)

# Configuration from settings (set via Pixi/env)
FASTAPI_BASE_URL = settings.FASTAPI_BASE_URL
MCP_EXECUTE_URL = f"{FASTAPI_BASE_URL}/mcp/execute"


class VehicleServiceError(Exception):
    """Custom exception for service-level failures."""
    pass


def _build_market_search_arguments(vehicle: Vehicle) -> Dict[str, Any]:
    """
    Helper to build comprehensive search arguments from vehicle data.
    Extracts specs and features to refine the market search.
    """
    arguments = {
        "make": vehicle.make,
        "model": vehicle.model,
        "year": vehicle.year,
        "trim": vehicle.trim,
    }
    
    if vehicle.mileage > 0:
        arguments["mileage"] = vehicle.mileage

    # Explicitly add the collector fields if they exist
    if vehicle.exterior_color:
        arguments["exterior_color"] = vehicle.exterior_color
    
    if vehicle.transmission:
        arguments["transmission"] = vehicle.transmission
        
    # Map common specs that affect value and appearance
    spec_keys = [
        'engine', 'drivetrain', 'drive_type', 
        'fuel_type', 'body_style', 'interior_color'
    ]
    
    if vehicle.specs:
        for key in spec_keys:
            # Try exact match
            val = vehicle.specs.get(key)
            # Try Title Case (e.g. "Body Style")
            if not val:
                val = vehicle.specs.get(key.replace('_', ' ').title())
            # Try lowercase space
            if not val:
                val = vehicle.specs.get(key.replace('_', ' '))
                
            if val:
                arguments[key] = val
    
    # Also check features for keywords that might be relevant
    if vehicle.features:
        if isinstance(vehicle.features, dict):
            keywords = [k for k, v in vehicle.features.items() if v]
            if keywords:
                arguments["keywords"] = keywords
        elif isinstance(vehicle.features, list):
            arguments["keywords"] = vehicle.features

    return arguments


@transaction.atomic
def vehicle_update_market_valuation(vehicle: Vehicle) -> Decimal:
    """
    Triggers the Web MCP agent to find comparable listings and
    updates the vehicle's current_market_value.
    """
    # Use the enhanced argument builder to include specs/mileage
    search_args = _build_market_search_arguments(vehicle)
    
    payload = {
        "tool_name": "search_market_listings",
        "arguments": search_args
    }

    try:
        logger.info(f"Requesting valuation for {vehicle} with args: {search_args}")
        response = requests.post(MCP_EXECUTE_URL, json=payload, timeout=20)
        response.raise_for_status()
        data = response.json()
        
        listings = data.get('results', [])
        if not listings:
            logger.warning(f"No listings found for {vehicle} (Valuation)")
            return vehicle.current_market_value

        # Logic: Calculate median price from listings
        prices = [Decimal(str(l['price'])) for l in listings if l.get('price')]
        if not prices:
            return vehicle.current_market_value
            
        median_price = sorted(prices)[len(prices) // 2]

        # Update and save the vehicle
        vehicle.current_market_value = median_price
        vehicle.save(update_fields=['current_market_value'])
        
        # Save history record with raw data
        ValuationHistory.objects.create(
            vehicle=vehicle,
            value=median_price,
            raw_data=data
        )

        return median_price

    except requests.RequestException as e:
        logger.error(f"Valuation request failed: {e}")
        raise VehicleServiceError(f"Failed to reach Valuation Engine: {str(e)}")


def vehicle_enrich_from_vin(vehicle: Vehicle) -> bool:
    """
    Uses the MCP agent to look up vehicle details based on VIN, including the model year.
    Updates the vehicle record with all available specs.
    """
    if not vehicle.vin:
        return False

    payload = {
        "tool_name": "lookup_vehicle_details",
        "arguments": {
            "vin": vehicle.vin,
            "model_year": vehicle.year,
        }
    }

    try:
        response = requests.post(MCP_EXECUTE_URL, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()

        if "error" in data:
            return False

        # Overwrite the specs field with all the data returned from the API
        vehicle.specs = data
        
        # Also update the core fields from the new data, if available
        vehicle.make = data.get("make", vehicle.make)
        vehicle.model = data.get("model", vehicle.model)
        vehicle.year = data.get("model_year", vehicle.year)
        
        # If no photo is uploaded, try to fetch a stock photo
        vehicle.save()
        
        if not vehicle.photo:
            vehicle_fetch_stock_photo(vehicle)

        return True

    except requests.RequestException:
        # Log error but don't crash the transaction
        return False


def vehicle_fetch_stock_photo(vehicle: Vehicle, force_refresh: bool = False) -> bool:
    """
    Uses the MCP agent to find a photo.
    Tries Market Listings first (high quality, specific), then falls back to Google Images.
    If all else fails, tries to generate an image using AI.
    """
    if vehicle.photo and not force_refresh:
        return True

    # --- Attempt 1: Market Listings (High Quality) ---
    base_args = _build_market_search_arguments(vehicle)
    
    # Strategy 1: Specific (Trim + Color) but NO mileage
    args_1 = base_args.copy()
    args_1.pop('mileage', None)
    
    # Strategy 2: Relaxed (Make + Model + Year + Trim) - No color/specs
    args_2 = {
        "make": vehicle.make,
        "model": vehicle.model,
        "year": vehicle.year,
    }
    if vehicle.trim:
        args_2["trim"] = vehicle.trim

    strategies = [
        ("market_specific", args_1),
        ("market_trim_only", args_2),
    ]
    
    for label, args in strategies:
        logger.info(f"Attempting photo fetch strategy '{label}' for {vehicle}")
        if _execute_photo_search_and_save(vehicle, args, label, tool="search_market_listings"):
            logger.info(f"Successfully fetched photo using strategy '{label}'")
            return True

    # --- Attempt 2: HQ Enthusiast Sites (Press Photos) ---
    # These sites have curated high-res images. We prioritize these over generic Google results.
    # Note: We don't include color here as press photos are often in a "hero color".
    # But if the user specified a color, we can try to append it.
    hq_query = f"{vehicle.year} {vehicle.make} {vehicle.model} {vehicle.trim or ''} site:netcarshow.com OR site:wsupercars.com"
    if vehicle.exterior_color:
        hq_query += f" {vehicle.exterior_color}"
        
    logger.info(f"Attempting HQ Site Search for {vehicle}: '{hq_query}'")
    if _execute_photo_search_and_save(vehicle, {"query": hq_query}, "hq_press", tool="search_google_images"):
         logger.info("Successfully fetched photo from HQ press sites")
         return True

    # --- Attempt 3: Google Image Search (Broad Fallback) ---
    # If market listings fail (e.g. rare car, or API limits), use Google Images
    # Add "high resolution" and size constraints to the query to avoid grainy thumbnails
    query = f"{vehicle.year} {vehicle.make} {vehicle.model} {vehicle.trim or ''} stock photo 4k wallpaper imagesize:large"
    if vehicle.exterior_color:
        query += f" {vehicle.exterior_color}"

    logger.info(f"Falling back to Google Image Search for {vehicle}: '{query}'")
    
    if _execute_photo_search_and_save(vehicle, {"query": query}, "google", tool="search_google_images"):
        logger.info("Successfully fetched photo using Google Images")
        return True
    
    # --- Attempt 4: AI Image Generation (Last Resort) ---
    logger.info(f"Falling back to AI Image Generation for {vehicle}")
    if _execute_image_generation_and_save(vehicle):
        logger.info("Successfully generated and saved AI image for vehicle")
        return True
            
    logger.warning(f"All photo fetch strategies failed for {vehicle}")
    return False


def _execute_photo_search_and_save(vehicle: Vehicle, search_args: Dict[str, Any], suffix: str, tool: str) -> bool:
    """
    Helper to execute the MCP search and save the first valid, high-quality image found.
    """
    payload = {
        "tool_name": tool,
        "arguments": search_args
    }

    try:
        response = requests.post(MCP_EXECUTE_URL, json=payload, timeout=20)
        response.raise_for_status()
        data = response.json()
        
        candidates = []

        if tool == "search_market_listings":
            listings = data.get('results', [])
            for listing in listings:
                url = listing.get('image_url') or listing.get('photo') or listing.get('primary_photo_url')
                if url and isinstance(url, str) and url.startswith('http'):
                    candidates.append(url)
                    
        elif tool == "search_google_images":
            candidates = data.get('images', [])
        
        if not candidates:
            return False

        # Try candidates until we find one with good quality
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        
        for image_url in candidates[:10]: # Try top 10
            try:
                img_response = requests.get(image_url, headers=headers, timeout=10)
                img_response.raise_for_status()
                
                # Check image size - skip if less than 50KB (likely a thumbnail)
                if len(img_response.content) < 50 * 1024:
                    logger.warning(f"Skipping image {image_url} (too small: {len(img_response.content)} bytes)")
                    continue

                # Save to the vehicle model
                filename = f"{vehicle.make}_{vehicle.model}_{vehicle.year}_{suffix}.jpg".lower().replace(" ", "_")
                vehicle.photo.save(filename, ContentFile(img_response.content), save=True)
                return True
                
            except Exception as e:
                logger.warning(f"Failed to download candidate {image_url}: {e}")
                continue

        return False

    except (requests.RequestException, Exception) as e:
        logger.warning(f"Photo fetch attempt failed ({tool}): {e}")
        return False


def _execute_image_generation_and_save(vehicle: Vehicle) -> bool:
    """
    Helper to generate an image using AI and save it to the vehicle.
    """
    prompt = f"A high quality, photorealistic image of a {vehicle.year} {vehicle.make} {vehicle.model}"
    if vehicle.trim:
        prompt += f" {vehicle.trim}"
    if vehicle.exterior_color:
        prompt += f" in {vehicle.exterior_color} color"
    prompt += ", parked in a modern garage or showroom, 4k, highly detailed"

    payload = {
        "tool_name": "generate_vehicle_image",
        "arguments": {
            "prompt": prompt
        }
    }

    try:
        response = requests.post(MCP_EXECUTE_URL, json=payload, timeout=70) # Longer timeout for generation
        response.raise_for_status()
        data = response.json()

        image_content = None

        if "image_base64" in data:
            image_content = base64.b64decode(data["image_base64"])
        elif "image_url" in data:
            img_response = requests.get(data["image_url"], timeout=20)
            img_response.raise_for_status()
            image_content = img_response.content
        
        if image_content:
            filename = f"{vehicle.make}_{vehicle.model}_{vehicle.year}_ai_generated.jpg".lower().replace(" ", "_")
            vehicle.photo.save(filename, ContentFile(image_content), save=True)
            return True
        
        return False

    except (requests.RequestException, Exception) as e:
        logger.warning(f"AI Image generation failed: {e}")
        return False


def service_record_create_from_ocr(vehicle: Vehicle, receipt_image: Any) -> ServiceRecord:
    """
    Initializes a service record and triggers the FastAPI OCR pipeline.
    """
    # Fix: Provide a default date (today) because the 'date' field is required (NOT NULL)
    # The OCR process will update this later if it finds a different date.
    record = ServiceRecord.objects.create(
        vehicle=vehicle,
        date=timezone.now().date(),  # Added default date
        vendor="Processing...",
        description="Awaiting AI extraction",
        total_cost=0.00,
        receipt_image=receipt_image,
        is_verified=False
    )

    from my_garage.tasks import task_process_receipt_ocr
    transaction.on_commit(lambda: task_process_receipt_ocr.delay(record.id))

    return record


def service_record_process_ocr_data(record: ServiceRecord) -> bool:
    """
    Processes OCR data for a service record by calling FastAPI OCR service.
    """
    try:
        ocr_url = f"{FASTAPI_BASE_URL}/ocr/process"
        if hasattr(record.receipt_image, 'open'):
            record.receipt_image.open('rb')
        
        files = {'file': record.receipt_image}

        response = requests.post(ocr_url, files=files, timeout=30)
        response.raise_for_status()

        ocr_data = response.json()

        # Always save the raw data to the JSONField for the UI preview
        record.ocr_raw_data = ocr_data

        # Try to save to MongoDB as well (for long-term storage/analytics)
        try:
            mongo_doc = ocr_data.copy()
            mongo_doc['service_record_id'] = record.id
            mongo_doc['vehicle_id'] = record.vehicle_id
            
            collection = get_collection('ocr_documents')
            result = collection.insert_one(mongo_doc)
            # We can store the Mongo ID in the JSONField too if we want
            record.ocr_raw_data["mongo_id"] = str(result.inserted_id)
        except (ServerSelectionTimeoutError, Exception) as mongo_err:
            logger.error(f"MongoDB connection failed: {mongo_err}. Proceeding with Postgres-only storage.")

        record.vendor = ocr_data.get('vendor', record.vendor)
        record.description = ocr_data.get('description', record.description)
        record.total_cost = Decimal(str(ocr_data.get('total_cost', record.total_cost)))
        record.is_verified = True
        record.save()

        return True

    except (requests.RequestException, ValueError, KeyError) as e:
        logger.error(f"OCR processing failed for record {record.id}: {str(e)}")
        return False


@transaction.atomic
def condition_report_add_ai_grade(
        vehicle: Vehicle,
        area: str,
        photo: Any,
        grade: float,
        feedback: str,
        impact: Decimal
) -> ConditionReport:
    """
    Saves a new AI-generated condition report and adjusts vehicle value.
    """
    report = ConditionReport.objects.create(
        vehicle=vehicle,
        area=area,
        photo=photo,
        grade=grade,
        ai_feedback=feedback,
        value_adjustment=impact
    )

    vehicle.current_market_value += impact
    vehicle.save(update_fields=['current_market_value'])

    return report


def upgrade_install_part(upgrade: Upgrade, cost: Optional[Decimal] = None) -> Upgrade:
    """
    Moves a part from Wishlist/Ordered to Installed and logs final cost.
    """
    upgrade.status = 'INSTALLED'
    if cost:
        upgrade.cost = cost
    upgrade.save()
    return upgrade