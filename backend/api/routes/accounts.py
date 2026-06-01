"""
Mirror Pupil v5.1 - Accounts API Routes
CRUD operations for TradeLocker accounts.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from loguru import logger

from ...database import DatabaseManager, Account
from ..main import get_db


router = APIRouter()


# Request/Response Models
class AccountCreate(BaseModel):
    """Request model for creating a new account."""
    credential_key: str
    tl_account_id: str
    tl_email: str
    tl_password: str
    tl_server: str = "live"
    display_name: Optional[str] = None
    initial_balance: float
    risk_profile_id: Optional[int] = None


class AccountUpdate(BaseModel):
    """Request model for updating an account."""
    display_name: Optional[str] = None
    paused: Optional[bool] = None
    risk_profile_id: Optional[int] = None
    max_concurrent_trades_override: Optional[int] = None


class AccountResponse(BaseModel):
    """Response model for account data."""
    account_key: str
    credential_key: str
    tl_account_id: str
    tl_email: str
    tl_server: str
    display_name: Optional[str]
    initial_balance: float
    current_balance: float
    highest_banked_balance: float
    profit_locked: bool
    daily_pnl: float
    daily_start_balance: float
    last_synced_balance: float
    cycle_start_date: Optional[str]
    cycle_best_day_pnl: float
    paused: bool
    breached: bool
    risk_profile_id: Optional[int]
    max_concurrent_trades_override: Optional[int]
    
    class Config:
        from_attributes = True


@router.get("/", response_model=List[AccountResponse])
async def get_all_accounts(db: DatabaseManager = Depends(get_db)):
    """
    Get all accounts.
    
    Returns:
        List of all accounts with full details
    """
    try:
        accounts = await db.get_all_accounts()
        return [AccountResponse.model_validate(acc) for acc in accounts]
    except Exception as e:
        logger.error(f"Failed to get accounts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get accounts: {str(e)}"
        )


@router.get("/{account_key}", response_model=AccountResponse)
async def get_account(account_key: str, db: DatabaseManager = Depends(get_db)):
    """
    Get a specific account by key.
    
    Args:
        account_key: Account key (format: email:account_id)
    
    Returns:
        Account details
    """
    try:
        account = await db.get_account(account_key)
        if not account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Account not found: {account_key}"
            )
        return AccountResponse.model_validate(account)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get account {account_key}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get account: {str(e)}"
        )


@router.post("/", response_model=AccountResponse, status_code=status.HTTP_201_CREATED)
async def create_account(account_data: AccountCreate, db: DatabaseManager = Depends(get_db)):
    """
    Create a new account.
    
    Args:
        account_data: Account creation data
    
    Returns:
        Created account details
    """
    try:
        # Create account key
        account_key = f"{account_data.credential_key}:{account_data.tl_account_id}"
        
        # Create Account object
        account = Account(
            account_key=account_key,
            credential_key=account_data.credential_key,
            tl_account_id=account_data.tl_account_id,
            tl_email=account_data.tl_email,
            tl_password=account_data.tl_password,
            tl_server=account_data.tl_server,
            display_name=account_data.display_name,
            initial_balance=account_data.initial_balance,
            current_balance=account_data.initial_balance,
            highest_banked_balance=account_data.initial_balance,
            daily_start_balance=account_data.initial_balance,
            last_synced_balance=account_data.initial_balance,
            risk_profile_id=account_data.risk_profile_id
        )
        
        # Add to database
        success = await db.add_account(account)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create account (may already exist)"
            )
        
        # Sync channel subscriptions
        await db.sync_channel_subscriptions()
        
        logger.info(f"✓ Created account: {account_key}")
        return AccountResponse.model_validate(account)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create account: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create account: {str(e)}"
        )


@router.put("/{account_key}", response_model=AccountResponse)
async def update_account(
    account_key: str,
    account_data: AccountUpdate,
    db: DatabaseManager = Depends(get_db)
):
    """
    Update an account.
    
    Args:
        account_key: Account key
        account_data: Account update data
    
    Returns:
        Updated account details
    """
    try:
        # Get existing account
        account = await db.get_account(account_key)
        if not account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Account not found: {account_key}"
            )
        
        # Update fields
        if account_data.display_name is not None:
            # TODO: Add update_account_display_name method to DatabaseManager
            pass
        
        if account_data.paused is not None:
            await db.update_account_paused(account_key, account_data.paused)
        
        if account_data.risk_profile_id is not None:
            # TODO: Add update_account_risk_profile method to DatabaseManager
            pass
        
        if account_data.max_concurrent_trades_override is not None:
            # TODO: Add update_account_max_concurrent method to DatabaseManager
            pass
        
        # Get updated account
        updated_account = await db.get_account(account_key)
        logger.info(f"✓ Updated account: {account_key}")
        return AccountResponse.model_validate(updated_account)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update account {account_key}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update account: {str(e)}"
        )


@router.delete("/{account_key}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(account_key: str, db: DatabaseManager = Depends(get_db)):
    """
    Delete an account.
    
    Args:
        account_key: Account key
    """
    try:
        # Check if account exists
        account = await db.get_account(account_key)
        if not account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Account not found: {account_key}"
            )
        
        # TODO: Add delete_account method to DatabaseManager
        # For now, just pause it
        await db.update_account_paused(account_key, True)
        
        logger.info(f"✓ Deleted (paused) account: {account_key}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete account {account_key}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete account: {str(e)}"
        )


@router.post("/{account_key}/pause", response_model=AccountResponse)
async def pause_account(account_key: str, db: DatabaseManager = Depends(get_db)):
    """
    Pause an account (stop opening new trades).
    
    Args:
        account_key: Account key
    
    Returns:
        Updated account details
    """
    try:
        success = await db.update_account_paused(account_key, True)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Account not found: {account_key}"
            )
        
        account = await db.get_account(account_key)
        logger.info(f"✓ Paused account: {account_key}")
        return AccountResponse.model_validate(account)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to pause account {account_key}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to pause account: {str(e)}"
        )


@router.post("/{account_key}/resume", response_model=AccountResponse)
async def resume_account(account_key: str, db: DatabaseManager = Depends(get_db)):
    """
    Resume an account (allow opening new trades).
    
    Args:
        account_key: Account key
    
    Returns:
        Updated account details
    """
    try:
        success = await db.update_account_paused(account_key, False)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Account not found: {account_key}"
            )
        
        account = await db.get_account(account_key)
        logger.info(f"✓ Resumed account: {account_key}")
        return AccountResponse.model_validate(account)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to resume account {account_key}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to resume account: {str(e)}"
        )
