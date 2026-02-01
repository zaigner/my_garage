import pytesseract
import re
from fastapi import APIRouter, UploadFile, File, HTTPException
from PIL import Image, ImageEnhance
import io
from datetime import datetime
from typing import Dict, Any, List, Optional

router = APIRouter()

def preprocess_image(image: Image.Image) -> Image.Image:
    """
    Basic preprocessing to improve OCR accuracy.
    Converts to grayscale and increases contrast.
    """
    # Convert to grayscale
    image = image.convert('L')
    
    # Increase contrast
    enhancer = ImageEnhance.Contrast(image)
    image = enhancer.enhance(1.5)
    
    return image

def extract_price_from_line(line: str) -> Optional[float]:
    """
    Attempts to extract a price from the end of a line.
    Returns float or None.
    Matches formats like: 10.99, $10.99, 1,000.00, 10.99 T
    """
    # Regex for price at the end of the line
    # Group 1: The number
    price_pattern = r'(?:\$)?\s*(\d{1,3}(?:,\d{3})*\.\d{2})(?:\s*[A-Za-z]{1,2})?$'
    match = re.search(price_pattern, line.strip())
    if match:
        try:
            return float(match.group(1).replace(',', ''))
        except ValueError:
            return None
    return None

def parse_receipt_data(text: str) -> Dict[str, Any]:
    """
    Wholistic parsing of receipt text to extract vendor, date, total, and line items.
    """
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    
    data = {
        "vendor": "Unknown Vendor",
        "date": datetime.now().strftime("%Y-%m-%d"),
        "total_cost": 0.0,
        "description": "Service Receipt",
        "line_items": []
    }

    if not lines:
        return data

    # 1. Vendor Extraction
    # Heuristic: The first non-empty line is usually the vendor.
    # We skip lines that are just dates or purely numeric.
    for line in lines[:3]:
        if len(line) > 3 and not re.match(r'^[\d\W]+$', line):
            data["vendor"] = line
            break

    # 2. Date Extraction
    # Scan all lines for common date patterns
    date_patterns = [
        r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b",  # 01/15/2024
        r"\b(\d{4}[/-]\d{1,2}[/-]\d{1,2})\b",    # 2024-01-15
        r"\b(\w{3}\s\d{1,2},?\s\d{4})\b",        # Jan 15, 2024
        r"\b(\d{1,2}\s\w{3}\s\d{4})\b"           # 15 Jan 2024
    ]
    
    for line in lines:
        found_date = False
        for pattern in date_patterns:
            match = re.search(pattern, line)
            if match:
                # In a real app, we would parse this to YYYY-MM-DD
                # For now, we just return the string found
                data["date"] = match.group(1)
                found_date = True
                break
        if found_date:
            break

    # 3. Line Items and Total Analysis
    potential_items = []
    explicit_total = 0.0
    max_price_found = 0.0
    
    # Keywords that suggest a line is a summary/payment info, not a service item
    summary_keywords = [
        'total', 'subtotal', 'tax', 'amount due', 'balance', 
        'change', 'cash', 'credit', 'visa', 'mastercard', 'amex', 'payment'
    ]
    
    # Keywords specifically for the Grand Total
    total_keywords = ['total', 'amount due', 'balance due', 'grand total']

    for line in lines:
        line_lower = line.lower()
        price = extract_price_from_line(line)
        
        if price is not None:
            # Track the maximum price found on the receipt (fallback for total)
            if price > max_price_found:
                max_price_found = price

            # Check if this is an explicit total line
            if any(keyword in line_lower for keyword in total_keywords):
                # If we find multiple "totals", we usually want the largest one (e.g. Total vs Subtotal)
                # But strictly speaking, "Total" usually comes after "Subtotal".
                # We'll trust the label.
                if price > explicit_total:
                    explicit_total = price
            
            # Check if it's a summary line (tax, subtotal, payment, etc.)
            is_summary = any(keyword in line_lower for keyword in summary_keywords)
            
            if not is_summary:
                # It's likely a line item
                # Extract description by removing the price part
                # Re-match to find where the price starts to slice the string
                match = re.search(r'(?:\$)?\s*(\d{1,3}(?:,\d{3})*\.\d{2})(?:\s*[A-Za-z]{1,2})?$', line)
                if match:
                    desc = line[:match.start()].strip()
                    # Filter out short garbage or pure numbers
                    if len(desc) > 2 and not re.match(r'^[\d\W]+$', desc):
                        potential_items.append({"item": desc, "price": price})

    # 4. Determine Final Total
    # Priority: Explicit "Total" label > Max price found
    if explicit_total > 0:
        data["total_cost"] = explicit_total
    elif max_price_found > 0:
        data["total_cost"] = max_price_found
    
    # 5. Assign Line Items
    data["line_items"] = potential_items
    
    # 6. Generate Smart Description
    # If we found line items, use the most expensive ones to describe the service
    if potential_items:
        # Sort by price descending
        sorted_items = sorted(potential_items, key=lambda x: x['price'], reverse=True)
        # Take top 2 items
        top_items = [item['item'] for item in sorted_items[:2]]
        data["description"] = ", ".join(top_items)
    else:
        # Fallback: Keyword matching on the full text
        full_text = "\n".join(lines).lower()
        if "oil" in full_text:
            data["description"] = "Oil Change / Fluid Service"
        elif "tire" in full_text:
            data["description"] = "Tire Service"
        elif "brake" in full_text:
            data["description"] = "Brake Service"
        elif "battery" in full_text:
            data["description"] = "Battery Replacement"
        elif "inspection" in full_text:
            data["description"] = "Vehicle Inspection"

    return data

@router.post("/process")
async def process_ocr(file: UploadFile = File(...)):
    """
    Processes an uploaded image file with OCR and returns the extracted text.
    """
    try:
        # Read the image file
        image_data = await file.read()
        image = Image.open(io.BytesIO(image_data))
        
        # Preprocess image
        processed_image = preprocess_image(image)
        
        # Use pytesseract to extract text
        text = pytesseract.image_to_string(processed_image)
        
        # Parse the text to extract structured data
        data = parse_receipt_data(text)
        data["raw_text"] = text
        
        return data

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OCR processing failed: {e}")
