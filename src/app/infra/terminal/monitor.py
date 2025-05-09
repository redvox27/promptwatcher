"""Terminal monitoring implementation."""

import asyncio
from typing import Dict, Optional
from uuid import UUID, uuid4

from app.domain.models import PromptRecord
from app.domain.services import PromptCaptureService


class ITerm2PromptCaptureService(PromptCaptureService):
    """Implementation of PromptCaptureService for iTerm2."""
    
    def __init__(self):
        """Initialize the service."""
        self.active_sessions: Dict[UUID, Dict] = {}
    
    async def capture_prompt(
        self,
        prompt_text: str,
        response_text: str,
        project_name: str,
        project_goal: str,
        terminal_type: str = "iTerm2",
        session_id: Optional[UUID] = None,
    ) -> PromptRecord:
        """
        Capture a prompt and its response.
        
        Args:
            prompt_text: The user's prompt
            response_text: The AI's response
            project_name: The name of the project
            project_goal: The goal of the project
            terminal_type: The type of terminal being used
            session_id: Optional session ID to group related prompts
            
        Returns:
            The created prompt record
        """
        # For now, just create a PromptRecord directly
        # In the future, this would integrate with the iTerm2 API to capture prompts
        if not session_id and self.active_sessions:
            # Use the most recent session if none is provided
            session_id = list(self.active_sessions.keys())[-1]
        
        record = PromptRecord(
            prompt_text=prompt_text,
            response_text=response_text,
            project_name=project_name,
            project_goal=project_goal,
            terminal_type=terminal_type,
            session_id=session_id
        )
        
        return record
    
    async def start_session(self) -> UUID:
        """
        Start a new terminal session.
        
        Returns:
            The session ID
        """
        session_id = uuid4()
        self.active_sessions[session_id] = {
            "start_time": asyncio.get_event_loop().time(),
            "status": "active"
        }
        return session_id
    
    async def end_session(self, session_id: UUID) -> bool:
        """
        End a terminal session.
        
        Args:
            session_id: The ID of the session to end
            
        Returns:
            True if the session was ended successfully, False otherwise
        """
        if session_id in self.active_sessions:
            self.active_sessions[session_id]["status"] = "closed"
            return True
        return False


class MockPromptCaptureService(PromptCaptureService):
    """Mock implementation of PromptCaptureService for testing."""
    
    def __init__(self):
        """Initialize the service."""
        self.active_sessions: Dict[UUID, Dict] = {}
    
    async def capture_prompt(
        self,
        prompt_text: str,
        response_text: str,
        project_name: str,
        project_goal: str,
        terminal_type: str = "Mock",
        session_id: Optional[UUID] = None,
    ) -> PromptRecord:
        """
        Capture a prompt and its response.
        
        Args:
            prompt_text: The user's prompt
            response_text: The AI's response
            project_name: The name of the project
            project_goal: The goal of the project
            terminal_type: The type of terminal being used
            session_id: Optional session ID to group related prompts
            
        Returns:
            The created prompt record
        """
        if not session_id:
            session_id = await self.start_session()
        
        record = PromptRecord(
            prompt_text=prompt_text,
            response_text=response_text,
            project_name=project_name,
            project_goal=project_goal,
            terminal_type=terminal_type,
            session_id=session_id
        )
        
        return record
    
    async def start_session(self) -> UUID:
        """
        Start a new terminal session.
        
        Returns:
            The session ID
        """
        session_id = uuid4()
        self.active_sessions[session_id] = {
            "start_time": asyncio.get_event_loop().time(),
            "status": "active"
        }
        return session_id
    
    async def end_session(self, session_id: UUID) -> bool:
        """
        End a terminal session.
        
        Args:
            session_id: The ID of the session to end
            
        Returns:
            True if the session was ended successfully, False otherwise
        """
        if session_id in self.active_sessions:
            self.active_sessions[session_id]["status"] = "closed"
            return True
        return False