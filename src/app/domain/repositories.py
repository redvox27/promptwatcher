"""Repository interfaces for the domain layer."""

from typing import List, Optional, Protocol, TypeVar
from uuid import UUID

from src.app.domain.models import PromptRecord

T = TypeVar("T")


class Repository(Protocol[T]):
    """Generic repository interface."""
    
    async def get(self, id: UUID) -> T:
        """Get entity by ID."""
        ...
    
    async def get_optional(self, id: UUID) -> Optional[T]:
        """Get entity by ID or None if not found."""
        ...
    
    async def find_all(self) -> List[T]:
        """Find all entities."""
        ...
    
    async def add(self, entity: T) -> T:
        """Add an entity to the repository."""
        ...
    
    async def update(self, entity: T) -> T:
        """Update an entity in the repository."""
        ...
    
    async def delete(self, id: UUID) -> None:
        """Delete an entity from the repository."""
        ...


class PromptRepository(Repository[PromptRecord]):
    """Repository interface for prompt records."""
    
    async def find_by_project(self, project_name: str, limit: int = 100, offset: int = 0) -> List[PromptRecord]:
        """Find prompt records by project name."""
        ...
    
    async def add_label(self, id: UUID, label: str) -> bool:
        """Add a label to a prompt record."""
        ...