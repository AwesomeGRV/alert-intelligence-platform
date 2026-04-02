import json
import structlog
from typing import Dict, Any
from kafka import KafkaProducer
from kafka.errors import KafkaError

from ..core.config import settings

logger = structlog.get_logger()

class KafkaProducerService:
    def __init__(self):
        self.producer = None
        self.bootstrap_servers = settings.KAFKA_BOOTSTRAP_SERVERS
        self.alerts_topic = settings.KAFKA_TOPIC_ALERTS
        self.incidents_topic = settings.KAFKA_TOPIC_INCIDENTS
    
    def _get_producer(self):
        if self.producer is None:
            self.producer = KafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                key_serializer=lambda k: k.encode('utf-8') if k else None,
                acks='all',
                retries=3,
                batch_size=16384,
                linger_ms=10,
                buffer_memory=33554432
            )
        return self.producer
    
    async def send_alert(self, alert: Dict[str, Any]):
        try:
            producer = self._get_producer()
            
            # Send to alerts topic
            future = producer.send(
                topic=self.alerts_topic,
                key=alert.get('alert_id'),
                value=alert
            )
            
            # Block for a maximum of 1 second to see if send succeeded
            record_metadata = future.get(timeout=1)
            
            logger.info(
                f"Alert sent to Kafka",
                topic=record_metadata.topic,
                partition=record_metadata.partition,
                offset=record_metadata.offset,
                alert_id=alert.get('alert_id')
            )
            
        except KafkaError as e:
            logger.error(f"Failed to send alert to Kafka: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error sending alert to Kafka: {str(e)}")
            raise
    
    async def send_incident(self, incident: Dict[str, Any]):
        try:
            producer = self._get_producer()
            
            # Send to incidents topic
            future = producer.send(
                topic=self.incidents_topic,
                key=incident.get('cluster_id'),
                value=incident
            )
            
            # Block for a maximum of 1 second to see if send succeeded
            record_metadata = future.get(timeout=1)
            
            logger.info(
                f"Incident sent to Kafka",
                topic=record_metadata.topic,
                partition=record_metadata.partition,
                offset=record_metadata.offset,
                cluster_id=incident.get('cluster_id')
            )
            
        except KafkaError as e:
            logger.error(f"Failed to send incident to Kafka: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error sending incident to Kafka: {str(e)}")
            raise
    
    def close(self):
        if self.producer:
            self.producer.flush()
            self.producer.close()
            logger.info("Kafka producer closed")
