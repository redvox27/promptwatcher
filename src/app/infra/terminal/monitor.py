"""Terminal monitoring implementation."""

import asyncio
import logging
import os
import re
import sys
import time
from typing import Dict, List, Optional
from uuid import UUID, uuid4

from app.domain.models import PromptRecord
from app.domain.repositories import PromptRepository
from app.domain.services import PromptCaptureService
from app.settings import Settings

# Add src to path for local imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))

from src.app.infra.terminal.docker_client import DockerClient
from src.app.infra.terminal.session_detector import TerminalSessionDetector
from src.app.infra.terminal.terminal_device_identifier import TerminalDeviceIdentifier
from src.app.infra.terminal.session_tracking_service import SessionTrackingService
from src.app.infra.terminal.terminal_output_capture import TerminalOutputCapture, TerminalOutputBuffer, TerminalOutputProcessor
from src.app.infra.terminal.conversation_repository_adapter import ConversationRepositoryAdapter
from src.app.infra.terminal.terminal_monitor_coordinator import TerminalMonitorCoordinator, MonitorInfo, MonitorStatus

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
        self._initialize_components()
    
    def _initialize_components(self):
        """Initialize the terminal monitoring components."""
        try:
            # Log environment for debugging
            host_proc = os.environ.get("HOST_PROC", "/proc")
            logger.info(f"Using HOST_PROC path: {host_proc}")
            logger.info(f"Host proc directory exists: {os.path.exists('/host/proc')}")
            
            # Check if we have host access
            has_host_access = os.path.exists('/host/proc') or host_proc != "/proc"
            logger.info(f"Application has host access: {has_host_access}")
            
            # Create Docker client
            self.docker_client = DockerClient()
            
            # Create session detector
            self.session_detector = TerminalSessionDetector(self.docker_client)
            
            # Log session detector configuration
            logger.info(f"Session detector using proc path: {self.session_detector.host_proc}")
            logger.info(f"Session detector direct access enabled: {self.session_detector.use_host_proc}")
            
            # Test session detection
            try:
                sessions = self.session_detector.list_terminal_sessions()
                terminal_count = len([s for s in sessions if s.get("terminal", "?") != "?"])
                logger.info(f"Initial session detection found {terminal_count} terminal sessions")
                
                # Log a sample of sessions for debugging
                for i, session in enumerate(sessions):
                    if i >= 3:  # Only log the first 3 sessions
                        break
                    if session.get("terminal", "?") != "?":
                        logger.info(
                            f"Sample terminal session: PID={session.get('pid')}, "
                            f"Terminal={session.get('terminal')}, "
                            f"Command={session.get('command', '')[:50]}"
                        )
            except Exception as e:
                logger.error(f"Error during initial session detection: {str(e)}")
            
            # Create device identifier
            self.device_identifier = TerminalDeviceIdentifier(self.docker_client)
            
            # Create terminal output capture components
            self.output_capture = TerminalOutputCapture(self.docker_client)
            self.output_processor = TerminalOutputProcessor()
            
            # Create repository adapter
            self.repository_adapter = ConversationRepositoryAdapter(self.repository)
            
            # Create session tracking service
            self.tracking_service = SessionTrackingService(
                self.session_detector,
                self.device_identifier,
                scan_interval=self.settings.MONITORING_INTERVAL
            )
            
            # Create terminal monitor coordinator
            self.coordinator = TerminalMonitorCoordinator(
                self.docker_client,
                self.session_detector,
                self.device_identifier,
                self.tracking_service,
                output_capture=self.output_capture,
                output_processor=self.output_processor,
                repository_adapter=self.repository_adapter,
                settings={
                    "project_name": self.settings.PROJECT_NAME,
                    "project_goal": self.settings.PROJECT_GOAL,
                    "monitoring_interval": self.settings.MONITORING_INTERVAL,
                    "buffer_size": 100000,  # 100KB per session
                    "capture_interval": self.settings.MONITORING_INTERVAL / 2  # Half of monitoring interval
                }
            )
            
            logger.info("Initialized terminal monitoring components")
            
        except Exception as e:
            logger.error(f"Error initializing monitoring components: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            # Fall back to mock implementation
            self.coordinator = None
    
    async def start_monitor(self) -> UUID:
        """
        Start a new terminal monitor.
        
        Returns:
            Monitor ID
        """
        try:
            if self.coordinator:
                # Use the real implementation
                monitor_id = self.coordinator.start_monitor()
                monitor_uuid = UUID(monitor_id)
                self.monitors[monitor_uuid] = {
                    "id": monitor_id,
                    "start_time": time.time(),
                    "status": "active"
                }
                
                # Create a dummy task for compatibility
                self.tasks[monitor_uuid] = asyncio.create_task(self._dummy_task())
                
                logger.info(f"Started real terminal monitor with ID {monitor_id}")
                return monitor_uuid
            else:
                # Fall back to mock implementation
                monitor_id = uuid4()
                self.monitors[monitor_id] = {
                    "start_time": time.time(),
                    "status": "active"
                }
                
                # Generate mock data
                self.tasks[monitor_id] = asyncio.create_task(
                    self._run_mock_monitor(monitor_id)
                )
                
                logger.info(f"Started mock terminal monitor with ID {monitor_id}")
                return monitor_id
        except Exception as e:
            logger.error(f"Error starting monitor: {str(e)}")
            # Create a fallback mock monitor
            monitor_id = uuid4()
            self.monitors[monitor_id] = {
                "start_time": time.time(),
                "status": "active"
            }
            return monitor_id
    
    async def stop_monitor(self, monitor_id: UUID) -> bool:
        """
        Stop a monitor.
        
        Args:
            monitor_id: Monitor ID
            
        Returns:
            Success flag
        """
        try:
            if self.coordinator and monitor_id in self.monitors:
                # Use the real implementation
                coordinator_id = self.monitors[monitor_id]["id"]
                success = self.coordinator.stop_monitor(coordinator_id)
                
                if success:
                    if monitor_id in self.tasks:
                        task = self.tasks[monitor_id]
                        task.cancel()
                        try:
                            await task
                        except asyncio.CancelledError:
                            pass
                        del self.tasks[monitor_id]
                    
                    del self.monitors[monitor_id]
                    logger.info(f"Stopped real terminal monitor with ID {monitor_id}")
                    return True
            
            # Fall back to mock implementation or if real implementation failed
            if monitor_id in self.tasks:
                task = self.tasks[monitor_id]
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                
                del self.tasks[monitor_id]
                del self.monitors[monitor_id]
                
                logger.info(f"Stopped mock terminal monitor with ID {monitor_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error stopping monitor: {str(e)}")
            return False
    
    async def stop_all(self) -> None:
        """Stop all monitors."""
        for monitor_id in list(self.tasks.keys()):
            await self.stop_monitor(monitor_id)
        
        logger.info("Stopped all monitors")
    
    async def get_status(self, monitor_id: UUID) -> Dict:
        """
        Get the status of a monitor.
        
        Args:
            monitor_id: Monitor ID
            
        Returns:
            Status information
        """
        try:
            if self.coordinator and monitor_id in self.monitors:
                # Use the real implementation
                coordinator_id = self.monitors[monitor_id]["id"]
                monitor_info = self.coordinator.get_monitor_status(coordinator_id)
                
                if monitor_info:
                    return {
                        "id": str(monitor_id),
                        "status": monitor_info.status.value,
                        "start_time": monitor_info.start_time.isoformat(),
                        "active_sessions": len(monitor_info.active_sessions),
                        "prompts_captured": monitor_info.prompts_captured
                    }
            
            # Fall back to mock implementation or if real implementation failed
            if monitor_id in self.monitors:
                return {
                    "id": str(monitor_id),
                    "status": self.monitors[monitor_id]["status"],
                    "start_time": self.monitors[monitor_id]["start_time"],
                    "active_sessions": 0,
                    "prompts_captured": 0
                }
            
            return {}
            
        except Exception as e:
            logger.error(f"Error getting monitor status: {str(e)}")
            return {}
    
    async def get_all_statuses(self) -> List[Dict]:
        """
        Get the status of all monitors.
        
        Returns:
            List of status information dictionaries
        """
        result = []
        for monitor_id in self.monitors:
            status = await self.get_status(monitor_id)
            if status:
                result.append(status)
        return result
    
    async def _run_mock_monitor(self, monitor_id: UUID) -> None:
        """
        Run a mock monitor for testing.
        
        Args:
            monitor_id: Monitor ID
        """
        try:
            # Generate some mock data initially
            await generate_mock_data(self.repository, self.settings, count=2)
            
            # Continue generating data at intervals
            while True:
                await asyncio.sleep(60)  # Generate more data every minute
                await generate_mock_data(self.repository, self.settings, count=1)
                
        except asyncio.CancelledError:
            logger.info(f"Mock monitor {monitor_id} cancelled")
        except Exception as e:
            logger.error(f"Error in mock monitor: {str(e)}")
    
    async def _dummy_task(self) -> None:
        """Dummy task that does nothing but can be cancelled."""
        while True:
            await asyncio.sleep(3600)  # Sleep for a long time
    
    async def generate_mock_data(self, count: int = 5) -> None:
        """
        Generate mock data for testing.
        
        Args:
            count: Number of mock prompts to generate
        """
        await generate_mock_data(self.repository, self.settings, count)