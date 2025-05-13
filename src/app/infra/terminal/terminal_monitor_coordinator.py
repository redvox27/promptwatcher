"""Terminal monitor coordinator implementation."""

import asyncio
import enum
import logging
import os
import sys
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple, Any
from uuid import UUID

# Add src directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))

from src.app.infra.terminal.docker_client import DockerClient
from src.app.infra.terminal.session_detector import TerminalSessionDetector
from src.app.infra.terminal.terminal_device_identifier import TerminalDeviceIdentifier
from src.app.infra.terminal.session_tracking_service import SessionTrackingService, TerminalSession
from src.app.infra.terminal.terminal_output_capture import (
    TerminalOutputCapture, 
    TerminalOutputBuffer,
    TerminalOutputProcessor,
    CaptureResult,
    ProcessingResult
)

logger = logging.getLogger(__name__)


class MonitorStatus(enum.Enum):
    """Status of a terminal monitor."""
    INITIALIZING = "initializing"
    ACTIVE = "active"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class MonitorInfo:
    """Information about a terminal monitor."""
    id: str
    status: MonitorStatus
    start_time: datetime
    stop_time: Optional[datetime] = None
    error: Optional[str] = None
    active_sessions: List[TerminalSession] = field(default_factory=list)
    closed_sessions: List[TerminalSession] = field(default_factory=list)
    prompts_captured: int = 0
    error_count: int = 0
    # Per-session output buffers
    session_buffers: Dict[str, TerminalOutputBuffer] = field(default_factory=dict)
    # Last capture time for each session
    last_capture_time: Dict[str, float] = field(default_factory=dict)
    # Captured Claude conversations by session
    claude_conversations: Dict[str, List[str]] = field(default_factory=dict)


