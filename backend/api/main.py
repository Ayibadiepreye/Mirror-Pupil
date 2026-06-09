# -*- coding: utf-8 -*-
"""
Mirror Pupil v5.1 - FastAPI Main Application
Entry point for the REST API and WebSocket server.
"""

import os
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from ..database import DatabaseManager
from ..risk import get_risk_enforcer
from ..risk.eod_close import get_eod_close_handler
from ..risk.daily_reset import get_daily_reset_handler
from ..core.account_manager import get_account_manager
from ..core.trade_executor import TradeExecutor
from ..core.health_monitor import get_health_monitor
from ..core.notification_service import get_notification_service
from ..channels.billirichy.autonomous import get_billirichy_autonomous_manager
from ..channels.firepips.autonomous import get_firepips_autonomous_manager
from ..core.balance_reconciliation import get_balance_monitor
from ..core.trailing_stop_updater import get_trailing_stop_updater
from ..core.pending_order_monitor import get_pending_order_monitor
from ..core.position_reconciliation import get_position_reconciliation_monitor
from ..telegram_integration import get_telegram_integration
from ..channels.registry import get_registry


# Background cleanup task for notifications
async def _notification_cleanup_loop(db: DatabaseManager):
    """Background task to cleanup notifications older than 48 hours."""
    while True:
        try:
            await asyncio.sleep(3600)  # Run every hour
            count = await db.cleanup_old_notifications()
            if count > 0:
                logger.info(f"Cleaned up {count} old notification(s)")
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Notification cleanup error: {e}")


# Global instances
db: DatabaseManager = None
trade_executor: TradeExecutor = None


# Dependency functions (must be defined before importing routes to avoid circular import)
def get_db() -> DatabaseManager:
    """Get database instance for dependency injection."""
    return db


def get_executor() -> TradeExecutor:
    """Get trade executor instance for dependency injection."""
    return trade_executor


