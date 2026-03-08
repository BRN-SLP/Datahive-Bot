import asyncio
import os
import sys
import random
import json
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))

from app.database import init_database
from app.database.models.accounts import Account
from app.database.models.devices import Device
from app.services.mission_service import MissionService
from app.utils.logging import get_logger, init_logger

# -------------------------------------------------------------
# ULTRATHINK STEALTH CONFIGURATION
# -------------------------------------------------------------
DAYS_MIN = 5
DAYS_MAX = 10
PERCENTAGE_TO_EXECUTE = 0.66  # ~66% (2/3 of total accounts)
STATE_FILE = "config/data/stealth_missions_state.json"
BASE_ZIP_PATH = "config/data/export.zip"
# -------------------------------------------------------------

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {"selected_accounts": [], "completed": [], "failed": [], "total_delay_sec": 0, "run_started": False}

def save_state(state):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=4)

async def run_stealth_protocol():
    # Setup logger
    init_logger(logging_level="INFO")
    logger = get_logger()
    
    logger.info("Initializing Stealth Mission Deployer (Anti-Sybil Mode) 🥷")
    await init_database()
    
    state = load_state()
    
    # 1. INITIAL ACCOUNT SELECTION (Run once)
    if not state.get("run_started"):
        # Fetch ONLY logged-in accounts
        all_accounts = await Account.filter(auth_token__not_isnull=True).all()
        total_accounts = len(all_accounts)
        
        if total_accounts == 0:
            logger.error("No authenticated accounts found.")
            return

        target_count = int(total_accounts * PERCENTAGE_TO_EXECUTE)
        logger.info(f"Total Auth'd Accounts: {total_accounts}. Selecting {target_count} ({PERCENTAGE_TO_EXECUTE*100}%) for varied stealth execution.")
        
        # Randomly sample the accounts to execute
        selected_accounts = random.sample(all_accounts, target_count)
        
        # Calculate random timeframe
        target_days = random.uniform(DAYS_MIN, DAYS_MAX)
        total_seconds = target_days * 24 * 3600
        
        logger.info(f"Target timeframe: {target_days:.2f} days ({total_seconds:.0f} seconds).")
        
        state["selected_accounts"] = [acc.email for acc in selected_accounts]
        state["total_delay_sec"] = total_seconds
        state["run_started"] = True
        save_state(state)
    
    # 2. CALCULATION & RESUMPTION
    selected_emails = set(state["selected_accounts"])
    completed_emails = set(state["completed"])
    failed_emails = set(state.get("failed", []))
    
    pending_emails = selected_emails - completed_emails - failed_emails
    
    if not pending_emails:
        logger.success("All selected accounts have completed their missions!")
        return
        
    # Calculate delay strictly based on remaining tasks to ensure uniform distribution
    total_sec = state["total_delay_sec"]
    # Distribute the remaining time relative to the proportion of pending tasks vs total tasks
    # Wait, simple math for average delay:
    avg_delay_sec = total_sec / max(1, len(state["selected_accounts"]))
    
    logger.info(f"Resuming stealth protocol. Remaining accounts: {len(pending_emails)} / {len(selected_emails)}")
    
    # We want to randomize the queue order for unpredictable execution
    pending_list = list(pending_emails)
    random.shuffle(pending_list)
    
    if not os.path.exists(BASE_ZIP_PATH):
        logger.error(f"Base Apple Health ZIP missing at {BASE_ZIP_PATH}. Cannot proceed.")
        return

    is_first_execution = True

    # 3. EXECUTION LOOP
    for email in pending_list:
        # Calculate a jittered delay (±30% of average)
        jitter = random.uniform(0.7, 1.3)
        current_delay = avg_delay_sec * jitter
        
        # If it's the very first task in this script run, don't wait hours. Wait 1-5 mins.
        if is_first_execution:
            current_delay = random.uniform(60, 300)
            is_first_execution = False
            
        delay_hrs = current_delay / 3600
        logger.info(f"⏳ Sleeping for {delay_hrs:.2f} hours (approx {current_delay/60:.1f} mins) before processing {email}...")
        
        # Sleep in chunks to allow keyboard interrupt easily
        chunk_size = 10
        for _ in range(int(current_delay // chunk_size)):
            await asyncio.sleep(chunk_size)
        await asyncio.sleep(current_delay % chunk_size)
        
        # Load account details
        account = await Account.get_account(email)
        if not account or not account.auth_token:
            logger.warning(f"Account {email} no longer valid or logged out. Skipping.")
            state.setdefault("failed", []).append(email)
            save_state(state)
            continue
            
        device = await Device.filter(account=account).first()
        device_id = device.device_id if device else None
        
        service = MissionService(
            session=None,
            auth_token=account.auth_token,
            proxy=account.proxy,
            device_id=device_id,
            timeout=120
        )
        
        logger.info(f"🎯 Executing payload for {email}...")
        try:
            # 1. Amazon Ext
            logger.debug("Running Amazon Mission...")
            await service.complete_amazon_extension_mission()
            
            # Mini delay between the two tasks
            await asyncio.sleep(random.uniform(5, 15))
            
            # 2. Apple Health
            logger.debug("Running Apple Health Mission...")
            success = await service.complete_apple_health_mission(str(account.id), BASE_ZIP_PATH)
            
            if success:
                logger.success(f"✅ Operations complete for {email}")
                state["completed"].append(email)
            else:
                logger.error(f"❌ Failed Apple Health for {email}")
                state.setdefault("failed", []).append(email)
                
        except Exception as e:
            logger.error(f"Critical error processing {email}: {e}")
            state.setdefault("failed", []).append(email)
            
        save_state(state)

if __name__ == "__main__":
    try:
        asyncio.run(run_stealth_protocol())
    except KeyboardInterrupt:
        print("\n[!] Stealth deployer paused. You can restart it anytime to resume.")
