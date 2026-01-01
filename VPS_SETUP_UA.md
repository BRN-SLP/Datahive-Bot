# 🖥️ Інструкція з налаштування

Інструкція для запуску Datahive Bot на VPS або локально.

---

## 📋 Зміст

- [Встановлення macOS](#-встановлення-macos)
- [Встановлення Windows](#-встановлення-windows)
- [Фоновий запуск (tmux/screen)](#-фоновий-запуск)
- [Швидке налаштування VPS (Ubuntu)](#-швидке-налаштування-vps-ubuntu)
- [⚠️ Розширені оптимізації](#️-розширені-оптимізації-тільки-для-експертів)

---

## 🍎 Встановлення macOS

### 1. Встановіть Homebrew
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

### 2. Встановіть Python та PostgreSQL
```bash
brew install python@3.11 postgresql@16
brew services start postgresql@16
```

### 3. Створіть базу даних
```bash
psql postgres
```
```sql
CREATE USER <ВАШ_ЮЗЕР> WITH PASSWORD '<ВАШ_ПАРОЛЬ>';
CREATE DATABASE <ВАША_БД> OWNER <ВАШ_ЮЗЕР>;
GRANT ALL PRIVILEGES ON DATABASE <ВАША_БД> TO <ВАШ_ЮЗЕР>;
\q
```

### 4. Встановіть бота
```bash
git clone https://github.com/BRN-SLP/Datahive-Bot.git
cd Datahive-Bot
python3 -m venv venv && source venv/bin/activate
pip3 install --upgrade pip
pip3 install -r requirements.txt
```

### 5. Запустіть
```bash
source venv/bin/activate
python main.py
```

---

## 🪟 Встановлення Windows

### 1. Встановіть Python 3.11+
Завантажте з [python.org](https://www.python.org/downloads/)
✅ Позначте **"Add Python to PATH"**!

### 2. Встановіть PostgreSQL 16
Завантажте з [postgresql.org](https://www.postgresql.org/download/windows/)
Запам'ятайте пароль для `postgres`.

### 3. Створіть базу даних
Відкрийте **pgAdmin** або **SQL Shell (psql)**:
```sql
CREATE USER <ВАШ_ЮЗЕР> WITH PASSWORD '<ВАШ_ПАРОЛЬ>';
CREATE DATABASE <ВАША_БД> OWNER <ВАШ_ЮЗЕР>;
GRANT ALL PRIVILEGES ON DATABASE <ВАША_БД> TO <ВАШ_ЮЗЕР>;
```

### 4. Встановіть бота
```cmd
git clone https://github.com/BRN-SLP/Datahive-Bot.git
cd Datahive-Bot
python -m venv venv
venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 5. Запустіть
```cmd
venv\Scripts\activate
python main.py
```

---

## 🔄 Фоновий запуск

Для VPS: **tmux** або **screen** щоб бот працював після відключення.

### tmux (рекомендовано)

```bash
sudo apt install tmux -y
tmux new -s datahive

# В tmux
cd ~/Datahive-Bot
source venv/bin/activate
python main.py

# Відключитись: Ctrl+B, потім D
# Підключитись: tmux attach -t datahive
```

### screen

```bash
sudo apt install screen -y
screen -S datahive

# В screen
cd ~/Datahive-Bot
source venv/bin/activate
python main.py

# Відключитись: Ctrl+A, потім D
# Підключитись: screen -r datahive
```

---

## 🚀 Швидке налаштування VPS (Ubuntu)

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

## ⚠️ Розширені оптимізації (ТІЛЬКИ ДЛЯ ЕКСПЕРТІВ)

> **🔴 УВАГА:** Може заблокувати доступ до сервера!

### Зміна SSH порту
```bash
sudo nano /etc/ssh/sshd_config
# Змініть: Port 22 → Port 2222
sudo systemctl restart ssh
# Нове підключення: ssh user@ip -p 2222
```

### UFW Firewall
```bash
sudo apt install -y ufw
sudo ufw allow 2222/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw enable
```

### Системні ліміти
Додайте до `/etc/security/limits.conf`:
```
* soft nofile 65535
* hard nofile 65535
```

Додайте до `/etc/sysctl.conf`:
```
net.core.somaxconn = 65535
vm.swappiness = 10
```
```bash
sudo sysctl -p && sudo reboot
```
