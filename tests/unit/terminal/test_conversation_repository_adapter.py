"""Unit tests for conversation repository adapter."""

import asyncio
import os
import sys
import unittest
import uuid
from datetime import datetime
from typing import Dict, List, Optional
from unittest.mock import MagicMock, AsyncMock, patch
from uuid import UUID

# Add the src directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

from src.app.domain.models import PromptRecord
from src.app.domain.repositories import PromptRepository

# This will be our adapter implementation
from src.app.infra.terminal.conversation_repository_adapter import ConversationRepositoryAdapter


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


class TestConversationRepositoryAdapter(unittest.TestCase):
    """Test cases for the conversation repository adapter."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_repository = MockPromptRepository()
        self.adapter = ConversationRepositoryAdapter(self.mock_repository)
        
    async def async_setUp(self):
        """Async setup for tests."""
        self.mock_repository = MockPromptRepository()
        self.adapter = ConversationRepositoryAdapter(self.mock_repository)
        
    async def async_tearDown(self):
        """Async teardown for tests."""
        pass
        
    def test_init(self):
        """Test initialization of the adapter."""
        self.assertEqual(self.adapter.repository, self.mock_repository)
        
    @patch('uuid.uuid4', return_value=UUID('123e4567-e89b-12d3-a456-426614174000'))
    async def test_store_conversation(self, mock_uuid):
        """Test storing a conversation."""
        await self.async_setUp()
        
        # Test data
        session_id = "123456789"
        prompt_text = "Test prompt"
        response_text = "Test response"
        terminal_type = "bash"
        project_name = "TestProject"
        project_goal = "Testing"
        
        # Store conversation
        result = await self.adapter.store_conversation(
            session_id=session_id,
            prompt_text=prompt_text,
            response_text=response_text,
            terminal_type=terminal_type,
            project_name=project_name,
            project_goal=project_goal
        )
        
        # Verify result
        self.assertIsNotNone(result)
        self.assertEqual(result.prompt_text, prompt_text)
        self.assertEqual(result.response_text, response_text)
        self.assertEqual(result.terminal_type, terminal_type)
        self.assertEqual(result.project_name, project_name)
        self.assertEqual(result.project_goal, project_goal)
        
        # Verify repository was called
        self.assertEqual(len(self.mock_repository.records), 1)
        
        # Verify metadata
        stored_record = list(self.mock_repository.records.values())[0]
        self.assertEqual(stored_record.metadata["terminal_session_id"], session_id)
        self.assertEqual(stored_record.metadata["source"], "terminal_monitor")
        self.assertIn("capture_time", stored_record.metadata)
        
        await self.async_tearDown()
        
    async def test_store_error_handling(self):
        """Test error handling during storage."""
        await self.async_setUp()
        
        # Create a new mock that can have side_effect set
        mock_repo = AsyncMock()
        mock_repo.add = AsyncMock(side_effect=Exception("Test error"))
        adapter = ConversationRepositoryAdapter(mock_repo)
        
        # Store conversation
        result = await adapter.store_conversation(
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
        
    async def test_is_duplicate_conversation(self):
        """Test duplicate detection."""
        await self.async_setUp()
        
        # Store a conversation
        prompt_text = "Test prompt"
        response_text = "Test response"
        session_id = "test_session"
        
        await self.adapter.store_conversation(
            session_id=session_id,
            prompt_text=prompt_text,
            response_text=response_text,
            terminal_type="bash",
            project_name="test",
            project_goal="test"
        )
        
        # Check if duplicate (same content)
        is_duplicate = await self.adapter.is_duplicate_conversation(
            session_id=session_id,
            prompt_text=prompt_text,
            response_text=response_text
        )
        
        # Should be a duplicate
        self.assertTrue(is_duplicate)
        
        # Check with different content
        is_duplicate = await self.adapter.is_duplicate_conversation(
            session_id=session_id,
            prompt_text="Different prompt",
            response_text=response_text
        )
        
        # Should not be a duplicate
        self.assertFalse(is_duplicate)
        
        await self.async_tearDown()
        
    async def test_get_session_conversations(self):
        """Test getting conversations for a session."""
        await self.async_setUp()
        
        # Store multiple conversations
        session_id = "test_session"
        
        await self.adapter.store_conversation(
            session_id=session_id,
            prompt_text="Prompt 1",
            response_text="Response 1",
            terminal_type="bash",
            project_name="test",
            project_goal="test"
        )
        
        await self.adapter.store_conversation(
            session_id=session_id,
            prompt_text="Prompt 2",
            response_text="Response 2",
            terminal_type="bash",
            project_name="test",
            project_goal="test"
        )
        
        await self.adapter.store_conversation(
            session_id="different_session",
            prompt_text="Prompt 3",
            response_text="Response 3",
            terminal_type="bash",
            project_name="test",
            project_goal="test"
        )
        
        # Get conversations for session
        conversations = await self.adapter.get_conversations_for_session(session_id)
        
        # Verify results
        self.assertEqual(len(conversations), 2)
        prompts = [c.prompt_text for c in conversations]
        self.assertIn("Prompt 1", prompts)
        self.assertIn("Prompt 2", prompts)
        
        await self.async_tearDown()
        
    async def test_compute_conversation_hash(self):
        """Test computing conversation hash."""
        await self.async_setUp()
        
        # Compute hash for test conversation
        hash1 = self.adapter.compute_conversation_hash(
            prompt_text="Test prompt",
            response_text="Test response"
        )
        
        # Same content should produce same hash
        hash2 = self.adapter.compute_conversation_hash(
            prompt_text="Test prompt",
            response_text="Test response"
        )
        
        # Different content should produce different hash
        hash3 = self.adapter.compute_conversation_hash(
            prompt_text="Different prompt",
            response_text="Test response"
        )
        
        # Verify hashes
        self.assertEqual(hash1, hash2)
        self.assertNotEqual(hash1, hash3)
        
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
TestConversationRepositoryAdapter.test_store_conversation = async_test(TestConversationRepositoryAdapter.test_store_conversation)
TestConversationRepositoryAdapter.test_store_error_handling = async_test(TestConversationRepositoryAdapter.test_store_error_handling)
TestConversationRepositoryAdapter.test_is_duplicate_conversation = async_test(TestConversationRepositoryAdapter.test_is_duplicate_conversation)
TestConversationRepositoryAdapter.test_get_session_conversations = async_test(TestConversationRepositoryAdapter.test_get_session_conversations)
TestConversationRepositoryAdapter.test_compute_conversation_hash = async_test(TestConversationRepositoryAdapter.test_compute_conversation_hash)


if __name__ == "__main__":
    unittest.main()