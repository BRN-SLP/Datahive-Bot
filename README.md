# Datahive Farm Bot

Automated farming and account management bot for [Datahive.ai](https://datahive.ai) platform.

> ⚠️ **Note:** 10% of registrations support the developer through referral codes. Thank you for using this free software!

---

## 💻 Requirements

| Software | Minimum Version | Recommended |
| :--- | :--- | :--- |
| Python | 3.11 | 3.12 |
| PostgreSQL | 16 | 16 |

| Resource | Notes |
| :--- | :--- |
| **RAM** | ~512MB base + ~1MB per active slot |
| **CPU** | Parallelism = `min(cpu_thread_count, accounts)` |
| **Proxies** | HTTP/SOCKS5. Test which work for your region |

---

## 🚀 Installation

### Linux (Ubuntu/Debian)

```bash
# Update & install packages
sudo apt update && sudo apt upgrade -y
sudo apt install -y git curl wget python3 python3-pip python3-venv

# PostgreSQL 16
sudo sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list'
wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add -
sudo apt update && sudo apt install -y postgresql-16
sudo systemctl start postgresql && sudo systemctl enable postgresql
```

**Create database:**

```bash
sudo -u postgres psql
```

```sql
CREATE USER <YOUR_USER> WITH PASSWORD '<YOUR_PASSWORD>';
CREATE DATABASE <YOUR_DB> OWNER <YOUR_USER>;
GRANT ALL PRIVILEGES ON DATABASE <YOUR_DB> TO <YOUR_USER>;
\q
```

**Install bot:**

```bash
git clone https://github.com/BRN-SLP/Datahive-Bot.git
cd Datahive-Bot
python3 -m venv venv && source venv/bin/activate
pip3 install --upgrade pip
pip3 install -r requirements.txt
```

### macOS / Windows

See [VPS_SETUP.md](VPS_SETUP.md) for detailed instructions.

---

## 🔄 Database Migration

If updating from v1.0.x, run the migration script once before starting the bot:

```bash
source venv/bin/activate
python migrate.py
```

> First-time installs do not need this — the schema is created automatically.

---

## ⚙️ Configuration

Edit `config/config.yaml`:

### Database

```yaml
application_settings:
  database_url: "postgres://<USER>:<PASSWORD>@localhost:5432/<DATABASE>"
```

### Threading

```yaml
threads:
  registration: 1    # MUST BE 1 (rate limit protection)
  farming: 20        # Concurrent farming slots (capped to account count)
```

> `farming` maps to `cpu_thread_count`. Actual slots = `min(cpu_thread_count, len(accounts))`.

### Farm Settings

```yaml
farm_settings:
  max_devices_per_batch: 600
  max_concurrent_tasks: 250
  device_task_timeout: 60
```

### Referral Codes

```yaml
referral_code_settings:
  source: "db"              # "db" | "file" | "static"
  static_referral_code: ""
```

### Delays & Retry

```yaml
delay_before_start:
  min: 60     # enforced minimum — cannot go below 60s
  max: 180    # enforced maximum — cannot exceed 1200s

retry:
  delay_seconds: 10
  max_registration_attempts: 5
  proxy_rotation: true
  proxy_rotation_after_timeouts: 3
```

### Email Redirect (Optional)

```yaml
redirect_settings:
  enable: false
  email: "your_email@gmail.com"
  password: "your_app_password"
  imap_server: "imap.gmail.com"
```

### IMAP Settings

```yaml
imap_settings:
  use_proxy_for_imap: false
  timeout: 30
  servers:
    gmail.com: imap.gmail.com
    icloud.com: imap.mail.me.com
```

---

## 📁 Data Files

Located in `config/data/`:

| File | Format |
| :--- | :--- |
| `login_accounts.txt` | `email:password` (one per line) |
| `farm_accounts.txt` | `email` (one per line, empty = all) |
| `proxies.txt` | `http://user:pass@host:port` |
| `referral_codes.txt` | `code` (one per line) |
| `export_stats_accounts.txt` | `email` (one per line, empty = all) |

---

## 🎮 Usage

```bash
source venv/bin/activate
python main.py
```

**Menu:**

| Option | Description |
| :--- | :--- |
| `Login accounts` | Authenticate accounts via email OTP |
| `Farm accounts` | Start the farming loop |
| `Bind Solana Wallets` | Link Solana wallets to accounts |
| `Execute Missions (Standard)` | Run standard mission set |
| `Deploy Stealth Missions (Anti-Sybil) 🥷` | Run missions with anti-Sybil profile rotation |
| `Export stats` | Export account stats to CSV (`results/stats/`) |
| `Clear proxies` | Clear proxy assignments |
| `Exit` | Exit the bot |

For background running use tmux:

```bash
tmux new -s datahive
python main.py
# Ctrl+B then D to detach
```

---

## ⚡ Performance Tuning

### Architecture (v1.2.0)

The bot runs a **single asyncio event loop** with N concurrent coroutines — no separate processes or threads.

```
Active farming slots = min(cpu_thread_count, len(accounts))
```

Accounts are distributed round-robin across slots. Each slot farms one account at a time.

### Recommended Settings by VPS Size

| VPS Specs | `cpu_thread_count` | Best for |
| :--- | :--- | :--- |
| 1 CPU / 1GB | 10–20 | Up to 100 accounts |
| 2 CPU / 2GB | 20–40 | Up to 300 accounts |
| 4 CPU / 4GB | 40–80 | Up to 600 accounts |
| 8+ CPU / 8GB+ | 80–150 | 600+ accounts |

### Example: 200 Accounts on 2 CPU / 2GB VPS

```yaml
threads:
  registration: 1
  farming: 30        # 30 concurrent slots

farm_settings:
  device_task_timeout: 60
  max_devices_per_batch: 600
  max_concurrent_tasks: 250

delay_before_start:
  min: 60
  max: 300
```

> ⚠️ `registration` must **always** be `1` — Datahive rate-limits OTP delivery aggressively.

---

## 🔧 Troubleshooting

| Problem | Solution |
| :--- | :--- |
| Database connection error | Check PostgreSQL is running: `sudo systemctl status postgresql` |
| Rate limit (HTTP 429) | Add more proxies; increase `delay_before_start.min` |
| OTP not received | Check IMAP settings; verify email provider supports IMAP |
| `IndexError` on task list | Update to v1.2.0 (fixed in this release) |
| XML health report corrupt | Update to v1.2.0 (fixed in this release) |
| Bot freezes at shutdown | Update to v1.2.0 (fixed in this release) |

---

## 📋 Changelog

### v1.2.0
- Fixed `IndexError` when task list is shorter than expected slot count
- Fixed XML health report — `ET.tostring` was injecting XML declaration per element
- Fixed `tempfile.mktemp()` race condition — replaced with `mkstemp()`
- Fixed database teardown — `close_database` now correctly calls Tortoise ORM shutdown
- Fixed `imap_server` attribute error — field does not exist on `Account` model (removed from 5 places)
- Fixed `save_registration_result` — missing `email_password` argument
- Fixed duplicate `next_task_request_available = True` assignment in farming loop
- Fixed `delay_min`/`delay_max` — values were not clamped, allowing sub-60s or unbounded delays
- Fixed `farm_settings` attribute access — dict accessed via `getattr` instead of `.get()`
- Added menu options: Bind Solana Wallets, Execute Missions (Standard), Deploy Stealth Missions (Anti-Sybil)
- Replaced multiprocess farming with single-loop `ThreadFarmingManager` (asyncio coroutines)
- Added `cpu_thread_count` config property

### v1.1.0
- Added `last_initialized_at` tracking for daily device initialization
- Added `migrate.py` for schema upgrades

### v1.0.0
- Initial public release

---

**Made with ❤️ by BRN.SLP** | [Telegram](https://t.me/BoRn_SliPPy) | [GitHub](https://github.com/BRN-SLP)
