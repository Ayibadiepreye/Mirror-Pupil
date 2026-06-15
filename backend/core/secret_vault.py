"""
Mirror Pupil v5.1 - Secret Vault
Encrypts and decrypts sensitive data (passwords, tokens) using Fernet symmetric encryption.
"""

import os
from cryptography.fernet import Fernet
from loguru import logger


class SecretVault:
    """
    Encrypts and decrypts secrets using Fernet (symmetric encryption).
    
    Usage:
        vault = SecretVault()
        encrypted = vault.encrypt("my_password")
        decrypted = vault.decrypt(encrypted)
    """
    
    def __init__(self, encryption_key: str | None = None):
        """
        Initialize vault with encryption key.
        
        Args:
            encryption_key: Base64-encoded Fernet key. If None, reads from ENCRYPTION_KEY env var.
        """
        self.key = encryption_key or os.getenv("ENCRYPTION_KEY")
        
        if not self.key:
            raise ValueError(
                "ENCRYPTION_KEY environment variable not set. "
                "Generate one with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
            )
        
        try:
            self.cipher = Fernet(self.key.encode() if isinstance(self.key, str) else self.key)
        except Exception as e:
            raise ValueError(f"Invalid encryption key: {e}")
    
    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt plaintext string.
        
        Args:
            plaintext: String to encrypt
        
        Returns:
            Base64-encoded encrypted string
        """
        try:
            encrypted_bytes = self.cipher.encrypt(plaintext.encode('utf-8'))
            return encrypted_bytes.decode('utf-8')
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise
    
    def decrypt(self, ciphertext: str) -> str:
        """
        Decrypt ciphertext string.
        
        Args:
            ciphertext: Base64-encoded encrypted string
        
        Returns:
            Decrypted plaintext string
        """
        try:
            decrypted_bytes = self.cipher.decrypt(ciphertext.encode('utf-8'))
            return decrypted_bytes.decode('utf-8')
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise


# Singleton instance
_vault: SecretVault | None = None


def get_vault() -> SecretVault:
    """Get singleton vault instance."""
    global _vault
    if _vault is None:
        _vault = SecretVault()
    return _vault
