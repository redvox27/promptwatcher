"""Terminal session tracking service implementation."""

import asyncio
import logging
import os
import sys
import uuid
from datetime import datetime
from typing import Callable, Dict, List, Optional, Set

# Add src directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))

from src.app.infra.terminal.session_detector import TerminalSessionDetector
from src.app.infra.terminal.terminal_device_identifier import TerminalDeviceIdentifier

logger = logging.getLogger(__name__)


class TerminalSession:
    """Data class representing a terminal session."""

    def __init__(
        self,
        id: str,
        pid: int,
        user: str,
        command: str,
        terminal: str,
        start_time: datetime,
        device_paths: List[str] = None,
        terminal_type: str = "unknown",
        is_readable: bool = False,
        last_active: datetime = None,
        metadata: Dict = None
    ):
        """
        Initialize a terminal session.
        
        Args:
            id: Unique identifier for the session
            pid: Process ID
            user: Username
            command: Command running in the terminal
            terminal: Terminal identifier (e.g., pts/0)
            start_time: When the session was first detected
            device_paths: List of associated device paths
            terminal_type: Type of terminal (e.g., xterm, vt100)
            is_readable: Whether the terminal is readable
            last_active: When the session was last active
            metadata: Additional metadata about the session
        """
        self.id = id
        self.pid = pid
        self.user = user
        self.command = command
        self.terminal = terminal
        self.start_time = start_time
        self.device_paths = device_paths or []
        self.terminal_type = terminal_type
        self.is_readable = is_readable
        self.last_active = last_active or start_time
        self.metadata = metadata or {}
        self.is_active = True


