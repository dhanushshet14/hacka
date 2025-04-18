import json
from typing import Any, Dict, List, Optional, Union
import redis
from motor.motor_asyncio import AsyncIOMotorClient
from confluent_kafka import Producer, Consumer, KafkaError
from loguru import logger

from app.core.config import settings

# MongoDB Connection
async def get_mongodb_client() -> AsyncIOMotorClient:
    """
    Returns a MongoDB client instance
    """
    try:
        client = AsyncIOMotorClient(settings.MONGODB_URI)
        yield client
        client.close()
    except Exception as e:
        logger.error(f"MongoDB connection error: {e}")
        raise

async def get_mongodb_db():
    """
    Returns a MongoDB database instance
    """
    client = AsyncIOMotorClient(settings.MONGODB_URI)
    return client[settings.MONGODB_DB_NAME]

# Redis Connection
def get_redis_connection():
    """
    Returns a Redis connection instance
    """
    try:
        redis_conn = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            password=settings.REDIS_PASSWORD,
            decode_responses=True
        )
        return redis_conn
    except Exception as e:
        logger.error(f"Redis connection error: {e}")
        raise

# Kafka Producer
def get_kafka_producer():
    """
    Returns a Kafka producer instance
    """
    try:
        conf = {
            'bootstrap.servers': settings.KAFKA_BOOTSTRAP_SERVERS,
            'client.id': 'aetherion-producer'
        }
        producer = Producer(conf)
        return producer
    except Exception as e:
        logger.error(f"Kafka producer creation error: {e}")
        raise

# Kafka Consumer
def get_kafka_consumer(topics: List[str]):
    """
    Returns a Kafka consumer instance subscribed to the specified topics
    """
    try:
        conf = {
            'bootstrap.servers': settings.KAFKA_BOOTSTRAP_SERVERS,
            'group.id': settings.KAFKA_CONSUMER_GROUP,
            'auto.offset.reset': 'earliest'
        }
        consumer = Consumer(conf)
        prefixed_topics = [f"{settings.KAFKA_TOPIC_PREFIX}{topic}" for topic in topics]
        consumer.subscribe(prefixed_topics)
        return consumer
    except Exception as e:
        logger.error(f"Kafka consumer creation error: {e}")
        raise

# Session Management with Redis
class SessionManager:
    def __init__(self):
        self.redis = get_redis_connection()
        self.prefix = settings.REDIS_PREFIX
    
    def get_session_key(self, user_id: str) -> str:
        return f"{self.prefix}session:{user_id}"
    
    def save_session(self, user_id: str, data: Dict[str, Any], expiry: int = 3600) -> bool:
        """Save session data with expiry in seconds"""
        key = self.get_session_key(user_id)
        try:
            self.redis.setex(key, expiry, json.dumps(data))
            return True
        except Exception as e:
            logger.error(f"Error saving session: {e}")
            return False
    
    def get_session(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get session data"""
        key = self.get_session_key(user_id)
        try:
            data = self.redis.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"Error retrieving session: {e}")
            return None
    
    def delete_session(self, user_id: str) -> bool:
        """Delete session data"""
        key = self.get_session_key(user_id)
        try:
            self.redis.delete(key)
            return True
        except Exception as e:
            logger.error(f"Error deleting session: {e}")
            return False

# Context Management with Redis
class ContextManager:
    def __init__(self):
        self.redis = get_redis_connection()
        self.prefix = settings.REDIS_PREFIX
    
    def get_context_key(self, context_id: str) -> str:
        return f"{self.prefix}context:{context_id}"
    
    def save_context(self, context_id: str, data: Dict[str, Any], expiry: int = 86400) -> bool:
        """Save context data with expiry in seconds (default 24 hours)"""
        key = self.get_context_key(context_id)
        try:
            self.redis.setex(key, expiry, json.dumps(data))
            return True
        except Exception as e:
            logger.error(f"Error saving context: {e}")
            return False
    
    def get_context(self, context_id: str) -> Optional[Dict[str, Any]]:
        """Get context data"""
        key = self.get_context_key(context_id)
        try:
            data = self.redis.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"Error retrieving context: {e}")
            return None
    
    def update_context(self, context_id: str, data: Dict[str, Any], expiry: int = 86400) -> bool:
        """Update context data with new values"""
        key = self.get_context_key(context_id)
        try:
            existing_data = self.get_context(context_id) or {}
            existing_data.update(data)
            self.redis.setex(key, expiry, json.dumps(existing_data))
            return True
        except Exception as e:
            logger.error(f"Error updating context: {e}")
            return False
    
    def delete_context(self, context_id: str) -> bool:
        """Delete context data"""
        key = self.get_context_key(context_id)
        try:
            self.redis.delete(key)
            return True
        except Exception as e:
            logger.error(f"Error deleting context: {e}")
            return False
