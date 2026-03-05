# Deployment Guide: KSERC Truing-Up Platform

This guide outlines the recommended deployment procedure for a production environment like a Virtual Private Server (VPS) or AWS EC2 instance.

## Prerequisites

- Ubuntu 22.04 LTS (recommended)
- Python 3.10 or 3.11
- Nginx
- Uvicorn / Gunicorn
- Supervisor or Systemd

---

## 1. System Setup

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install python3-pip python3-venv nginx sqlite3 libmagickwand-dev -y
```

## 2. Application Setup

1. **Clone the repository:**
```bash
git clone https://github.com/KSERC/sdl-truing-up.git
cd sdl-truing-up
```

2. **Set up Virtual Environment:**
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

3. **Initialize the Data Directories:**
```bash
mkdir -p data/myt_baselines data/regulations uploads output_orders audit_logs
```

## 3. Running with Supervisor / Systemd

Create a `systemd` service file `/etc/systemd/system/kserc-api.service`:

```ini
[Unit]
Description=KSERC SDL Truing-Up FastAPI Application
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/sdl-truing-up
Environment="PATH=/var/www/sdl-truing-up/venv/bin"
ExecStart=/var/www/sdl-truing-up/venv/bin/uvicorn app:app --host 127.0.0.1 --port 8000 --workers 4

[Install]
WantedBy=multi-user.target
```

Enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable kserc-api
sudo systemctl start kserc-api
```

## 4. Nginx Reverse Proxy Configuration

Configure Nginx to proxy requests to the FastAPI backend running on port 8000.

Create a block in `/etc/nginx/sites-available/kserc`:

```nginx
server {
    listen 80;
    server_name api.kserctrueup.gov.in;

    client_max_body_size 50M; # Crucial for PDF uploads

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable the Nginx block:
```bash
sudo ln -s /etc/nginx/sites-available/kserc /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

## 5. Security & Maintenance

- **SSL:** Use `certbot` and Let's Encrypt to secure the API domain.
- **Log Rotation:** The audit logs and app logs should be managed by `logrotate`.
- **Backups:** Setup a cron job to backup the `data/kserc_truing_up.db` SQLite database daily.
