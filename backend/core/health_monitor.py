"""
Mirror Pupil v5.1 - Health Monitor
Centralized health checking for all TradeLocker credentials.

Features:
- Validates all credentials every 60 minutes
- Detects authentication failures early
- Attempts automatic re-authentication
- Logs health status for monitoring
"""

import asyncio
from typing import Optional
from loguru import logger

from .account_manager import AccountManager


class HealthMonitor:
    """
    Centralized health monitoring for TradeLocker credentials.
    
    Runs a background loop that validates all credentials can authenticate
    and make API calls. Provides early warning of credential problems.
    """
    
    def __init__(self, account_manager: AccountManager):
        self.account_manager = account_manager
        self.monitor_task: Optional[asyncio.Task] = None
        self.check_interval = 3600  # 60 minutes
        self.startup_delay = 300    # 5 minutes after startup
        
        logger.info("Initialized HealthMonitor")
    
    async def start_monitoring(self):
        """Start background health monitoring task."""
        if self.monitor_task:
            logger.warning("Health monitor already running")
            return
        
        self.monitor_task = asyncio.create_task(self._monitoring_loop())
        logger.info(f"✓ Started health monitor (checks every {self.check_interval}s)")
    
    async def stop_monitoring(self):
        """Stop background health monitoring task."""
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
            logger.info("✓ Stopped health monitor")
    
    async def _monitoring_loop(self):
        """Main monitoring loop - runs every 60 minutes."""
        # Wait 5 minutes after startup before first check
        await asyncio.sleep(self.startup_delay)
        
        while True:
            try:
                await self._perform_health_checks()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check error: {e}")
            
            await asyncio.sleep(self.check_interval)
    
    async def _perform_health_checks(self):
        """Perform health checks on all credentials."""
        logger.info("[HealthCheck] Starting credential validation...")
        
        if not self.account_manager.clients:
            logger.warning("[HealthCheck] No credentials to check")
            return
        
        healthy_count = 0
        failed_count = 0
        
        for credential_key, client in self.account_manager.clients.items():
            try:
                # Test authentication by fetching accounts
                accounts = await client.get_all_accounts()
                logger.info(f"[HealthCheck] ✓ {credential_key} OK ({len(accounts)} accounts)")
                healthy_count += 1
                
            except Exception as e:
                logger.error(f"[HealthCheck] ✗ {credential_key} FAILED: {e}")
                failed_count += 1
                
                # Attempt re-authentication
                try:
                    logger.info(f"[HealthCheck] Attempting re-authentication for {credential_key}...")
                    await client.authenticate()
                    logger.info(f"[HealthCheck] ✓ {credential_key} re-authenticated successfully")
                except Exception as auth_e:
                    logger.error(f"[HealthCheck] ✗ Re-auth failed for {credential_key}: {auth_e}")
        
        logger.info(
            f"[HealthCheck] Complete - Healthy: {healthy_count}, Failed: {failed_count}"
        )


# Singleton instance
_health_monitor: Optional[HealthMonitor] = None


def get_health_monitor(account_manager: Optional[AccountManager] = None) -> HealthMonitor:
    """Get or create singleton health monitor."""
    global _health_monitor
    if _health_monitor is None:
        if account_manager is None:
            raise ValueError("AccountManager required for first initialization")
        _health_monitor = HealthMonitor(account_manager)
    return _health_monitor
