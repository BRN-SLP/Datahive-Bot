
import asyncio
import sys
from loguru import logger
from app.database import initialize_database, close_connections
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
                logger.info("✅ Migration successful! Database is now updated.")
            except Exception as e:
                logger.error(f"❌ Migration failed: {e}")
        else:
            logger.info("✅ Column 'last_initialized_at' already exists. No action needed.")

    except Exception as e:
        logger.error(f"❌ Critical error: {e}")
    finally:
        await close_connections()

if __name__ == "__main__":
    try:
        asyncio.run(run_migration())
    except KeyboardInterrupt:
        pass
