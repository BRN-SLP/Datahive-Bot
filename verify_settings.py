#!/usr/bin/env python3
"""
Configuration Verification Script
Проверяет, что все настройки правильно читаются из config.yaml
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.absolute()
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from app.config.settings import get_settings


def check_setting(name: str, value, expected_type, expected_value=None):
    """Check a single setting"""
    status = "✅"
    details = f"{type(value).__name__}: {value}"
    
    if not isinstance(value, expected_type):
        status = "❌"
        details = f"Expected {expected_type.__name__}, got {type(value).__name__}"
    elif expected_value is not None and value != expected_value:
        status = "⚠️"
        details = f"Expected {expected_value}, got {value}"
    
    print(f"{status} {name}: {details}")
    return status == "✅"


def main():
    print("=" * 60)
    print("CONFIGURATION VERIFICATION")
    print("=" * 60)
    
    settings = get_settings()
    all_passed = True
    
    # === DATABASE ===
    print("\n📦 DATABASE SETTINGS:")
    all_passed &= check_setting("database_url", settings.database_url, str)
    
    # === MULTIPROCESSING ===
    print("\n🔄 MULTIPROCESS SETTINGS:")
    all_passed &= check_setting("multiprocess_farming_enabled", settings.multiprocess_farming_enabled, bool, True)
    all_passed &= check_setting("multiprocess_max_processes", settings.multiprocess_max_processes, int, 3)
    
    # === FARM SETTINGS ===
    print("\n🌾 FARM SETTINGS:")
    farm = settings.farm_settings
    all_passed &= check_setting("max_devices_per_batch", farm.get("max_devices_per_batch"), int, 600)
    all_passed &= check_setting("max_concurrent_tasks", farm.get("max_concurrent_tasks"), int, 250)
    all_passed &= check_setting("device_task_timeout", farm.get("device_task_timeout"), int, 60)
    
    # === DEVICE SETTINGS ===
    print("\n📱 DEVICE SETTINGS:")
    device = settings.device_settings
    active = device.get("active_devices_per_account", {})
    all_passed &= check_setting("devices_per_account.min", active.get("min"), int, 1)
    all_passed &= check_setting("devices_per_account.max", active.get("max"), int, 3)
    
    # === DELAY SETTINGS ===
    print("\n⏱️ DELAY SETTINGS:")
    all_passed &= check_setting("delay_min", settings.delay_min, int, 60)
    all_passed &= check_setting("delay_max", settings.delay_max, int, 180)
    
    # === RETRY SETTINGS ===
    print("\n🔁 RETRY SETTINGS:")
    all_passed &= check_setting("retry_delay", settings.retry_delay, int, 10)
    all_passed &= check_setting("max_registration_attempts", settings.max_registration_attempts, int, 5)
    all_passed &= check_setting("max_farm_attempts", settings.max_farm_attempts, int, 5)
    all_passed &= check_setting("proxy_rotation_enabled", settings.proxy_rotation_enabled, bool, True)
    
    # === PROXY SETTINGS ===
    print("\n🌐 PROXY SETTINGS:")
    all_passed &= check_setting("check_uniqueness_of_proxies", settings.check_uniqueness_of_proxies, bool, True)
    
    # === REFERRAL SETTINGS ===
    print("\n🎁 REFERRAL SETTINGS:")
    all_passed &= check_setting("use_random_ref_code_from_db", settings.use_random_ref_code_from_db, bool, True)
    all_passed &= check_setting("static_referral_code", settings.static_referral_code, (str, type(None)))
    
    # === REDIRECT SETTINGS ===
    print("\n📧 REDIRECT SETTINGS:")
    all_passed &= check_setting("redirect_enabled", settings.redirect_enabled, bool, True)
    redirect = settings.redirect_settings
    all_passed &= check_setting("redirect.email", redirect.get("email"), str)
    all_passed &= check_setting("redirect.password", redirect.get("password"), str)
    all_passed &= check_setting("redirect.imap_server", redirect.get("imap_server"), str, "imap.gmail.com")
    
    # === IMAP SETTINGS ===
    print("\n📬 IMAP SETTINGS:")
    all_passed &= check_setting("use_proxy_for_imap", settings.use_proxy_for_imap, bool, False)
    all_passed &= check_setting("email_validation_timeout", settings.email_validation_timeout, int, 30)
    imap = settings.imap_settings
    use_single = imap.get("use_single_imap", {})
    all_passed &= check_setting("use_single_imap.enable", use_single.get("enable"), bool, True)
    all_passed &= check_setting("use_single_imap.imap_server", use_single.get("imap_server"), str, "imap.gmail.com")
    
    servers = imap.get("servers", {})
    print(f"   📋 IMAP servers mapping: {len(servers)} domains configured")
    expected_domains = ["gmail.com", "yahoo.com", "icloud.com", "mail.ru"]
    for domain in expected_domains:
        if domain in servers:
            print(f"      ✅ {domain} → {servers[domain]}")
        else:
            print(f"      ❌ {domain} → MISSING!")
            all_passed = False
    
    # === THREADS ===
    print("\n🧵 THREAD SETTINGS:")
    all_passed &= check_setting("registration_threads", settings.registration_threads, int, 1)
    all_passed &= check_setting("farming_threads", settings.farming_threads, int)
    
    # === LOGGING ===
    print("\n📝 LOGGING SETTINGS:")
    all_passed &= check_setting("logging_level", settings.logging_level, str, "INFO")
    
    # === SUMMARY ===
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ ALL SETTINGS VERIFIED SUCCESSFULLY!")
    else:
        print("⚠️ SOME SETTINGS MAY NEED ATTENTION")
    print("=" * 60)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
