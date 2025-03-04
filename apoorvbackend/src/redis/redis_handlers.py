import redis
import json
import os
import time
from dotenv import load_dotenv

from langchain_core.messages import AIMessage, HumanMessage

from apoorvbackend.src.logger import logger

load_dotenv()

class RedisChatHandler:
    def __init__(self):
        self.host = os.getenv("REDIS_HOST", "localhost")
        self.port = int(os.getenv("REDIS_PORT", 6379))
        self.db = int(os.getenv("REDIS_DB", 0))
        
        self.pool = redis.ConnectionPool(host=self.host, port=self.port, db=self.db)
        self.client = redis.Redis(connection_pool=self.pool)

    def _get_key(self, user_id: str, level: str, actor: str) -> str:
        """Build a Redis key based on user id, level and actor."""
        return f"chat:{user_id}:{level}:{actor}"

    def serialize_message(self, message) -> dict:
        """Convert a message object to a dict for JSON storage."""
        if isinstance(message, HumanMessage):
            role = "human"
        elif isinstance(message, AIMessage):
            role = "ai"
        else:
            raise ValueError("Invalid message type")
        return {"role": role, "content": message.content}

    def deserialize_message(self, data: dict):
        """Convert dict data back to a message object."""
        role = data.get("role")
        content = data.get("content")
        if role == "human":
            return HumanMessage(content=content)
        elif role == "ai":
            return AIMessage(content=content)
        else:
            raise ValueError("Invalid message role")

    def save_chat_history(self, user_id: str, level: str, actor: str, chat_history: list) -> None:
        """
        Save the chat history list in Redis.
        Each message is serialized to a dictionary.
        """
        key = self._get_key(user_id, level, actor)
        serialized_history = [self.serialize_message(msg) for msg in chat_history]
        self.client.set(key, json.dumps(serialized_history))
        # @TODO: Add a sheduled task to save the data in postgres after every 10 mins

    def load_chat_history(self, user_id: str, level: str, actor: str):
        """
        Load the chat history list from Redis.
        If no history is found, return None.
        """
        key = self._get_key(user_id, level, actor)
        data = self.client.get(key)
        if data is None:
            return None
        try:
            serialized_history = json.loads(data)
            return [self.deserialize_message(item) for item in serialized_history]
        except Exception as e:
            logger.info(f"No previous history found for user {user_id} at level {level} with actor {actor}")
            return None
