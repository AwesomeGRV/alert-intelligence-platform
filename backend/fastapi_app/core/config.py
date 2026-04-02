from pydantic_settings import BaseSettings
from typing import List
import os

class Settings(BaseSettings):
    # API Settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = False
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "https://localhost:3000"]
    
    # Database Settings
    DATABASE_URL: str = "postgresql+asyncpg://postgres:password@localhost:5432/alert_intelligence"
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 30
    
    # Elasticsearch Settings
    ELASTICSEARCH_URL: str = "http://localhost:9200"
    ELASTICSEARCH_INDEX_PREFIX: str = "alerts"
    
    # Redis Settings
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_CACHE_TTL: int = 3600
    
    # Kafka Settings
    KAFKA_BOOTSTRAP_SERVERS: List[str] = ["localhost:9092"]
    KAFKA_TOPIC_ALERTS: str = "alerts"
    KAFKA_TOPIC_INCIDENTS: str = "incidents"
    
    # Security Settings
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # External Integrations
    SLACK_BOT_TOKEN: str = ""
    SLACK_SIGNING_SECRET: str = ""
    TEAMS_WEBHOOK_URL: str = ""
    
    # Monitoring
    PROMETHEUS_PORT: int = 9090
    JAEGER_ENDPOINT: str = ""
    
    # Alert Processing
    ALERT_DEDUP_WINDOW_MINUTES: int = 5
    CLUSTERING_SIMILARITY_THRESHOLD: float = 0.8
    MAX_ALERTS_PER_CLUSTER: int = 100
    
    # ML Settings
    ML_MODEL_PATH: str = "./models"
    ENABLE_ML_CORRELATION: bool = False
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
