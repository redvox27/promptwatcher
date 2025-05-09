"""Application bootstrap module."""

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.infra.opensearch.client import OpenSearchClient
from app.infra.services_container import Services
from app.presentation.routes import get_routes
from app.settings import Settings

logger = logging.getLogger(__name__)

# Global app state for accessing resources in other modules
app_state: dict = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager for startup/shutdown events."""
    settings = app.state.settings
    logger.info("Starting application...")
    
    try:
        # Create OpenSearch client with retry logic
        logger.info(f"Connecting to OpenSearch at {settings.OPENSEARCH_HOST}:{settings.OPENSEARCH_PORT}")
        opensearch_client = await OpenSearchClient.create_client(settings)
        
        # Initialize OpenSearch indices
        logger.info("Initializing OpenSearch indices")
        await OpenSearchClient.create_indices(opensearch_client)
        
        # Create services container
        services = Services(
            settings=settings,
            opensearch_client=opensearch_client,
            use_mock=settings.DEBUG
        )
        
        # Store in app state
        app.state.opensearch_client = opensearch_client
        app.state.services = services
        
        # Store for global access
        app_state["settings"] = settings
        app_state["opensearch_client"] = opensearch_client
        app_state["services"] = services
        
        logger.info("Application started successfully")
        yield
    except Exception as e:
        logger.error(f"Error during startup: {e}")
        raise
    finally:
        logger.info("Shutting down application...")
        # Clean up resources if needed
        
        # Clear app state on shutdown
        app_state.clear()


def create_app(settings: Optional[Settings] = None) -> FastAPI:
    """
    Create FastAPI application.
    
    Args:
        settings: Application settings
        
    Returns:
        FastAPI application
    """
    if settings is None:
        settings = Settings()
    
    # Create FastAPI application
    app = FastAPI(
        title="PromptWatcher API",
        description="API for capturing and analyzing Claude prompts",
        version="0.1.0",
        lifespan=lifespan
    )
    
    # Set up templates
    templates_dir = settings.TEMPLATES_DIR
    templates = Jinja2Templates(directory=str(templates_dir))
    
    # Make resources available in app state
    app.state.settings = settings
    app.state.templates = templates
    
    # Include routes
    for route in get_routes():
        app.include_router(route)
    
    # Mount static files
    # Look for static files in multiple possible locations to handle both development and production
    static_dirs = [
        Path(__file__).parent.parent.parent.parent / "static",  # /static (root directory)
        Path(__file__).parent.parent.parent / "static",         # /src/static
    ]
    
    # Use the first directory that exists
    static_dir = next((d for d in static_dirs if d.exists()), None)
    
    if static_dir:
        logger.info(f"Mounting static files from: {static_dir}")
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    else:
        logger.warning("No static directory found! Static files will not be available.")
    
    return app