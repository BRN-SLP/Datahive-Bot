
import asyncio
import sys
from loguru import logger
from app.database import initialize_database, close_database
from tortoise import Tortoise

# Configure simplified logging
logger.remove()
logger.add(sys.stderr, format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{message}</level>", level="INFO")

async def run_migration():
    logger.info("Starting database migration...")
    
    try:
        await initialize_database()
        conn = Tortoise.get_connection("default")
        
        # Check if column exists
        logger.info("Checking schema...")
        result = await conn.execute_query_dict(
            "SELECT column_name FROM information_schema.columns WHERE table_name = 'datahive_devices' AND column_name = 'last_initialized_at'"
        )
        
        if not result:
            logger.info("Adding 'last_initialized_at' column to 'datahive_devices'...")
            try:
                await conn.execute_script(
                    "ALTER TABLE datahive_devices ADD COLUMN last_initialized_at TIMESTAMP WITH TIME ZONE;"
                )
                logger.info("✅ Migration successful! Devices table updated.")
            except Exception as e:
                logger.error(f"❌ Migration failed for devices: {e}")
        else:
            logger.info("✅ Column 'last_initialized_at' already exists.")

        # Check for wallet_address in accounts
        logger.info("Checking accounts schema for v2 updates...")
        wallet_result = await conn.execute_query_dict(
            "SELECT column_name FROM information_schema.columns WHERE table_name = 'datahive_accounts' AND column_name = 'wallet_address'"
        )
        # Using SQLite PRAGMA fallback if information_schema is not supported (often the case in SQLite Tortoise)
        if not wallet_result:
            try:
                sqlite_check = await conn.execute_query_dict("PRAGMA table_info(datahive_accounts);")
                has_wallet = any(col['name'] == 'wallet_address' for col in sqlite_check)
            except:
                has_wallet = False
        else:
            has_wallet = True

        if not has_wallet:
            logger.info("Adding 'wallet_address' column to 'datahive_accounts'...")
            try:
                await conn.execute_script(
                    "ALTER TABLE datahive_accounts ADD COLUMN wallet_address VARCHAR(255) NULL;"
                )
                logger.info("✅ Migration successful! Accounts table updated.")
            except Exception as e:
                logger.error(f"❌ Migration failed for accounts: {e}")
        else:
            logger.info("✅ Column 'wallet_address' already exists.")

    except Exception as e:
        logger.error(f"❌ Critical error: {e}")
    finally:
        await close_database()

if __name__ == "__main__":
    try:
        asyncio.run(run_migration())
    except KeyboardInterrupt:
        pass
