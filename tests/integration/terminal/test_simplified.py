"""Simplified test for terminal capture to repository integration."""

import asyncio
import os
import sys
import unittest
from datetime import datetime
from unittest.mock import MagicMock, AsyncMock
from uuid import uuid4

# Add the src directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

from src.app.domain.models import PromptRecord
from src.app.domain.repositories import PromptRepository
from src.app.infra.terminal.session_tracking_service import TerminalSession
from src.app.infra.terminal.terminal_output_capture import (
    CaptureResult, 
    ProcessingResult
)
from src.app.infra.terminal.conversation_repository_adapter import ConversationRepositoryAdapter


class InMemoryPromptRepository(PromptRepository):
    """Simple in-memory implementation of PromptRepository for testing."""
    
    def __init__(self):
        """Initialize the repository."""
        self.records = {}
        
    async def get(self, id):
        """Get a record by ID."""
        if str(id) not in self.records:
            raise KeyError(f"Record with ID {id} not found")
        return self.records[str(id)]
        
    async def find_all(self):
        """Find all records."""
        return list(self.records.values())
        
    async def add(self, entity):
        """Add a record."""
        self.records[str(entity.id)] = entity
        return entity
        
    async def find_by_metadata(self, key, value):
        """Find records by metadata."""
        return [r for r in self.records.values() 
                if key in r.metadata and r.metadata[key] == value]


class TestSimplifiedRepositoryAdapter(unittest.TestCase):
    """Test the repository adapter directly without coordinator."""
    
    async def test_store_two_conversations(self):
        """Test storing multiple conversations."""
        # Create repository and adapter
        repository = InMemoryPromptRepository()
        adapter = ConversationRepositoryAdapter(repository)
        
        # Force deduplication off
        adapter.is_duplicate_conversation = AsyncMock(return_value=False)
        
        # Session ID for both conversations
        session_id = str(uuid4())
        
        # Store first conversation
        await adapter.store_conversation(
            session_id=session_id,
            prompt_text="What is the capital of France?",
            response_text="The capital of France is Paris.",
            terminal_type="bash",
            project_name="Test Project",
            project_goal="Testing"
        )
        
        # Check record was stored
        records = await repository.find_by_metadata("terminal_session_id", session_id)
        self.assertEqual(len(records), 1)
        
        # Store second conversation
        await adapter.store_conversation(
            session_id=session_id,
            prompt_text="Tell me about Python programming.",
            response_text="Python is a versatile programming language.",
            terminal_type="bash",
            project_name="Test Project",
            project_goal="Testing"
        )
        
        # Check both records are stored
        records = await repository.find_by_metadata("terminal_session_id", session_id)
        self.assertEqual(len(records), 2)
        
        # Verify content
        prompts = [r.prompt_text for r in records]
        self.assertTrue(any("France" in p for p in prompts))
        self.assertTrue(any("Python" in p for p in prompts))


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
TestSimplifiedRepositoryAdapter.test_store_two_conversations = async_test(
    TestSimplifiedRepositoryAdapter.test_store_two_conversations
)


if __name__ == "__main__":
    unittest.main()