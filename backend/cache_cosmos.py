"""
Cosmos DB Cache Manager for Hercule.
Production-ready cache implementation using Azure Cosmos DB.
"""
import os
import logging
import hashlib
from typing import Optional, Dict, Any
from datetime import datetime, timedelta, timezone

logger = logging.getLogger("hercule-api.cache.cosmos")

# Import AnalysisResult - handle import error gracefully for module loading
try:
    from models import AnalysisResult
except ImportError:
    AnalysisResult = None


class CosmosDBCacheManager:
    """
    Cache manager using Azure Cosmos DB for persistence.
    Compatible with the local CacheManager interface.
    """
    
    def __init__(self):
        """Initialize Cosmos DB client."""
        self._initialized = False
        self._container = None
        self._ttl_days = int(os.getenv("CACHE_TTL_DAYS", "30"))
        
        try:
            from azure.cosmos import CosmosClient, PartitionKey
            
            connection_string = os.getenv("COSMOS_CONNECTION_STRING")
            if not connection_string:
                raise ValueError("COSMOS_CONNECTION_STRING not set")
            
            database_name = os.getenv("COSMOS_DATABASE_NAME", "privacy-analyzer")
            container_name = os.getenv("COSMOS_CONTAINER_NAME", "analysis-cache")
            
            # Initialize Cosmos client
            self._client = CosmosClient.from_connection_string(connection_string)
            
            # Get or create database
            self._database = self._client.create_database_if_not_exists(id=database_name)
            
            # Get or create container with TTL enabled
            self._container = self._database.create_container_if_not_exists(
                id=container_name,
                partition_key=PartitionKey(path="/id"),
                default_ttl=self._ttl_days * 24 * 60 * 60  # TTL in seconds
            )
            
            self._initialized = True
            logger.info(f"🌐 Cosmos DB cache initialized: {database_name}/{container_name}")
            
        except ImportError:
            logger.error("azure-cosmos package not installed. Run: pip install azure-cosmos")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize Cosmos DB: {e}")
            raise
    
    @staticmethod
    def generate_key(policy_text: str) -> str:
        """
        Generate SHA-256 hash of normalized policy text.
        
        Args:
            policy_text: The privacy policy text
            
        Returns:
            SHA-256 hash as hexadecimal string
        """
        normalized = policy_text.strip().lower()
        return hashlib.sha256(normalized.encode('utf-8')).hexdigest()
    
    @staticmethod
    def generate_url_key(url: str) -> str:
        """
        Generate SHA-256 hash of normalized URL/domain.
        
        Args:
            url: The URL to generate key for
            
        Returns:
            SHA-256 hash as hexadecimal string prefixed with 'url:'
        """
        from urllib.parse import urlparse
        
        if not url.startswith('http'):
            url = f'https://{url}'
        
        parsed = urlparse(url)
        domain = parsed.netloc.lower().replace('www.', '')
        
        path = parsed.path.strip('/')
        if path:
            normalized = f"{domain}/{path}"
        else:
            normalized = domain
        
        return 'url:' + hashlib.sha256(normalized.encode('utf-8')).hexdigest()
    
    @staticmethod
    def generate_domain_key(url: str) -> str:
        """
        Generate SHA-256 hash of just the base domain.
        Used for domain-level cache hits.

        Args:
            url: The URL to extract domain from

        Returns:
            SHA-256 hash as hexadecimal string prefixed with 'domain:'
        """
        from urllib.parse import urlparse
        
        if not url.startswith('http'):
            url = f'https://{url}'
        
        parsed = urlparse(url)
        domain = parsed.netloc.lower().replace('www.', '')
        
        # Extract base domain
        parts = domain.split('.')
        if len(parts) > 2:
            if parts[-2] in ('co', 'com', 'org', 'net', 'gov', 'edu'):
                base_domain = '.'.join(parts[-3:])
            else:
                base_domain = '.'.join(parts[-2:])
        else:
            base_domain = domain
        
        return 'domain:' + hashlib.sha256(base_domain.encode('utf-8')).hexdigest()
    
    def get(self, cache_key: str) -> Optional['AnalysisResult']:
        """
        Retrieve cached analysis result from Cosmos DB.
        
        Args:
            cache_key: SHA-256 hash key
            
        Returns:
            AnalysisResult if found and valid, None otherwise
        """
        if not self._initialized or not self._container:
            return None
        
        try:
            # Query for the item
            query = "SELECT * FROM c WHERE c.id = @id"
            parameters = [{"name": "@id", "value": cache_key}]
            
            items = list(self._container.query_items(
                query=query,
                parameters=parameters,
                enable_cross_partition_query=True
            ))
            
            if not items:
                return None
            
            cached_entry = items[0]
            
            # Check TTL (Cosmos DB handles this, but double-check)
            try:
                cached_timestamp = datetime.fromisoformat(cached_entry["timestamp"])
                if datetime.now(timezone.utc) - cached_timestamp > timedelta(days=self._ttl_days):
                    # Expired - delete
                    self._container.delete_item(item=cache_key, partition_key=cache_key)
                    return None
            except (KeyError, ValueError):
                return None
            
            # Convert to AnalysisResult
            if AnalysisResult is None:
                from models import AnalysisResult as AR
                return AR(**cached_entry["result"])
            
            return AnalysisResult(**cached_entry["result"])
            
        except Exception as e:
            logger.warning(f"Cosmos DB get error: {e}")
            return None
    
    def set(self, cache_key: str, result: 'AnalysisResult') -> None:
        """
        Store analysis result in Cosmos DB.
        
        Args:
            cache_key: SHA-256 hash key
            result: AnalysisResult to cache
        """
        if not self._initialized or not self._container:
            return
        
        try:
            item = {
                "id": cache_key,
                "result": result.model_dump(mode='json'),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "cache_key": cache_key
            }
            
            # Upsert (create or update)
            self._container.upsert_item(item)
            logger.debug(f"Cached result in Cosmos DB: {cache_key[:12]}...")
            
        except Exception as e:
            logger.warning(f"Cosmos DB set error: {e}")
    
    def clear(self) -> None:
        """Clear all cached entries (expensive operation)."""
        if not self._initialized or not self._container:
            return
        
        try:
            # Query all items
            items = list(self._container.query_items(
                query="SELECT c.id FROM c",
                enable_cross_partition_query=True
            ))
            
            # Delete each item
            for item in items:
                self._container.delete_item(item=item["id"], partition_key=item["id"])
            
            logger.info(f"Cleared {len(items)} items from Cosmos DB cache")
            
        except Exception as e:
            logger.warning(f"Cosmos DB clear error: {e}")
    
    def size(self) -> int:
        """Return approximate number of cached entries."""
        if not self._initialized or not self._container:
            return 0
        
        try:
            items = list(self._container.query_items(
                query="SELECT VALUE COUNT(1) FROM c",
                enable_cross_partition_query=True
            ))
            return items[0] if items else 0
        except Exception:
            return 0
