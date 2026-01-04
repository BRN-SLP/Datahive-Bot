# 🐝 Datahive Farm Bot

Автоматизований бот для фармінгу на платформі [Datahive.ai](https://datahive.ai).

> ⚠️ **Примітка:** 10% реєстрацій підтримують розробника через реферальні коди. Дякуємо!

---

## 💻 Вимоги

| Програма | Мінімальна | Рекомендована |
|----------|------------|---------------|
| Python | 3.9 | 3.11+ |
| PostgreSQL | 16 | 16+ |

| Ресурс | Примітки |
|--------|----------|
| **RAM** | Від 1GB залежно від акаунтів |
| **Диск** | 500MB+ (логи ростуть) |
| **Проксі** | HTTP/SOCKS5. Тестуйте |

---

## 🚀 Встановлення

### Linux (Ubuntu/Debian)

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y git curl wget python3 python3-pip python3-venv

# PostgreSQL 16
sudo sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list'
wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add -
sudo apt update && sudo apt install -y postgresql-16
sudo systemctl start postgresql && sudo systemctl enable postgresql
```

**База даних:**

```sql
CREATE USER <ВАШ_ЮЗЕР> WITH PASSWORD '<ВАШ_ПАРОЛЬ>';
CREATE DATABASE <ВАША_БД> OWNER <ВАШ_ЮЗЕР>;
GRANT ALL PRIVILEGES ON DATABASE <ВАША_БД> TO <ВАШ_ЮЗЕР>;
```

**Бот:**

```bash
git clone https://github.com/BRN-SLP/Datahive-Bot.git && cd Datahive-Bot
python3 -m venv venv && source venv/bin/activate
pip3 install --upgrade pip && pip3 install -r requirements.txt
```

### macOS / Windows

Див. [VPS_SETUP_UA.md](VPS_SETUP_UA.md)

---

## ⚙️ Налаштування (config/config.yaml)

### База даних

```yaml
application_settings:
  database_url: "postgres://<ЮЗЕР>:<ПАРОЛЬ>@localhost:5432/<БД>"
```

### Потоки

```yaml
threads:
  registration: 1   # ОБОВ.ЯЗКОВО 1 (захист від rate limit)
  farming: 100      # Фармінг
```

### Мультипроцесинг

```yaml
multiprocess_farming:
  enabled: true
  max_processes: 3
```

### Реферальні коди

```yaml
referral_code_settings:
  source: "db"              # "db" = випадковий з БД
                            # "file" = випадковий з referral_codes.txt
                            # "static" = використовувати static_referral_code
  static_referral_code: ""  # Використовується при source: "static"
```

### Затримки та повтори

```yaml
delay_before_start:
  min: 60
  max: 180

retry:
  delay_seconds: 10
  max_registration_attempts: 5
  proxy_rotation: true
  proxy_rotation_after_timeouts: 3  # Ротація проксі після N таймаутів поспіль
```

### Редірект пошти (опціонально)

```yaml
redirect_settings:
  enable: false
  email: "your_email@gmail.com"
  password: "your_app_password"
```

---

## 📁 Файли даних (config/data/)

| Файл | Формат |
|------|--------|
| `login_accounts.txt` | `email:password` |
| `farm_accounts.txt` | `email` (порожній = всі) |
| `proxies.txt` | `http://user:pass@host:port` |
| `referral_codes.txt` | `код` |
| `export_stats_accounts.txt` | `email` (порожній = всі) |

---

## 🎮 Використання

```bash
source venv/bin/activate
python main.py
```

**Меню:**

- `Login accounts` - Реєстрація
- `Farm accounts` - Фармінг
- `Export stats` - Експорт CSV
- `Clear proxies` - Очистити проксі
- `Exit`

Фоновий запуск: див. [VPS_SETUP_UA.md](VPS_SETUP_UA.md) (tmux/screen)

---

**Зроблено з ❤️ BRN.SLP**

---

## ⚡ Оптимізація продуктивності

### Формула розрахунку

```
Реальний паралелізм = min(farming_threads × max_processes, max_concurrent_tasks)
```

### Рекомендації за розміром VPS

| VPS | farming | max_processes | max_concurrent_tasks | Для |
|-----|---------|---------------|----------------------|-----|
| 1 CPU / 1GB | 50 | 1 | 50 | До 200 акаунтів |
| 2 CPU / 2GB | 100 | 2 | 150 | До 500 акаунтів |
| 4 CPU / 4GB | 100 | 3 | 300 | До 1000 акаунтів |
| 8+ CPU / 8GB+ | 150 | 4-6 | 500 | 1000+ акаунтів |

### Приклад: 500 акаунтів на 4 CPU / 4GB

```yaml
threads:
  registration: 1         # Завжди 1!
  farming: 100

multiprocess_farming:
  enabled: true
  max_processes: 3

farm_settings:
  max_concurrent_tasks: 300   # 100 × 3 = 300
```

**Результат:** `100 потоків × 3 процеси = 300 паралельних задач`

> ⚠️ `registration` ЗАВЖДИ `1` з затримкою ≥60 секунд!
