"""
Mirror Pupil v5.1 - WebSocket Server
Real-time updates for the React GUI.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from loguru import logger
import json
import asyncio
from typing import Set


router = APIRouter()


# Active WebSocket connections
active_connections: Set[WebSocket] = set()


@router.websocket("/updates")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time updates.
    
    Sends updates for:
    - Trade execution
    - Balance changes
    - Risk breaches
    - Management actions
    - System status
    """
    await websocket.accept()
    active_connections.add(websocket)
    logger.info(f"WebSocket client connected (total: {len(active_connections)})")
    
    try:
        # Send initial connection confirmation
        await websocket.send_json({
            "type": "connection",
            "status": "connected",
            "message": "Mirror Pupil WebSocket connected"
        })
        
        # Keep connection alive
        while True:
            # Wait for messages from client (ping/pong)
            data = await websocket.receive_text()
            
            # Echo back (for testing)
            if data == "ping":
                await websocket.send_text("pong")
                
    except WebSocketDisconnect:
        active_connections.remove(websocket)
        logger.info(f"WebSocket client disconnected (total: {len(active_connections)})")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        active_connections.discard(websocket)


async def broadcast_update(update_type: str, data: dict):
    """
    Broadcast an update to all connected WebSocket clients.
    
    Args:
        update_type: Type of update (trade, balance, risk, etc.)
        data: Update data
    """
    if not active_connections:
        return
    
    message = {
        "type": update_type,
        "data": data,
        "timestamp": asyncio.get_event_loop().time()
    }
    
    # Send to all connected clients
    disconnected = set()
    for connection in active_connections:
        try:
            await connection.send_json(message)
        except Exception as e:
            logger.error(f"Failed to send WebSocket message: {e}")
            disconnected.add(connection)
    
    # Remove disconnected clients
    active_connections.difference_update(disconnected)
