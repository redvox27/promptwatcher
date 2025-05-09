"""Main entry point for the application."""

import logging
import os

import uvicorn

from app.bootstrap import create_app
from app.settings import Settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

# Create application
settings = Settings()
app = create_app(settings)

if __name__ == "__main__":
    """Run the application using uvicorn."""
    uvicorn.run(
        "main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000")),
        reload=settings.DEBUG,
    )