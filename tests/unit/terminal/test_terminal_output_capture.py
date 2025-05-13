"""Unit tests for terminal output capture."""

import asyncio
import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

# Add the src directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

from src.app.infra.terminal.docker_client import DockerClient
from src.app.infra.terminal.terminal_output_capture import (
    TerminalOutputCapture,
    TerminalOutputBuffer,
    TerminalOutputProcessor,
    CaptureResult
)


class TestTerminalOutputCapture(unittest.TestCase):
    """Test cases for the terminal output capture functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_docker_client = MagicMock(spec=DockerClient)
        self.mock_docker_client.is_connected.return_value = True
        self.capture = TerminalOutputCapture(self.mock_docker_client)

    def test_capture_output_success(self):
        """Test successful output capture."""
        # Reset the mock to clear call history
        self.mock_docker_client.run_in_host.reset_mock()
        # Mock successful terminal read
        sample_output = "User input\nClaude response\nMore text"
        self.mock_docker_client.run_in_host.return_value = sample_output
        
        # Capture output
        result = self.capture.capture_output("/dev/pts/0", timeout=1)
        
        # Verify result
        self.assertEqual(result.status, "success")
        self.assertEqual(result.content, sample_output)
        self.assertFalse(result.is_error)
        # Since we're now using a method parameter, we expect only one call
        self.assertEqual(self.mock_docker_client.run_in_host.call_count, 1)

    def test_capture_output_permission_error(self):
        """Test handling of permission errors."""
        # Reset the mock to clear call history
        self.mock_docker_client.run_in_host.reset_mock()
        # Mock permission error
        self.mock_docker_client.run_in_host.side_effect = Exception("Permission denied")
        
        # Capture output
        result = self.capture.capture_output("/dev/pts/0", timeout=1)
        
        # Verify error handling
        self.assertEqual(result.status, "error")
        self.assertTrue(result.is_error)
        self.assertIn("permission", result.error_message.lower())
        # Since we use method="direct" by default, only one call is expected
        self.assertEqual(self.mock_docker_client.run_in_host.call_count, 1)

    def test_capture_output_timeout(self):
        """Test handling of timeout."""
        # Mock timeout
        self.mock_docker_client.run_in_host.side_effect = Exception("Timeout occurred")
        
        # Capture output
        result = self.capture.capture_output("/dev/pts/0", timeout=1)
        
        # Verify error handling
        self.assertEqual(result.status, "timeout")
        self.assertTrue(result.is_error)
        self.assertIn("timeout", result.error_message.lower())

    def test_capture_multiple_devices(self):
        """Test capturing from multiple devices."""
        # Reset the mock to clear call history
        self.mock_docker_client.run_in_host.reset_mock()
        
        # Mock device outputs
        device_outputs = {
            "/dev/pts/0": "Output from device 0",
            "/dev/pts/1": "Output from device 1"
        }
        
        def mock_run_in_host(command, timeout=None):
            # Extract device path from command
            for device in device_outputs:
                if device in command:
                    return device_outputs[device]
            raise ValueError("Unknown device")
        
        self.mock_docker_client.run_in_host.side_effect = mock_run_in_host
        
        # Capture from multiple devices
        results = self.capture.capture_multiple(["/dev/pts/0", "/dev/pts/1"], timeout=1)
        
        # Verify results
        self.assertEqual(len(results), 2)
        self.assertEqual(results["/dev/pts/0"].content, "Output from device 0")
        self.assertEqual(results["/dev/pts/1"].content, "Output from device 1")
        # With the direct method, we expect one call per device
        self.assertEqual(self.mock_docker_client.run_in_host.call_count, 2)

    def test_create_temp_capture_script(self):
        """Test creating a temporary capture script."""
        # Test script creation
        script_path = self.capture._create_temp_capture_script("/dev/pts/0", 1)
        
        # Verify script exists and contains expected content
        self.assertTrue(os.path.exists(script_path))
        with open(script_path, "r") as f:
            content = f.read()
            self.assertIn("/dev/pts/0", content)
            self.assertIn("timeout", content)
        
        # Clean up
        os.remove(script_path)

    def test_auto_detect_capture_method(self):
        """Test auto-detection of capture method."""
        # Mock successful direct read
        self.mock_docker_client.run_in_host.return_value = "Success"
        
        # Test auto-detection
        method = self.capture.auto_detect_capture_method("/dev/pts/0")
        
        # Verify direct read was detected
        self.assertEqual(method, "direct")

        # Now mock failure for direct read but success for script
        self.mock_docker_client.run_in_host.side_effect = [
            Exception("Permission denied"),  # Direct read fails
            "Script success"  # Script method succeeds
        ]
        
        # Test auto-detection again
        method = self.capture.auto_detect_capture_method("/dev/pts/0")
        
        # Verify script method was detected
        self.assertEqual(method, "script")


class TestTerminalOutputBuffer(unittest.TestCase):
    """Test cases for terminal output buffer."""

    def setUp(self):
        """Set up test fixtures."""
        self.buffer = TerminalOutputBuffer(max_size=1000)

    def test_append_content(self):
        """Test appending content to the buffer."""
        # Append content
        self.buffer.append("First chunk")
        self.buffer.append("Second chunk")
        
        # Verify buffer content
        self.assertIn("First chunk", self.buffer.get_content())
        self.assertIn("Second chunk", self.buffer.get_content())
        self.assertEqual(len(self.buffer.get_content()), 23)  # "First chunk" + "Second chunk" + space

    def test_buffer_overflow(self):
        """Test buffer overflow handling."""
        # Fill buffer beyond max size
        long_content = "X" * 1500  # Longer than max_size
        self.buffer.append(long_content)
        
        # Verify buffer handled overflow
        self.assertEqual(len(self.buffer.get_content()), 1000)  # Truncated to max_size
        self.assertEqual(self.buffer.get_content(), "X" * 1000)

    def test_clear_buffer(self):
        """Test clearing the buffer."""
        # Add content
        self.buffer.append("Content to clear")
        
        # Clear buffer
        self.buffer.clear()
        
        # Verify empty buffer
        self.assertEqual(self.buffer.get_content(), "")
        self.assertEqual(len(self.buffer.get_content()), 0)

    def test_get_last_lines(self):
        """Test getting last N lines from buffer."""
        # Add multi-line content
        self.buffer.append("Line 1\nLine 2\nLine 3\nLine 4\nLine 5")
        
        # Get last 3 lines
        last_lines = self.buffer.get_last_lines(3)
        
        # Verify correct lines returned
        self.assertEqual(len(last_lines), 3)
        self.assertEqual(last_lines, ["Line 3", "Line 4", "Line 5"])

    def test_circular_buffer(self):
        """Test circular buffer behavior."""
        # Create a new test case to ensure clean state
        buffer = TerminalOutputBuffer(max_size=10)
        
        # First, append content that fits within the max_size
        buffer.append("12345")
        self.assertEqual(buffer.get_content(), "12345")
        
        # Then append content that would make the total exceed max_size
        buffer.append("67890")
        # Total length would be 10, which equals max_size
        self.assertEqual(len(buffer.get_content()), 10)
        self.assertEqual(buffer.get_content(), "1234567890")
        
        # Now append content that would definitely make it exceed max_size
        buffer.append("ABCDE")
        # Check that the buffer has been trimmed to max_size
        self.assertEqual(len(buffer.get_content()), 10)
        # The oldest content should be dropped
        content = buffer.get_content()
        self.assertIn("ABCDE", content)  # Newest content is there
        self.assertNotIn("12345", content)  # Oldest content is dropped


class TestTerminalOutputProcessor(unittest.TestCase):
    """Test cases for terminal output processor."""

    def setUp(self):
        """Set up test fixtures."""
        self.processor = TerminalOutputProcessor()

    def test_remove_ansi_escape_sequences(self):
        """Test removing ANSI escape sequences."""
        # Text with ANSI escape sequences
        text_with_ansi = "\033[31mRed text\033[0m \033[1mBold text\033[0m"
        
        # Process text
        clean_text = self.processor.remove_ansi_escape_sequences(text_with_ansi)
        
        # Verify escape sequences removed
        self.assertEqual(clean_text, "Red text Bold text")
        self.assertNotIn("\033", clean_text)

    def test_normalize_line_endings(self):
        """Test normalizing line endings."""
        # Text with mixed line endings
        mixed_endings = "Line 1\r\nLine 2\rLine 3\nLine 4"
        
        # Process text
        normalized = self.processor.normalize_line_endings(mixed_endings)
        
        # Verify all endings converted to \n
        self.assertEqual(normalized.count("\n"), 3)
        self.assertNotIn("\r\n", normalized)
        self.assertNotIn("\r", normalized)
        self.assertEqual(normalized, "Line 1\nLine 2\nLine 3\nLine 4")

    def test_clean_text(self):
        """Test the full text cleaning process."""
        # Text with various issues
        dirty_text = "\033[31mColored\033[0m\r\nText\rwith\nIssues"
        
        # Process text
        clean_text = self.processor.clean_text(dirty_text)
        
        # Verify all cleaning steps applied
        self.assertEqual(clean_text, "Colored\nText\nwith\nIssues")
        self.assertNotIn("\033", clean_text)
        self.assertNotIn("\r", clean_text)

    def test_detect_content_type(self):
        """Test detecting Claude content."""
        # Claude conversation text
        claude_text = """
