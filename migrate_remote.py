
import asyncio
from app.database import initialize_database, close_database
from tortoise import Tortoise

async def run_migration():
    print("Initializing DB...")
    await initialize_database()
    
    print("Running migration...")
    conn = Tortoise.get_connection("default")
    
    # Check if column exists
    result = await conn.execute_query_dict(
        "SELECT column_name FROM information_schema.columns WHERE table_name = 'datahive_devices' AND column_name = 'last_initialized_at'"
    )
    
    if not result:
        print("Adding last_initialized_at column...")
        try:
            await conn.execute_script(
                "ALTER TABLE datahive_devices ADD COLUMN last_initialized_at TIMESTAMP WITH TIME ZONE;"
            )
            print("Migration successful.")
        except Exception as e:
            print(f"Migration failed: {e}")
    else:
        print("Column last_initialized_at already exists.")

    await close_database()

if __name__ == "__main__":
    asyncio.run(run_migration())
