# 1. Image készítése
podman build -t my-batch-job .

# 2. Egyszeri futtatás teszteléshez
podman run --rm -v ./data:/app/data my-batch-job

# 3. Egyszeri futtatás logokkal
podman run --rm -v ./data:/app/data my-batch-job 2>&1 | tee batch-$(date +%Y%m%d-%H%M%S).log

# 4. Systemd timer konfigurálása (ajánlott módszer)

# Systemd service fájl létrehozása: /etc/systemd/system/my-batch-job.service
cat > /etc/systemd/system/my-batch-job.service << 'EOF'
[Unit]
Description=My Python Batch Job
After=multi-user.target

[Service]
Type=oneshot
User=your-username
ExecStart=/usr/bin/podman run --rm -v /path/to/your/data:/app/data my-batch-job
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Systemd timer fájl létrehozása: /etc/systemd/system/my-batch-job.timer
cat > /etc/systemd/system/my-batch-job.timer << 'EOF'
[Unit]
Description=Run My Python Batch Job every hour
Requires=my-batch-job.service

[Timer]
OnCalendar=hourly
Persistent=true

[Install]
WantedBy=timers.target
EOF

# Systemd szolgáltatások engedélyezése és indítása
sudo systemctl daemon-reload
sudo systemctl enable my-batch-job.timer
sudo systemctl start my-batch-job.timer

# Timer állapotának ellenőrzése
sudo systemctl status my-batch-job.timer
sudo systemctl list-timers my-batch-job.timer

# Manuális szolgáltatás futtatás teszteléshez
sudo systemctl start my-batch-job.service

# 5. Alternatív: Crontab használata (ha systemd timer nem elérhető)
# Crontab bejegyzés hozzáadása
(crontab -l 2>/dev/null; echo "0 * * * * /usr/bin/podman run --rm -v /path/to/your/data:/app/data my-batch-job >> /var/log/my-batch-job.log 2>&1") | crontab -

# 6. Podman auto-update beállítása (opcionális)
# Ha új verziót szeretnél automatikusan használni
podman build -t my-batch-job:latest .
podman auto-update

# 7. Log fájlok megtekintése
# Systemd esetén
journalctl -u my-batch-job.service -f

# Cron esetén
tail -f /var/log/my-batch-job.log

# 8. Debug és troubleshooting
# Konténer interaktív futtatása
podman run -it --rm -v ./data:/app/data my-batch-job /bin/bash

# Image tartalmának ellenőrzése
podman run -it --rm my-batch-job ls -la /app