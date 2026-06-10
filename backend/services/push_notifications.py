"""
Mirror Pupil v5.1 - Push Notifications Service
Sends FCM push notifications to mobile devices.
"""

import os
from typing import Optional, Dict, Any
from firebase_admin import messaging
from loguru import logger


class PushNotificationService:
    """Service for sending push notifications via Firebase Cloud Messaging."""
    
    def __init__(self):
        self.enabled = os.getenv("FIREBASE_SERVICE_ACCOUNT_KEY") is not None
        if not self.enabled:
            logger.warning("⚠️ Push notifications disabled - Firebase not configured")
    
    async def send_notification(
        self,
        fcm_token: str,
        title: str,
        body: str,
        data: Optional[Dict[str, str]] = None,
        notification_id: Optional[int] = None
    ) -> bool:
        """
        Send push notification to a single device.
        
        Args:
            fcm_token: Firebase Cloud Messaging token
            title: Notification title
            body: Notification body text
            data: Optional data payload
            notification_id: Optional notification ID for navigation
        
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.enabled:
            return False
        
        try:
            # Prepare data payload
            payload = data or {}
            if notification_id is not None:
                payload['notification_id'] = str(notification_id)
            
            # Create FCM message
            message = messaging.Message(
                notification=messaging.Notification(
                    title=title,
                    body=body,
                ),
                data=payload,
                token=fcm_token,
                android=messaging.AndroidConfig(
                    priority='high',
                    notification=messaging.AndroidNotification(
                        channel_id='mirror_pupil_channel',
                        icon='ic_notification',
                        color='#DC143C',  # Crimson red
                    ),
                ),
                apns=messaging.APNSConfig(
                    payload=messaging.APNSPayload(
                        aps=messaging.Aps(
                            alert=messaging.ApsAlert(
                                title=title,
                                body=body,
                            ),
                            badge=1,
                            sound='default',
                        ),
                    ),
                ),
            )
            
            # Send message
            response = messaging.send(message)
            logger.debug(f"✓ Push notification sent: {response}")
            return True
            
        except messaging.UnregisteredError:
            logger.warning(f"FCM token unregistered or invalid: {fcm_token[:20]}...")
            return False
        except Exception as e:
            logger.error(f"Failed to send push notification: {e}")
            return False
    
    async def send_to_multiple(
        self,
        fcm_tokens: list[str],
        title: str,
        body: str,
        data: Optional[Dict[str, str]] = None,
        notification_id: Optional[int] = None
    ) -> Dict[str, int]:
        """
        Send push notification to multiple devices.
        
        Args:
            fcm_tokens: List of FCM tokens
            title: Notification title
            body: Notification body text
            data: Optional data payload
            notification_id: Optional notification ID
        
        Returns:
            Dictionary with 'success' and 'failed' counts
        """
        if not self.enabled or not fcm_tokens:
            return {'success': 0, 'failed': 0}
        
        success = 0
        failed = 0
        
        for token in fcm_tokens:
            result = await self.send_notification(
                fcm_token=token,
                title=title,
                body=body,
                data=data,
                notification_id=notification_id
            )
            if result:
                success += 1
            else:
                failed += 1
        
        logger.info(f"Push notifications sent: {success} success, {failed} failed")
        return {'success': success, 'failed': failed}


# Global instance
_push_service: Optional[PushNotificationService] = None


def get_push_notification_service() -> PushNotificationService:
    """Get or create push notification service instance."""
    global _push_service
    if _push_service is None:
        _push_service = PushNotificationService()
    return _push_service
