"""Unit tests for terminal session tracking service."""

import asyncio
import os
import sys
import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

# Add the src directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

from src.app.infra.terminal.session_detector import TerminalSessionDetector
from src.app.infra.terminal.terminal_device_identifier import TerminalDeviceIdentifier
from src.app.infra.terminal.session_tracking_service import SessionTrackingService, TerminalSession


class TestSessionTrackingService(unittest.TestCase):
    """Test cases for the session tracking service."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_session_detector = MagicMock(spec=TerminalSessionDetector)
        self.mock_device_identifier = MagicMock(spec=TerminalDeviceIdentifier)
        self.tracking_service = SessionTrackingService(
            self.mock_session_detector,
            self.mock_device_identifier,
            scan_interval=0.1  # Fast interval for testing
        )

    def test_start_stop_tracking(self):
        """Test starting and stopping session tracking."""
        # Create a test coroutine to use in place of the real _tracking_loop
        async def test_coro():
            pass
        
        # Patch asyncio.create_task
        with patch('asyncio.create_task') as mock_create_task:
            mock_task = MagicMock()
            mock_create_task.return_value = mock_task
            
            # Start tracking
            self.tracking_service.start_tracking()
            
            # Verify task creation
            mock_create_task.assert_called_once()
            self.assertTrue(self.tracking_service.is_active)
            
            # Stop tracking
            self.tracking_service.stop_tracking()
            
            # Verify task cancellation
            mock_task.cancel.assert_called_once()
            self.assertFalse(self.tracking_service.is_active)

    def test_get_all_sessions(self):
        """Test getting all tracked sessions."""
        # Add some test sessions
        session1 = TerminalSession(
            id="session1",
            pid=1001,
            user="user1",
            command="bash",
            terminal="/dev/pts/0",
            start_time=datetime.now() - timedelta(minutes=5)
        )
        session2 = TerminalSession(
            id="session2",
            pid=1002,
            user="user2",
            command="zsh",
            terminal="/dev/pts/1",
            start_time=datetime.now() - timedelta(minutes=3)
        )
        
        # Set up the internal sessions dictionary
        self.tracking_service._sessions = {
            "session1": session1,
            "session2": session2
        }
        
        # Get all sessions
        sessions = self.tracking_service.get_all_sessions()
        
        # Verify the result
        self.assertEqual(len(sessions), 2)
        self.assertIn(session1, sessions)
        self.assertIn(session2, sessions)

    def test_get_session(self):
        """Test getting a specific session by ID."""
        # Add a test session
        session = TerminalSession(
            id="test_session",
            pid=1001,
            user="user1",
            command="bash",
            terminal="/dev/pts/0",
            start_time=datetime.now() - timedelta(minutes=5)
        )
        
        # Set up the internal sessions dictionary
        self.tracking_service._sessions = {"test_session": session}
        
        # Get the session
        retrieved_session = self.tracking_service.get_session("test_session")
        
        # Verify the result
        self.assertEqual(retrieved_session, session)
        
        # Try to get a non-existent session
        none_session = self.tracking_service.get_session("non_existent")
        self.assertIsNone(none_session)

    def test_scan_sessions(self):
        """Test scanning and updating sessions."""
        # Mock session detector result
        self.mock_session_detector.list_terminal_sessions.return_value = [
            {"pid": 1001, "user": "user1", "command": "bash", "terminal": "pts/0"},
            {"pid": 1002, "user": "user2", "command": "zsh", "terminal": "pts/1"}
        ]
        
        # Mock device identifier results
        self.mock_device_identifier.get_terminal_devices.return_value = [
            {"device_path": "/dev/pts/0", "file_descriptors": [0, 1, 2]}
        ]
        self.mock_device_identifier.get_terminal_type.return_value = "xterm-256color"
        self.mock_device_identifier.is_terminal_readable.return_value = True
        
        # Call scan_sessions
        self.tracking_service.scan_sessions()
        
        # Verify results
        self.assertEqual(len(self.tracking_service._sessions), 2)
        
        # Check the details of the first session
        session = next(iter(self.tracking_service._sessions.values()))
        self.assertEqual(session.pid, 1001)
        self.assertEqual(session.user, "user1")
        self.assertEqual(session.command, "bash")
        # The terminal path is formatted in the _add_new_session method
        self.assertEqual(session.terminal, "pts/0")

    def test_session_change_detection(self):
        """Test detection of new and closed sessions."""
        # Set up initial sessions
        initial_session = TerminalSession(
            id="initial_session",
            pid=1001,
            user="user1",
            command="bash",
            terminal="/dev/pts/0",
            start_time=datetime.now() - timedelta(minutes=5)
        )
        self.tracking_service._sessions = {"initial_session": initial_session}
        
        # Mock session detector to return a different set of sessions
        self.mock_session_detector.list_terminal_sessions.return_value = [
            {"pid": 1002, "user": "user2", "command": "zsh", "terminal": "pts/1"}
        ]
        
        # Mock device identifier
        self.mock_device_identifier.get_terminal_devices.return_value = [
            {"device_path": "/dev/pts/1", "file_descriptors": [0, 1, 2]}
        ]
        self.mock_device_identifier.get_terminal_type.return_value = "xterm-256color"
        self.mock_device_identifier.is_terminal_readable.return_value = True
        
        # Set up event handlers to track callbacks
        new_sessions = []
        closed_sessions = []
        
        def on_new_session(session):
            new_sessions.append(session)
            
        def on_session_closed(session):
            closed_sessions.append(session)
            
        self.tracking_service.on_new_session = on_new_session
        self.tracking_service.on_session_closed = on_session_closed
        
        # Scan for sessions
        self.tracking_service.scan_sessions()
        
        # Verify new and closed session detection
        self.assertEqual(len(new_sessions), 1)
        self.assertEqual(new_sessions[0].pid, 1002)
        
        self.assertEqual(len(closed_sessions), 1)
        self.assertEqual(closed_sessions[0].pid, 1001)


if __name__ == "__main__":
    unittest.main()