"""Routes for handling terminal monitors."""

import logging
import sys
import time
from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from app.infra.terminal.monitor import TerminalMonitorManager, MockPromptCaptureService
from app.presentation.deps import get_services, get_settings, get_templates

logger = logging.getLogger(__name__)

class MonitorResponse(BaseModel):
    """Response for monitor operations."""
    
    message: str
    status: str = "success"


class MonitorStatusInfo(BaseModel):
    """Status information for a monitor."""
    
    id: str
    status: str
    start_time: str
    active_sessions: int
    prompts_captured: int


class MonitorStatusResponse(BaseModel):
    """Response for monitor status."""
    
    active: bool
    stats: Dict[str, object]
    monitors: List[MonitorStatusInfo]


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


@router.get("/monitoring", response_class=HTMLResponse)
async def monitoring_dashboard(request: Request, templates=Depends(get_templates)):
    """Render the monitoring dashboard page."""
    return templates.TemplateResponse("monitoring/dashboard.html", {"request": request})


@router.get("/api/monitors/ui/status", response_class=HTMLResponse)
async def get_monitor_status_ui(
    request: Request,
    monitor_manager: TerminalMonitorManager = Depends(get_monitor_manager),
    templates=Depends(get_templates)
):
    """
    Get HTML representation of monitoring status.
    
    Args:
        request: FastAPI request
        monitor_manager: Terminal monitor manager
        templates: Jinja2 templates
        
    Returns:
        HTML for monitoring status
    """
    # Get status data
    monitor_statuses = await monitor_manager.get_all_statuses()
    
    # Calculate summary statistics
    is_active = len(monitor_statuses) > 0
    active_sessions_count = sum(m.get("active_sessions", 0) for m in monitor_statuses)
    prompts_captured_count = sum(m.get("prompts_captured", 0) for m in monitor_statuses)
    
    # Get uptime from the first monitor (if any)
    uptime = "0 minutes"
    if monitor_statuses:
        first_monitor = monitor_statuses[0]
        if isinstance(first_monitor.get("start_time"), str):
            try:
                start_time = datetime.fromisoformat(first_monitor["start_time"])
                delta = datetime.now() - start_time
                uptime = f"{delta.total_seconds() // 60:.0f} minutes"
            except (ValueError, TypeError):
                # If start_time is a timestamp
                try:
                    start_timestamp = float(first_monitor["start_time"])
                    delta_seconds = time.time() - start_timestamp
                    uptime = f"{delta_seconds // 60:.0f} minutes"
                except (ValueError, TypeError):
                    pass
    
    # Format monitor statuses for the template
    formatted_monitors = []
    for status in monitor_statuses:
        # Convert timestamps to ISO format if needed
        start_time = status.get("start_time", "")
        if not isinstance(start_time, str):
            try:
                start_time = datetime.fromtimestamp(start_time).isoformat()
            except (ValueError, TypeError, OverflowError):
                start_time = datetime.now().isoformat()
        
        formatted_monitors.append({
            "id": status.get("id", "unknown"),
            "status": status.get("status", "unknown"),
            "start_time": start_time,
            "active_sessions": status.get("active_sessions", 0),
            "prompts_captured": status.get("prompts_captured", 0)
        })
    
    # Create context for template
    context = {
        "request": request,
        "active": is_active,
        "stats": {
            "monitors_count": len(monitor_statuses),
            "active_sessions": active_sessions_count,
            "total_prompts_captured": prompts_captured_count,
            "uptime": uptime
        },
        "monitors": formatted_monitors
    }
    
    return templates.TemplateResponse("partials/monitor_status.html", context)


@router.get("/api/monitors/status", response_model=MonitorStatusResponse)
async def get_monitor_status(
    request: Request,
    monitor_manager: TerminalMonitorManager = Depends(get_monitor_manager),
):
    """
    Get current monitoring status.
    
    Args:
        request: FastAPI request
        monitor_manager: Terminal monitor manager
        
    Returns:
        Current monitoring status and statistics
    """
    logger.info("Status request received")
    
    # Get status of all monitors
    monitor_statuses = await monitor_manager.get_all_statuses()
    
    # Calculate summary statistics
    is_active = len(monitor_statuses) > 0
    active_sessions_count = sum(m.get("active_sessions", 0) for m in monitor_statuses)
    prompts_captured_count = sum(m.get("prompts_captured", 0) for m in monitor_statuses)
    
    # Get uptime from the first monitor (if any)
    uptime = "0 minutes"
    if monitor_statuses:
        first_monitor = monitor_statuses[0]
        if isinstance(first_monitor.get("start_time"), str):
            try:
                start_time = datetime.fromisoformat(first_monitor["start_time"])
                delta = datetime.now() - start_time
                uptime = f"{delta.total_seconds() // 60:.0f} minutes"
            except (ValueError, TypeError):
                # If start_time is a timestamp
                try:
                    start_timestamp = float(first_monitor["start_time"])
                    delta_seconds = time.time() - start_timestamp
                    uptime = f"{delta_seconds // 60:.0f} minutes"
                except (ValueError, TypeError):
                    pass
    
    # Format monitor statuses for response
    formatted_monitors = []
    for status in monitor_statuses:
        # Convert timestamps to ISO format if needed
        start_time = status.get("start_time", "")
        if not isinstance(start_time, str):
            try:
                start_time = datetime.fromtimestamp(start_time).isoformat()
            except (ValueError, TypeError, OverflowError):
                start_time = datetime.now().isoformat()
        
        formatted_monitors.append(MonitorStatusInfo(
            id=status.get("id", "unknown"),
            status=status.get("status", "unknown"),
            start_time=start_time,
            active_sessions=status.get("active_sessions", 0),
            prompts_captured=status.get("prompts_captured", 0)
        ))
    
    # Construct the response
    return MonitorStatusResponse(
        active=is_active,
        stats={
            "monitors_count": len(monitor_statuses),
            "active_sessions": active_sessions_count,
            "total_prompts_captured": prompts_captured_count,
            "uptime": uptime
        },
        monitors=formatted_monitors
    )


