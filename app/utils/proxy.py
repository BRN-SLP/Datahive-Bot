import asyncio
from collections import deque
from typing import Optional, List, Set

from app.utils.logging import get_logger

logger = get_logger()


class ProxyManager:
    """Proxy manager with uniqueness tracking"""
    
    def __init__(self):
        self.proxies: deque = deque()
        self.used_proxies: Set[str] = set()  # Proxies used in current session
        self.lock = asyncio.Lock()
        
    def load_proxies(self, proxy_urls: List[str]) -> None:
        self.proxies = deque([url.strip() for url in proxy_urls if url.strip()])
        self.used_proxies.clear()
    
    async def load_db_proxies(self) -> None:
        """Load proxies already used by accounts in database"""
        try:
            from app.database.models.accounts import Account
            accounts = await Account.all()
            for account in accounts:
                if account.proxy:
                    self.used_proxies.add(account.proxy)
            logger.info(f"Loaded {len(self.used_proxies)} used proxies from database")
        except Exception as e:
            logger.warning(f"Could not load DB proxies: {e}")
    
    async def get_proxy(self, require_unique: bool = True) -> Optional[str]:
        """Get a proxy, optionally requiring it to be unused"""
        async with self.lock:
            if not self.proxies:
                logger.warning("No available proxies")
                return None
            
            if not require_unique:
                proxy = self.proxies.popleft()
                return proxy
            
            # Find unused proxy
            checked = 0
            while checked < len(self.proxies):
                proxy = self.proxies.popleft()
                if proxy not in self.used_proxies:
                    self.used_proxies.add(proxy)
                    return proxy
                # Put back and try next
                self.proxies.append(proxy)
                checked += 1
            
            logger.warning("All proxies have been used, returning any available")
            proxy = self.proxies.popleft()
            return proxy
    
    async def release_proxy(self, proxy: Optional[str]) -> None:
        """Return proxy to pool (keeps it marked as used)"""
        if not proxy:
            return
        async with self.lock:
            self.proxies.append(proxy)
    
    async def remove_proxy(self, proxy: Optional[str]) -> bool:
        if not proxy:
            return False
        async with self.lock:
            try:
                self.proxies.remove(proxy)
                logger.info("Removed bad proxy from pool")
                return True
            except ValueError:
                return False
    
    def get_stats(self) -> dict:
        return {
            "total": len(self.proxies),
            "used": len(self.used_proxies)
        }


_proxy_manager: Optional[ProxyManager] = None


def get_proxy_manager() -> ProxyManager:
    global _proxy_manager
    if _proxy_manager is None:
        _proxy_manager = ProxyManager()
    return _proxy_manager

