import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class GoogleImageSearchInput(BaseModel):
    query: str = Field(..., description="The search query for the image.")

def search_google_images(query: str) -> Dict[str, Any]:
    """
    Searches Google Images for a given query and returns a list of image URLs.
    Note: This uses a basic scraping approach and may be rate-limited or blocked.
    For production, use the official Google Custom Search JSON API.
    """
    
    # Construct the search URL
    # tbm=isch means "Image Search"
    url = f"https://www.google.com/search?q={query}&tbm=isch"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        image_urls = []
        
        # Google's HTML structure changes, but typically images are in <img> tags
        # In the basic HTML version (which requests often gets), they are simpler.
        # However, with a modern User-Agent, we get complex JS-heavy HTML.
        # A reliable way without JS rendering is to look for 'src' attributes in img tags
        # that start with http.
        
        for img in soup.find_all('img'):
            src = img.get('src')
            # Filter out small icons, base64, or relative paths
            if src and src.startswith('http') and 'google' not in src:
                 image_urls.append(src)
            # Also check data-src which is often used for lazy loading
            data_src = img.get('data-src')
            if data_src and data_src.startswith('http') and 'google' not in data_src:
                image_urls.append(data_src)

        # Limit to top 5 results
        return {"images": image_urls[:5]}

    except Exception as e:
        return {"error": f"Google search failed: {str(e)}"}