@router.post("/api/monitors/start", response_model=MonitorResponse)
async def start_monitor(
    request: Request,
    monitor_manager: TerminalMonitorManager = Depends(get_monitor_manager),
):
    """
    Start the prompt monitor.
    
    Args:
        request: FastAPI request
        monitor_manager: Terminal monitor manager
        
    Returns:
        Status message
    """
    logger.info("Start monitor requested")
    
    try:
        # Start a new monitor
        monitor_id = await monitor_manager.start_monitor()
        logger.info(f"Started monitor with ID {monitor_id}")
        
        return MonitorResponse(
            message=f"Monitor started successfully with ID {monitor_id}"
        )
    except Exception as e:
        logger.error(f"Error starting monitor: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/monitors/ui/sessions", response_class=HTMLResponse)
async def get_sessions_ui(
    request: Request,
    monitor_manager: TerminalMonitorManager = Depends(get_monitor_manager),
    templates=Depends(get_templates)
):
    """
    Get HTML representation of terminal sessions.
    
    Args:
        request: FastAPI request
        monitor_manager: Terminal monitor manager
        templates: Jinja2 templates
        
    Returns:
        HTML for terminal sessions
    """
    try:
        # Get active sessions
        sessions = []
        device_readable_map = {}
        
        if monitor_manager.coordinator:
            # Get active sessions from the tracking service
            tracking_service = monitor_manager.tracking_service
            raw_sessions = tracking_service.get_all_sessions()
            
            # Format sessions for the template
            for session in raw_sessions:
                devices = session.device_paths if hasattr(session, 'device_paths') else []
                
                # Check if each device is readable
                for device in devices:
                    if hasattr(session, 'is_readable'):
                        device_readable_map[device] = session.is_readable
                    else:
                        device_readable_map[device] = False
                
                # Create formatted session info
                sessions.append({
                    "id": session.id,
                    "pid": session.pid,
                    "user": session.user,
                    "command": session.command,
                    "terminal": session.terminal,
                    "device_paths": devices,
                    "is_readable": getattr(session, 'is_readable', False),
                    "is_active": True,
                    "start_time": session.start_time.isoformat() if hasattr(session, 'start_time') else ""
                })
        
        # Sort sessions by PID
        sessions.sort(key=lambda s: s.get("pid", 0))
        
        # Create context for template
        context = {
            "request": request,
            "sessions": sessions,
            "device_readable_map": device_readable_map
        }
        
        return templates.TemplateResponse("partials/session_list.html", context)
        
    except Exception as e:
        logger.error(f"Error getting terminal sessions: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        
        # Return error message
        return f"""
        <div class="bg-red-50 p-4 rounded border border-red-300">
            <p class="text-center text-red-800">Error retrieving terminal sessions: {str(e)}</p>
        </div>
        """


@router.post("/api/monitors/sessions/{session_id}/capture", response_model=MonitorResponse)
async def capture_session(
    request: Request,
    session_id: str,
    monitor_manager: TerminalMonitorManager = Depends(get_monitor_manager),
):
    """
    Trigger a capture for a specific session.
    
    Args:
        request: FastAPI request
        session_id: Session ID to capture
        monitor_manager: Terminal monitor manager
        
    Returns:
        Status message
    """
    logger.info(f"Capture requested for session {session_id}")
    
    try:
        if monitor_manager.coordinator:
            # Get the first monitor ID
            monitor_statuses = await monitor_manager.get_all_statuses()
            if not monitor_statuses:
                return MonitorResponse(
                    message="No active monitors found",
                    status="error"
                )
                
            monitor_id = monitor_statuses[0]["id"]
            
            # Find the session in the tracking service
            tracking_service = monitor_manager.tracking_service
            session = tracking_service.get_session(session_id)
            
            if not session:
                return MonitorResponse(
                    message=f"Session with ID {session_id} not found",
                    status="error"
                )
                
            # Manually trigger capture for this session
            await monitor_manager.coordinator._capture_session_content(monitor_id, session)
            
            return MonitorResponse(
                message=f"Capture triggered for session {session_id}"
            )
        else:
            return MonitorResponse(
                message="Terminal monitoring coordinator not available",
                status="error"
            )
    except Exception as e:
        logger.error(f"Error capturing session {session_id}: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return MonitorResponse(
            message=f"Error capturing session: {str(e)}",
            status="error"
        )


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
    logger.info("Stop monitor requested (stub)")
    
    try:
        await monitor_manager.stop_all()
        logger.info("All monitors stopped successfully")
        return MonitorResponse(message="All monitors stopped")
    except Exception as e:
        logger.error(f"Error stopping monitors: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
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