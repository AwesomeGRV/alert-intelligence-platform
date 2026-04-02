from elasticsearch import AsyncElasticsearch
from elasticsearch.helpers import async_bulk
import structlog
from typing import Dict, List, Any, Optional
from datetime import datetime

from .config import settings

logger = structlog.get_logger()

class ElasticsearchClient:
    def __init__(self):
        self.client = None
        self.index_prefix = settings.ELASTICSEARCH_INDEX_PREFIX
    
    async def connect(self):
        try:
            self.client = AsyncElasticsearch([settings.ELASTICSEARCH_URL])
            await self.client.ping()
            logger.info("Connected to Elasticsearch")
        except Exception as e:
            logger.error("Failed to connect to Elasticsearch", error=str(e))
            raise
    
    async def disconnect(self):
        if self.client:
            await self.client.close()
    
    async def create_index(self, index_name: str, mapping: Dict[str, Any]):
        try:
            full_index_name = f"{self.index_prefix}_{index_name}"
            if not await self.client.indices.exists(index=full_index_name):
                await self.client.indices.create(
                    index=full_index_name,
                    body={"mappings": mapping}
                )
                logger.info(f"Created Elasticsearch index: {full_index_name}")
        except Exception as e:
            logger.error(f"Failed to create index {index_name}", error=str(e))
            raise
    
    async def index_document(self, index_name: str, doc_id: str, document: Dict[str, Any]):
        try:
            full_index_name = f"{self.index_prefix}_{index_name}"
            await self.client.index(
                index=full_index_name,
                id=doc_id,
                body=document
            )
        except Exception as e:
            logger.error(f"Failed to index document {doc_id} in {index_name}", error=str(e))
            raise
    
    async def search(self, index_name: str, query: Dict[str, Any], size: int = 100) -> Dict[str, Any]:
        try:
            full_index_name = f"{self.index_prefix}_{index_name}"
            response = await self.client.search(
                index=full_index_name,
                body=query,
                size=size
            )
            return response
        except Exception as e:
            logger.error(f"Failed to search in {index_name}", error=str(e))
            raise
    
    async def aggregate(self, index_name: str, query: Dict[str, Any]) -> Dict[str, Any]:
        try:
            full_index_name = f"{self.index_prefix}_{index_name}"
            response = await self.client.search(
                index=full_index_name,
                body=query,
                size=0
            )
            return response.get('aggregations', {})
        except Exception as e:
            logger.error(f"Failed to aggregate in {index_name}", error=str(e))
            raise
    
    async def bulk_index(self, index_name: str, documents: List[Dict[str, Any]]):
        try:
            full_index_name = f"{self.index_prefix}_{index_name}"
            actions = []
            for doc in documents:
                actions.append({
                    "_index": full_index_name,
                    "_id": doc.get('id'),
                    "_source": doc
                })
            
            await async_bulk(self.client, actions)
            logger.info(f"Bulk indexed {len(documents)} documents in {index_name}")
        except Exception as e:
            logger.error(f"Failed to bulk index in {index_name}", error=str(e))
            raise

# Elasticsearch mappings
ALERTS_MAPPING = {
    "properties": {
        "alert_id": {"type": "keyword"},
        "source": {"type": "keyword"},
        "service": {"type": "keyword"},
        "severity": {"type": "keyword"},
        "status": {"type": "keyword"},
        "timestamp": {"type": "date"},
        "description": {"type": "text"},
        "tags": {"type": "keyword"},
        "metrics_snapshot": {"type": "object"},
        "cluster_id": {"type": "keyword"},
        "fingerprint": {"type": "keyword"},
        "dedup_count": {"type": "integer"},
        "first_seen": {"type": "date"},
        "last_seen": {"type": "date"},
        "created_at": {"type": "date"},
        "updated_at": {"type": "date"}
    }
}

INCIDENTS_MAPPING = {
    "properties": {
        "cluster_id": {"type": "keyword"},
        "title": {"type": "text"},
        "description": {"type": "text"},
        "severity": {"type": "keyword"},
        "status": {"type": "keyword"},
        "service": {"type": "keyword"},
        "affected_services": {"type": "keyword"},
        "alert_count": {"type": "integer"},
        "first_alert_time": {"type": "date"},
        "last_alert_time": {"type": "date"},
        "tags": {"type": "keyword"},
        "metrics_impact": {"type": "object"},
        "suggested_root_cause": {"type": "text"},
        "root_cause_type": {"type": "keyword"},
        "confidence_score": {"type": "float"},
        "created_at": {"type": "date"},
        "updated_at": {"type": "date"},
        "assigned_to": {"type": "keyword"}
    }
}

es_client = ElasticsearchClient()

async def init_elasticsearch():
    await es_client.connect()
    await es_client.create_index("alerts", ALERTS_MAPPING)
    await es_client.create_index("incidents", INCIDENTS_MAPPING)
