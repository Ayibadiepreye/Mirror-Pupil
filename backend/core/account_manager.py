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
        # Credential key (email) → TradeLockerClient
        self.clients: Dict[str, TradeLockerClient] = {}
        
        # Account key (email:account_id) → account info
        self.accounts: Dict[str, Dict] = {}
        
        # Background tasks
        self.refresh_tasks: Dict[str, asyncio.Task] = {}
        
        logger.info("Initialized AccountManager")
    
    async def add_credential(
        self,
        email: str,
        password: str,
        server: str = "live"
    ) -> bool:
        """
        Add a TradeLocker credential and discover its sub-accounts.
        
        Args:
            email: TradeLocker login email
            password: TradeLocker password
            server: "live" or "demo"
        
        Returns:
            True if successful, False otherwise
        """
        if email in self.clients:
            logger.warning(f"Credential {email} already exists")
            return False
        
        logger.info(f"Adding credential: {email} ({server})")
        
        # Create client
        client = TradeLockerClient(
            email=email,
            password=password,
            server=server
        )
        
        # Authenticate
        try:
            success = await client.authenticate()
            if not success:
                logger.error(f"Failed to authenticate {email}")
                return False
        except Exception as e:
            logger.error(f"Authentication error for {email}: {e}")
            return False
        
        # Store client
        self.clients[email] = client
        
        # Discover sub-accounts
        try:
            accounts = await client.get_all_accounts()
            
            for acct in accounts:
                account_id = acct.get('id') or acct.get('accountId')
                account_number = acct.get('accountNumber') or acct.get('number')
                balance = acct.get('balance', 0.0)
                
                account_key = f"{email}:{account_id}"
                
                self.accounts[account_key] = {
                    'account_key': account_key,
                    'credential_key': email,
                    'account_id': account_id,
                    'account_number': account_number,
                    'email': email,
                    'server': server,
                    'initial_balance': balance,
                    'current_balance': balance,
                    'client': client  # Reference to shared client
                }
                
                logger.info(
                    f"  ✓ Discovered sub-account: {account_number} "
                    f"(ID: {account_id}, Balance: ${balance:,.2f})"
                )
            
            logger.info(f"✓ Added credential {email} with {len(accounts)} sub-account(s)")
            
            # Start token refresh task
            task = asyncio.create_task(token_refresh_loop(client))
            self.refresh_tasks[email] = task
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to discover accounts for {email}: {e}")
            # Clean up
            del self.clients[email]
            return False
    
    def get_client(self, credential_key: str) -> Optional[TradeLockerClient]:
        """Get TradeLocker client for a credential."""
        return self.clients.get(credential_key)
    
    def get_account(self, account_key: str) -> Optional[Dict]:
        """Get account info by account key."""
        return self.accounts.get(account_key)
    
    def get_client_for_account(self, account_key: str) -> Optional[TradeLockerClient]:
        """
        Get TradeLocker client for a specific account.
        
        Args:
            account_key: Account key (format: email:account_id)
        
        Returns:
            TradeLockerClient instance or None if account not found
        """
        account = self.get_account(account_key)
        return account['client'] if account else None
    
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
        
        client = account['client']
        account_id = account['account_id']
        
        try:
            state = await client.get_account_state(account_id)
            balance = state.get('balance', 0.0)
            equity = state.get('equity', 0.0)
            
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
        account = self.get_account(account_key)
        if not account:
            logger.error(f"Account not found: {account_key}")
            return []
        
        client = account['client']
        
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
        
        account = self.get_account(account_key)
        client = account['client']
        
        closed_count = 0
        
        for pos in positions:
            position_id = pos.get('id') or pos.get('positionId')
            
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
        for email, task in self.refresh_tasks.items():
            task.cancel()
            logger.debug(f"Cancelled refresh task for {email}")
        
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
