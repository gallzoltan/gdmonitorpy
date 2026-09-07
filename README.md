# gdmonitor

A Magyar Közlöny önkormányzatokra vonatkozó tartalmának figyelése.

A program letölti a Magyar Közlöny RSS feedjéből az új számokat, kinyeri
belőlük a kormányhatározatokat, pontozza őket önkormányzati kulcsszavak
alapján, az eredményt SQLite adatbázisban tárolja, majd a releváns
találatokról HTML összefoglalót küld egy levélküldő relay REST API-ján át.

## Futtatás

```bash
uv sync
cp .env.example .env    # majd töltsd ki

uv run gdmonitor                    # csak letöltés
uv run gdmonitor --analyze          # letöltés + elemzés
uv run gdmonitor --analyze --email  # a teljes futás
uv run gdmonitor --since 2025-07-30 # a dátumszűrő felülírása erre a futásra
```

Kilépési kód: `0` siker, `1` váratlan hiba, `2` konfigurációs hiba.

## Konfiguráció

Környezeti változókból jön; fejlesztéskor a projekt gyökerében lévő `.env`
fájlból is (lásd `.env.example`).

| Változó | Kötelező | Leírás |
|---|---|---|
| `FEED_URL` | igen | A Magyar Közlöny RSS feedje |
| `DB_PATH` | igen | Az SQLite adatbázis útvonala |
| `DOWNLOAD_PATH` | igen | A letöltött PDF-ek könyvtára |
| `SINCE_DATE` | nem | Statikus alsó korlát (ÉÉÉÉ-HH-NN) |
| `CERTIFICATE_PATH` | nem | Saját CA köteg TLS-t bontó proxy mögé |
| `MSG_SERVER`, `MSG_PORT` | `--email`-hez | A levélküldő relay címe |
| `EMAIL_TO`, `EMAIL_CC`, `EMAIL_BCC` | `EMAIL_TO` az `--email`-hez | Címzettek vesszővel elválasztva |
| `LOG_LEVEL` | nem | DEBUG, INFO (alapértelmezett), WARNING, ERROR |

A `SINCE_DATE` csak optimalizáció, nem állapot: a program soha nem írja felül.
Az inkrementális működést az adatbázis URL-alapú deduplikációja adja, így egy
közlöny akkor sem töltődik le kétszer, ha a dátumszűrő átengedi.

## Tesztek

```bash
uv run pytest
uv run pytest tests/test_sentence_splitter.py::test_does_not_split_on_house_number
```

## Éles üzem

Konténerben fut, rootless Podmannel, systemd timerrel ütemezve. A konténert
Podman Quadlet (`deploy/gdmonitor.container`) vagy a gyökérben lévő
`compose.yaml` definiálja; a telepítés lépései:
[`deploy/README.md`](deploy/README.md).

```bash
podman build -t gdmonitor:latest .   # vagy: podman-compose build

# Batch job, ezért `run` és nem `up`: a `run --rm` továbbadja a kilépési kódot.
# Kell hozzá egy env fájl (alapból ./deploy/gdmonitor.env, lásd
# deploy/gdmonitor.env.example) és egy adatkönyvtár (alapból ./data).
podman-compose run --rm gdmonitor
```

## Felépítés

| Modul | Feladat |
|---|---|
| `gdmodule/fetcher` | RSS feed feldolgozása, PDF letöltés |
| `gdmodule/gdmonitor` | Szövegkinyerés, határozatok kibontása, relevancia és összefoglaló |
| `gdmodule/repository` | SQLite műveletek |
| `gdmodule/sender` | HTML digest küldése a relay felé |
| `gdmodule/cli` | Parancssori belépési pont |
