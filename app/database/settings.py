"""
Database settings and initialization
"""

import os
from loguru import logger
from tortoise import Tortoise
from sys import exit


async def initialize_database():
    """Initialize database connection"""
    try:
        await Tortoise.close_connections()
    except:
        pass
    
    
    from app.config.settings import get_settings
    settings = get_settings()
    db_url = settings.database_url
    
    # Log the DB URL being used (masking protocol for debug)
    logger.debug(f"Initializing database connection: {db_url.split('@')[-1] if '@' in db_url else db_url}")
    
    try:
        await Tortoise.init(
            db_url=db_url,
            modules={"models": ["app.database.models.accounts", "app.database.models.devices"]},
            timezone="UTC"
        )
        
        # Generate schemas - safe=True to avoid errors if table already exists
        await Tortoise.generate_schemas(safe=True)
        logger.debug("Database initialized successfully")
    except Exception as error:
        logger.error(f"Error while initializing database: {error}")
        try:
            await Tortoise.close_connections()
        except Exception as close_error:
            logger.error(f"Error while closing database connections: {close_error}")
        exit(1)


async def close_database():
    """Close database connections"""
    try:
        await Tortoise.close_connections()
        logger.debug("Database connections closed")
    except Exception as error:
        logger.error(f"Error while closing database: {error}")