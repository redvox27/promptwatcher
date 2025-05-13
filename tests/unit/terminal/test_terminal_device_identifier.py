"""Unit tests for terminal device identification."""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# Add the src directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

from src.app.infra.terminal.docker_client import DockerClient
from src.app.infra.terminal.terminal_device_identifier import TerminalDeviceIdentifier


class TestTerminalDeviceIdentifier(unittest.TestCase):
    """Test cases for the terminal device identifier."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_docker_client = MagicMock(spec=DockerClient)
        self.mock_docker_client.is_connected.return_value = True
        self.identifier = TerminalDeviceIdentifier(self.mock_docker_client)

    def test_get_terminal_devices_for_pid(self):
        """Test getting terminal devices for a process."""
        # Mock lsof output for a process with a terminal
        lsof_output = """
COMMAND   PID   USER   FD   TYPE DEVICE SIZE/OFF NODE NAME
bash    12345 testuser    0u   CHR  136,0      0t0    3 /dev/pts/0
bash    12345 testuser    1u   CHR  136,0      0t0    3 /dev/pts/0
bash    12345 testuser    2u   CHR  136,0      0t0    3 /dev/pts/0
bash    12345 testuser  255u   CHR  136,0      0t0    3 /dev/pts/0
"""
        self.mock_docker_client.run_in_host.return_value = lsof_output
        
        # Get terminal devices for PID 12345
        devices = self.identifier.get_terminal_devices(12345)
        
        # Verify the result
        self.assertEqual(len(devices), 1)
        self.assertEqual(devices[0]["device_path"], "/dev/pts/0")
        self.assertEqual(devices[0]["file_descriptors"], [0, 1, 2, 255])
        self.mock_docker_client.run_in_host.assert_called_once()

    def test_get_terminal_devices_no_terminal(self):
        """Test getting terminal devices for a process without a terminal."""
        # Mock lsof output for a process without a terminal
        lsof_output = """
COMMAND   PID   USER   FD   TYPE DEVICE SIZE/OFF NODE NAME
daemon  12345 testuser    0r   REG    8,1      4096  123 /dev/null
daemon  12345 testuser    1w   REG    8,1      4096  456 /var/log/daemon.log
daemon  12345 testuser    2w   REG    8,1      4096  456 /var/log/daemon.log
"""
        self.mock_docker_client.run_in_host.return_value = lsof_output
        
        # Get terminal devices for PID 12345
        devices = self.identifier.get_terminal_devices(12345)
        
        # Verify empty result
        self.assertEqual(len(devices), 0)

    def test_is_terminal_readable(self):
        """Test checking if a terminal device is readable."""
        # Mock successful access check
        self.mock_docker_client.run_in_host.return_value = "Access check successful"
        
        # Check if terminal is readable
        readable = self.identifier.is_terminal_readable("/dev/pts/0")
        
        # Verify result
        self.assertTrue(readable)
        self.mock_docker_client.run_in_host.assert_called_once()

    def test_is_terminal_not_readable(self):
        """Test checking if a terminal device is not readable."""
        # Mock failed access check
        self.mock_docker_client.run_in_host.side_effect = Exception("Permission denied")
        
        # Check if terminal is readable
        readable = self.identifier.is_terminal_readable("/dev/pts/0")
        
        # Verify result
        self.assertFalse(readable)

    def test_get_terminal_type(self):
        """Test detecting terminal type."""
        # Mock process environment check
        self.mock_docker_client.run_in_host.return_value = """
TERM=xterm-256color
SHELL=/bin/bash
USER=testuser
"""
        
        # Get terminal type
        terminal_type = self.identifier.get_terminal_type("/dev/pts/0")
        
        # Verify result
        self.assertEqual(terminal_type, "xterm-256color")

    def test_get_active_terminal_devices(self):
        """Test getting all active terminal devices on the system."""
        # Mock find command output
        find_output = """
/dev/pts/0
/dev/pts/1
/dev/ttys000
"""
        self.mock_docker_client.run_in_host.return_value = find_output
        
        # Get active terminal devices
        devices = self.identifier.get_active_terminal_devices()
        
        # Verify result
        self.assertEqual(len(devices), 3)
        self.assertIn("/dev/pts/0", devices)
        self.assertIn("/dev/pts/1", devices)
        self.assertIn("/dev/ttys000", devices)


if __name__ == "__main__":
    unittest.main()