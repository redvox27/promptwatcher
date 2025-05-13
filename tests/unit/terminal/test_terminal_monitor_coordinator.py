"""Unit tests for terminal monitor coordinator."""

import asyncio
import os
import sys
import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch, AsyncMock

# Add the src directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

from src.app.infra.terminal.docker_client import DockerClient
from src.app.infra.terminal.session_detector import TerminalSessionDetector
from src.app.infra.terminal.terminal_device_identifier import TerminalDeviceIdentifier
from src.app.infra.terminal.session_tracking_service import SessionTrackingService, TerminalSession
from src.app.infra.terminal.terminal_monitor_coordinator import TerminalMonitorCoordinator, MonitorStatus


class TestTerminalMonitorCoordinator(unittest.TestCase):
    """Test cases for the terminal monitor coordinator."""

    def setUp(self):
        """Set up test fixtures."""
        # Mock dependencies
        self.mock_docker_client = MagicMock(spec=DockerClient)
        self.mock_session_detector = MagicMock(spec=TerminalSessionDetector)
        self.mock_device_identifier = MagicMock(spec=TerminalDeviceIdentifier)
        self.mock_tracking_service = MagicMock(spec=SessionTrackingService)
        
        # Create coordinator with mocked dependencies
        self.coordinator = TerminalMonitorCoordinator(
            docker_client=self.mock_docker_client,
            session_detector=self.mock_session_detector,
            device_identifier=self.mock_device_identifier,
            tracking_service=self.mock_tracking_service
        )

    def test_start_monitor(self):
        """Test starting the monitor."""
        # Set up tracking service mock
        self.mock_tracking_service.start_tracking = MagicMock()
        
        # Start the monitor
        monitor_id = self.coordinator.start_monitor()
        
        # Verify result
        self.assertIsNotNone(monitor_id)
        self.assertEqual(len(self.coordinator.monitors), 1)
        self.assertEqual(self.coordinator.monitors[monitor_id].status, MonitorStatus.ACTIVE)
        self.mock_tracking_service.start_tracking.assert_called_once()

    def test_stop_monitor(self):
        """Test stopping the monitor."""
        # Set up tracking service mock
        self.mock_tracking_service.start_tracking = MagicMock()
        self.mock_tracking_service.stop_tracking = MagicMock()
        
        # Start and then stop the monitor
        monitor_id = self.coordinator.start_monitor()
        result = self.coordinator.stop_monitor(monitor_id)
        
        # Verify result
        self.assertTrue(result)
        self.assertEqual(self.coordinator.monitors[monitor_id].status, MonitorStatus.STOPPED)
        self.mock_tracking_service.stop_tracking.assert_called_once()

    def test_get_monitor_status(self):
        """Test getting the status of a monitor."""
        # Start a monitor
        self.mock_tracking_service.start_tracking = MagicMock()
        monitor_id = self.coordinator.start_monitor()
        
        # Get status
        status = self.coordinator.get_monitor_status(monitor_id)
        
        # Verify result
        self.assertEqual(status.id, monitor_id)
        self.assertEqual(status.status, MonitorStatus.ACTIVE)
        self.assertIsNotNone(status.start_time)

    def test_get_all_monitors(self):
        """Test getting all monitors."""
        # Start multiple monitors
        self.mock_tracking_service.start_tracking = MagicMock()
        id1 = self.coordinator.start_monitor()
        id2 = self.coordinator.start_monitor()
        
        # Get all monitors
        monitors = self.coordinator.get_all_monitors()
        
        # Verify result
        self.assertEqual(len(monitors), 2)
        self.assertIn(id1, [m.id for m in monitors])
        self.assertIn(id2, [m.id for m in monitors])

    @patch('asyncio.run')
    def test_on_new_session(self, mock_run):
        """Test the new session callback."""
        # Create a test session
        session = TerminalSession(
            id="test_session",
            pid=1001,
            user="user1",
            command="bash",
            terminal="/dev/pts/0",
            start_time=datetime.now()
        )
        
        # Start a monitor
        self.mock_tracking_service.start_tracking = MagicMock()
        monitor_id = self.coordinator.start_monitor()
        
        # Trigger the new session callback
        self.coordinator.on_new_session(session)
        
        # Verify result
        monitor = self.coordinator.monitors[monitor_id]
        self.assertEqual(len(monitor.active_sessions), 1)
        self.assertEqual(monitor.active_sessions[0].id, "test_session")

    @patch('asyncio.run')
    def test_on_session_closed(self, mock_run):
        """Test the session closed callback."""
        # Create a test session
        session = TerminalSession(
            id="test_session",
            pid=1001,
            user="user1",
            command="bash",
            terminal="/dev/pts/0",
            start_time=datetime.now()
        )
        
        # Start a monitor and add the session
        self.mock_tracking_service.start_tracking = MagicMock()
        monitor_id = self.coordinator.start_monitor()
        monitor = self.coordinator.monitors[monitor_id]
        monitor.active_sessions.append(session)
        
        # Trigger the session closed callback
        self.coordinator.on_session_closed(session)
        
        # Verify result
        self.assertEqual(len(monitor.active_sessions), 0)
        self.assertEqual(len(monitor.closed_sessions), 1)
        self.assertEqual(monitor.closed_sessions[0].id, "test_session")


if __name__ == "__main__":
    unittest.main()