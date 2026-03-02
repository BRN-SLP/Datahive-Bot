import os
import aiohttp
import logging
from app.services.health_generator import generate_unique_health_export

logger = logging.getLogger("DatahiveBot")

class MissionService:
    def __init__(self, session, auth_token):
        self.session = session # Optional: can be an existing bot requests/aiohttp session
        self.auth_token = auth_token
        self.base_url = "https://api.datahive.ai/api/mission"

    async def complete_amazon_extension_mission(self):
        """
        Spoofs the background request made by the Datahive Chrome Extension.
        This grants 500 points + x2 boost without actually needing the extension.
        """
        headers = {
            "Authorization": f"Bearer {self.auth_token}",
            "Content-Type": "application/json",
            # Spoof extension headers that they might check
            "Origin": "chrome-extension://plhffonmnaagghjicdofjlofpkmdmldp", 
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        
        url = f"{self.base_url}/amazon/connect"
        logger.info("Attempting to spoof Amazon Extension mission...")
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json={}) as response:
                if response.status in [200, 201]:
                    data = await response.json()
                    logger.info(f"Amazon Mission Success: {data}")
                    return True
                else:
                    err = await response.text()
                    logger.error(f"Amazon Mission Failed [{response.status}]: {err}")
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
        
        try:
            with open(output_zip, 'rb') as file_data:
                # aiohttp handles multipart/form-data natively if we pass a dict to `data`
                form_data = aiohttp.FormData()
                form_data.add_field('file', 
                                  file_data, 
                                  filename='export.zip', 
                                  content_type='application/zip')
                                  
                async with aiohttp.ClientSession() as session:
                    async with session.post(url, headers=headers, data=form_data) as response:
                        if response.status in [200, 201]:
                            logger.info("Apple Health Mission Completed (20,000 Points)")
                            return True
                        else:
                            err = await response.text()
                            logger.error(f"Upload Failed [{response.status}]: {err}")
                            return False
        finally:
            # Clean up the 500mb file after uploading so we don't blow up the VPS drive
            if os.path.exists(output_zip):
                os.remove(output_zip)
                logger.info("Cleaned up temporary health payload.")
