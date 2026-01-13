from fastapi import APIRouter, UploadFile, File

router = APIRouter()

@router.post("/process")
async def process_ocr(file: UploadFile = File(...)):
    """
    Mock endpoint for OCR processing.
    """
    return {
        "vendor": "AutoZone",
        "date": "2024-01-15",
        "total_cost": 125.50,
        "description": "Oil change and filter replacement",
        "line_items": [
            {"item": "Oil Filter", "price": 15.00},
            {"item": "Synthetic Oil 5qt", "price": 45.00}
        ]
    }
