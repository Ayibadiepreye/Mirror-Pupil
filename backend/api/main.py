# -*- coding: utf-8 -*-
"""
Mirror Pupil v5.1 - FastAPI Main Application
Entry point for the REST API and WebSocket server.
"""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from ..database import DatabaseManager
from ..risk import get_risk_enforcer
from ..core.account_manager import get_account_manager
from ..core.trade_executor import TradeExecutor
from ..channels.billirichy.autonomous import get_billirichy_autonomous_manager
from ..channels.firepips.autonomous import get_firepips_autonomous_manager
from ..core.balance_reconciliation import get_balance_monitor
from ..core.trailing_stop_updater import get_trailing_stop_updater
from ..core.pending_order_monitor import get_pending_order_monitor


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
    
    # Initialize trade executor
    trade_executor = TradeExecutor(db, dry_run=False)
    await trade_executor.initialize()
    logger.info("✓ Trade executor initialized")
    
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
    
    logger.info("✅ Mirror Pupil Backend Ready")
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down Mirror Pupil Backend...")
    
    # Stop all background tasks
    await billirichy_manager.stop_managing()
    await firepips_manager.stop_managing()
    await balance_monitor.stop_monitoring()
    await trailing_updater.stop_updating()
    await pending_monitor.stop_monitoring()
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
