"""Conversation repository adapter for terminal monitoring."""

import asyncio
import hashlib
import logging
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from uuid import UUID

from src.app.domain.models import PromptRecord
from src.app.domain.repositories import PromptRepository

# Configure logging
logger = logging.getLogger(__name__)


class ConversationRepositoryAdapter:
    """Adapter to connect terminal monitoring with prompt repository."""
    
    def __init__(self, repository: PromptRepository):
        """
        Initialize the adapter.
        
        Args:
            repository: The prompt repository for storage
        """
        self.repository = repository
        self._conversation_cache: Dict[str, List[str]] = {}  # Session ID -> list of conversation hashes
        
    async def store_conversation(
        self, 
        session_id: str,
        prompt_text: str,
        response_text: str,
        terminal_type: str,
        project_name: str,
        project_goal: str,
        additional_metadata: Optional[Dict] = None
    ) -> Optional[PromptRecord]:
        """
        Store a conversation in the repository.
        
        Args:
            session_id: Terminal session ID
            prompt_text: Human prompt text
            response_text: Claude response text
            terminal_type: Type of terminal
            project_name: Name of the project
            project_goal: Goal of the project
            additional_metadata: Additional metadata to store
            
        Returns:
            The created prompt record or None if there was an error
        """
        try:
            # Check if this is a duplicate conversation
            is_duplicate = await self.is_duplicate_conversation(session_id, prompt_text, response_text)
            if is_duplicate:
                logger.info(f"Skipping duplicate conversation for session {session_id}")
                return None
                
            # Prepare metadata
            metadata = {
                "source": "terminal_monitor",
                "terminal_session_id": session_id,
                "capture_time": datetime.now().isoformat()
            }
            
            # Add additional metadata if provided
            if additional_metadata:
                metadata.update(additional_metadata)
                
            # Create the record
            prompt_record = PromptRecord(
                prompt_text=prompt_text,
                response_text=response_text,
                project_name=project_name,
                project_goal=project_goal,
                terminal_type=terminal_type,
                session_id=None,  # We use our own session tracking in metadata
                metadata=metadata
            )
            
            # Store in repository
            stored_record = await self.repository.add(prompt_record)
            
            # Add to conversation cache for deduplication
            self._add_to_conversation_cache(
                session_id, 
                self.compute_conversation_hash(prompt_text, response_text)
            )
            
            logger.info(f"Stored conversation for session {session_id} with ID {stored_record.id}")
            return stored_record
            
        except Exception as e:
            logger.error(f"Error storing conversation: {str(e)}")
            return None
            
    async def is_duplicate_conversation(self, session_id: str, prompt_text: str, response_text: str) -> bool:
        """
        Check if a conversation is a duplicate.
        
        Args:
            session_id: Terminal session ID
            prompt_text: Human prompt text
            response_text: Claude response text
            
        Returns:
            True if the conversation is a duplicate
        """
        try:
            # Compute hash of the conversation
            conversation_hash = self.compute_conversation_hash(prompt_text, response_text)
            
            # Check the in-memory cache first for performance
            if session_id in self._conversation_cache:
                if conversation_hash in self._conversation_cache[session_id]:
                    return True
                    
            # If not in cache, check the repository
            existing_records = await self.get_conversations_for_session(session_id)
            
            for record in existing_records:
                existing_hash = self.compute_conversation_hash(
                    record.prompt_text, 
                    record.response_text
                )
                
                if existing_hash == conversation_hash:
                    # Add to cache for future checks
                    self._add_to_conversation_cache(session_id, conversation_hash)
                    return True
                    
            return False
            
        except Exception as e:
            logger.error(f"Error checking for duplicate conversation: {str(e)}")
            # If there's an error, assume it's not a duplicate
            return False
            
    def compute_conversation_hash(self, prompt_text: str, response_text: str) -> str:
        """
        Compute a hash for the conversation content.
        
        Args:
            prompt_text: Human prompt text
            response_text: Claude response text
            
        Returns:
            Hash of the conversation
        """
        # Normalize content for consistent hashing
        prompt_normalized = prompt_text.strip().lower()
        response_normalized = response_text.strip().lower()
        
        # Create combined content for hashing
        combined = f"{prompt_normalized}:{response_normalized}"
        
        # Generate hash
        return hashlib.md5(combined.encode('utf-8')).hexdigest()
        
    def _add_to_conversation_cache(self, session_id: str, conversation_hash: str) -> None:
        """
        Add a conversation hash to the cache.
        
        Args:
            session_id: Terminal session ID
            conversation_hash: Hash of the conversation
        """
        if session_id not in self._conversation_cache:
            self._conversation_cache[session_id] = []
            
        # Add the hash if not already in cache
        if conversation_hash not in self._conversation_cache[session_id]:
            self._conversation_cache[session_id].append(conversation_hash)
            
        # Limit cache size for each session (keep last 100 conversations)
        max_cache_size = 100
        if len(self._conversation_cache[session_id]) > max_cache_size:
            self._conversation_cache[session_id] = self._conversation_cache[session_id][-max_cache_size:]
            
    async def get_conversations_for_session(self, session_id: str) -> List[PromptRecord]:
        """
        Get all conversations for a session.
        
        Args:
            session_id: Terminal session ID
            
        Returns:
            List of prompt records for the session
        """
        try:
            # Find records with this session ID in metadata
            records = await self.repository.find_by_metadata("terminal_session_id", session_id)
            return records
            
        except Exception as e:
            logger.error(f"Error getting conversations for session {session_id}: {str(e)}")
            return []
            
    def clear_cache_for_session(self, session_id: str) -> None:
        """
        Clear the conversation cache for a session.
        
        Args:
            session_id: Terminal session ID
        """
        if session_id in self._conversation_cache:
            del self._conversation_cache[session_id]
            
    def clear_all_caches(self) -> None:
        """Clear all conversation caches."""
        self._conversation_cache.clear()