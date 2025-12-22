from fastapi import FastAPI
from my_garage.api import router as garage_router

app = FastAPI(title="My Garage AI Services", version="1.0.0")

# Mount the specific garage AI logic
app.include_router(garage_router, prefix="/v1/garage", tags=["AI"])

# In your FastAPI logic, you can use 'asgiref' to access Django models
# if needed, though we primarily communicate via HTTP/JSON.