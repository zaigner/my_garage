import pytesseract
import re
from fastapi import APIRouter, UploadFile, File, HTTPException
from PIL import Image
import io

router = APIRouter()

def parse_total_cost(text: str) -> float:
    """
    Parses the total cost from the OCR text using regular expressions.
    """
    # Look for lines containing "Total" or "Amount Due" and a dollar amount
    match = re.search(r"(?i)(?:total|amount due)\s*[:\s]*\$?(\d+\.\d{2})", text)
    if match:
        return float(match.group(1))
    return 0.0

@router.post("/process")
async def process_ocr(file: UploadFile = File(...)):
    """
    Processes an uploaded image file with OCR and returns the extracted text.
    """
    try:
        # Read the image file
        image_data = await file.read()
        image = Image.open(io.BytesIO(image_data))
        
        # Use pytesseract to extract text
        text = pytesseract.image_to_string(image)
        
        # Parse the text to extract structured data
        total_cost = parse_total_cost(text)
        
        return {
            "raw_text": text,
            "vendor": "AutoZone (mock)",
            "date": "2024-01-15 (mock)",
            "total_cost": total_cost,
            "description": "Oil change and filter replacement (mock)",
            "line_items": [
                {"item": "Oil Filter", "price": 15.00},
                {"item": "Synthetic Oil 5qt", "price": 45.00}
            ]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OCR processing failed: {e}")
