"""
Mirror Pupil v5.1 - Accounts API Routes
CRUD operations for TradeLocker accounts.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from loguru import logger

from ...database import DatabaseManager, Account
from ...core.tradelocker_client import TradeLockerClient
from ...core.account_manager import get_account_manager
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


class DiscoverAccountsRequest(BaseModel):
    """Request model for discovering TradeLocker accounts."""
    email: str
    password: str
    server: str  # Environment: "live" or "demo"
    prop_firm: str = ""  # Broker/Prop firm name (e.g., "Blue Guardian")


class DiscoveredAccount(BaseModel):
    """Model for a discovered account (not yet added to database)."""
    id: str
    number: str
    balance: float


class DiscoverAccountsResponse(BaseModel):
    """Response model for account discovery."""
    accounts: List[DiscoveredAccount]


class BulkAddAccountsRequest(BaseModel):
    """Request model for bulk adding accounts."""
    email: str
    password: str
    server: str  # Environment: "live" or "demo"
    prop_firm: str = ""  # Broker/Prop firm name
    account_ids: List[str]


class BulkAddAccountsResponse(BaseModel):
    """Response model for bulk add operation."""
    added: List[str]
    skipped: List[str]  # Already exist
    failed: List[str]


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
    
    @classmethod
    def from_account(cls, account: Account):
        """Convert Account model to AccountResponse with date serialization."""
        data = account.model_dump()
        # Convert date to string if present
        if data.get('cycle_start_date') is not None:
            data['cycle_start_date'] = data['cycle_start_date'].isoformat()
        return cls(**data)
    
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
        return [AccountResponse.from_account(acc) for acc in accounts]
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
        return AccountResponse.from_account(account)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get account {account_key}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get account: {str(e)}"
        )


@router.post("/discover", response_model=DiscoverAccountsResponse)
async def discover_accounts(request: DiscoverAccountsRequest):
    """
    Discover TradeLocker accounts for given credentials without adding them to database.
    
    Args:
        request: Credentials (email, password, server)
    
    Returns:
        List of discovered accounts with IDs and balances
    """
    try:
        logger.info(f"Discovering accounts for {request.email} on {request.prop_firm or 'default'} ({request.server})")
        
        # Create temporary client
        client = TradeLockerClient(
            email=request.email,
            password=request.password,
            server=request.prop_firm,  # Broker/prop firm name
            environment=request.server  # "live" or "demo"
        )
        
        # Authenticate
        success = await client.authenticate()
        if not success:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid TradeLocker credentials"
            )
        
        # Get all accounts
        accounts = await client.get_all_accounts()
        
        # Format response
        discovered = []
        for acct in accounts:
            account_id = str(acct.get('id') or acct.get('accountId'))
            account_number = str(acct.get('accNum', account_id))
            balance = float(acct.get('accountBalance', 0.0))
            
            discovered.append(DiscoveredAccount(
                id=account_id,
                number=account_number,
                balance=balance
            ))
        
        logger.info(f"✓ Discovered {len(discovered)} account(s) for {request.email}")
        return DiscoverAccountsResponse(accounts=discovered)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to discover accounts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to discover accounts: {str(e)}"
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
        
        # Add credential to AccountManager if not already added
        account_manager = get_account_manager()
        if not account_manager.get_client(account_data.credential_key):
            try:
                await account_manager.add_credential(
                    email=account_data.tl_email,
                    password=account_data.tl_password,
                    server=account_data.tl_server
                )
                logger.info(f"✓ Added credential to AccountManager: {account_data.credential_key}")
            except Exception as e:
                logger.warning(f"⚠️ Failed to add credential to AccountManager: {e}")
        
        # Sync channel subscriptions
        await db.sync_channel_subscriptions()
        
        logger.info(f"✓ Created account: {account_key}")
        return AccountResponse.from_account(account)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create account: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create account: {str(e)}"
        )


@router.post("/bulk-add", response_model=BulkAddAccountsResponse, status_code=status.HTTP_201_CREATED)
async def bulk_add_accounts(request: BulkAddAccountsRequest, db: DatabaseManager = Depends(get_db)):
    """
    Add multiple TradeLocker accounts at once.
    Only adds NEW accounts - skips existing ones without modifying them.
    
    Args:
        request: Credentials and list of account IDs to add
    
    Returns:
        Lists of added, skipped (already exist), and failed accounts
    """
    try:
        logger.info(f"Bulk adding {len(request.account_ids)} account(s) for {request.email} on {request.prop_firm or 'default'} ({request.server})")
        
        # Create temporary client to fetch account details
        client = TradeLockerClient(
            email=request.email,
            password=request.password,
            server=request.prop_firm,  # Broker/prop firm name
            environment=request.server  # "live" or "demo"
        )
        
        # Authenticate
        success = await client.authenticate()
        if not success:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid TradeLocker credentials"
            )
        
        # Get all accounts from TradeLocker
        all_accounts = await client.get_all_accounts()
        
        # Map account IDs to full account data
        accounts_map = {}
        for acct in all_accounts:
            account_id = str(acct.get('id') or acct.get('accountId'))
            accounts_map[account_id] = acct
        
        added = []
        skipped = []
        failed = []
        
        # Process each requested account
        for account_id in request.account_ids:
            account_key = f"{request.email}:{account_id}"
            
            try:
                # Check if account already exists
                existing = await db.get_account(account_key)
                if existing:
                    logger.info(f"  ⊘ Skipping existing account: {account_key}")
                    skipped.append(account_key)
                    continue
                
                # Get account details from TradeLocker
                if account_id not in accounts_map:
                    logger.warning(f"  ✗ Account ID not found in TradeLocker: {account_id}")
                    failed.append(account_key)
                    continue
                
                tl_account = accounts_map[account_id]
                account_number = str(tl_account.get('accNum', account_id))
                balance = float(tl_account.get('accountBalance', 0.0))
                
                # Create Account object
                account = Account(
                    account_key=account_key,
                    credential_key=request.email,
                    tl_account_id=account_id,
                    tl_email=request.email,
                    tl_password=request.password,
                    tl_server=request.server,  # Environment: live/demo
                    tl_prop_firm=request.prop_firm,  # Broker/prop firm name
                    display_name=f"{account_number}",
                    initial_balance=balance,
                    current_balance=balance,
                    highest_banked_balance=balance,
                    daily_start_balance=balance,
                    last_synced_balance=balance,
                    risk_profile_id=None  # Use default
                )
                
                # Add to database
                add_success = await db.add_account(account)
                if add_success:
                    logger.info(f"  ✓ Added account: {account_key} (${balance:,.2f})")
                    added.append(account_key)
                    
                    # Add credential to AccountManager if not already added
                    account_manager = get_account_manager()
                    if not account_manager.get_client(request.email):
                        try:
                            await account_manager.add_credential(
                                email=request.email,
                                password=request.password,
                                server=request.server
                            )
                            logger.info(f"  ✓ Added credential to AccountManager: {request.email}")
                        except Exception as e:
                            logger.warning(f"  ⚠️ Failed to add credential to AccountManager: {e}")
                else:
                    logger.warning(f"  ✗ Failed to add account: {account_key}")
                    failed.append(account_key)
                    
            except Exception as e:
                logger.error(f"  ✗ Error adding account {account_key}: {e}")
                failed.append(account_key)
        
        # Sync channel subscriptions for all new accounts
        if added:
            await db.sync_channel_subscriptions()
        
        logger.info(
            f"✓ Bulk add complete: {len(added)} added, "
            f"{len(skipped)} skipped, {len(failed)} failed"
        )
        
        return BulkAddAccountsResponse(
            added=added,
            skipped=skipped,
            failed=failed
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to bulk add accounts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to bulk add accounts: {str(e)}"
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
            await db.update_account_display_name(account_key, account_data.display_name)
        
        if account_data.paused is not None:
            await db.update_account_paused(account_key, account_data.paused)
        
        if account_data.risk_profile_id is not None:
            await db.update_account_risk_profile(account_key, account_data.risk_profile_id)
        
        if account_data.max_concurrent_trades_override is not None:
            await db.update_account_max_concurrent(account_key, account_data.max_concurrent_trades_override)
        
        # Get updated account
        updated_account = await db.get_account(account_key)
        logger.info(f"✓ Updated account: {account_key}")
        return AccountResponse.from_account(updated_account)
        
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
        
        # Delete account and all related data
        success = await db.delete_account(account_key)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete account"
            )
        
        logger.info(f"✓ Deleted account: {account_key}")
        
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
        return AccountResponse.from_account(account)
        
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
        return AccountResponse.from_account(account)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to resume account {account_key}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to resume account: {str(e)}"
        )


class PayoutResetRequest(BaseModel):
    """Request model for payout reset."""
    new_balance: float


@router.post("/{account_key}/reset-payout", response_model=AccountResponse)
async def reset_payout(
    account_key: str,
    reset_data: PayoutResetRequest,
    db: DatabaseManager = Depends(get_db)
):
    """
    Reset account after payout withdrawal.
    
    This resets all balance tracking fields to start fresh with the new balance
    after a trader withdraws profits.
    
    Args:
        account_key: Account key
        reset_data: New balance after withdrawal
    
    Returns:
        Updated account details
    """
    try:
        # Check if account exists
        account = await db.get_account(account_key)
        if not account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Account not found: {account_key}"
            )
        
        # Perform payout reset
        success = await db.reset_payout_after_withdrawal(account_key, reset_data.new_balance)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to reset payout"
            )
        
        # Get updated account
        updated_account = await db.get_account(account_key)
        logger.info(
            f"✓ Reset payout for {account_key}: "
            f"new balance ${reset_data.new_balance:.2f}"
        )
        return AccountResponse.from_account(updated_account)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to reset payout for {account_key}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset payout: {str(e)}"
        )
