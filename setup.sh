#!/bin/bash
# =============================================================
# setup.sh — первичная установка на Ubuntu 24.04
# Запускать от root: bash setup.sh
# =============================================================

set -e

APP_DIR="/opt/welders"
REPO_URL="https://github.com/Ilya16302/welders.git"
SERVICE_NAME="welders"

echo "=== Установка зависимостей ==="
apt update -q
apt install -y python3-pip python3-venv nginx git unzip

echo "=== Клонирование репозитория ==="
if [ -d "$APP_DIR" ]; then
    cd "$APP_DIR"
    git pull
else
    git clone "$REPO_URL" "$APP_DIR"
    cd "$APP_DIR"
fi

echo "=== Виртуальное окружение ==="
python3 -m venv venv
source venv/bin/activate
pip install -q -r requirements.txt

echo "=== Распаковка базы данных ==="
cd "$APP_DIR"
python3 -c "
import zipfile, os
zp = 'data/db.zip'
jp = 'data/db.json'
if os.path.exists(zp):
    with zipfile.ZipFile(zp) as z:
        z.extract('db.json', 'data/')
    print('db.json распакован')
else:
    print('ВНИМАНИЕ: data/db.zip не найден!')
"

echo "=== Systemd сервис ==="
cat > /etc/systemd/system/${SERVICE_NAME}.service << EOF
[Unit]
Description=Welder Statistics App
After=network.target

[Service]
User=root
WorkingDirectory=${APP_DIR}
ExecStart=${APP_DIR}/venv/bin/gunicorn -w 2 -b 127.0.0.1:5000 --timeout 120 app:app
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable $SERVICE_NAME
systemctl restart $SERVICE_NAME

echo "=== Nginx ==="
cat > /etc/nginx/sites-available/$SERVICE_NAME << EOF
server {
    listen 80;
    server_name _;

    client_max_body_size 200M;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_read_timeout 120s;
    }
}
EOF

ln -sf /etc/nginx/sites-available/$SERVICE_NAME /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl restart nginx

echo ""
echo "======================================"
echo "✅ Установка завершена!"
echo "   Сайт доступен по IP сервера"
echo "======================================"
