"""Checkpointer setup — encrypted MongoDB-backed LangGraph state persistence."""
from langgraph.checkpoint.mongodb import MongoDBSaver
from langgraph.checkpoint.serde.encrypted import EncryptedSerializer
from pymongo import MongoClient

from app.config import SETTINGS, logger
from app.utils.crypto import FernetCipher

checkpointer: MongoDBSaver | None = None  # LangGraph checkpoint handler for thread state
mongo_client: MongoClient | None = None   # Sync MongoDB client used internally by checkpointer
serde = EncryptedSerializer(cipher=FernetCipher())  # Encrypts checkpoint data before storing in DB


async def init_checkpointer() -> None:
    """Initialise encrypted MongoDB checkpointer — sets up persistent state storage for agent threads."""
    global checkpointer, mongo_client
    mongo_client = MongoClient(SETTINGS.MONGODB_URI)
    db_name = mongo_client.get_default_database().name
    checkpointer = MongoDBSaver(client=mongo_client, db_name=db_name, serde=serde)
    logger.info("LangGraph checkpointer initialised (encrypted)")


async def close_checkpointer() -> None:
    """Close MongoDB client — cleans up checkpointer connection on shutdown."""
    global mongo_client
    if mongo_client:
        mongo_client.close()
        mongo_client = None