class SessionTrackingService:
    """Service for tracking terminal sessions over time."""
    
    def __init__(
        self,
        session_detector: TerminalSessionDetector,
        device_identifier: TerminalDeviceIdentifier,
        scan_interval: float = 5.0
    ):
        """
        Initialize the session tracking service.
        
        Args:
            session_detector: For detecting terminal sessions
            device_identifier: For identifying terminal devices
            scan_interval: Interval between scans in seconds
        """
        self.session_detector = session_detector
        self.device_identifier = device_identifier
        self.scan_interval = scan_interval
        self._sessions: Dict[str, TerminalSession] = {}
        self._tracking_task = None
        self.is_active = False
        
        # Event handlers
        self.on_new_session: Optional[Callable[[TerminalSession], None]] = None
        self.on_session_closed: Optional[Callable[[TerminalSession], None]] = None
        self.on_scan_complete: Optional[Callable[[List[TerminalSession]], None]] = None
    
    def start_tracking(self) -> None:
        """Start tracking terminal sessions."""
        if self.is_active:
            logger.warning("Session tracking is already active")
            return
            
        logger.info("Starting terminal session tracking")
        self.is_active = True
        self._tracking_task = asyncio.create_task(self._tracking_loop())
    
    def stop_tracking(self) -> None:
        """Stop tracking terminal sessions."""
        if not self.is_active:
            logger.warning("Session tracking is not active")
            return
            
        logger.info("Stopping terminal session tracking")
        self.is_active = False
        if self._tracking_task:
            self._tracking_task.cancel()
            self._tracking_task = None
    
    async def _tracking_loop(self) -> None:
        """Main tracking loop for continuous monitoring."""
        try:
            while self.is_active:
                try:
                    # Scan for sessions
                    self.scan_sessions()
                    
                    # Notify listeners of scan completion
                    if self.on_scan_complete:
                        await asyncio.to_thread(
                            self.on_scan_complete,
                            self.get_all_sessions()
                        )
                except Exception as e:
                    logger.error(f"Error in session tracking loop: {str(e)}")
                
                # Wait for the next scan interval
                await asyncio.sleep(self.scan_interval)
        except asyncio.CancelledError:
            logger.info("Session tracking loop cancelled")
        except Exception as e:
            logger.error(f"Unexpected error in session tracking loop: {str(e)}")
            raise
    
    def scan_sessions(self) -> None:
        """
        Scan for terminal sessions and update the tracking registry.
        
        This identifies new sessions, updates existing ones, and
        detects closed sessions.
        """
        try:
            # Get current set of terminal sessions
            current_sessions = self.session_detector.list_terminal_sessions(interactive_only=True)
            
            # Track PIDs for change detection
            current_pids = set(session["pid"] for session in current_sessions)
            previous_pids = set(session.pid for session in self._sessions.values())
            
            # Identify new sessions
            new_pids = current_pids - previous_pids
            closed_pids = previous_pids - current_pids
            
            # Process new sessions
            for session_data in current_sessions:
                pid = session_data.get("pid")
                if pid in new_pids:
                    self._add_new_session(session_data)
                elif pid in current_pids:
                    self._update_session(pid, session_data)
            
            # Process closed sessions
            for pid in closed_pids:
                self._close_session(pid)
            
            logger.debug(f"Session scan complete: {len(self._sessions)} active sessions")
            
        except Exception as e:
            logger.error(f"Error scanning sessions: {str(e)}")
    
    def _add_new_session(self, session_data: Dict) -> None:
        """
        Add a new session to the registry.
        
        Args:
            session_data: Session data from detector
        """
        try:
            pid = session_data.get("pid")
            user = session_data.get("user", "unknown")
            command = session_data.get("command", "")
            terminal = session_data.get("terminal", "?")
            
            # Format terminal path
            terminal_path = terminal
            if terminal != "?" and not terminal.startswith("/dev/"):
                terminal_path = f"/dev/{terminal}"
            
            # Get terminal device information
            device_info = self.device_identifier.get_terminal_devices(pid)
            device_paths = [device["device_path"] for device in device_info]
            
            # If no specific devices were found but we have a terminal, add it
            if not device_paths and terminal_path.startswith("/dev/"):
                device_paths = [terminal_path]
            
            # Get terminal type and check if it's readable
            terminal_type = "unknown"
            is_readable = False
            
            if device_paths:
                # Use the first device for type detection
                terminal_type = self.device_identifier.get_terminal_type(device_paths[0]) or "unknown"
                is_readable = self.device_identifier.is_terminal_readable(device_paths[0])
            
            # Create a new session object
            session_id = str(uuid.uuid4())
            session = TerminalSession(
                id=session_id,
                pid=pid,
                user=user,
                command=command,
                terminal=terminal,
                start_time=datetime.now(),
                device_paths=device_paths,
                terminal_type=terminal_type,
                is_readable=is_readable
            )
            
            # Add to registry
            self._sessions[session_id] = session
            
            logger.info(f"New terminal session detected: PID={pid}, User={user}, Terminal={terminal}")
            
            # Notify listeners
            if self.on_new_session:
                self.on_new_session(session)
                
        except Exception as e:
            logger.error(f"Error adding new session: {str(e)}")
    
    def _update_session(self, pid: int, session_data: Dict) -> None:
        """
        Update an existing session in the registry.
        
        Args:
            pid: Process ID to update
            session_data: New session data
        """
        try:
            # Find the session by PID
            session = None
            for s in self._sessions.values():
                if s.pid == pid:
                    session = s
                    break
            
            if not session:
                return
            
            # Update basic fields
            session.command = session_data.get("command", session.command)
            session.terminal = session_data.get("terminal", session.terminal)
            session.user = session_data.get("user", session.user)
            
            # Update last_active timestamp
            session.last_active = datetime.now()
            
            # Check if terminal is still readable
            if session.device_paths:
                session.is_readable = self.device_identifier.is_terminal_readable(session.device_paths[0])
            
            logger.debug(f"Updated terminal session: PID={pid}")
            
        except Exception as e:
            logger.error(f"Error updating session PID={pid}: {str(e)}")
    
    def _close_session(self, pid: int) -> None:
        """
        Mark a session as closed.
        
        Args:
            pid: Process ID to close
        """
        try:
            # Find the session by PID
            session_id = None
            session = None
            
            for sid, s in self._sessions.items():
                if s.pid == pid:
                    session_id = sid
                    session = s
                    break
            
            if not session:
                return
            
            # Mark as inactive
            session.is_active = False
            
            # Remove from active sessions
            del self._sessions[session_id]
            
            logger.info(f"Terminal session closed: PID={pid}, User={session.user}, Terminal={session.terminal}")
            
            # Notify listeners
            if self.on_session_closed:
                self.on_session_closed(session)
                
        except Exception as e:
            logger.error(f"Error closing session PID={pid}: {str(e)}")
    
    def get_all_sessions(self) -> List[TerminalSession]:
        """
        Get all currently tracked sessions.
        
        Returns:
            List of terminal sessions
        """
        return list(self._sessions.values())
    
    def get_session(self, session_id: str) -> Optional[TerminalSession]:
        """
        Get a specific session by ID.
        
        Args:
            session_id: Session ID to retrieve
            
        Returns:
            Terminal session or None if not found
        """
        return self._sessions.get(session_id)