#!/bin/bash
# =============================================================
# update.sh — обновление базы данных на сервере
# Запускать после того как загрузил новый db.zip на GitHub:
#   bash /opt/welders/update.sh
# =============================================================

APP_DIR="/opt/welders"

echo "=== Получаем обновления с GitHub ==="
cd "$APP_DIR"
git pull

echo "=== Распаковываем db.zip ==="
python3 -c "
import zipfile, os
zp = 'data/db.zip'
jp = 'data/db.json'
if os.path.exists(zp):
    with zipfile.ZipFile(zp) as z:
        z.extract('db.json', 'data/')
    print('✅ db.json обновлён')
else:
    print('❌ data/db.zip не найден!')
"

echo "=== Перезапускаем сервис ==="
systemctl restart welders

echo "✅ Готово! Сайт обновлён."