# Import routes AFTER defining dependencies
from .routes import accounts, channels, risk_profiles, trades, bot_control, notifications
from .websocket import router as websocket_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup and shutdown handlers for the FastAPI application.
    """
    global db, trade_executor
    
    # Startup
    logger.info("🚀 Starting Mirror Pupil FastAPI Backend...")
    
    # Initialize database
    db = DatabaseManager()
    await db.connect()
    logger.info("✓ Database connected")
    
    # Load accounts from database into AccountManager
    account_manager = get_account_manager()
    all_accounts = await db.get_all_accounts()
    credentials_added = set()
    
    for account in all_accounts:
        credential_key = account.credential_key
        
        # Skip if we already added this credential
        if credential_key in credentials_added:
            continue
        
        try:
            # Add credential to AccountManager
            success = await account_manager.add_credential(
                email=account.tl_email,
                password=account.tl_password,
                server=account.tl_prop_firm,      # Prop firm name (e.g., "HEROFX")
                environment=account.tl_server     # "live" or "demo"
            )
            
            if success:
                credentials_added.add(credential_key)
                logger.info(f"✓ Loaded credential: {credential_key}")
            else:
                logger.error(f"✗ Failed to load credential: {credential_key}")
                
        except Exception as e:
            logger.error(f"✗ Error loading credential {credential_key}: {e}")
    
    logger.info(f"✓ Loaded {len(credentials_added)} credential(s) into AccountManager")
    
    # Initialize trade executor
    trade_executor = TradeExecutor(db, dry_run=False)
    await trade_executor.initialize()
    logger.info("✓ Trade executor initialized")
    
    # Initialize notification service
    notification_service = get_notification_service(db)
    logger.info("✓ Notification service initialized")
    
    # Start notification cleanup scheduler (48-hour cleanup)
    asyncio.create_task(_notification_cleanup_loop(db))
    logger.info("✓ Notification cleanup scheduler started")
    
    # Inject TradeExecutor into channel registry (CRITICAL: enables signal execution)
    registry = get_registry()
    registry.inject_trade_executor(trade_executor)
    logger.info("✓ TradeExecutor injected into channel plugins")
    
    # Initialize risk enforcer
    risk_enforcer = await get_risk_enforcer(db)
    logger.info("✓ Risk enforcer initialized")
    
    # Initialize autonomous managers
    billirichy_manager = get_billirichy_autonomous_manager(db, trade_executor)
    await billirichy_manager.start_managing()
    logger.info("✓ BillirichyFX autonomous manager started")
    
    firepips_manager = get_firepips_autonomous_manager(db, trade_executor)
    await firepips_manager.start_managing()
    logger.info("✓ Firepips autonomous manager started")
    
    # Initialize balance monitor
    balance_monitor = get_balance_monitor(db)
    await balance_monitor.start_monitoring()
    logger.info("✓ Balance reconciliation started")
    
    # Initialize trailing stop updater
    trailing_updater = get_trailing_stop_updater(db)
    await trailing_updater.start_updating()
    logger.info("✓ Trailing stop updater started")
    
    # Initialize pending order monitor
    pending_monitor = await get_pending_order_monitor(db)
    await pending_monitor.start_monitoring()
    logger.info("✓ Pending order monitor started")
    
    # Initialize position reconciliation monitor
    position_monitor = await get_position_reconciliation_monitor(db)
    await position_monitor.start_monitoring()
    logger.info("✓ Position reconciliation monitor started")
    
    # Initialize health monitor (credential validation every 60 minutes)
    health_monitor = get_health_monitor(account_manager)
    await health_monitor.start_monitoring()
    logger.info("✓ Health monitor started (checks every 60 minutes)")
    
    # Initialize EOD close handler (closes all trades at 4:45 PM EST)
    eod_handler = await get_eod_close_handler(db)
    logger.info("✓ EOD close handler started (4:45 PM EST)")
    
    # Initialize daily reset handler (resets accounts at 5:00 PM EST)
    reset_handler = await get_daily_reset_handler(db)
    logger.info("✓ Daily reset handler started (5:00 PM EST)")
    
    # Initialize Telegram client integration
    telegram = get_telegram_integration()
    telegram_started = await telegram.start(db)  # Pass database for channel loading
    if telegram_started:
        logger.info("✓ Telegram client integration started")
    else:
        logger.warning("⚠️ Telegram client not started (check credentials in .env)")
    
    logger.info("✅ Mirror Pupil Backend Ready")
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down Mirror Pupil Backend...")
    
    # Stop Telegram client
    await telegram.stop()
    
    # Stop all background tasks
    await health_monitor.stop_monitoring()
    await eod_handler.stop_eod_close_scheduler()
    await reset_handler.stop_daily_reset_scheduler()
    await billirichy_manager.stop_managing()
    await firepips_manager.stop_managing()
    await balance_monitor.stop_monitoring()
    await trailing_updater.stop_updating()
    await pending_monitor.stop_monitoring()
    await position_monitor.stop_monitoring()
    await risk_enforcer.stop_breach_monitoring()
    
    # Disconnect database
    await db.disconnect()
    
    logger.info("✅ Shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="Mirror Pupil API",
    description="REST API and WebSocket server for Mirror Pupil v5.1 copy-trading bot",
    version="5.1.0",
    lifespan=lifespan
)


# CORS configuration for Telegram Web App
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://web.telegram.org",
        "https://k.web.telegram.org",
        "*"  # Allow all origins for development (remove in production)
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include routers
app.include_router(accounts.router, prefix="/api/accounts", tags=["Accounts"])
app.include_router(channels.router, prefix="/api/channels", tags=["Channels"])
app.include_router(risk_profiles.router, prefix="/api/risk-profiles", tags=["Risk Profiles"])
app.include_router(trades.router, prefix="/api/trades", tags=["Trades"])
app.include_router(bot_control.router, prefix="/api/bot", tags=["Bot Control"])
app.include_router(notifications.router, prefix="/api/notifications", tags=["Notifications"])
app.include_router(websocket_router, prefix="/ws", tags=["WebSocket"])


@app.get("/")
async def root():
    """Root endpoint - API status."""
    return {
        "name": "Mirror Pupil API",
        "version": "5.1.0",
        "status": "running",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "database": "connected" if db and db.pool else "disconnected"
    }
