"""MongoDB utility functions."""
from django.conf import settings
from pymongo import MongoClient
from pymongo.collection import Collection
import logging

logger = logging.getLogger(__name__)

_client = None

def get_client():
    """Get or create MongoDB client."""
    global _client
    if _client is None:
        # Use settings for connection string if available, otherwise default
        mongo_uri = getattr(settings, 'MONGO_URI', 'mongodb://localhost:27017/')
        # Set a shorter timeout for server selection to fail fast if Mongo is down
        # serverSelectionTimeoutMS is in milliseconds (default is 30000ms = 30s)
        _client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
    return _client

def get_db():
    """Get MongoDB database."""
    client = get_client()
    db_name = getattr(settings, 'MONGO_DB_NAME', 'my_garage_docs')
    return client[db_name]

def get_collection(collection_name: str) -> Collection:
    """Get a specific collection."""
    db = get_db()
    return db[collection_name]