Human: What is the capital of France?
Claude: The capital of France is Paris. Paris is located in the north-central part of the country on the Seine River.
Human: And what's the population?
Claude: The population of Paris is approximately 2.2 million people in the city proper. However, the greater Paris metropolitan area has a population of about 12 million people.
"""
        
        # Generic terminal text
        regular_text = """
$ ls -la
total 12
drwxr-xr-x  2 user  staff   64 May 13 10:30 .
drwxr-xr-x 10 user  staff  320 May 13 10:29 ..
-rw-r--r--  1 user  staff  123 May 13 10:30 example.py
$ python example.py
Hello world!
$
"""

        # Test Claude content detection
        is_claude = self.processor.detect_claude_conversation(claude_text)
        self.assertTrue(is_claude)
        
        # Test regular content detection
        is_claude = self.processor.detect_claude_conversation(regular_text)
        self.assertFalse(is_claude)
        
    def test_extract_claude_conversations(self):
        """Test extracting Claude conversations from terminal output."""
        # Mixed terminal output with Claude conversation
        mixed_text = """
$ echo "Hello"
Hello
$ claude
Human: Tell me about quantum computing
Claude: Quantum computing is a type of computing that uses quantum-mechanical phenomena, such as superposition and entanglement, to perform operations on data.

Unlike classical computers that use bits (0 or 1), quantum computers use quantum bits or qubits, which can exist in multiple states simultaneously.
Human: Thanks, that's helpful
Claude: You're welcome! Let me know if you have any other questions about quantum computing or related topics.
$ ls
file1.txt file2.txt
"""
        
        # Extract conversations
        conversations = self.processor.extract_claude_conversations(mixed_text)
        
        # Verify extraction
        self.assertEqual(len(conversations), 1)
        self.assertIn("quantum computing", conversations[0])
        self.assertIn("Human: Tell me about", conversations[0])
        self.assertIn("Human: Thanks", conversations[0])
        
    def test_process_raw_capture(self):
        """Test processing raw terminal capture."""
        # Raw terminal output
        raw_output = "\033[32m$ claude\033[0m\r\nHuman: Hello\r\nClaude: Hi there! How can I help you today?\r\n\033[32m$\033[0m"
        
        # Process raw output
        result = self.processor.process_raw_capture(raw_output)
        
        # Verify processing steps
        self.assertNotIn("\033", result.clean_text)
        self.assertNotIn("\r", result.clean_text)
        self.assertTrue(result.contains_claude_conversation)
        self.assertEqual(len(result.claude_conversations), 1)
        self.assertIn("Human: Hello", result.claude_conversations[0])
        self.assertIn("Claude: Hi there!", result.claude_conversations[0])