import os
import aiohttp
import logging
import json
from solders.keypair import Keypair

logger = logging.getLogger("DatahiveBot")

class SolanaService:
    def __init__(self, session, auth_token):
        self.session = session # Existing bot requests/aiohttp session
        self.auth_token = auth_token
        self.base_url = "https://api.datahive.ai/api/user/wallet"

    def _load_wallet(self, private_key_base58):
        """Reconstructs the Keypair from a Base58 private key."""
        try:
            keypair = Keypair.from_base58_string(private_key_base58)
            return keypair
        except Exception as e:
            logger.error(f"Failed to load wallet: {e}")
            return None

    async def get_nonce(self):
        """Fetches the signing nonce from Datahive."""
        headers = {
            "Authorization": f"Bearer {self.auth_token}",
            "Content-Type": "application/json"
        }
        
        url = f"{self.base_url}/nonce"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("nonce")
                else:
                    err = await response.text()
                    logger.error(f"Failed to fetch nonce [{response.status}]: {err}")
                    return None

    async def bind_wallet(self, private_key_base58):
        """
        Executes the full wallet binding flow without a browser.
        """
        logger.info("Starting headless wallet binding process...")
        
        keypair = self._load_wallet(private_key_base58)
        if not keypair:
            return False
            
        public_key_str = str(keypair.pubkey())
        logger.info(f"Loaded Wallet: {public_key_str[:6]}...{public_key_str[-4:]}")

        nonce = await self.get_nonce()
        if not nonce:
            logger.error("Datahive did not return a nonce. Cannot bind.")
            return False

        # Sign the nonce as UTF-8 bytes
        signature = keypair.sign_message(nonce.encode('utf-8'))
        
        # Typically the signature is expected as a base58 string
        import base58
        sig_bytes = bytes(signature)
        sig_base58 = base58.b58encode(sig_bytes).decode('utf-8')

        payload = {
            "publicKey": public_key_str,
            "signature": sig_base58,  
            "walletName": "Phantom" # Spoof the wallet adapter name
        }

        headers = {
            "Authorization": f"Bearer {self.auth_token}",
            "Content-Type": "application/json",
            "Origin": "https://dashboard.datahive.ai",
            "Referer": "https://dashboard.datahive.ai/"
        }

        url = f"{self.base_url}/bind" # Adjust endpoint slightly based on actual API
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as response:
                if response.status in [200, 201]:
                    data = await response.json()
                    logger.info("Successfully bound Solana wallet to Datahive!")
                    return True
                else:
                    err = await response.text()
                    logger.error(f"Wallet Binding Failed [{response.status}]: {err}")
                    return False
