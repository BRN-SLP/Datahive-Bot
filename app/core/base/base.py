import asyncio
import random
from typing import Optional, Literal

from app.api.client import DatahiveAPI
from app.core.exceptions import APIError, APIErrorType
from app.core.farm.task import FarmTask
from app.database import get_db
from app.database.models.accounts import Account
from app.database.models.devices import Device
from app.utils.logging import get_logger, short_id
from app.utils.proxy import get_proxy_manager
from app.utils.shutdown import is_shutdown_requested
from app.utils.email import EmailValidator, LinkExtractor
from app.config.settings import get_settings

logger = get_logger()


def _task_data_preview(fields: dict, max_len: int = 60) -> str:
    """Build a compact one-line summary of extracted task fields."""
    parts = []
    for key, val in fields.items():
        if isinstance(val, list):
            parts.append(f"{key}: [{len(val)} items]")
        elif isinstance(val, dict):
            parts.append(f"{key}: {{...}}")
        elif val:
            text = str(val).strip()
            total = len(text)
            preview = text[:max_len] + ("…" if total > max_len else "")
            parts.append(f'{key}: "{preview}" ({total} chars)')
        else:
            parts.append(f"{key}: empty")
    return " | ".join(parts) if parts else "no fields"


class Bot:
    def __init__(self, email: str, email_password: str, imap_server: str, 
                 proxy: Optional[str] = None, account_index: Optional[int] = None):
        self.email = email
        self.email_password = email_password
        self.imap_server = imap_server
        self.proxy = proxy
        self.account_index = account_index
        self.api = DatahiveAPI(proxy=proxy)
        self.db = get_db()
        self.settings = get_settings()
        self.proxy_manager = get_proxy_manager()
        
        self.running = True
        self.attempt_count = 0
        self._initialized_devices = set()

    @staticmethod
    def _build_log_prefix(
        process_id: Optional[int] = None,
        account: Optional[Account] = None,
        device: Optional[Device] = None
    ) -> str:
        """Compose a compact log prefix: P:N | email | dev:xxxxxxxx"""
        parts = []
        if process_id is not None:
            parts.append(f'P:{process_id}')
        if account:
            parts.append(account.email)
        if device:
            parts.append(f'dev:{short_id(device.device_id)}')
        return ' | '.join(parts)
    
    async def _get_or_assign_proxy(self) -> Optional[str]:
        """Get proxy from database or assign a new one"""
        account = await Account.get_account(self.email)
        
        if account and account.active_account_proxy:
            self.proxy = account.active_account_proxy
            logger.debug("Using saved proxy from database", self.email)
            return self.proxy
        
        new_proxy = await self.proxy_manager.get_proxy()
        if new_proxy:
            self.proxy = new_proxy
            if account:
                await account.update_proxy(new_proxy)
            logger.debug("Assigned new proxy", self.email)
        
        return self.proxy
    
    async def _rotate_proxy(self) -> Optional[str]:
        """Rotate proxy - get new from pool, release old one"""
        old_proxy = self.proxy
        
        new_proxy = await self.proxy_manager.get_proxy()
        
        if old_proxy:
            await self.proxy_manager.release_proxy(old_proxy)
        
        if new_proxy:
            self.proxy = new_proxy
            
            account = await Account.get_account(self.email)
            if account:
                await account.update_proxy(new_proxy)
            
            logger.info("Rotated proxy", self.email)
        else:
            logger.warning("No proxy available", self.email)
        
        return self.proxy
    
    async def _handle_curl_cffi_error(self) -> bool:
        """Handle curl_cffi errors"""
        logger.info("Handling curl_cffi error: waiting 1-2 seconds before session reset", self.email)
        
        try:
            await asyncio.sleep(1.5)
        except asyncio.CancelledError:
            return False
        
        if not self.running or is_shutdown_requested():
            return False
        
        await self.api.close()
        
        if self.settings.proxy_rotation_enabled:
            try:
                await self._rotate_proxy()
                self.attempt_count = 0
            except Exception as e:
                logger.error(f"Error rotating proxy: {e}", self.email)
        
        try:
            await asyncio.sleep(1)
        except asyncio.CancelledError:
            return False
        
        if not self.running or is_shutdown_requested():
            return False
        
        try:
            self.api = DatahiveAPI(proxy=self.proxy)
            logger.debug("New API session created after curl_cffi error", self.email)
            return True
        except Exception as e:
            logger.error(f"Failed to create new API session after curl_cffi error: {e}", self.email)
            return False
    
    async def _prepare_account_proxy(self, value=None) -> Optional[str]:
        """Prepare proxy for account or device"""
        if value:
            if isinstance(value, Device):
                proxy = value.active_device_proxy
                if not proxy:
                    account = await value.account
                    if account and account.active_account_proxy:
                        proxy = account.active_account_proxy
                        await value.update_device_proxy(proxy)
            elif isinstance(value, Account):
                proxy = value.active_account_proxy
            else:
                proxy = None
            
            if not proxy:
                new_proxy = await self.proxy_manager.get_proxy()
                if not new_proxy:
                    raise Exception('No proxies available')
                
                proxy = new_proxy
                self.proxy = new_proxy
                
                if isinstance(value, Device):
                    await value.update_device_proxy(proxy)
                    account = await value.account
                    if account:
                        await account.update_proxy(proxy)
                elif isinstance(value, Account):
                    await value.update_proxy(proxy)
            
            return proxy
        else:
            if self.proxy:
                return self.proxy
            
            return await self._get_or_assign_proxy()
    
    async def _update_account_proxy(
        self,
        account_data,
        attempt: int,
        max_attempts: int,
        proxy: Optional[str] = None,
        process_id: Optional[int] = None
    ):
        """Update proxy for account or device on error"""
        account = None
        if isinstance(account_data, Device):
            account = await account_data.account
        prefix = self._build_log_prefix(process_id, account or None, account_data if isinstance(account_data, Device) else None)
        prefix_text = f'{prefix} | ' if prefix else ''
        
        if not self.settings.proxy_rotation_enabled:
            logger.info(f'{prefix_text}Proxy change disabled | Retrying in {self.settings.retry_delay}s.. | Attempt: {attempt + 1}/{max_attempts}..')
            await asyncio.sleep(self.settings.retry_delay)
            return
        
        proxy_changed_log = f'{prefix_text}Proxy changed | Retrying in {self.settings.retry_delay}s.. | Attempt: {attempt + 1}/{max_attempts}..'
        
        new_proxy = await self._rotate_proxy()
        
        if isinstance(account_data, Device):
            if new_proxy:
                await account_data.update_device_proxy(new_proxy)
        
        logger.info(proxy_changed_log)
        await asyncio.sleep(self.settings.retry_delay)
    
    async def _validate_email(self, proxy: Optional[str] = None) -> dict:
        """Validate email via IMAP"""
        try:
            # Use redirect email if enabled
            if self.settings.redirect_enabled:
                redirect = self.settings.redirect_settings
                validator = EmailValidator(
                    redirect.get("imap_server", ""),
                    redirect.get("email", ""),
                    redirect.get("password", "")
                )
            else:
                validator = EmailValidator(
                    self.imap_server,
                    self.email,
                    self.email_password
                )
            
            result = await validator.validate(proxy=proxy)
            return result
        except Exception as e:
            logger.error(f"Error in _validate_email for {self.email}: {e}", self.email)
            return {
                'status': False,
                'identifier': self.email,
                'data': None,
                'error': f'Validation failed: {str(e)}'
            }
    
    async def _extract_link(self, proxy: Optional[str] = None) -> dict:
        """Extract confirmation link from email"""
        try:
            # Use redirect email if enabled
            if self.settings.redirect_enabled:
                redirect = self.settings.redirect_settings
                extractor = LinkExtractor(
                    imap_server=redirect.get("imap_server", ""),
                    email=redirect.get("email", ""),
                    password=redirect.get("password", "")
                )
            else:
                extractor = LinkExtractor(
                    imap_server=self.imap_server,
                    email=self.email,
                    password=self.email_password
                )
            
            result = await extractor.extract_link(proxy=proxy)
            return result
        except Exception as e:
            logger.error(f"Error in _extract_link for {self.email}: {e}", self.email)
            return {
                'status': False,
                'identifier': self.email,
                'data': None,
                'error': f'Extraction failed: {str(e)}'
            }
    
    async def _get_auth_token(self) -> Optional[str]:
        """Get auth_token from database"""
        try:
            await self.db.init()
            token = await Account.get_auth_token(self.email)
            if token:
                self.api.auth_token = token
            return token
        except Exception as e:
            logger.error(f"Failed to get auth token: {e}", self.email)
            return None
    
    async def _cleanup(self) -> None:
        """Cleanup resources"""
        try:
            if hasattr(self, 'api') and self.api:
                await self.api.close()
            
            if hasattr(self, 'proxy') and self.proxy:
                try:
                    await self.proxy_manager.release_proxy(self.proxy)
                except Exception:
                    pass
                    
        except (asyncio.CancelledError, Exception) as e:
            if isinstance(e, asyncio.CancelledError):
                if hasattr(self, 'api') and self.api:
                    try:
                        await self.api.close()
                    except Exception:
                        pass
            else:
                logger.debug(f"Cleanup error (safe to ignore): {e}", self.email)
    
    async def process_task(self, device: Device, account: Account, api: DatahiveAPI, process_id: Optional[int] = None):
        """Process farming task"""
        # Build log prefix BEFORE try so it stays defined for the except block.
        prefix = self._build_log_prefix(process_id, account, device)
        prefix_text = f'{prefix} | ' if prefix else ''

        try:
            task_data = await api.request_task(device=device)

            if task_data:
                task_id = task_data.get('id')
                rule_collection = task_data.get('ruleCollection') or {}
                yaml_rules = rule_collection.get('yamlRules')
                task_vars = task_data.get('vars') or {}
                target_url = task_vars.get('url')
                request_timeout = task_vars.get('timeout')
                task_short = task_id[:8] if task_id else '?'

                if not task_id or not yaml_rules:
                    logger.warning(f'{prefix_text}Invalid task data received, skipping')
                    return

                target_page_html = await api.fetch_task_html(target_url, timeout=request_timeout)

                farm_task = FarmTask(
                    task_id=task_id,
                    target_url_html=target_page_html,
                    task_yaml_rules=yaml_rules,
                    task_vars=task_vars
                )
                task_json_data = farm_task.build_task_json_data()

                await asyncio.sleep(random.randint(2, 5))

                # Collect fields from all outputs in the result
                fields = {}
                result = task_json_data.get('result') or {}
                for out_key, out_val in result.items():
                    if isinstance(out_val, dict) and 'fields' in out_val:
                        fields.update(out_val.get('fields') or {})

                has_data = any(str(v).strip() for v in fields.values())

                await api.complete_task(device=device, task_id=task_id, json_data=task_json_data)

                if has_data:
                    field_count = len(fields)
                    preview = _task_data_preview(fields)
                    logger.success(f'{prefix_text}Task {task_short} ─ {field_count} field{"s" if field_count != 1 else ""} ─ {preview}')
                else:
                    logger.debug(f'{prefix_text}Task {task_short} ─ no data | URL: {target_url} | HTML: {len(target_page_html) if target_page_html else 0} chars')
                    logger.info(f'{prefix_text}Task {task_short} ─ no data extracted')
            else:
                logger.info(f'{prefix_text}No task available')

        except Exception as e:
            logger.error(f'{prefix_text}Error processing task: {e}')
            if 'task_id' in locals() and task_id:
                try:
                    await api.report_error(
                        device=device,
                        task_id=task_id,
                        error=str(e),
                        metadata={'url': target_url if 'target_url' in locals() else None}
                    )
                    logger.info(f'{prefix_text}Reported error to API')
                except Exception as report_error:
                    logger.error(f'{prefix_text}Failed to report error: {report_error}')

    async def process_farm(
        self,
        device: Device,
        task: Literal['ping', 'request_task'],
        process_id: Optional[int] = None
    ):
        """Process account farming"""
        max_attempts = self.settings.max_farm_attempts
        account = await device.account
        api = None
        prefix = self._build_log_prefix(process_id, account, device)
        prefix_text = f'{prefix} | ' if prefix else ''
        
        for attempt in range(max_attempts):
            try:
                proxy = await self._prepare_account_proxy(device)
                api = DatahiveAPI(proxy=proxy, auth_token=account.auth_token)
                
                if task == 'ping':
                    # Extension 0.2.6 has NO background ping. POST /api/ping was removed.
                    # Real extension only polls /api/configuration every 30 min via setInterval(Wr, 1.8e6).
                    # We reuse this scheduler slot to (a) refresh /configuration every 30 min,
                    # and (b) do full init (worker/config/worker-ip) every 24h.

                    # Full init every 24h
                    should_initialize = True
                    if device.last_initialized_at:
                        from datetime import datetime, timezone, timedelta
                        now = datetime.now(timezone.utc)
                        last_init = device.last_initialized_at
                        if last_init.tzinfo is None:
                            last_init = last_init.replace(tzinfo=timezone.utc)

                        if now - last_init < timedelta(hours=24):
                            should_initialize = False

                    if should_initialize:
                        try:
                            logger.info(f'{prefix_text}Device init (worker / config / ip)..')
                            worker_data = await api.get_worker(device=device)

                            # Extension 0.2.6: gate on user.isActivated
                            user_info = (worker_data or {}).get('user') or {}
                            if user_info.get('isActivated') is False:
                                logger.warning(
                                    f'{prefix_text}Account is not activated (isActivated=false). '
                                    f'New 0.2.6 flow requires POST /api/user/activate with accessCode. '
                                    f'Job requests may be refused by server.'
                                )

                            await api.get_configuration(device=device)
                            await api.get_worker_ip_metadata(device=device)

                            # Mark as initialized in DB for persistence
                            from datetime import datetime, timezone
                            await device.update_device(last_initialized_at=datetime.now(timezone.utc))
                            self._initialized_devices.add(device.device_id)
                        except Exception as e:
                            logger.warning(f'{prefix_text}Initialization warning: {e}')
                            pass  # Non-critical
                    else:
                        # Between 24h init cycles — mimic extension's periodic Wr() poll of /configuration.
                        try:
                            await api.get_configuration(device=device)
                            logger.debug(f'{prefix_text}Configuration refreshed')
                        except Exception as e:
                            logger.debug(f'{prefix_text}Config refresh skipped: {e}')
                else:
                    logger.info(f'{prefix_text}Requesting task')
                    await self.process_task(device=device, account=account, api=api, process_id=process_id)
                
                if api:
                    await api.close()
                return
                
            except APIError as error:
                if hasattr(error, 'error_type') and error.error_type == APIErrorType.CLIENT_UPGRADE_REQUIRED:
                    logger.warning(f'{prefix_text}Client upgrade required, skipped')
                    if api:
                        await api.close()
                    return

                logger.error(f'{prefix_text}API error: {error} | skipped')
                if api:
                    await api.close()
                return
            except Exception as error:
                error_str = str(error)
                if 'Proxy Authentication Required' in error_str and not self.settings.proxy_rotation_enabled:
                    logger.error(f'{prefix_text}Proxy auth failed — check proxy settings | skipped')
                    if api:
                        await api.close()
                    return

                is_last_attempt = attempt == max_attempts - 1
                if is_last_attempt:
                    logger.error(f'{prefix_text}Max retries reached, skipped | {error}')
                    if api:
                        await api.close()
                    return

                logger.error(f'{prefix_text}Farm error: {error}')
                await self._update_account_proxy(
                    device,
                    attempt,
                    max_attempts,
                    proxy=api.proxy if api else None,
                    process_id=process_id
                )
                if api:
                    await api.close()
                continue
        
        if api:
            await api.close()
    
    def stop(self) -> None:
        """Stop bot"""
        self.running = False
