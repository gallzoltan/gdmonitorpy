# Telepítés AlmaLinux 9-re (rootless Podman + systemd timer)

A `gdmonitor` batch jobként fut: elindul, letölti és feldolgozza az új
közlönyöket, majd kilép. Az ütemezést minden esetben systemd timer adja,
a konténer definíciójára viszont két út közül lehet választani:

- **Quadlet** (`gdmonitor.container`) — nincs külön függősége, a systemd maga
  kezeli a konténert;
- **podman-compose** (`compose.yaml` a repó gyökerében) — egy fájlban a build,
  a kötetek és a környezet, kézzel is kényelmesen futtatható.

Mindkettő `gdmonitor.service` néven jelenik meg, ezért **csak az egyiket
telepítsd**. A `gdmonitor.timer` változtatás nélkül mindkettőt elindítja.

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

Compose úton ugyanez, szintén a repó gyökeréből:

```bash
podman-compose build
```

## 5. Unitok telepítése

A timer mindkét úton kell:

```bash
mkdir -p ~/.config/systemd/user
cp gdmonitor.timer ~/.config/systemd/user/

# A timer OnCalendar sorát igazítsd a jelenlegi crontab bejegyzésedhez
$EDITOR ~/.config/systemd/user/gdmonitor.timer
```

### A) Quadlet

```bash
mkdir -p ~/.config/containers/systemd
cp gdmonitor.container ~/.config/containers/systemd/
```

### B) podman-compose

```bash
sudo dnf install -y podman-compose    # vagy: pipx install podman-compose
command -v podman-compose             # ha nem /usr/bin/podman-compose, igazítsd
                                      # a unit ExecStart sorát

# A compose fájl a repó gyökerében van, mert a build kontextusa a projekt.
cp /a/repo/gyokere/compose.yaml ~/gdmonitor/
cp gdmonitor.compose.service ~/.config/systemd/user/gdmonitor.service
```

A unit két környezeti változóval mutat a hoszt oldali fájlokra
(`GDMONITOR_ENV`, `GDMONITOR_DATA`), ezért ugyanaz a compose fájl szolgál ki
fejlesztést és éles futást.

### Indítás

```bash
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

# Ugyanez compose-zal, a compose.yaml könyvtárából. A szolgáltatásnév után írt
# parancs felülírja a compose-beli `command`-ot, a `run --rm` pedig továbbadja
# a konténer kilépési kódját — az `up` elnyelné.
GDMONITOR_ENV=~/.config/gdmonitor/gdmonitor.env \
GDMONITOR_DATA=~/gdmonitor/data \
  podman-compose run --rm gdmonitor gdmonitor

# Teljes futás kézzel
systemctl --user start gdmonitor.service
journalctl --user-unit gdmonitor.service -n 50 --no-pager

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

# Compose úton
podman-compose run --rm gdmonitor /bin/bash

# Bőbeszédű napló
# a gdmonitor.env-ben: LOG_LEVEL=DEBUG
```

Ha `Permission denied` jön az adatkönyvtárra, a `:Z` SELinux-címke vagy a
`UserNS=keep-id` leképezés hiányzik a `.container` fájlból — compose úton a
`volumes` `:Z` utótagja, illetve a `userns_mode`.

Ha a compose futás a pod létrehozásán akad el, a `network_mode: host` ütközik
a podman-compose alapértelmezett pod-jával. Ezt oldja fel a compose fájl
`x-podman: in_pod: false` blokkja; ha a telepített verzió ezt a kulcsot még
nem ismeri, a `--in-pod=false` kapcsoló teszi ugyanezt.

A napló olvasásánál a `journalctl --user` **nem szűrő, hanem fájlválasztás**:
csak a per-user journal fájlokat (`user-<uid>.journal`) nyitja meg. Ha a gépen
ilyen nincs — nincs `/var/log/journal`, vagy a journald `SplitMode` beállítása
nem uid szerint bont —, akkor `No journal files were found` a válasz, miközben
a sorok ott vannak a rendszer-journalben. Ezért `--user-unit` a helyes kapcsoló:
az `_SYSTEMD_USER_UNIT=` mezőre illeszt, függetlenül attól, melyik fájlban ül az
üzenet. Ugyanezért mutat a `systemctl --user status` naplósorokat akkor is,
amikor a `journalctl --user` üresen tér vissza.

Ha `/var/log/journal` nem létezik, a napló csak a memóriában él, és
újraindításkor elvész a teljes futási előzmény. Egy batch jobnál, aminek ez az
egyetlen nyoma, érdemes tartóssá tenni (root kell hozzá):

```bash
sudo mkdir -p /var/log/journal
sudo systemd-tmpfiles --create --prefix /var/log/journal
sudo systemctl restart systemd-journald
```

Ha a timer `LAST` oszlopa üresen marad és magától sosem indul futás, a linger
hiányzik: kijelentkezés után leáll a felhasználó systemd példánya, és vele
együtt az időzítés is. Ellenőrzés:

```bash
loginctl show-user "$USER" --property=Linger
```
