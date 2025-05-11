"""Terminal monitoring implementation."""

import asyncio
import logging
import os
import re
import time
from typing import Dict, Optional
from uuid import UUID, uuid4

from app.domain.models import PromptRecord
from app.domain.repositories import PromptRepository
from app.domain.services import PromptCaptureService
from app.settings import Settings

logger = logging.getLogger(__name__)


class TerminalMonitor:
    """Base class for terminal monitors."""

    def __init__(self, repository: PromptRepository, settings: Settings):
        """
        Initialize the terminal monitor.
        
        Args:
            repository: Repository for storing prompt records
            settings: Application settings
        """
        self.repository = repository
        self.settings = settings
        self.active_sessions: Dict[UUID, Dict] = {}
        self.current_session_id: Optional[UUID] = None
    
    async def start_session(self) -> UUID:
        """
        Start a new terminal session.
        
        Returns:
            Session ID
        """
        session_id = uuid4()
        self.active_sessions[session_id] = {
            "start_time": time.time(),
            "status": "active",
            "prompts": []
        }
        self.current_session_id = session_id
        logger.info(f"Started terminal session with ID {session_id}")
        return session_id
    
    async def end_session(self, session_id: UUID) -> bool:
        """
        End a terminal session.
        
        Args:
            session_id: Session ID
            
        Returns:
            Success flag
        """
        if session_id in self.active_sessions:
            self.active_sessions[session_id]["status"] = "closed"
            logger.info(f"Ended terminal session with ID {session_id}")
            if self.current_session_id == session_id:
                self.current_session_id = None
            return True
        return False
    
    async def capture_prompt(
        self,
        prompt_text: str,
        response_text: str,
        project_name: str,
        project_goal: str,
        terminal_type: str = "generic",
        session_id: Optional[UUID] = None,
    ) -> PromptRecord:
        """
        Create a new prompt record.
        
        Args:
            prompt_text: User prompt text
            response_text: AI response text
            project_name: Project name
            project_goal: Project goal
            terminal_type: Terminal type
            session_id: Session ID
            
        Returns:
            Created prompt record
        """
        if not session_id:
            if not self.current_session_id:
                session_id = await self.start_session()
            else:
                session_id = self.current_session_id
        
        record = PromptRecord(
            prompt_text=prompt_text,
            response_text=response_text,
            project_name=project_name,
            project_goal=project_goal,
            terminal_type=terminal_type,
            session_id=session_id
        )
        
        logger.info(f"Captured prompt for session {session_id}: {prompt_text[:50]}...")
        
        # Save the prompt to the repository
        await self.repository.add(record)
        
        return record


class MockPromptCaptureService(PromptCaptureService):
    """Mock implementation of PromptCaptureService for testing."""
    
    def __init__(self, repository: PromptRepository, settings: Settings):
        """
        Initialize the service.
        
        Args:
            repository: Repository for storing prompts
            settings: Application settings
        """
        self.repository = repository
        self.settings = settings
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
        
        # Save to repository
        await self.repository.add(record)
        
        return record
    
    async def start_session(self) -> UUID:
        """
        Start a new terminal session.
        
        Returns:
            The session ID
        """
        session_id = uuid4()
        self.active_sessions[session_id] = {
            "start_time": time.time(),
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


async def generate_mock_data(repository: PromptRepository, settings: Settings, count: int = 5) -> None:
    """
    Generate mock data for testing.
    
    Args:
        repository: Repository for storing prompts
        settings: Application settings
        count: Number of mock prompts to generate
    """
    service = MockPromptCaptureService(repository, settings)
    session_id = await service.start_session()
    
    # Sample prompts and responses
    samples = [
        (
            "Write a function to calculate Fibonacci numbers in Python.",
            """Here's a Python function to calculate Fibonacci numbers:

```python
def fibonacci(n):
    if n <= 0:
        return 0
    elif n == 1:
        return 1
    else:
        return fibonacci(n-1) + fibonacci(n-2)
```

This is a recursive implementation. For large values of n, you might want to use a more efficient approach:

```python
def fibonacci_efficient(n):
    if n <= 0:
        return 0
    elif n == 1:
        return 1
    
    a, b = 0, 1
    for _ in range(2, n+1):
        a, b = b, a + b
    return b
```

The second implementation has O(n) time complexity, while the recursive version has exponential time complexity."""
        ),
        (
            "Explain the concept of dependency injection.",
            """Dependency Injection (DI) is a design pattern that implements Inversion of Control (IoC) for resolving dependencies. It allows you to "inject" the dependencies a class needs from the outside rather than having the class create or find those dependencies itself.

Key benefits of dependency injection include:

1. **Decoupling**: Classes are not responsible for creating their dependencies, making them more loosely coupled.

2. **Testability**: You can easily mock or stub dependencies during unit testing.

3. **Flexibility**: You can change implementations without modifying the dependent classes.

4. **Maintainability**: Code becomes more modular and easier to maintain.

There are three common types of dependency injection:

1. **Constructor Injection**: Dependencies are provided through the class constructor.
2. **Setter Injection**: Dependencies are set through setter methods.
3. **Interface Injection**: The dependency provides an injector method that will inject the dependency into any client passed to it.

In Python, DI can be implemented using libraries like `dependency-injector`, `injector`, or manually through constructor parameters."""
        ),
    ]
    
    for i in range(count):
        idx = i % len(samples)
        prompt_text, response_text = samples[idx]
        
        await service.capture_prompt(
            prompt_text=prompt_text,
            response_text=response_text,
            project_name=settings.PROJECT_NAME,
            project_goal=settings.PROJECT_GOAL,
            terminal_type="Mock",
            session_id=session_id
        )
    
    await service.end_session(session_id)
    
    logger.info(f"Generated {count} mock prompt records")


class TerminalMonitorManager:
    """
    Manager for terminal monitors.
    Responsible for starting and stopping monitors.
    """
    
    def __init__(self, repository: PromptRepository, settings: Settings):
        """
        Initialize the manager.
        
        Args:
            repository: Repository for storing prompts
            settings: Application settings
        """
        self.repository = repository
        self.settings = settings
        self.monitors = {}
        self.tasks = {}
    
    async def stop_all(self) -> None:
        """Stop all monitors."""
        for monitor_id in list(self.tasks.keys()):
            await self.stop_monitor(monitor_id)
        
        logger.info("Stopped all monitors")
    
    async def stop_monitor(self, monitor_id: UUID) -> bool:
        """
        Stop a monitor.
        
        Args:
            monitor_id: Monitor ID
            
        Returns:
            Success flag
        """
        if monitor_id in self.tasks:
            task = self.tasks[monitor_id]
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            
            del self.tasks[monitor_id]
            del self.monitors[monitor_id]
            
            logger.info(f"Stopped monitor with ID {monitor_id}")
            return True
        
        return False
    
    async def generate_mock_data(self, count: int = 5) -> None:
        """
        Generate mock data for testing.
        
        Args:
            count: Number of mock prompts to generate
        """
        await generate_mock_data(self.repository, self.settings, count)