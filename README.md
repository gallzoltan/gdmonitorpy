# gdmonitor
A Magyar Közlöny önkormányzatokra vonatkozó tartalom elemzése

## Telepítési lépések

### 1. Projekt előkészítése
```bash
mkdir my-batch-job
cd my-batch-job
mkdir data logs config
```

### 2. Image készítése
```bash
podman build -t my-batch-job .
```

### 3. Tesztelés
```bash
# Egyszeri futtatás
podman run --rm -v ./data:/app/data my-batch-job

# Debug módban
podman run -it --rm -v ./data:/app/data my-batch-job /bin/bash
```

### 4. Ütemezés beállítása (systemd - ajánlott)
```bash
# Service és timer fájlok létrehozása (lásd a Podman parancsok részt)
sudo systemctl daemon-reload
sudo systemctl enable my-batch-job.timer
sudo systemctl start my-batch-job.timer
```

### 5. Monitorozás
```bash
# Timer állapot
sudo systemctl status my-batch-job.timer

# Logok megtekintése
journalctl -u my-batch-job.service -f
```

## Környezeti változók
A konténerben a következő környezeti változókat használhatod:

- `DATA_DIR`: Input/output fájlok könyvtára (alapértelmezett: /app/data)
- `LOG_LEVEL`: Logging szint (DEBUG, INFO, WARNING, ERROR)
- `CONFIG_FILE`: Konfigurációs fájl elérési útja

## Biztonsági megfontolások

- A konténer nem-root felhasználóként fut
- AlmaLinux biztonságos alaprendszer
- Minimális függőségek telepítése
- Volume-ok használata az adatok elkülönítésére
