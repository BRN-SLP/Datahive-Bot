#!/usr/bin/env python3
"""
Script to extract referral codes from database
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.absolute()
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


async def main():
    from app.database import initialize_database, close_database
    from app.database.models.accounts import Account
    
    await initialize_database()
    
    print("\n" + "=" * 60)
    print("REFERRAL CODES FROM DATABASE")
    print("=" * 60)
    
    accounts = await Account.filter(invite_code__isnull=False).all()
    
    if not accounts:
        print("No accounts with referral codes found.")
    else:
        print(f"\nFound {len(accounts)} accounts with referral codes:\n")
        for i, account in enumerate(accounts, 1):
            print(f"{i:3}. {account.email:<40} | Code: {account.invite_code}")
    
    print("\n" + "=" * 60)
    
    await close_database()


if __name__ == "__main__":
    asyncio.run(main())
