"""
Mirror Pupil v5.1 - Account Manager
Manages multiple TradeLocker credentials and their sub-accounts.
"""

import asyncio
from typing import Dict, List, Optional
from loguru import logger

from .tradelocker_client import TradeLockerClient, token_refresh_loop


class AccountManager:
    """
    Manages multiple TradeLocker credentials and their sub-accounts.
    
    Architecture:
    - One credential (email + password) can have multiple sub-accounts
    - Each credential has one TradeLockerClient instance
    - Sub-accounts share the client but have independent tracking
    """
    
    def __init__(self):
        # Account key (email:account_id) → TradeLockerClient (ONE CLIENT PER SUB-ACCOUNT)
        self.clients: Dict[str, TradeLockerClient] = {}
        
        # Account key (email:account_id) → account info
        self.accounts: Dict[str, Dict] = {}
        
        # Background tasks per account
        self.refresh_tasks: Dict[str, asyncio.Task] = {}
        
        logger.info("Initialized AccountManager")
    
    async def add_credential(
        self,
        email: str,
        password: str,
        server: str = "live",
        environment: str = "demo"
    ) -> bool:
        """
        Add a TradeLocker credential and discover its sub-accounts.
        Creates ONE CLIENT PER SUB-ACCOUNT (not per credential).
        
        Args:
            email: TradeLocker login email
            password: TradeLocker password
            server: Prop firm server name (e.g., "HEROFX", "Blue Guardian")
            environment: "live" or "demo" (for URL construction)
        
        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Adding credential: {email} ({environment}, {server})")
        
        # Step 1: Create temporary client to discover sub-accounts
        temp_client = TradeLockerClient(
            email=email,
            password=password,
            server=server,
            environment=environment
        )
        
        # Authenticate
        try:
            success = await temp_client.authenticate()
            if not success:
                logger.error(f"Failed to authenticate {email}")
                return False
        except Exception as e:
            logger.error(f"Authentication error for {email}: {e}")
            return False
        
        # Step 2: Discover sub-accounts
        try:
            accounts = await temp_client.get_all_accounts()
            
            if not accounts:
                logger.warning(f"No sub-accounts found for {email}")
                return False
            
            # Step 3: Create ONE CLIENT PER SUB-ACCOUNT
            for acct in accounts:
                account_id = acct.get('id')
                account_number = acct.get('accNum', account_id)
                balance = acct.get('accountBalance', 0.0)
                
                account_key = f"{email}:{account_id}"
                
                # Create dedicated client for this sub-account
                account_client = TradeLockerClient(
                    email=email,
                    password=password,
                    server=server,
                    environment=environment,
                    account_id=account_id  # Bind to specific sub-account
                )
                
                # Authenticate this client
                await account_client.authenticate()
                
                # Store client per sub-account
                self.clients[account_key] = account_client
                
                self.accounts[account_key] = {
                    'account_key': account_key,
                    'credential_key': email,
                    'account_id': account_id,
                    'account_number': account_number,
                    'email': email,
                    'server': server,
                    'environment': environment,
                    'initial_balance': balance,
                    'current_balance': balance,
                    'client': account_client  # Dedicated client for this account
                }
                
                logger.info(
                    f"  ✓ Discovered sub-account: {account_number} "
                    f"(ID: {account_id}, Balance: ${balance:,.2f})"
                )
            
            logger.info(f"✓ Added credential {email} with {len(accounts)} sub-account(s)")
            
            # Start token refresh task for each client
            for account_key, client in self.clients.items():
                task = asyncio.create_task(token_refresh_loop(client))
                self.refresh_tasks[account_key] = task
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to discover accounts for {email}: {e}")
            return False
    
    def get_client(self, credential_key: str) -> Optional[TradeLockerClient]:
        """
        Get TradeLocker client for a credential.
        
        Note: This returns the first account's client for backwards compatibility.
        For multi-account setups, use get_client_for_account() instead.
        """
        # Find first account with this credential
        for account_key, account in self.accounts.items():
            if account['credential_key'] == credential_key:
                return self.clients.get(account_key)
        return None
    
    def get_account(self, account_key: str) -> Optional[Dict]:
        """Get account info by account key."""
        return self.accounts.get(account_key)
    
    def get_client_for_account(self, account_key: str) -> Optional[TradeLockerClient]:
        """
        Get TradeLocker client for a specific account.
        
        Args:
            account_key: Account key (format: email:account_id)
        
        Returns:
            TradeLockerClient instance (dedicated to this account) or None
        """
        return self.clients.get(account_key)
    
    def get_all_accounts(self) -> List[Dict]:
        """Get all registered accounts."""
        return list(self.accounts.values())
    
    def get_accounts_for_credential(self, credential_key: str) -> List[Dict]:
        """Get all sub-accounts for a specific credential."""
        return [
            acct for acct in self.accounts.values()
            if acct['credential_key'] == credential_key
        ]
    
    async def update_account_balance(self, account_key: str) -> Optional[float]:
        """
        Fetch and update account balance from TradeLocker.
        
        Returns:
            Updated balance or None if failed
        """
        account = self.get_account(account_key)
        if not account:
            logger.error(f"Account not found: {account_key}")
            return None
        
        client = self.clients.get(account_key)
        if not client:
            logger.error(f"Client not found for account: {account_key}")
            return None
        
        try:
            # Client is dedicated to this account, no account_id needed
            state = await client.get_account_state()
            balance = state.get('balance') or state.get('accountBalance', 0.0)
            # Note: equity is NOT a field - calculate it from balance + openNetPnL
            open_pnl = state.get('openNetPnL', 0.0) or state.get('openGrossPnL', 0.0)
            equity = balance + open_pnl
            
            # Update stored balance
            account['current_balance'] = balance
            account['equity'] = equity
            
            logger.debug(
                f"[{account_key}] Balance updated: ${balance:,.2f} "
                f"(Equity: ${equity:,.2f})"
            )
            
            return balance
            
        except Exception as e:
            logger.error(f"Failed to update balance for {account_key}: {e}")
            return None
    
    async def get_open_positions(self, account_key: str) -> List[Dict]:
        """
        Get all open positions for an account.
        """
        client = self.clients.get(account_key)
        if not client:
            logger.error(f"Client not found for account: {account_key}")
            return []
        
        try:
            positions = await client.get_all_positions()
            logger.debug(f"[{account_key}] Found {len(positions)} open position(s)")
            return positions
        except Exception as e:
            logger.error(f"Failed to get positions for {account_key}: {e}")
            return []
    
    async def close_all_positions(self, account_key: str) -> int:
        """
        Close all open positions for an account.
        
        Returns:
            Number of positions closed
        """
        positions = await self.get_open_positions(account_key)
        
        if not positions:
            return 0
        
        client = self.clients.get(account_key)
        if not client:
            logger.error(f"Client not found for account: {account_key}")
            return 0
        
        closed_count = 0
        
        for pos in positions:
            position_id = pos.get('positionId') or pos.get('id')
            
            try:
                await client.close_position(position_id)
                closed_count += 1
                logger.info(f"[{account_key}] Closed position {position_id}")
            except Exception as e:
                logger.error(f"[{account_key}] Failed to close position {position_id}: {e}")
        
        logger.info(f"[{account_key}] Closed {closed_count}/{len(positions)} position(s)")
        return closed_count
    
    async def shutdown(self):
        """Gracefully shutdown all background tasks."""
        logger.info("Shutting down AccountManager...")
        
        # Cancel all refresh tasks
        for account_key, task in self.refresh_tasks.items():
            task.cancel()
            logger.debug(f"Cancelled refresh task for {account_key}")
        
        # Wait for tasks to finish
        if self.refresh_tasks:
            await asyncio.gather(*self.refresh_tasks.values(), return_exceptions=True)
        
        logger.info("✓ AccountManager shutdown complete")


# Global account manager instance
_account_manager: Optional[AccountManager] = None


def get_account_manager() -> AccountManager:
    """Get the global account manager instance."""
    global _account_manager
    if _account_manager is None:
        _account_manager = AccountManager()
    return _account_manager
