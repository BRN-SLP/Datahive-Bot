import asyncio
import random
from typing import List

from app.ui.menu import get_menu
from app.utils.logging import get_logger
from app.database import (
    load_accounts, load_proxies, initialize_proxy_manager,
    load_accounts_from_database,
    initialize_database, close_database
)
from app.utils.proxy import get_proxy_manager
from app.utils.results import initialize_results
from app.utils.email import get_imap_server_for_email
from app.core.modules.executor import ModuleExecutor
from app.core.farm import MultiprocessFarmingManager
from app.config.settings import get_settings
from app.database.models.accounts import Account

logger = get_logger()


class DatahiveApp:
    def __init__(self):
        self.menu = get_menu()
        self.settings = get_settings()
        self.running = True
        self.database_initialized = False
    
    async def run(self) -> None:
        await self._initialize_database()
        
        while self.running:
            try:
                # self.menu.show_welcome() - Removed, show_menu handles header
                choice = await self.menu.show_menu()
                
                if choice == 1:
                    await self._handle_registration()
                elif choice == 2:
                    await self._handle_farming()
                elif choice == 3:
                    await self._handle_export_stats()
                elif choice == 4:
                    await self._handle_clear_proxies()
                elif choice == 6:
                    await self._handle_bind_wallets()
                elif choice == 7:
                    await self._handle_missions()
                elif choice == 5:
                    self.running = False
                    logger.info("Shutting down...")
                    break
                
                if self.running:
                    input("Press Enter to continue...")
                    
            except KeyboardInterrupt:
                self.running = False
                logger.info("Interrupted by user")
                break
            except Exception as e:
                logger.error(f"Application error: {e}")
                input("Press Enter to continue...")
        
        await self._cleanup()
    
    async def _handle_registration(self) -> None:
        accounts = load_accounts("login_accounts.txt")
        if not accounts:
            logger.error("No accounts found in login_accounts.txt")
            return
        
        proxies = load_proxies()
        # Initialize proxy manager for rotation
        try:
            initialize_proxy_manager()
            # Load proxies already used by accounts in database
            proxy_manager = get_proxy_manager()
            await proxy_manager.load_db_proxies()
        except Exception as e:
            logger.warning(f"Failed to initialize proxy manager: {e}. Proxy rotation may not work.")
        
        self.menu.show_operation_info("Registration", len(accounts))
        
        semaphore = asyncio.Semaphore(self.settings.registration_threads)
        
        async def process_account(account_data: dict, index: int) -> bool:
            async with semaphore:
                delay = random.randint(self.settings.delay_min, self.settings.delay_max)
                if delay > 0:
                    logger.info(f"Waiting {delay}s before registration", account_data['email'])
                    await asyncio.sleep(delay)
                
                from app.utils.proxy import get_proxy_manager
                proxy_manager = get_proxy_manager()
                proxy = await proxy_manager.get_proxy()
                
                executor = ModuleExecutor(
                    email=account_data['email'],
                    email_password=account_data['email_password'],
                    imap_server=account_data['imap_server'],
                    proxy=proxy,
                    account_index=index
                )
                return await executor.process_registration()
        
        tasks = [process_account(account_data, i) for i, account_data in enumerate(accounts)]
        
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
        except KeyboardInterrupt:
            logger.info("Registration interrupted")
            return
        
        for idx, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Registration task #{idx + 1} failed: {result}")
        
        success_count = sum(1 for r in results if r is True)
        failed_count = sum(1 for r in results if r is False or isinstance(r, Exception))
        
        logger.info(f"Registration completed: {success_count} processed, {failed_count} failed")
    
    async def _handle_farming(self) -> None:
        from app.database.loader import load_farm_accounts
        farm_emails = load_farm_accounts("farm_accounts.txt")
        
        db_accounts = []
        
        if farm_emails:
            for email in farm_emails:
                account = await Account.get_account(email)
                if account:
                    if not account.auth_token:
                        logger.warning(f"Account {email} not logged in. Skipped for farming.")
                        continue
                    db_accounts.append(account)
                else:
                    logger.warning(f"Account {email} not found in database. Skipped for farming.")
        else:
            logger.info("No valid emails in farm_accounts.txt, loading all accounts from database...")
            all_accounts = await load_accounts_from_database()
            for account in all_accounts:
                if account.auth_token:
                    db_accounts.append(account)
                else:
                    logger.debug(f"Account {account.email} not logged in. Skipped for farming.")
        
        if not db_accounts:
            logger.error("No valid accounts found in database for farming (accounts must have auth_token)")
            return
        
        accounts_data = []
        for account in db_accounts:
            accounts_data.append({
                'email': account.email,
                'email_password': account.email_password,
                'imap_server': get_imap_server_for_email(account.email)
            })
        
        self.menu.show_operation_info("Farming", len(accounts_data))
        
        if self.settings.multiprocess_farming_enabled:
            logger.debug("Using multiprocess farming mode")
            # Shuffle accounts if enabled
            if hasattr(self.settings, 'shuffle_accounts') and self.settings.shuffle_accounts:
                logger.debug("Shuffling accounts before multiprocess farming...")
                random.shuffle(accounts_data)
            await self._handle_multiprocess_farming(accounts_data)
        else:
            logger.debug("Using single process farming mode")
            # Shuffle accounts if enabled
            if hasattr(self.settings, 'shuffle_accounts') and self.settings.shuffle_accounts:
                logger.debug("Shuffling accounts before single process farming...")
                random.shuffle(accounts_data)
            await self._handle_single_process_farming(accounts_data)
    
    async def _handle_multiprocess_farming(self, accounts: List[dict]) -> None:
        logger.debug("Starting multiprocess farming mode")
        
        try:
            initialize_proxy_manager()
        except Exception as e:
            logger.error(f"Failed to initialize proxy manager: {e}")
            return
        
        farming_manager = MultiprocessFarmingManager()
        
        try:
            await farming_manager.start_multiprocess_farming(accounts)
        except KeyboardInterrupt:
            logger.info("Multiprocess farming interrupted, stopping processes...")
            farming_manager.stop()
            return
        except Exception as e:
            logger.error(f"Multiprocess farming error: {e}")
            farming_manager.stop()
    
    async def _handle_single_process_farming(self, accounts: List[dict]) -> None:
        logger.info("Starting single process farming mode")
        
        proxies = load_proxies()
        proxy_manager = get_proxy_manager()
        proxy_manager.load_proxies(proxies)
        
        total_accounts = len(accounts)
        semaphore = asyncio.Semaphore(self.settings.farming_threads)
        
        async def process_account(account_data: dict, index: int) -> None:
            async with semaphore:
                delay = random.randint(self.settings.delay_min, self.settings.delay_max)
                if delay > 0:
                    await asyncio.sleep(delay)
                
                from app.database.models.accounts import Account
                account = await Account.get_account(account_data['email'])
                proxy = account.active_account_proxy if account and account.active_account_proxy else None
                
                if not proxy:
                    proxy = await proxy_manager.get_proxy()
                
                executor = ModuleExecutor(
                    email=account_data['email'],
                    email_password=account_data['email_password'],
                    imap_server=account_data['imap_server'],
                    proxy=proxy,
                    account_index=index
                )
                try:
                    await executor.process_farming()
                finally:
                    pass
        
        tasks = [process_account(account_data, i) for i, account_data in enumerate(accounts)]
        
        try:
            await asyncio.gather(*tasks)
        except KeyboardInterrupt:
            logger.info("Farming interrupted")
        except Exception as e:
            logger.error(f"Farming error: {e}")
    
    async def _handle_export_stats(self) -> None:
        """Handle account statistics export"""
        from app.core.modules.stats import AccountStats
        from app.database.models.accounts import Account
        from pathlib import Path
        
        logger.info("Collecting account statistics...")
        
        # Try to load accounts from export_stats_accounts.txt
        stats_file = Path("config/data/export_stats_accounts.txt")
        if stats_file.exists():
            with open(stats_file, 'r') as f:
                emails = [line.strip() for line in f if line.strip() and not line.startswith('#')]
            
            if emails:
                logger.info(f"Loading {len(emails)} accounts from export_stats_accounts.txt")
                accounts = []
                for email in emails:
                    # Extract email if in email:password format
                    if ':' in email:
                        email = email.split(':')[0]
                    account = await Account.get_account(email)
                    if account and account.auth_token:
                        accounts.append(account)
                    else:
                        logger.warning(f"Account {email} not found or has no auth_token")
            else:
                logger.info("export_stats_accounts.txt is empty, loading all accounts")
                accounts = await Account.filter(auth_token__isnull=False).all()
        else:
            logger.info("No export_stats_accounts.txt found, loading all accounts from database")
            accounts = await Account.filter(auth_token__isnull=False).all()
        
        if not accounts:
            logger.warning("No accounts with auth_token found")
            return
        
        logger.info(f"Found {len(accounts)} accounts with auth_token")
        
        self.menu.show_operation_info("Export Stats", len(accounts))
        
        stats = AccountStats()
        await stats.collect_stats(accounts)
        
        # Print to console
        stats.print_table()
        
        # Export to CSV
        csv_file = stats.export_to_csv()
        logger.success(f"Stats exported to: {csv_file}")
    
    async def _handle_bind_wallets(self) -> None:
        """Bind Solana wallets to accounts based on data/wallets.txt"""
        from app.database.models.accounts import Account
        from app.services.solana_service import SolanaService
        import os
        
        logger.info("Starting Solana Wallet Binding process...")
        wallets_file = "data/wallets.txt"
        
        if not os.path.exists(wallets_file):
            logger.error(f"File {wallets_file} not found. Please create it first.")
            return

        with open(wallets_file, 'r') as f:
            lines = [line.strip() for line in f if line.strip() and not line.startswith('#')]
            
        if not lines:
            logger.warning(f"No valid entries found in {wallets_file}")
            return
            
        self.menu.show_operation_info("Binding Wallets", len(lines))
        
        success_count = 0
        skip_count = 0
        fail_count = 0

        for line in lines:
            if ':' not in line:
                logger.warning(f"Invalid format: {line}. Expected email:private_key")
                fail_count += 1
                continue
                
            email, pkey = line.split(':', 1)
            account = await Account.get_account(email)
            
            if not account:
                logger.warning(f"Account {email} not found in database. Skipping.")
                skip_count += 1
                continue
                
            if account.wallet_address:
                logger.info(f"Account {email} already has a wallet bound: {account.wallet_address}. Skipping.")
                skip_count += 1
                continue
                
            if not account.auth_token:
                logger.warning(f"Account {email} has no auth_token (not logged in). Cannot bind offline. Skipping.")
                skip_count += 1
                continue
                
            logger.info(f"Binding wallet for {email}...")
            
            # Using dummy session since SolanaService isolates its own requests currently, 
            # or pass None if SolanaService creates its own aiohttp Session.
            service = SolanaService(session=None, auth_token=account.auth_token)
            success, address = await service.bind_wallet(pkey)
            
            if success and address:
                account.wallet_address = address
                await account.save(update_fields=['wallet_address'])
                logger.success(f"Successfully bound wallet to {email} and saved to DB.")
                success_count += 1
            else:
                logger.error(f"Failed to bind wallet for {email}")
                fail_count += 1
                
        logger.info(f"Wallet Binding Complete: {success_count} success, {skip_count} skipped, {fail_count} failed")

    async def _handle_missions(self) -> None:
        """Execute Datahive Amazon & Apple Health missions for eligible accounts."""
        from app.database.models.accounts import Account
        from app.services.mission_service import MissionService
        import questionary
        import os
        
        # We use a custom style to match the neon aesthetic
        custom_style = questionary.Style([
            ('qmark', 'fg:#673ab7 bold'),       
            ('question', 'bold'),               
            ('answer', 'fg:#f44336 bold'),      
            ('pointer', 'fg:#00ffff bold'),     
            ('highlighted', 'fg:#00ffff bold'), 
            ('selected', 'fg:#cc5454')
        ])

        choice = await questionary.select(
            "Which missions do you want to run?",
            choices=[
                "1. Amazon Extension (500 pts)",
                "2. Apple Health Upload (20,000 pts)",
                "3. Both Missions",
                "Cancel"
            ],
            style=custom_style
        ).unsafe_ask_async()
        
        if choice == "Cancel":
            return
            
        run_amazon = choice in ["1. Amazon Extension (500 pts)", "3. Both Missions"]
        run_health = choice in ["2. Apple Health Upload (20,000 pts)", "3. Both Missions"]
        
        base_zip_path = "data/export.zip"
        if run_health and not os.path.exists(base_zip_path):
            logger.error(f"Apple Health seed file not found at {base_zip_path}. Please place your export.zip there.")
            return

        # Load only logged in accounts
        accounts = await Account.filter(auth_token__not_isnull=True).all()
        
        if not accounts:
            logger.warning("No logged-in accounts found to execute missions.")
            return
            
        self.menu.show_operation_info(f"Executing Missions ({choice.split('.')[1].strip()})", len(accounts))

        for account in accounts:
            logger.info(f"Processing missions for {account.email}...")
            service = MissionService(session=None, auth_token=account.auth_token)
            
            if run_amazon:
                await service.complete_amazon_extension_mission()
                # Adding slight delay between missions
                await asyncio.sleep(2)
                
            if run_health:
                # We use the internal DB ID or a hashed version of email to stay deterministic
                await service.complete_apple_health_mission(str(account.id), base_zip_path)
                await asyncio.sleep(2)
                
        logger.info("All selected missions completed.")

    async def _handle_clear_proxies(self) -> None:
        """Clear all proxy assignments from accounts in database"""
        from app.database.models.accounts import Account
        from app.database.models.devices import Device
        
        logger.info("Clearing proxies from all accounts and devices...")
        
        accounts = await Account.all()
        devices = await Device.all()
        
        if not accounts and not devices:
            logger.warning("No accounts or devices found in database")
            return
        
        cleared_accounts = 0
        for account in accounts:
            if account.active_account_proxy:
                account.active_account_proxy = None
                await account.save(update_fields=['active_account_proxy'])
                cleared_accounts += 1
        
        cleared_devices = 0
        for device in devices:
            if device.active_device_proxy:
                device.active_device_proxy = None
                await device.save(update_fields=['active_device_proxy'])
                cleared_devices += 1
        
        logger.success(f"Cleared proxies from {cleared_accounts} accounts and {cleared_devices} devices")
    
    async def _initialize_database(self) -> None:
        if self.database_initialized:
            return
        
        try:
            await initialize_database()
            self.database_initialized = True
            logger.success("Database initialized")
            
            await initialize_results()
            
            accounts = await load_accounts_from_database()
            logger.info(f"Found {len(accounts)} accounts in database")
                
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    async def _cleanup(self) -> None:
        try:
            if self.database_initialized:
                await close_database()
                logger.debug("Database connections closed")
            
        except Exception as e:
            logger.error(f"Cleanup error: {e}")
    
    async def stop(self) -> None:
        self.running = False
        await self._cleanup()
        logger.info("Application stopped")
        logger.info("Application stopped")
