"""MongoDB Client Provider — initializes and returns a shared async database instance ( singleton)."""
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient
from app.config import SETTINGS, logger

mongo_client: Optional[AsyncIOMotorClient] = None
database = None

#Return the MongoDB database instance (singleton)
def get_db():
    global mongo_client, database
    if database is None:
        mongo_client = AsyncIOMotorClient(SETTINGS.MONGODB_URI)
        database = mongo_client.get_default_database()
        logger.info("MongoDB connected", db=database.name)
    return database
