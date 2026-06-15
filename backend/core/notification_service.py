"""
Mirror Pupil v5.1 - Notification Service
Centralized notification creation and broadcasting.
"""

from typing import Optional, Dict, Any, TYPE_CHECKING
from loguru import logger

from ..api.websocket import broadcast_update

if TYPE_CHECKING:
    from ..database import DatabaseManager


class NotificationService:
    """
    Centralized service for creating and broadcasting notifications.
    Handles both database persistence and real-time WebSocket updates.
    """
    
    def __init__(self, db: "DatabaseManager"):
        self.db = db
    
    async def create_notification(
        self,
        category: str,
        severity: str,
        title: str,
        message: str,
        account_key: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[int]:
        """
        Create a notification and broadcast it to WebSocket clients.
        
        Args:
            category: SIGNAL, EXECUTION, MANAGEMENT, BREACH, SYSTEM
            severity: CRITICAL, ERROR, WARNING, INFO
            title: Short notification title
            message: Detailed notification message
            account_key: Optional account key
            metadata: Optional additional data
        
        Returns:
            notification_id if successful, None otherwise
        """
        try:
            # Create notification in database
            notification_id = await self.db.add_notification(
                account_key=account_key,
                category=category,
                severity=severity,
                title=title,
                message=message,
                metadata=metadata
            )
            
            if notification_id:
                # Broadcast to WebSocket clients
                await broadcast_update('notification', {
                    'notification_id': notification_id,
                    'category': category,
                    'severity': severity,
                    'title': title,
                    'message': message,
                    'account_key': account_key,
                    'metadata': metadata
                })
                
                logger.debug(f"Notification created: {title}")
                return notification_id
            else:
                logger.warning(f"Failed to create notification: {title}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating notification: {e}")
            return None
    
    async def signal_received(
        self,
        channel_name: str,
        symbol: str,
        direction: str,
        account_key: Optional[str] = None
    ):
        """Notification for new signal received."""
        await self.create_notification(
            category='SIGNAL',
            severity='INFO',
            title=f'Signal Received: {symbol}',
            message=f'{channel_name} sent {direction} signal for {symbol}',
            account_key=account_key,
            metadata={'symbol': symbol, 'direction': direction, 'channel': channel_name}
        )
    
    async def trade_executed(
        self,
        account_key: str,
        symbol: str,
        direction: str,
        lot_size: float,
        entry_price: float,
        channel_name: str
    ):
        """Notification for trade execution."""
        await self.create_notification(
            category='EXECUTION',
            severity='INFO',
            title=f'Trade Opened: {symbol}',
            message=f'Opened {direction} {lot_size} lots at {entry_price} on {account_key.split(":")[0]}',
            account_key=account_key,
            metadata={
                'symbol': symbol,
                'direction': direction,
                'lot_size': lot_size,
                'entry_price': entry_price,
                'channel': channel_name
            }
        )
    
    async def trade_closed(
        self,
        account_key: str,
        symbol: str,
        pnl: float,
        close_reason: str
    ):
        """Notification for trade closure."""
        severity = 'INFO' if pnl >= 0 else 'WARNING'
        await self.create_notification(
            category='EXECUTION',
            severity=severity,
            title=f'Trade Closed: {symbol}',
            message=f'Closed {symbol} with P&L ${pnl:.2f} ({close_reason}) on {account_key.split(":")[0]}',
            account_key=account_key,
            metadata={'symbol': symbol, 'pnl': pnl, 'close_reason': close_reason}
        )
    
    async def management_action(
        self,
        account_key: str,
        action_type: str,
        symbol: str,
        details: str
    ):
        """Notification for management actions."""
        await self.create_notification(
            category='MANAGEMENT',
            severity='INFO',
            title=f'Management: {action_type}',
            message=f'{action_type} on {symbol}: {details} ({account_key.split(":")[0]})',
            account_key=account_key,
            metadata={'action_type': action_type, 'symbol': symbol}
        )
    
    async def risk_breach(
        self,
        account_key: str,
        breach_type: str,
        current_value: float,
        limit: float
    ):
        """Notification for risk breach."""
        await self.create_notification(
            category='BREACH',
            severity='CRITICAL',
            title=f'Risk Breach: {breach_type}',
            message=f'{breach_type} breach on {account_key.split(":")[0]}: {current_value:.2f}% (limit: {limit:.2f}%)',
            account_key=account_key,
            metadata={'breach_type': breach_type, 'current': current_value, 'limit': limit}
        )
    
    async def system_event(
        self,
        title: str,
        message: str,
        severity: str = 'INFO',
        metadata: Optional[Dict] = None
    ):
        """Notification for system events."""
        await self.create_notification(
            category='SYSTEM',
            severity=severity,
            title=title,
            message=message,
            metadata=metadata
        )


# Global notification service instance
_notification_service: Optional[NotificationService] = None


def get_notification_service(db: "DatabaseManager" = None) -> NotificationService:
    """Get or create the global notification service instance."""
    global _notification_service
    
    if _notification_service is None:
        if db is None:
            raise ValueError("DatabaseManager required for first initialization")
        _notification_service = NotificationService(db)
    
    return _notification_service