class TerminalMonitorCoordinator:
    """Coordinator for terminal monitoring."""
    
    def __init__(
        self,
        docker_client: DockerClient,
        session_detector: TerminalSessionDetector,
        device_identifier: TerminalDeviceIdentifier,
        tracking_service: SessionTrackingService,
        output_capture: TerminalOutputCapture = None,
        output_processor: TerminalOutputProcessor = None,
        repository_adapter = None,  # Type is ConversationRepositoryAdapter
        settings: Optional[Dict] = None
    ):
        """
        Initialize the terminal monitor coordinator.
        
        Args:
            docker_client: For executing commands on the host
            session_detector: For detecting terminal sessions
            device_identifier: For identifying terminal devices
            tracking_service: For tracking terminal sessions
            output_capture: For capturing terminal output
            output_processor: For processing terminal output
            repository_adapter: For storing conversations in the repository
            settings: Optional configuration settings
        """
        self.docker_client = docker_client
        self.session_detector = session_detector
        self.device_identifier = device_identifier
        self.tracking_service = tracking_service
        self.settings = settings or {}
        self.monitors: Dict[str, MonitorInfo] = {}
        
        # Terminal output capture components
        self.output_capture = output_capture or TerminalOutputCapture(docker_client)
        self.output_processor = output_processor or TerminalOutputProcessor()
        
        # Repository adapter for storing conversations
        self.repository_adapter = repository_adapter
        
        # Configure buffer size and capture interval
        self.buffer_size = self.settings.get("buffer_size", 100000)  # Default: 100KB per session
        self.capture_interval = self.settings.get("capture_interval", 2.0)  # Default: 2 seconds
        
        # Set up event handlers
        self.tracking_service.on_new_session = self.on_new_session
        self.tracking_service.on_session_closed = self.on_session_closed
        self.tracking_service.on_scan_complete = self.on_scan_complete
    
    def start_monitor(self) -> str:
        """
        Start a new terminal monitor.
        
        Returns:
            Monitor ID
        """
        try:
            # Generate a unique ID for this monitor
            monitor_id = str(uuid.uuid4())
            
            # Create monitor info
            monitor = MonitorInfo(
                id=monitor_id,
                status=MonitorStatus.INITIALIZING,
                start_time=datetime.now()
            )
            
            # Add to registry
            self.monitors[monitor_id] = monitor
            
            # Start session tracking
            self.tracking_service.start_tracking()
            
            # Update status
            monitor.status = MonitorStatus.ACTIVE
            
            logger.info(f"Started terminal monitor: {monitor_id}")
            return monitor_id
            
        except Exception as e:
            logger.error(f"Error starting terminal monitor: {str(e)}")
            raise
    
    def stop_monitor(self, monitor_id: str) -> bool:
        """
        Stop a terminal monitor.
        
        Args:
            monitor_id: ID of monitor to stop
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get monitor info
            monitor = self.monitors.get(monitor_id)
            if not monitor:
                logger.warning(f"Monitor not found: {monitor_id}")
                return False
            
            # Stop session tracking
            self.tracking_service.stop_tracking()
            
            # Update status
            monitor.status = MonitorStatus.STOPPED
            monitor.stop_time = datetime.now()
            
            logger.info(f"Stopped terminal monitor: {monitor_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error stopping terminal monitor: {str(e)}")
            return False
    
    def get_monitor_status(self, monitor_id: str) -> Optional[MonitorInfo]:
        """
        Get the status of a monitor.
        
        Args:
            monitor_id: ID of monitor to check
            
        Returns:
            Monitor info or None if not found
        """
        return self.monitors.get(monitor_id)
    
    def get_all_monitors(self) -> List[MonitorInfo]:
        """
        Get all monitors.
        
        Returns:
            List of monitor info objects
        """
        return list(self.monitors.values())
    
    def clear_inactive_monitors(self) -> int:
        """
        Clear inactive monitors from the registry.
        
        Returns:
            Number of monitors cleared
        """
        inactive_ids = [
            monitor_id
            for monitor_id, monitor in self.monitors.items()
            if monitor.status in (MonitorStatus.STOPPED, MonitorStatus.ERROR)
        ]
        
        for monitor_id in inactive_ids:
            del self.monitors[monitor_id]
            
        return len(inactive_ids)
    
    def on_new_session(self, session: TerminalSession) -> None:
        """
        Handle a new terminal session.
        
        Args:
            session: New terminal session
        """
        try:
            # Update monitor with the new session
            for monitor in self.monitors.values():
                if monitor.status == MonitorStatus.ACTIVE:
                    monitor.active_sessions.append(session)
                    logger.info(f"Added session {session.id} to monitor {monitor.id}")
                    
                    # Trigger content capture if implemented
                    asyncio.run(self._capture_session_content(monitor.id, session))
                    
        except Exception as e:
            logger.error(f"Error handling new session: {str(e)}")
    
    def on_session_closed(self, session: TerminalSession) -> None:
        """
        Handle a closed terminal session.
        
        Args:
            session: Closed terminal session
        """
        try:
            # Update monitor with the closed session
            for monitor in self.monitors.values():
                if monitor.status == MonitorStatus.ACTIVE:
                    # Remove from active sessions
                    monitor.active_sessions = [
                        s for s in monitor.active_sessions
                        if s.id != session.id
                    ]
                    
                    # Add to closed sessions
                    monitor.closed_sessions.append(session)
                    logger.info(f"Moved session {session.id} to closed sessions in monitor {monitor.id}")
                    
        except Exception as e:
            logger.error(f"Error handling closed session: {str(e)}")
    
    async def on_scan_complete(self, sessions: List[TerminalSession]) -> None:
        """
        Handle completion of a session scan.
        
        Args:
            sessions: List of active sessions
        """
        try:
            # Update metrics for each monitor
            for monitor in self.monitors.values():
                if monitor.status == MonitorStatus.ACTIVE:
                    logger.debug(f"Monitor {monitor.id}: {len(sessions)} active sessions")
                    
                    # Capture content from each active session
                    for session in sessions:
                        await self._capture_session_content(monitor.id, session)
                    
        except Exception as e:
            logger.error(f"Error handling scan completion: {str(e)}")
            
    async def store_prompt(
        self,
        session_id: str,
        prompt_text: str,
        response_text: str,
        terminal_type: str,
        project_name: str,
        project_goal: str
    ) -> Any:
        """
        Store a prompt record in the repository.
        
        Args:
            session_id: Terminal session ID
            prompt_text: Human prompt text
            response_text: Claude response text
            terminal_type: Type of terminal
            project_name: Name of the project
            project_goal: Goal of the project
            
        Returns:
            Created prompt record
        """
        if self.repository_adapter is None:
            # No repository adapter available
            logger.info(f"No repository adapter available. Would store prompt from session {session_id}: {prompt_text[:50]}...")
            return None
            
        try:
            # Store the conversation using the repository adapter
            result = await self.repository_adapter.store_conversation(
                session_id=session_id,
                prompt_text=prompt_text,
                response_text=response_text,
                terminal_type=terminal_type,
                project_name=project_name,
                project_goal=project_goal
            )
            
            if result:
                logger.info(f"Stored prompt from session {session_id} with ID {result.id}")
            else:
                logger.info(f"Prompt from session {session_id} was not stored (possibly a duplicate)")
                
            return result
            
        except Exception as e:
            logger.error(f"Error storing prompt from session {session_id}: {str(e)}")
            return None
    
    async def _capture_session_content(self, monitor_id: str, session: TerminalSession) -> None:
        """
        Capture content from a terminal session.
        
        Args:
            monitor_id: ID of the monitor
            session: Terminal session to capture from
        """
        try:
            # Get monitor info
            monitor = self.monitors.get(monitor_id)
            if not monitor or monitor.status != MonitorStatus.ACTIVE:
                return
                
            # Create a session buffer if it doesn't exist
            session_id = str(session.id)
            if session_id not in monitor.session_buffers:
                monitor.session_buffers[session_id] = TerminalOutputBuffer(max_size=self.buffer_size)
                logger.info(f"Created output buffer for session {session_id}")
                
            # Check if enough time has passed since the last capture
            current_time = time.time()
            last_capture = monitor.last_capture_time.get(session_id, 0)
            if current_time - last_capture < self.capture_interval:
                return
                
            # Update last capture time
            monitor.last_capture_time[session_id] = current_time
            
            # Get list of terminal devices for this session
            devices = []
            
            # Check if session has terminal_devices attribute (added in tests)
            if hasattr(session, 'terminal_devices') and session.terminal_devices:
                for device in session.terminal_devices:
                    if device.get("is_readable", False):
                        devices.append(device.get("device_path"))
            # Fall back to device_paths from the session
            elif hasattr(session, 'device_paths') and session.device_paths:
                devices = session.device_paths
            
            if not devices:
                logger.debug(f"No readable devices found for session {session_id}")
                return
            
            # Capture output from terminal devices
            results = self.output_capture.capture_multiple(devices, timeout=1.0)
            
            # Process successful captures
            for device_path, result in results.items():
                if not result.is_error and result.content:
                    # Process the raw capture
                    processing_result = self.output_processor.process_raw_capture(result.content)
                    
                    # Append cleaned content to the buffer
                    buffer = monitor.session_buffers[session_id]
                    buffer.append(processing_result.clean_text)
                    
                    # Check for Claude conversations
                    if processing_result.contains_claude_conversation:
                        if session_id not in monitor.claude_conversations:
                            monitor.claude_conversations[session_id] = []
                        
                        # Add new conversations to the list
                        for conversation in processing_result.claude_conversations:
                            # Only add if not already captured (simple duplicate detection)
                            if not any(conversation in conv for conv in monitor.claude_conversations[session_id]):
                                monitor.claude_conversations[session_id].append(conversation)
                                monitor.prompts_captured += 1
                                logger.info(f"Captured Claude conversation from session {session_id}")
                                
                                # Extract human and Claude messages
                                try:
                                    human_prompt, claude_response = self.output_processor.extract_message_pair(conversation)
                                    
                                    # Record the prompt in the repository if we have a repository adapter
                                    if self.repository_adapter:
                                        prompt_record = await self.store_prompt(
                                            session_id=session_id,
                                            prompt_text=human_prompt,
                                            response_text=claude_response,
                                            terminal_type=session.terminal_type or "terminal",
                                            project_name=self.settings.get("project_name", "Unknown"),
                                            project_goal=self.settings.get("project_goal", "")
                                        )
                                        
                                        if prompt_record:
                                            logger.info(f"Extracted and stored prompt for session {session_id}")
                                        else:
                                            logger.info(f"Extracted but did not store prompt for session {session_id} (possibly a duplicate)")
                                    else:
                                        logger.info(f"Extracted prompt for session {session_id} but no repository adapter available")
                                        
                                except Exception as e:
                                    logger.error(f"Error extracting or storing message pair: {str(e)}")
                    
            logger.debug(f"Captured and processed content from {len(results)} devices for session {session_id}")
                
        except Exception as e:
            logger.error(f"Error capturing session content: {str(e)}")
            if monitor:
                monitor.error_count += 1