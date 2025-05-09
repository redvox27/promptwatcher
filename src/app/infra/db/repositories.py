"""Repository implementations."""

from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

from opensearchpy import AsyncOpenSearch, NotFoundError

from app.domain.models import PromptRecord
from app.domain.repositories import PromptRepository


class OpenSearchPromptRepository(PromptRepository):
    """OpenSearch implementation of the prompt repository."""
    
    INDEX_NAME = "prompt_records"
    
    def __init__(self, client: AsyncOpenSearch):
        """Initialize the repository with an OpenSearch client."""
        self.client = client
    
    async def get(self, id: UUID) -> PromptRecord:
        """
        Get prompt record by ID.
        
        Args:
            id: Record ID
            
        Returns:
            The prompt record
            
        Raises:
            KeyError: If the record doesn't exist
        """
        result = await self.get_optional(id)
        if result is None:
            raise KeyError(f"PromptRecord with ID {id} not found")
        return result
    
    async def get_optional(self, id: UUID) -> Optional[PromptRecord]:
        """
        Get prompt record by ID or None if not found.
        
        Args:
            id: Record ID
            
        Returns:
            The prompt record or None
        """
        try:
            response = await self.client.get(
                index=self.INDEX_NAME,
                id=str(id)
            )
            
            source = response["_source"]
            return self._map_to_domain(source, UUID(response["_id"]))
        except NotFoundError:
            return None
        except Exception as e:
            # Log error here
            print(f"Error getting prompt record: {e}")
            return None
    
    async def find_all(self, limit: int = 100, offset: int = 0) -> List[PromptRecord]:
        """
        Find all prompt records with pagination.
        
        Args:
            limit: Maximum number of records to return
            offset: Number of records to skip
            
        Returns:
            List of prompt records
        """
        try:
            response = await self.client.search(
                index=self.INDEX_NAME,
                body={
                    "query": {"match_all": {}},
                    "sort": [{"timestamp": {"order": "desc"}}],
                    "from": offset,
                    "size": limit
                }
            )
            
            hits = response["hits"]["hits"]
            return [self._map_to_domain(hit["_source"], UUID(hit["_id"])) for hit in hits]
        except Exception as e:
            # Log error here
            print(f"Error finding all prompt records: {e}")
            return []
    
    async def find_by_project(self, project_name: str, limit: int = 100, offset: int = 0) -> List[PromptRecord]:
        """
        Find prompt records by project name.
        
        Args:
            project_name: The name of the project
            limit: Maximum number of records to return
            offset: Number of records to skip
            
        Returns:
            List of prompt records
        """
        try:
            response = await self.client.search(
                index=self.INDEX_NAME,
                body={
                    "query": {"match": {"project_name": project_name}},
                    "sort": [{"timestamp": {"order": "desc"}}],
                    "from": offset,
                    "size": limit
                }
            )
            
            hits = response["hits"]["hits"]
            return [self._map_to_domain(hit["_source"], UUID(hit["_id"])) for hit in hits]
        except Exception as e:
            # Log error here
            print(f"Error finding prompt records by project: {e}")
            return []
    
    async def add(self, entity: PromptRecord) -> PromptRecord:
        """
        Add a new prompt record.
        
        Args:
            entity: The prompt record to add
            
        Returns:
            The added prompt record
        """
        try:
            document = self._map_to_document(entity)
            
            await self.client.index(
                index=self.INDEX_NAME,
                id=str(entity.id),
                body=document,
                refresh=True
            )
            
            return entity
        except Exception as e:
            # Log error here
            print(f"Error adding prompt record: {e}")
            raise
    
    async def update(self, entity: PromptRecord) -> PromptRecord:
        """
        Update an existing prompt record.
        
        Args:
            entity: The prompt record to update
            
        Returns:
            The updated prompt record
        """
        try:
            document = self._map_to_document(entity)
            
            await self.client.update(
                index=self.INDEX_NAME,
                id=str(entity.id),
                body={"doc": document},
                refresh=True
            )
            
            return entity
        except Exception as e:
            # Log error here
            print(f"Error updating prompt record: {e}")
            raise
    
    async def delete(self, id: UUID) -> None:
        """
        Delete a prompt record.
        
        Args:
            id: The ID of the prompt record to delete
        """
        try:
            await self.client.delete(
                index=self.INDEX_NAME,
                id=str(id),
                refresh=True
            )
        except Exception as e:
            # Log error here
            print(f"Error deleting prompt record: {e}")
            raise
    
    async def add_label(self, id: UUID, label: str) -> bool:
        """
        Add a label to a prompt record.
        
        Args:
            id: The ID of the prompt record
            label: The label to add
            
        Returns:
            True if the label was added successfully, False otherwise
        """
        try:
            # Get the current record
            record = await self.get_optional(id)
            
            if record is None:
                return False
            
            # Add the label if it's not already present
            if label not in record.labels:
                record.labels.append(label)
                await self.update(record)
            
            return True
        except Exception as e:
            # Log error here
            print(f"Error adding label to prompt record: {e}")
            return False
    
    def _map_to_document(self, entity: PromptRecord) -> Dict:
        """
        Map a domain entity to a document for storage.
        
        Args:
            entity: The prompt record to map
            
        Returns:
            A dictionary suitable for storing in OpenSearch
        """
        return {
            "prompt_text": entity.prompt_text,
            "response_text": entity.response_text,
            "project_name": entity.project_name,
            "project_goal": entity.project_goal,
            "timestamp": entity.timestamp.isoformat(),
            "terminal_type": entity.terminal_type,
            "session_id": str(entity.session_id) if entity.session_id else None,
            "labels": entity.labels,
            "metadata": entity.metadata
        }
    
    def _map_to_domain(self, source: Dict, id: UUID) -> PromptRecord:
        """
        Map a document from storage to a domain entity.
        
        Args:
            source: The document source from OpenSearch
            id: The document ID
            
        Returns:
            A PromptRecord domain entity
        """
        session_id = source.get("session_id")
        
        return PromptRecord(
            id=id,
            prompt_text=source["prompt_text"],
            response_text=source["response_text"],
            project_name=source["project_name"],
            project_goal=source["project_goal"],
            timestamp=datetime.fromisoformat(source["timestamp"]),
            terminal_type=source["terminal_type"],
            session_id=UUID(session_id) if session_id else None,
            labels=source.get("labels", []),
            metadata=source.get("metadata", {})
        )