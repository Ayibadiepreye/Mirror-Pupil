"""
Mirror Pupil v5.1 - WebSocket Server
Real-time updates for the React GUI.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from loguru import logger
import json
import asyncio
from typing import Set
from datetime import datetime


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
    - Notifications
    """
    await websocket.accept()
    active_connections.add(websocket)
    logger.info(f"WebSocket client connected (total: {len(active_connections)})")
    
    try:
        # Send initial connection confirmation
        await websocket.send_json({
            "type": "connection",
            "status": "connected",
            "message": "Mirror Pupil WebSocket connected",
            "timestamp": datetime.utcnow().isoformat()
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
        update_type: Type of update (trade, balance, risk, notification, etc.)
        data: Update data
    """
    if not active_connections:
        return
    
    message = {
        "type": update_type,
        "data": data,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    # Send to all connected clients
    disconnected = set()
    for connection in active_connections:
        try:
            await connection.send_json(message)
        except Exception as e:
            logger.debug(f"Failed to send WebSocket message: {e}")
            disconnected.add(connection)
    
    # Remove disconnected clients
    active_connections.difference_update(disconnected)


async def broadcast_trade_update(trade_data: dict):
    """Broadcast trade execution/closure."""
    await broadcast_update('trade', trade_data)


async def broadcast_balance_update(account_key: str, balance: float, pnl: float):
    """Broadcast account balance change."""
    await broadcast_update('balance', {
        'account_key': account_key,
        'balance': balance,
        'pnl': pnl
    })


async def broadcast_notification(notification: dict):
    """Broadcast new notification."""
    await broadcast_update('notification', notification)
