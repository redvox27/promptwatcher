"""Dependencies for FastAPI routes."""

from fastapi import Depends, Request
from fastapi.templating import Jinja2Templates

from app.domain.repositories import PromptRepository
from app.domain.services import PromptCaptureService
from app.infra.services_container import Services
from app.settings import Settings


def get_settings(request: Request) -> Settings:
    """
    Get application settings.
    
    Args:
        request: FastAPI request
        
    Returns:
        Application settings
    """
    return request.app.state.settings


def get_templates(request: Request) -> Jinja2Templates:
    """
    Get Jinja2 templates.
    
    Args:
        request: FastAPI request
        
    Returns:
        Jinja2 templates
    """
    return request.app.state.templates


def get_services(request: Request) -> Services:
    """
    Get services container.
    
    Args:
        request: FastAPI request
        
    Returns:
        Services container
    """
    return request.app.state.services


def get_prompt_repository(services: Services = Depends(get_services)) -> PromptRepository:
    """
    Get prompt repository.
    
    Args:
        services: Services container
        
    Returns:
        Prompt repository
    """
    return services.prompt_repository


def get_prompt_capture_service(services: Services = Depends(get_services)) -> PromptCaptureService:
    """
    Get prompt capture service.
    
    Args:
        services: Services container
        
    Returns:
        Prompt capture service
    """
    return services.prompt_capture_service