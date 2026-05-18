# Drink POS

Lokale touch-freundliche Getraenkeliste fuer Vereins- oder Veranstaltungsbetrieb.
Die App besteht aus einem FastAPI-Backend, SQLite/WAL und einer Vanilla HTML/CSS/JS PWA.

## Lokal starten

```powershell
cd C:\Users\Dani\Documents\CODEX-Projects\drink_pos\app
$env:DRINK_POS_ENV = "development"
$env:DRINK_POS_DB = "C:\Users\Dani\Documents\CODEX-Projects\drink_pos\data\drink_pos_dev.db"
py -m uvicorn main:app --host 127.0.0.1 --port 8088
```

Kasse: http://127.0.0.1:8088/

Admin: http://127.0.0.1:8088/admin

## Docker

```powershell
cd C:\Users\Dani\Documents\CODEX-Projects\drink_pos
docker compose up -d
```

Die Compose-Datei veroeffentlicht den Container auf Port `8088` und mountet `./data`.
Der Backup-Service schreibt freitags um 03:00 Uhr CSV-Snapshots nach `./data/backups`.
Lege fuer den produktiven Betrieb eine `.env` neben `docker-compose.yml` an oder setze die
Variablen vor `docker compose up -d`; Compose liest `DRINK_POS_PIN` und `DRINK_POS_ENV` daraus.

## Konfiguration

Siehe `.env.example` fuer die wichtigsten Variablen:

- `DRINK_POS_ENV`: `development` oder `production`
- `DRINK_POS_PIN`: Start-PIN beim ersten DB-Start; ersetzt außerdem eine bestehende Default-PIN `1234`
- `DRINK_POS_DB`: SQLite-Dateipfad
- `DRINK_POS_BACKUP_DIR`: Zielordner fuer CSV-Backups

In Produktion sollte die Default-PIN `1234` nicht verwendet werden. Die YAML-Projektdoku ist keine
Konfigurationsdatei; fuer den echten PIN entweder `DRINK_POS_PIN` setzen oder den PIN im Adminmenue ändern.

## Tests

```powershell
cd C:\Users\Dani\Documents\CODEX-Projects\drink_pos
py -m unittest discover -s tests
```

Die Backend-Tests verwenden pro Test eine temporaere SQLite-Datenbank.

## Sicherheit

Die App ist fuer ein vertrauenswuerdiges lokales Netzwerk gedacht. Fuer Zugriff per VPN,
Tailscale oder Reverse Proxy sollten mindestens PINs geaendert, Backups aktiviert und
externe Zugriffe zusaetzlich abgesichert werden.
