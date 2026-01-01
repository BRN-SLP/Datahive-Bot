"""
Account statistics module for Datahive
Collects and exports account stats (points, status, etc.)
"""

import asyncio
import csv
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

from app.api.client import DatahiveAPI
from app.database.models.accounts import Account
from app.utils.logging import get_logger

logger = get_logger()


class AccountStats:
    """Collect and export account statistics"""
    
    def __init__(self):
        self.stats: List[Dict] = []
        self.errors: List[str] = []
    
    async def collect_stats(self, accounts: List[Account], max_concurrent: int = 5) -> None:
        """Collect stats for all accounts"""
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def process_account(account: Account) -> Optional[Dict]:
            async with semaphore:
                if not account.auth_token:
                    self.errors.append(f"{account.email}: No auth token")
                    return None
                
                try:
                    api = DatahiveAPI(proxy=account.proxy, auth_token=account.auth_token)
                    user_data = await api.request_user()
                    await api.close()
                    
                    return {
                        'email': account.email,
                        'points': user_data.get('points', 0),
                        'is_activated': user_data.get('isActivated', False),
                        'is_signup_completed': user_data.get('isSignUpCompleted', False),
                        'created_at': user_data.get('createdAt', ''),
                        'invite_code': account.invite_code or '',
                        'proxy': account.proxy or ''
                    }
                except Exception as e:
                    self.errors.append(f"{account.email}: {str(e)}")
                    return None
        
        tasks = [process_account(acc) for acc in accounts]
        results = await asyncio.gather(*tasks)
        
        self.stats = [r for r in results if r is not None]
    
    def get_summary(self) -> Dict:
        """Get summary statistics"""
        if not self.stats:
            return {'total': 0, 'total_points': 0, 'activated': 0, 'errors': len(self.errors)}
        
        total_points = sum(s['points'] for s in self.stats)
        activated = sum(1 for s in self.stats if s['is_activated'])
        completed = sum(1 for s in self.stats if s['is_signup_completed'])
        
        return {
            'total': len(self.stats),
            'total_points': round(total_points, 2),
            'avg_points': round(total_points / len(self.stats), 2),
            'activated': activated,
            'signup_completed': completed,
            'errors': len(self.errors)
        }
    
    def export_to_csv(self, filename: str = None) -> str:
        """Export stats to CSV file"""
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'results/stats/account_stats_{timestamp}.csv'
        
        # Ensure directory exists
        Path(filename).parent.mkdir(parents=True, exist_ok=True)
        
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            if not self.stats:
                f.write("No data collected\n")
                return filename
            
            writer = csv.DictWriter(f, fieldnames=self.stats[0].keys())
            writer.writeheader()
            writer.writerows(self.stats)
        
        return filename
    
    def print_table(self) -> None:
        """Print stats as a table to console"""
        if not self.stats:
            logger.warning("No stats collected")
            return
        
        # Sort by points descending
        sorted_stats = sorted(self.stats, key=lambda x: x['points'], reverse=True)
        
        print("\n" + "=" * 80)
        print(f"{'EMAIL':<40} {'POINTS':>12} {'STATUS':>10} {'SIGNUP':>10}")
        print("=" * 80)
        
        for s in sorted_stats:
            status = "Active" if s['is_activated'] else "Inactive"
            signup = "Yes" if s['is_signup_completed'] else "No"
            print(f"{s['email']:<40} {s['points']:>12.2f} {status:>10} {signup:>10}")
        
        print("=" * 80)
        
        # Print summary
        summary = self.get_summary()
        print(f"\nTotal accounts: {summary['total']}")
        print(f"Total points: {summary['total_points']}")
        print(f"Average points: {summary['avg_points']}")
        print(f"Activated: {summary['activated']}")
        print(f"Errors: {summary['errors']}")
        
        if self.errors:
            print("\nErrors:")
            for err in self.errors[:10]:  # Show first 10 errors
                print(f"  - {err}")
            if len(self.errors) > 10:
                print(f"  ... and {len(self.errors) - 10} more")


async def export_account_stats() -> None:
    """Main function to export account stats"""
    from app.database import initialize_database, close_database
    
    await initialize_database()
    
    logger.info("Collecting account statistics...")
    
    accounts = await Account.filter(auth_token__isnull=False).all()
    
    if not accounts:
        logger.warning("No accounts with auth_token found")
        await close_database()
        return
    
    logger.info(f"Found {len(accounts)} accounts with auth_token")
    
    stats = AccountStats()
    await stats.collect_stats(accounts)
    
    # Print to console
    stats.print_table()
    
    # Export to CSV
    csv_file = stats.export_to_csv()
    logger.success(f"Stats exported to: {csv_file}")
    
    await close_database()
