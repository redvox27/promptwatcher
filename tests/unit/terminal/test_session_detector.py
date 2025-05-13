"""Unit tests for terminal session detector."""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# Add the src directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

from src.app.infra.terminal.docker_client import DockerClient
from src.app.infra.terminal.session_detector import TerminalSessionDetector


class TestSessionDetector(unittest.TestCase):
    """Test cases for the terminal session detector."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_docker_client = MagicMock(spec=DockerClient)
        self.mock_docker_client.is_connected.return_value = True
        self.detector = TerminalSessionDetector(self.mock_docker_client)

    def test_list_terminal_sessions_empty(self):
        """Test empty process list."""
        # Mock empty process list
        self.mock_docker_client.run_in_host.return_value = "PID   USER     TIME  COMMAND\n"
        
        # Call method
        sessions = self.detector.list_terminal_sessions()
        
        # Assert
        self.assertEqual(len(sessions), 0)
        self.mock_docker_client.run_in_host.assert_called_once()

    def test_list_terminal_sessions(self):
        """Test parsing process list with terminals."""
        # Mock process list with various processes
        ps_output = """PID   USER     TIME  COMMAND
    1 root      0:04 /init
   10 root      0:00 [kworker/0:1]
  206 root      0:00 -bash
  240 root      0:00 /bin/sh /usr/bin/entrypoint.sh
  300 root      0:00 python3 /app/main.py
"""
        self.mock_docker_client.run_in_host.return_value = ps_output
        
        # Call method
        sessions = self.detector.list_terminal_sessions()
        
        # Assert - only bash and sh are detected as terminals (python not detected as terminal in current implementation)
        self.assertEqual(len(sessions), 2)  # bash and sh are detected
        
        # Verify the bash process was detected correctly
        bash_session = next((s for s in sessions if s["command"] == "-bash"), None)
        self.assertIsNotNone(bash_session)
        self.assertEqual(bash_session["pid"], 206)
        self.assertEqual(bash_session["user"], "root")
        self.assertEqual(bash_session["terminal"], "pts/0")  # Should be detected as a terminal

    def test_list_interactive_sessions(self):
        """Test filtering for interactive terminal sessions."""
        # Mock process list with various processes
        ps_output = """PID   USER     TIME  COMMAND
    1 root      0:04 /init
   10 root      0:00 [kworker/0:1]
  206 root      0:00 -bash
  207 root      0:00 grep --color=auto ssh
  240 root      0:00 /bin/sh /usr/bin/entrypoint.sh
  300 root      0:00 python3 /app/main.py
"""
        self.mock_docker_client.run_in_host.return_value = ps_output
        
        # Call method
        sessions = self.detector.list_terminal_sessions(interactive_only=True)
        
        # Assert - grep should be excluded from interactive sessions
        self.assertEqual(len(sessions), 2)  # Only bash and python are interactive
        
        # Bash should be detected as interactive
        self.assertTrue(any(s["command"] == "-bash" for s in sessions))
        
        # Grep should not be detected as interactive
        self.assertFalse(any("grep" in s["command"] for s in sessions))

    def test_error_handling(self):
        """Test error handling when Docker client fails."""
        # Mock Docker client error
        self.mock_docker_client.run_in_host.side_effect = Exception("Docker error")
        
        # Call method should not raise exception
        sessions = self.detector.list_terminal_sessions()
        
        # Assert empty list is returned on error
        self.assertEqual(len(sessions), 0)

    def test_parse_process_line(self):
        """Test parsing individual process lines."""
        # Test normal process line
        line = "  100 root      0:01 /bin/bash"
        session = self.detector._parse_process_line(line)
        self.assertIsNotNone(session)
        self.assertEqual(session["pid"], 100)
        self.assertEqual(session["user"], "root")
        self.assertEqual(session["command"], "/bin/bash")
        self.assertEqual(session["terminal"], "pts/0")  # Should detect as terminal
        
        # Test non-terminal process
        line = "  101 root      0:01 [kworker/0:1]"
        session = self.detector._parse_process_line(line)
        self.assertIsNotNone(session)
        self.assertEqual(session["terminal"], "?")  # Should not be a terminal

        # Test invalid line
        line = "invalid line"
        session = self.detector._parse_process_line(line)
        self.assertIsNone(session)


if __name__ == "__main__":
    unittest.main()