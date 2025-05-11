"""Routes for handling terminal monitors."""

import logging
import sys
from typing import Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel

from app.infra.terminal.monitor import TerminalMonitorManager, MockPromptCaptureService
from app.presentation.deps import get_services, get_settings, get_templates

logger = logging.getLogger(__name__)

class MonitorResponse(BaseModel):
    """Response for monitor operations."""
    
    message: str
    status: str = "success"


router = APIRouter()


def get_monitor_manager(request: Request) -> TerminalMonitorManager:
    """Get terminal monitor manager."""
    services = get_services(request)
    return services.terminal_monitor_manager


def get_mock_service(request: Request) -> MockPromptCaptureService:
    """Get the mock prompt capture service."""
    services = get_services(request)
    logger.info(f"Service type: {type(services.prompt_capture_service)}")
    return services.prompt_capture_service


@router.post("/api/monitors/mock", response_model=MonitorResponse)
async def generate_mock_data(
    request: Request,
    count: int = Query(5, ge=1, le=100),
    monitor_manager: TerminalMonitorManager = Depends(get_monitor_manager),
):
    """
    Generate mock prompt data.
    
    Args:
        request: FastAPI request
        count: Number of mock records to generate
        monitor_manager: Terminal monitor manager
        
    Returns:
        Status message
    """
    logger.info(f"Generating {count} mock records")
    
    try:
        await monitor_manager.generate_mock_data(count)
        return MonitorResponse(
            message=f"Generated {count} mock prompt records"
        )
    except Exception as e:
        logger.error(f"Error generating mock data: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))




@router.delete("/api/monitors", response_model=MonitorResponse)
async def stop_all_monitors(
    request: Request,
    monitor_manager: TerminalMonitorManager = Depends(get_monitor_manager),
):
    """
    Stop all monitors.
    
    Args:
        request: FastAPI request
        monitor_manager: Terminal monitor manager
        
    Returns:
        Status message
    """
    try:
        await monitor_manager.stop_all()
        return MonitorResponse(message="All monitors stopped")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))




@router.post("/api/monitors/submit", response_model=MonitorResponse)
async def submit_prompt(
    request: Request,
    prompt_text: str,
    response_text: str,
    mock_service: MockPromptCaptureService = Depends(get_mock_service),
):
    """
    Submit a prompt and response pair directly.
    
    Args:
        request: FastAPI request
        prompt_text: Claude prompt text
        response_text: Claude response text
        mock_service: Mock service for capturing prompts
        
    Returns:
        Status message
    """
    logger.info("Received direct prompt submission")
    
    try:
        # Get the settings for project info
        settings = get_settings(request)
        
        # Create a new prompt record
        record = await mock_service.capture_prompt(
            prompt_text=prompt_text,
            response_text=response_text,
            project_name=settings.PROJECT_NAME,
            project_goal=settings.PROJECT_GOAL,
            terminal_type="Direct API Submission",
        )
        
        return MonitorResponse(
            message=f"Prompt captured successfully with ID: {record.id}"
        )
    except Exception as e:
        logger.error(f"Error capturing prompt: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))