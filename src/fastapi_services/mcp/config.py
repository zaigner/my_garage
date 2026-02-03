from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # The API key is now optional to allow the server to start without it.
    marketcheck_api_key: Optional[str] = None
    
    # Google Gemini configuration
    google_api_key: Optional[str] = None

    # WatchCharts Configuration
    watchcharts_api_key: Optional[str] = None

    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'
        # Ignore extra variables found in the .env file (e.g., Django settings)
        extra = 'ignore'

settings = Settings()
