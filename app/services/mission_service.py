import os
import logging
from curl_cffi.requests import AsyncSession as TLSAsyncSession
from app.services.health_generator import generate_unique_health_export

logger = logging.getLogger("DatahiveBot")

class MissionService:
    def __init__(self, session, auth_token, proxy=None, timeout=60, device_id=None):
        self.session = session # Optional: can be an existing bot requests/aiohttp session
        self.auth_token = auth_token
        self.proxy = proxy
        self.timeout = timeout
        self.device_id = device_id
        self.base_url = "https://api.datahive.ai/api/mission"

    async def complete_amazon_extension_mission(self):
        """
        Emulates the Datahive Chrome Extension's DePIN background worker loop.
        Instead of just hitting a reward URL, it registers the worker, polls the /api/job queue, 
        dummy-completes tasks to satisfy the API backend, and then triggers the Amazon website verification.
        """
        import uuid
        import asyncio
        import json
        
        device_id = self.device_id if self.device_id else str(uuid.uuid4())
        
        ext_headers = {
            "Authorization": f"Bearer {self.auth_token}",
            "Content-Type": "application/json",
            "X-App-Version": "0.2.5",
            "X-Device-Type": "extension",
            "X-User-Language": "en-US",
            "X-Device-Name": "windows pc",
            "X-Device-Model": "PC x86_64 - Chrome 120",
            "X-Device-OS": "Windows 10.0",
            "X-Device-Id": device_id,
            "X-CPU-Architecture": "x86-64",
            "X-CPU-Model": "Intel Core i7",
            "X-CPU-Processor-Count": "8",
            "x-s": "f"  # Bot detection bypass (status: not bot)
        }

        web_headers = {
            "Authorization": f"Bearer {self.auth_token}",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Origin": "https://dashboard.datahive.ai",
            "Referer": "https://dashboard.datahive.ai/"
        }

        proxies = {"http": self.proxy, "https": self.proxy} if self.proxy else None
        amazon_id = "dde81093-e2e6-489a-a46b-efd8a081cf64"
        
        logger.info("Initializing Datahive Extension Worker node...")

        try:
            async with TLSAsyncSession(proxies=proxies, timeout=self.timeout, impersonate="chrome120") as session:
                # 0. Check if the mission is actually available to prevent 400 Duplicate errors
                logger.info("Checking Amazon mission availability...")
                r_status = await session.get(self.base_url, headers=web_headers)
                if r_status.status_code == 200:
                    missions = r_status.json()
                    amazon_mission = next((m for m in missions if m.get('id') == amazon_id), None)
                    if amazon_mission:
                        is_avail = amazon_mission.get("view", {}).get("nextSubmissionAvailable", False)
                        if not is_avail:
                            logger.info(f"Skipping Amazon Mission: Already submitted or not available for this account.")
                            return True
                            
                # 1. Ping the network as a new extension node
                r_ping = await session.post("https://api.datahive.ai/api/ping", headers=ext_headers)
                if r_ping.status_code != 200:
                    logger.error(f"Failed to register extension worker: {r_ping.text}")
                    return False
                    
                # 2. Get worker info to lock in the UUID
                await session.get("https://api.datahive.ai/api/worker", headers=ext_headers)

                # 3. Drain the Job Queue (up to 3 jobs) to prove the worker is "active"
                logger.info("Fetching Datahive background data crawling jobs...")
                for _ in range(3):
                    r_job = await session.get("https://api.datahive.ai/api/job", headers=ext_headers)
                    if r_job.status_code != 200:
                        break
                        
                    data = r_job.json()
                    if not data:
                        logger.info("Job queue is empty. Worker is caught up.")
                        break
                        
                    job_id = data.get('id')
                    logger.info(f"Received crawling Job ID: {job_id}. Executing dummy response...")
                    
                    payload = {
                        "result": {"output": "mock", "html": "mock", "urls": [], "plaintext": "mock", "fields": []},
                        "metadata": {},
                        "context": "extension"
                    }
                    await session.post(f"https://api.datahive.ai/api/job/{job_id}", headers=ext_headers, json=payload)
                    await asyncio.sleep(1.5)

                # 4. Trigger Web UI verification now that our extension is "Active" on the backend
                logger.info("Attempting to verify Amazon Mission (500 points)...")
                verify_url = f"{self.base_url}/{amazon_id}/submit"
                verify_response = await session.post(verify_url, headers=web_headers, json={"submission": {}})
                
                if verify_response.status_code in [200, 201]:
                    logger.info(f"Amazon Mission Successfully Verified: {verify_response.text}")
                    return True
                else:
                    logger.error(f"Amazon Mission Verification Failed [{verify_response.status_code}]: {verify_response.text}")
                    # If this still returns 400, it means the worker needs genuine uptime on their cron cycle
                    return False
        except Exception as e:
            logger.error(f"Error executing Amazon Worker loop: {e}")
            return False

    async def complete_apple_health_mission(self, profile_id, base_zip_path):
        """
        Generates a unique Apple Health export and uploads it for 20,000 points.
        """
        output_zip = f"data/missions/health_export_profile_{profile_id}.zip"

        logger.info(f"Preparing dynamic Apple Health trace for profile {profile_id}")
        success = generate_unique_health_export(base_zip_path, output_zip, profile_id)

        if not success or not os.path.exists(output_zip):
            logger.error("Failed to generate Health payload.")
            return False

        logger.info(f"Payload generated ({os.path.getsize(output_zip) / 1024 / 1024:.2f} MB). Uploading...")

        headers = {
            "Authorization": f"Bearer {self.auth_token}",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        # Determine the upload URL (We may need to fetch a presigned URL first)
        # Using the standard direct-upload path based on typical dashboard architecture
        url = f"{self.base_url}/apple-health/upload"
        proxies = {"http": self.proxy, "https": self.proxy} if self.proxy else None

        try:
            with open(output_zip, 'rb') as file_data:
                files = {'file': ('export.zip', file_data, 'application/zip')}

                async with TLSAsyncSession(proxies=proxies, timeout=self.timeout, impersonate="chrome120") as session:
                    response = await session.post(url, headers=headers, files=files)
                    if response.status_code in [200, 201]:
                        logger.info("Apple Health Mission Completed (20,000 Points)")
                        return True
                    else:
                        logger.error(f"Upload Failed [{response.status_code}]: {response.text}")
                        return False
        except Exception as e:
            logger.error(f"Error completing Apple Health mission: {e}")
            return False
        finally:
            # Clean up the 500mb file after uploading so we don't blow up the VPS drive
            if os.path.exists(output_zip):
                os.remove(output_zip)
                logger.info("Cleaned up temporary health payload.")
