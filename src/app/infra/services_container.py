"""Service container for managing all services."""

from functools import cached_property

from opensearchpy import AsyncOpenSearch

from app.domain.repositories import PromptRepository
from app.domain.services import PromptCaptureService
from app.infra.db.repositories import OpenSearchPromptRepository
from app.infra.terminal.monitor import ITerm2PromptCaptureService, MockPromptCaptureService
from app.settings import Settings


class Services:
    """Container for all services."""
    
    def __init__(
        self,
        settings: Settings,
        opensearch_client: AsyncOpenSearch,
        use_mock: bool = False
    ):
        """
        Initialize the service container.
        
        Args:
            settings: Application settings
            opensearch_client: OpenSearch client
            use_mock: Whether to use mock implementations
        """
        self._settings = settings
        self._opensearch_client = opensearch_client
        self._use_mock = use_mock
    
    @cached_property
    def prompt_repository(self) -> PromptRepository:
        """Get the prompt repository."""
        return OpenSearchPromptRepository(self._opensearch_client)
    
    @cached_property
    def prompt_capture_service(self) -> PromptCaptureService:
        """Get the prompt capture service."""
        if self._use_mock:
            return MockPromptCaptureService()
        return ITerm2PromptCaptureService()