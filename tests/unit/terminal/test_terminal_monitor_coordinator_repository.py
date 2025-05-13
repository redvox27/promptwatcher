"""Unit tests for terminal monitor coordinator repository integration."""

import asyncio
import os
import sys
import unittest
from datetime import datetime
from typing import List, Optional
from unittest.mock import MagicMock, AsyncMock, patch
from uuid import UUID, uuid4

# Add the src directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

from src.app.domain.models import PromptRecord
from src.app.domain.repositories import PromptRepository
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
from src.app.infra.terminal.conversation_repository_adapter import ConversationRepositoryAdapter
from src.app.infra.terminal.terminal_monitor_coordinator import TerminalMonitorCoordinator, MonitorStatus


class MockPromptRepository(AsyncMock):
    """Mock implementation of the PromptRepository."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.records = {}
        
    async def add(self, entity: PromptRecord) -> PromptRecord:
        """Add a prompt record."""
        self.records[str(entity.id)] = entity
        return entity
        
    async def get(self, id: UUID) -> PromptRecord:
        """Get a prompt record."""
        if str(id) not in self.records:
            raise KeyError(f"Record with ID {id} not found")
        return self.records[str(id)]
    
    async def find_by_metadata(self, key: str, value: str) -> List[PromptRecord]:
        """Find records by metadata."""
        results = []
        for record in self.records.values():
            if key in record.metadata and record.metadata[key] == value:
                results.append(record)
        return results


class TestTerminalMonitorCoordinatorRepository(unittest.TestCase):
    """Test cases for the terminal monitor coordinator repository integration."""

    def setUp(self):
        """Set up test fixtures."""
        # Mock dependencies
        self.mock_docker_client = MagicMock(spec=DockerClient)
        self.mock_session_detector = MagicMock(spec=TerminalSessionDetector)
        self.mock_device_identifier = MagicMock(spec=TerminalDeviceIdentifier)
        self.mock_tracking_service = MagicMock(spec=SessionTrackingService)
        self.mock_output_capture = MagicMock(spec=TerminalOutputCapture)
        self.mock_output_processor = MagicMock(spec=TerminalOutputProcessor)
        self.mock_repository = MockPromptRepository()
        self.repository_adapter = ConversationRepositoryAdapter(self.mock_repository)
        
        # Create coordinator with mocked dependencies
        self.coordinator = TerminalMonitorCoordinator(
            docker_client=self.mock_docker_client,
            session_detector=self.mock_session_detector,
            device_identifier=self.mock_device_identifier,
            tracking_service=self.mock_tracking_service,
            output_capture=self.mock_output_capture,
            output_processor=self.mock_output_processor,
            repository_adapter=self.repository_adapter,
            settings={
                "project_name": "TestProject",
                "project_goal": "Testing",
                "buffer_size": 10000,
                "capture_interval": 1.0
            }
        )
        
    async def async_setUp(self):
        """Async setup for tests."""
        # Mock dependencies
        self.mock_docker_client = MagicMock(spec=DockerClient)
        self.mock_session_detector = MagicMock(spec=TerminalSessionDetector)
        self.mock_device_identifier = MagicMock(spec=TerminalDeviceIdentifier)
        self.mock_tracking_service = MagicMock(spec=SessionTrackingService)
        self.mock_output_capture = MagicMock(spec=TerminalOutputCapture)
        self.mock_output_processor = MagicMock(spec=TerminalOutputProcessor)
        self.mock_repository = MockPromptRepository()
        self.repository_adapter = ConversationRepositoryAdapter(self.mock_repository)
        
        # Create coordinator with mocked dependencies
        self.coordinator = TerminalMonitorCoordinator(
            docker_client=self.mock_docker_client,
            session_detector=self.mock_session_detector,
            device_identifier=self.mock_device_identifier,
            tracking_service=self.mock_tracking_service,
            output_capture=self.mock_output_capture,
            output_processor=self.mock_output_processor,
            repository_adapter=self.repository_adapter,
            settings={
                "project_name": "TestProject",
                "project_goal": "Testing",
                "buffer_size": 10000,
                "capture_interval": 1.0
            }
        )
        
    async def async_tearDown(self):
        """Async teardown for tests."""
        pass
        
    async def test_store_prompt(self):
        """Test storing a prompt in the repository."""
        await self.async_setUp()
        
        # Test data
        session_id = "123456789"
        prompt_text = "Test prompt"
        response_text = "Test response"
        terminal_type = "bash"
        
        # Call the method
        result = await self.coordinator.store_prompt(
            session_id=session_id,
            prompt_text=prompt_text,
            response_text=response_text,
            terminal_type=terminal_type,
            project_name="TestProject",
            project_goal="Testing"
        )
        
        # Verify result
        self.assertIsNotNone(result)
        self.assertEqual(result.prompt_text, prompt_text)
        self.assertEqual(result.response_text, response_text)
        self.assertEqual(result.terminal_type, terminal_type)
        
        # Verify repository was called
        self.assertEqual(len(self.mock_repository.records), 1)
        
        # Get the stored record
        stored_record = list(self.mock_repository.records.values())[0]
        
        # Verify record data
        self.assertEqual(stored_record.prompt_text, prompt_text)
        self.assertEqual(stored_record.response_text, response_text)
        self.assertEqual(stored_record.terminal_type, terminal_type)
        self.assertEqual(stored_record.project_name, "TestProject")
        self.assertEqual(stored_record.project_goal, "Testing")
        
        # Verify metadata
        self.assertEqual(stored_record.metadata["terminal_session_id"], session_id)
        self.assertEqual(stored_record.metadata["source"], "terminal_monitor")
        self.assertIn("capture_time", stored_record.metadata)
        
        await self.async_tearDown()
        
    async def test_store_prompt_error_handling(self):
        """Test error handling during prompt storage."""
        await self.async_setUp()
        
        # Create new mock objects that can have side_effect set
        mock_repo = AsyncMock()
        mock_repo.add = AsyncMock(side_effect=Exception("Test error"))
        
        # Create new adapter with the mock repo
        mock_adapter = ConversationRepositoryAdapter(mock_repo)
        
        # Replace repository adapter in coordinator
        self.coordinator.repository_adapter = mock_adapter
        
        # Call the method
        result = await self.coordinator.store_prompt(
            session_id="test",
            prompt_text="test",
            response_text="test",
            terminal_type="test",
            project_name="test",
            project_goal="test"
        )
        
        # Verify result is None on error
        self.assertIsNone(result)
        
        await self.async_tearDown()
        
    async def test_capture_and_store_conversation(self):
        """Test capturing and storing a conversation."""
        await self.async_setUp()
        
        # Create a test session
        session = TerminalSession(
            id=str(uuid4()),
            pid=1001,
            user="user1",
            command="bash",
            terminal="/dev/pts/0",
            start_time=datetime.now(),
            device_paths=["/dev/pts/0"],
            terminal_type="bash",
            is_readable=True
        )
        
        # Create a test monitor
        monitor_id = self.coordinator.start_monitor()
        
        # Mock the output capture to return test content
        capture_result = CaptureResult(
            device_path="/dev/pts/0",
            status="success",
            content="Human: Test prompt\nClaude: Test response"
        )
        
        self.mock_output_capture.capture_multiple.return_value = {
            "/dev/pts/0": capture_result
        }
        
        # Mock the output processor to detect Claude conversations
        processing_result = ProcessingResult(
            raw_text=capture_result.content,
            clean_text=capture_result.content,
            contains_claude_conversation=True,
            claude_conversations=["Human: Test prompt\nClaude: Test response"]
        )
        
        self.mock_output_processor.process_raw_capture.return_value = processing_result
        self.mock_output_processor.extract_message_pair.return_value = ("Test prompt", "Test response")
        
        # Call the capture method
        await self.coordinator._capture_session_content(monitor_id, session)
        
        # Verify a record was stored
        self.assertEqual(len(self.mock_repository.records), 1)
        
        # Get the stored record
        stored_record = list(self.mock_repository.records.values())[0]
        
        # Verify record data
        self.assertEqual(stored_record.prompt_text, "Test prompt")
        self.assertEqual(stored_record.response_text, "Test response")
        self.assertEqual(stored_record.terminal_type, "bash")
        
        # Verify metadata
        self.assertEqual(stored_record.metadata["terminal_session_id"], str(session.id))
        self.assertEqual(stored_record.metadata["source"], "terminal_monitor")
        
        await self.async_tearDown()
        
    async def test_deduplication(self):
        """Test conversation deduplication."""
        await self.async_setUp()
        
        # Create a test session
        session = TerminalSession(
            id=str(uuid4()),
            pid=1001,
            user="user1",
            command="bash",
            terminal="/dev/pts/0",
            start_time=datetime.now(),
            device_paths=["/dev/pts/0"],
            terminal_type="bash",
            is_readable=True
        )
        
        # Create a test monitor
        monitor_id = self.coordinator.start_monitor()
        
        # Mock the output capture to return test content
        capture_result = CaptureResult(
            device_path="/dev/pts/0",
            status="success",
            content="Human: Test prompt\nClaude: Test response"
        )
        
        self.mock_output_capture.capture_multiple.return_value = {
            "/dev/pts/0": capture_result
        }
        
        # Mock the output processor to detect Claude conversations
        processing_result = ProcessingResult(
            raw_text=capture_result.content,
            clean_text=capture_result.content,
            contains_claude_conversation=True,
            claude_conversations=["Human: Test prompt\nClaude: Test response"]
        )
        
        self.mock_output_processor.process_raw_capture.return_value = processing_result
        self.mock_output_processor.extract_message_pair.return_value = ("Test prompt", "Test response")
        
        # Patch the is_duplicate_conversation method to test both paths
        original_is_duplicate = self.repository_adapter.is_duplicate_conversation
        
        # First capture - not a duplicate
        self.repository_adapter.is_duplicate_conversation = AsyncMock(return_value=False)
        await self.coordinator._capture_session_content(monitor_id, session)
        
        # Verify a record was stored
        self.assertEqual(len(self.mock_repository.records), 1)
        
        # Second capture - duplicate
        self.repository_adapter.is_duplicate_conversation = AsyncMock(return_value=True)
        await self.coordinator._capture_session_content(monitor_id, session)
        
        # Verify no additional record was stored
        self.assertEqual(len(self.mock_repository.records), 1)
        
        # Restore the original method
        self.repository_adapter.is_duplicate_conversation = original_is_duplicate
        
        await self.async_tearDown()


# Helper to run async tests
def async_test(coro):
    def wrapper(*args, **kwargs):
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro(*args, **kwargs))
        finally:
            loop.close()
    return wrapper


# Apply async_test decorator to async test methods
TestTerminalMonitorCoordinatorRepository.test_store_prompt = async_test(TestTerminalMonitorCoordinatorRepository.test_store_prompt)
TestTerminalMonitorCoordinatorRepository.test_store_prompt_error_handling = async_test(TestTerminalMonitorCoordinatorRepository.test_store_prompt_error_handling)
TestTerminalMonitorCoordinatorRepository.test_capture_and_store_conversation = async_test(TestTerminalMonitorCoordinatorRepository.test_capture_and_store_conversation)
TestTerminalMonitorCoordinatorRepository.test_deduplication = async_test(TestTerminalMonitorCoordinatorRepository.test_deduplication)


if __name__ == "__main__":
    unittest.main()