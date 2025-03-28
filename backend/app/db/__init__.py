from motor.motor_asyncio import AsyncIOMotorClient
import redis
from loguru import logger

from app.core.config import settings

# MongoDB connection
async def init_mongodb():
    """Initialize MongoDB connection"""
    try:
        client = AsyncIOMotorClient(settings.MONGODB_URI)
        db = client[settings.MONGODB_DB_NAME]
        await db.command('ping')
        logger.info(f"Connected to MongoDB at {settings.MONGODB_URI}")
        return db
    except Exception as e:
        logger.error(f"MongoDB connection error: {e}")
        raise

# Redis connection
def init_redis():
    """Initialize Redis connection"""
    try:
        redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            password=settings.REDIS_PASSWORD,
            decode_responses=True
        )
        redis_client.ping()
        logger.info(f"Connected to Redis at {settings.REDIS_HOST}:{settings.REDIS_PORT}")
        return redis_client
    except Exception as e:
        logger.error(f"Redis connection error: {e}")
        raise
