"""Domain services."""

from typing import List, Optional, Protocol
from uuid import UUID

from app.domain.models import PromptRecord


class PromptCaptureService(Protocol):
    """Service for capturing prompts from terminals."""
    
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
        ...
    
    async def start_session(self) -> UUID:
        """
        Start a new terminal session.
        
        Returns:
            The session ID
        """
        ...
    
    async def end_session(self, session_id: UUID) -> bool:
        """
        End a terminal session.
        
        Args:
            session_id: The ID of the session to end
            
        Returns:
            True if the session was ended successfully, False otherwise
        """
        ...