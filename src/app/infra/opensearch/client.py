"""OpenSearch client module."""

import asyncio
import logging
from typing import Optional

from opensearchpy import AsyncOpenSearch
from opensearchpy.exceptions import ConnectionError

from app.settings import Settings

logger = logging.getLogger(__name__)


class OpenSearchClient:
    """OpenSearch client factory."""
    
    @staticmethod
    async def create_client(settings: Settings, max_retries: int = 5, retry_delay: int = 5) -> AsyncOpenSearch:
        """
        Create an AsyncOpenSearch client with retry mechanism.
        
        Args:
            settings: Application settings
            max_retries: Maximum number of connection retries
            retry_delay: Delay between retries in seconds
            
        Returns:
            An AsyncOpenSearch client
        """
        auth = None
        if settings.OPENSEARCH_USERNAME and settings.OPENSEARCH_PASSWORD:
            auth = (settings.OPENSEARCH_USERNAME, settings.OPENSEARCH_PASSWORD)
        
        hosts = [f"{settings.OPENSEARCH_HOST}:{settings.OPENSEARCH_PORT}"]
        
        client = AsyncOpenSearch(
            hosts=hosts,
            http_auth=auth,
            use_ssl=settings.OPENSEARCH_USE_SSL,
            verify_certs=settings.OPENSEARCH_VERIFY_CERTS,
            ssl_show_warn=False,
        )
        
        # Attempt to connect with retries
        for attempt in range(max_retries):
            try:
                # Test the connection by making a simple request
                await client.info()
                logger.info(f"Successfully connected to OpenSearch at {hosts}")
                return client
            except ConnectionError as e:
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (attempt + 1)
                    logger.warning(f"Connection to OpenSearch failed (attempt {attempt + 1}/{max_retries}). "
                                  f"Retrying in {wait_time} seconds... Error: {str(e)}")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"Failed to connect to OpenSearch after {max_retries} attempts: {str(e)}")
                    raise
        
        # This should not be reached due to the exception in the loop, but just in case
        return client
    
    @staticmethod
    async def create_indices(client: AsyncOpenSearch) -> None:
        """
        Create required indices if they don't exist.
        
        Args:
            client: The OpenSearch client
        """
        try:
            # Check if prompt_records index exists
            exists = await client.indices.exists(index="prompt_records")
            
            if not exists:
                logger.info("Creating prompt_records index")
                # Create prompt_records index with mapping
                await client.indices.create(
                    index="prompt_records",
                    body={
                        "settings": {
                            "number_of_shards": 1,
                            "number_of_replicas": 1
                        },
                        "mappings": {
                            "properties": {
                                "prompt_text": {"type": "text"},
                                "response_text": {"type": "text"},
                                "project_name": {"type": "keyword"},
                                "project_goal": {"type": "text"},
                                "timestamp": {"type": "date"},
                                "terminal_type": {"type": "keyword"},
                                "session_id": {"type": "keyword"},
                                "labels": {"type": "keyword"},
                                "metadata": {"type": "object"}
                            }
                        }
                    }
                )
                logger.info("prompt_records index created successfully")
            else:
                logger.info("prompt_records index already exists")
        except Exception as e:
            logger.error(f"Error creating indices: {str(e)}")
            raise