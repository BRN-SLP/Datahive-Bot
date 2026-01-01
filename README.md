# 🐝 Datahive Farm Bot

Automated farming and account management bot for [Datahive.ai](https://datahive.ai) platform.

> ⚠️ **Note:** 10% of registrations support the developer through referral codes. Thank you for using this free software!

---

## 💻 Requirements

| Software | Minimum Version | Recommended |
|----------|-----------------|-------------|
| Python | 3.9 | 3.11+ |
| PostgreSQL | 16 | 16+ |

| Resource | Notes |
|----------|-------|
| **RAM** | Depends on accounts/threads. Start with 1GB |
| **Disk** | 500MB+ (logs can grow) |
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
  registration: 1   # MUST BE 1 (rate limit protection)
  farming: 100      # Parallel farming threads
```

### Multiprocess Farming
```yaml
multiprocess_farming:
  enabled: true       # Enable multiprocess mode
  max_processes: 3    # Number of processes (0 = auto)
```

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
  use_random_ref_code_from_db: true  # Random from DB
  static_referral_code: ""            # Or set specific code
```

### Delays & Retry
```yaml
delay_before_start:
  min: 60
  max: 180

retry:
  delay_seconds: 10
  max_registration_attempts: 5
  proxy_rotation: true
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
    # ... more servers
```

---

## 📁 Data Files

Located in `config/data/`:

| File | Format |
|------|--------|
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
- `Login accounts` - Register new accounts
- `Farm accounts` - Start farming
- `Export stats` - Export to CSV (results/stats/)
- `Clear proxies` - Clear proxy assignments
- `Exit`

For background running, see [VPS_SETUP.md](VPS_SETUP.md) (tmux/screen).

---

## 🔧 Troubleshooting

| Problem | Solution |
|---------|----------|
| Database error | Check PostgreSQL is running |
| Rate limit 429 | Add more proxies |
| OTP not found | Check IMAP settings |

---

**Made with ❤️ by BRN.SLP**

---

## ⚡ Performance Tuning

### How Settings Work Together

```
Real parallelism = min(farming_threads × max_processes, max_concurrent_tasks)
```

### Calculation Formula

| Your Setup | Formula | Result |
|------------|---------|--------|
| 500 accounts × 2 devices | = 1000 total devices | |
| max_concurrent_tasks: 250 | 1000 ÷ 250 | 4 iterations |

### Recommended Settings by VPS Size

| VPS Specs | farming | max_processes | max_concurrent_tasks | Best for |
|-----------|---------|---------------|----------------------|----------|
| 1 CPU / 1GB | 50 | 1 | 50 | Up to 200 accounts |
| 2 CPU / 2GB | 100 | 2 | 150 | Up to 500 accounts |
| 4 CPU / 4GB | 100 | 3 | 300 | Up to 1000 accounts |
| 8+ CPU / 8GB+ | 150 | 4-6 | 500 | 1000+ accounts |

### Example: 500 Accounts on 4 CPU / 4GB VPS

```yaml
threads:
  registration: 1         # Always 1!
  farming: 100

multiprocess_farming:
  enabled: true
  max_processes: 3        # 3 parallel processes

farm_settings:
  max_devices_per_batch: 600
  max_concurrent_tasks: 300   # 100 × 3 = 300
  device_task_timeout: 60
```

**Result:** `100 threads × 3 processes = 300 parallel tasks`

> ⚠️ **Important:** `registration` must ALWAYS be `1` with delay ≥60 seconds to avoid rate limits!

