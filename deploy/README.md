# Telepítés AlmaLinux 9-re (rootless Podman + systemd timer)

A `gdmonitor` batch jobként fut: elindul, letölti és feldolgozza az új
közlönyöket, majd kilép. Az ütemezést systemd timer adja, a konténert
Podman Quadlet definiálja.

Az alábbi lépések a **jelenlegi cron felhasználó** nevében futnak, root nélkül.

## 1. Előkészítés

```bash
# Rootless szolgáltatás kijelentkezés után is fusson
loginctl enable-linger "$USER"

# Adatkönyvtár a hoszton
mkdir -p ~/gdmonitor/data/downloads
```

## 2. Az éles adatok átemelése

A konténer a `~/gdmonitor/data` könyvtárat látja `/data` néven.

```bash
cp /a/jelenlegi/utvonal/gazettes.db ~/gdmonitor/data/gazettes.db
cp -r /a/jelenlegi/utvonal/downloads/. ~/gdmonitor/data/downloads/
```

**Sémaellenőrzés — ezt ne hagyd ki.** A program `CREATE TABLE IF NOT EXISTS`-t
használ, ami meglévő táblához *nem* ad hozzá hiányzó oszlopot. Ha az éles
adatbázis régebbi, az első futás `no such column` hibára fut:

```bash
sqlite3 ~/gdmonitor/data/gazettes.db "PRAGMA table_info(gazettes)"
```

Mind a kilenc oszlopnak meg kell lennie: `id, title, publication_date, url,
filename, download_date, analyzed, relevant, sent_email`. Ha valamelyik
hiányzik, pótold `ALTER TABLE gazettes ADD COLUMN <név> INTEGER DEFAULT 0`
paranccsal.

## 3. Konfiguráció

```bash
mkdir -p ~/.config/gdmonitor
cp gdmonitor.env.example ~/.config/gdmonitor/gdmonitor.env
chmod 600 ~/.config/gdmonitor/gdmonitor.env
$EDITOR ~/.config/gdmonitor/gdmonitor.env
```

Ez systemd `EnvironmentFile`, nem shell szkript: az `=` köré nem kerülhet
szóköz, és az idézőjelek az érték részévé válnának.

## 4. Image építése

```bash
cd /a/repo/gyokere
podman build -t gdmonitor:latest .
podman images gdmonitor   # a várt méret ~200 MB
```

## 5. Unitok telepítése

```bash
mkdir -p ~/.config/containers/systemd ~/.config/systemd/user
cp gdmonitor.container ~/.config/containers/systemd/
cp gdmonitor.timer     ~/.config/systemd/user/

# A timer OnCalendar sorát igazítsd a jelenlegi crontab bejegyzésedhez
$EDITOR ~/.config/systemd/user/gdmonitor.timer

systemctl --user daemon-reload
systemctl --user enable --now gdmonitor.timer
```

## 6. Ellenőrzés

```bash
# Száraz futás: csak letöltés, elemzés és email nélkül
podman run --rm \
  --env-file ~/.config/gdmonitor/gdmonitor.env \
  -v ~/gdmonitor/data:/data:Z \
  --userns=keep-id:uid=1000,gid=1000 \
  --network=host \
  gdmonitor:latest gdmonitor

# Teljes futás kézzel
systemctl --user start gdmonitor.service
journalctl --user -u gdmonitor.service -n 50 --no-pager

# Időzítés állapota
systemctl --user list-timers gdmonitor.timer
```

A kilépési kód 0 sikeres futásnál, 1 váratlan hibánál, 2 konfigurációs hibánál,
így a `systemctl --user status gdmonitor` valóban `failed`-et mutat, ha baj van.

## 7. A cron kivezetése

Csak akkor, ha a konténeres futás már bizonyítottan jó. A bejegyzést érdemes
kikommentelni, nem törölni, hogy legyen visszaállási pont:

```bash
crontab -e
```

## Hibakeresés

```bash
# Konténer belülről
podman run --rm -it --entrypoint /bin/bash \
  --env-file ~/.config/gdmonitor/gdmonitor.env \
  -v ~/gdmonitor/data:/data:Z gdmonitor:latest

# Bőbeszédű napló
# a gdmonitor.env-ben: LOG_LEVEL=DEBUG
```

Ha `Permission denied` jön az adatkönyvtárra, a `:Z` SELinux-címke vagy a
`UserNS=keep-id` leképezés hiányzik a `.container` fájlból.
