# 🖥️ Setup Guide

Guide for running Datahive Bot on VPS or local machine.

---

## 📋 Contents

- [macOS Installation](#-macos-installation)
- [Windows Installation](#-windows-installation)
- [Running in Background (tmux/screen)](#-running-in-background)
- [Quick VPS Setup (Ubuntu)](#-quick-vps-setup-ubuntu)
- [⚠️ Advanced Optimizations](#️-advanced-optimizations-experts-only)

---

## 🍎 macOS Installation

### 1. Install Homebrew
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

### 2. Install Python & PostgreSQL
```bash
brew install python@3.11 postgresql@16
brew services start postgresql@16
```

### 3. Create Database
```bash
psql postgres
```
```sql
CREATE USER <YOUR_USER> WITH PASSWORD '<YOUR_PASSWORD>';
CREATE DATABASE <YOUR_DB> OWNER <YOUR_USER>;
GRANT ALL PRIVILEGES ON DATABASE <YOUR_DB> TO <YOUR_USER>;
\q
```

### 4. Install Bot
```bash
git clone https://github.com/BRN-SLP/Datahive-Bot.git
cd Datahive-Bot
python3 -m venv venv && source venv/bin/activate
pip3 install --upgrade pip
pip3 install -r requirements.txt
```

### 5. Run
```bash
source venv/bin/activate
python main.py
```

---

## 🪟 Windows Installation

### 1. Install Python 3.11+
Download from [python.org](https://www.python.org/downloads/)
✅ Check **"Add Python to PATH"** during installation!

### 2. Install PostgreSQL 16
Download from [postgresql.org](https://www.postgresql.org/download/windows/)
Remember the password for `postgres` user.

### 3. Create Database
Open **pgAdmin** or **SQL Shell (psql)**:
```sql
CREATE USER <YOUR_USER> WITH PASSWORD '<YOUR_PASSWORD>';
CREATE DATABASE <YOUR_DB> OWNER <YOUR_USER>;
GRANT ALL PRIVILEGES ON DATABASE <YOUR_DB> TO <YOUR_USER>;
```

### 4. Install Bot
Open Command Prompt or PowerShell:
```cmd
git clone https://github.com/BRN-SLP/Datahive-Bot.git
cd Datahive-Bot
python -m venv venv
venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 5. Run
```cmd
venv\Scripts\activate
python main.py
```

---

## 🔄 Running in Background

For VPS - use **tmux** or **screen** to keep bot running after disconnect.

### tmux (recommended)

```bash
sudo apt install tmux -y

# Create session
tmux new -s datahive

# Inside tmux
cd ~/Datahive-Bot
source venv/bin/activate
python main.py

# Detach: Ctrl+B, then D
# Reconnect: tmux attach -t datahive
```

### screen

```bash
sudo apt install screen -y

# Create session
screen -S datahive

# Inside screen
cd ~/Datahive-Bot
source venv/bin/activate
python main.py

# Detach: Ctrl+A, then D
# Reconnect: screen -r datahive
```

### tmux Cheat Sheet

| Command | Description |
|---------|-------------|
| `tmux new -s name` | Create session |
| `Ctrl+B, D` | Detach |
| `tmux attach -t name` | Attach |
| `tmux ls` | List sessions |

---

## 🚀 Quick VPS Setup (Ubuntu)

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y git curl wget python3 python3-pip python3-venv tmux screen

# PostgreSQL 16
sudo sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list'
wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add -
sudo apt update && sudo apt install -y postgresql-16
sudo systemctl start postgresql && sudo systemctl enable postgresql
```

---

## ⚠️ Advanced Optimizations (EXPERTS ONLY)

> **🔴 WARNING:** Can lock you out of server if applied incorrectly!

### Change SSH Port (reduces attacks)
```bash
sudo nano /etc/ssh/sshd_config
# Change: Port 22 → Port 2222
sudo systemctl restart ssh
# New connect: ssh user@ip -p 2222
```

### UFW Firewall
```bash
sudo apt install -y ufw
sudo ufw allow 2222/tcp  # or 22
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw enable
```

### System Limits
Add to `/etc/security/limits.conf`:
```
* soft nofile 65535
* hard nofile 65535
```

Add to `/etc/sysctl.conf`:
```
net.core.somaxconn = 65535
vm.swappiness = 10
```
```bash
sudo sysctl -p && sudo reboot
```
