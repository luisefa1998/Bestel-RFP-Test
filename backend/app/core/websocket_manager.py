"""
WebSocket Connection Manager for handling real-time AI service interactions.

This module provides a connection manager for WebSocket connections,
supporting real-time interactions with AI services.
"""
from fastapi import WebSocket
from typing import Dict, Optional
import logging

# Set up logging
logger = logging.getLogger(__name__)

class ConnectionManager:
    """
    Manages WebSocket connections for AI service interactions.
    
    This class handles WebSocket connections for clients interacting with AI services.
    It's designed to be extensible for various AI features and agent interactions.
    """
    
    def __init__(self):
        # Map connection_id to WebSocket connection
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, connection_id: str):
        """
        Accept a WebSocket connection and store it.
        
        Args:
            websocket: The WebSocket connection
            connection_id: Unique identifier for the connection
        """
        await websocket.accept()
        
        # Store the connection, replacing any existing one for this connection_id
        if connection_id in self.active_connections:
            logger.warning(f"Replacing existing connection for connection_id: {connection_id}")
            
        self.active_connections[connection_id] = websocket
        logger.info(f"Client connected with ID: {connection_id}. Total connections: {len(self.active_connections)}")
    
    def disconnect(self, connection_id: str):
        """
        Remove a WebSocket connection.
        
        Args:
            connection_id: Unique identifier for the connection
        """
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]
            logger.info(f"Client disconnected: {connection_id}. Remaining connections: {len(self.active_connections)}")
    
    async def send_message(self, connection_id: str, data: dict):
        """
        Send a message to a specific client connection.
        
        Args:
            connection_id: Unique identifier for the connection
            data: Data to send
        
        Returns:
            bool: True if the message was sent, False if no connection exists
        """
        if connection_id not in self.active_connections:
            logger.warning(f"No active connection for ID: {connection_id}")
            return False
        
        try:
            await self.active_connections[connection_id].send_json(data)
            return True
        except Exception as e:
            logger.error(f"Error sending message to connection {connection_id}: {str(e)}")
            # Remove the connection if it's broken
            self.disconnect(connection_id)
            return False
    
    def is_connected(self, connection_id: str) -> bool:
        """
        Check if a specific connection is active.
        
        Args:
            connection_id: Unique identifier for the connection
            
        Returns:
            bool: True if the connection is active, False otherwise
        """
        return connection_id in self.active_connections
    
    def get_active_documents(self) -> list:
        """
        Get a list of all active connection IDs.
        
        Returns:
            list: List of connection IDs
        """
        return list(self.active_connections.keys())
    
    def get_connection_count(self) -> int:
        """
        Get the total number of active connections.
        
        Returns:
            int: Number of active connections
        """
        return len(self.active_connections)


# Create a global instance of the connection manager
manager = ConnectionManager()
