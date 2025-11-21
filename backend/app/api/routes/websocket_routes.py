"""
WebSocket routes for real-time AI service interactions.

This module provides WebSocket endpoints for clients to interact
with AI services in real-time.
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from app.core.websocket_manager import manager
from app.services.ai_service import AIService
from app.schemas.models import StreamResponse
import logging
import json
import uuid
import asyncio

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/ws/status")
async def get_websocket_status():
    """
    Get information about active WebSocket connections.
    
    Returns:
        dict: Information about active connections
    """
    return {
        "active_connections": manager.get_active_documents(),
        "connection_count": manager.get_connection_count()
    }

@router.websocket("/ws/chat/{project_id}")
async def websocket_chat(websocket: WebSocket, project_id: str, ai_service: AIService = Depends()):
    """
    WebSocket endpoint for streaming AI chat responses.
    
    Args:
        websocket: The WebSocket connection
        project_id: The project ID to use for retrieval
        ai_service: The AI service to use
    """
    connection_id = str(uuid.uuid4())
    await manager.connect(websocket, connection_id)
    
    try:
        while True:
            # Wait for a message from the client
            data = await websocket.receive_text()
            
            try:
                # Parse the message
                message_data = json.loads(data)
                messages = message_data.get("messages", [])
                
                if not messages:
                    await websocket.send_json({"error": "No messages provided"})
                    continue
                
                last_message = messages[-1]["content"] if messages else ""
                logger.info(f"Processing streaming query: '{last_message}' for project: {project_id}")
                
                # Process the query with streaming
                try:
                    # Send initial message to indicate processing has started
                    await websocket.send_json({
                        "chunk": "Procesando tu consulta...",
                        "done": False,
                        "metadata": {"type": "status", "status": "started"}
                    })
                    
                    # Stream the response chunks
                    async for chunk, metadata in AIService.stream_query(messages, project_id):
                        response = StreamResponse(
                            chunk=chunk,
                            done=False,
                            metadata=metadata
                        )
                        await websocket.send_json(response.model_dump())
                    
                    # Send final message to indicate processing is complete
                    await websocket.send_json({
                        "chunk": "",
                        "done": True,
                        "metadata": {"type": "status", "status": "completed"}
                    })
                    
                except Exception as stream_error:
                    logger.error(f"Error streaming response: {str(stream_error)}")
                    await websocket.send_json({
                        "chunk": f"Error: {str(stream_error)}",
                        "done": True,
                        "metadata": {"type": "error"}
                    })
                
            except json.JSONDecodeError:
                await websocket.send_json({"error": "Invalid JSON"})
            except Exception as e:
                logger.error(f"Error processing websocket query: {str(e)}")
                await websocket.send_json({"error": f"Error processing query: {str(e)}"})
    
    except WebSocketDisconnect:
        logger.info(f"Client disconnected: {connection_id}")
        manager.disconnect(connection_id)
