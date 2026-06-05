# Drink POS

Lokale touch-freundliche Getraenkeliste / Strichliste fuer Vereins- oder Veranstaltungsbetrieb.
Die App besteht aus einem FastAPI-Backend, SQLite/WAL und einer Vanilla HTML/CSS/JS PWA.

## Lokal starten

```powershell
cd <repo-path>\app
$env:DRINK_POS_ENV = "development"
$env:DRINK_POS_DB = "<repo-path>\data\drink_pos_dev.db"
py -m uvicorn main:app --host 127.0.0.1 --port 8088
```

Kasse: http://127.0.0.1:8088/

Admin: http://127.0.0.1:8088/admin

## GitHub + GHCR

Das Repository ist fuer GitHub Container Registry vorbereitet. Der Workflow
`.github/workflows/container.yml` baut bei jedem Push ein Image und veroeffentlicht den Tag
`latest`, den Branch-Tag und einen `sha-...` Tag.

Repo anlegen und pushen:

```powershell
cd <repo-path>
gh repo create tostman1/drink-pos --private --source . --remote origin --push
```

Wenn `gh` nicht installiert ist:

```powershell
git remote add origin git@github.com:tostman1/drink-pos.git
git push -u origin HEAD
```

Nach dem ersten erfolgreichen GitHub-Actions-Lauf ist das Image hier verfuegbar:

```text
ghcr.io/tostman1/drink-pos:latest
```

## Synology Container Manager

Fuer Synology ist `compose.synology.yaml` die einfachste Vorlage. Sie zieht das fertige
Image aus GHCR, baut nichts lokal und speichert alle produktiven Daten in `./data`.

1. In der File Station einen Projektordner anlegen, z. B.:

   ```text
   /volume1/docker/drink-pos
   /volume1/docker/drink-pos/data
   /volume1/docker/drink-pos/data/backups
   ```

2. Wenn bereits eine Datenbank existiert: alten Container stoppen und die Dateien in den
   neuen `data`-Ordner kopieren:

   ```text
   drink_pos.db
   drink_pos.db-wal   falls vorhanden
   drink_pos.db-shm   falls vorhanden
   ```

   Wichtig: `DRINK_POS_DB` in der YAML leer lassen. Dann verwendet die App automatisch
   `/app/data/drink_pos.db`. Eine vorhandene `drink_pos.db` wird weiterverwendet.

3. In Synology Container Manager:

   ```text
   Project > Create > Name: drink-pos
   Path: /volume1/docker/drink-pos
   Source: compose.synology.yaml einfuegen oder hochladen
   Build/Deploy starten
   ```

4. Danach die App oeffnen:

   ```text
   http://<NAS-IP>:8088/
   http://<NAS-IP>:8088/admin
   ```

Die App erstellt nur dann eine neue SQLite-Datei, wenn im gemounteten `data`-Ordner noch
keine `drink_pos.db` vorhanden ist. Beim Start werden Tabellen und fehlende Spalten mit
`CREATE TABLE IF NOT EXISTS` bzw. Migrationen ergaenzt; die bestehende DB-Datei wird nicht
geloescht oder ersetzt. Backups werden freitags um 03:00 nach `data/backups` geschrieben.

Synology darf keinen Host-Ordner auf `/app` mounten. `/app` gehoert komplett dem Container-Image:
dort liegen `main.py`, `backup_database.py` und die Webdateien. Ein leerer Host-Ordner wie
`/volume1/docker/drink-pos/app` wuerde diesen Image-Inhalt verdecken und fuehrt zu Fehlern wie
`/app/backup_database.py not found`. In der Compose-Datei ist deshalb nur dieses Volume korrekt:

```yaml
volumes:
  - ./data:/app/data
```

`DRINK_POS_BACKUP_DIR: /app/data/backups` liegt damit auf dem NAS unter
`/volume1/docker/drink-pos/data/backups`, also direkt neben der Datenbank.

## Podman-Instanz starten

Auf jeder Instanz:

```bash
git clone https://github.com/tostman1/drink-pos.git
cd drink-pos
cp .env.example .env
mkdir -p data
```

In `.env` mindestens setzen:

```dotenv
DRINK_POS_IMAGE=ghcr.io/tostman1/drink-pos:latest
DRINK_POS_ENV=production
DRINK_POS_PIN=change-this-pin
DRINK_POS_AGENT_TOKEN=change-this-long-random-token
```

Dann starten:

```bash
. ./.env
podman compose up -d
```

Die kanonische Compose-Datei ist `compose.yaml`. Sie setzt fuer beide Services
`pull_policy: always`, veroeffentlicht die App auf Port `8088` und mountet nur `./data`.
Damit bleiben SQLite-Datenbank und Backups beim Container-Update erhalten.
Die Update-Skripte darunter verwenden `podman pull --policy newer`, also wird nur gezogen,
wenn im Registry wirklich ein neueres Image verfuegbar ist.

## Container direkt updaten

Linux:

```bash
./deploy/podman-update.sh
```

PowerShell:

```powershell
.\deploy\podman-update.ps1
```

Die Skripte lesen `.env`, fuehren `podman pull --policy newer $DRINK_POS_IMAGE` aus, starten die Container mit
`podman compose up -d --force-recreate` neu und raeumen alte Images auf. Fuer manuelle Updates reicht:

```bash
podman pull --policy newer ghcr.io/tostman1/drink-pos:latest
podman compose up -d --force-recreate
```

Optionaler systemd-Timer auf einer Linux-Instanz:

```bash
sudo cp deploy/drink-pos-update.service deploy/drink-pos-update.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now drink-pos-update.timer
```

Die Unit erwartet das Repo unter `/opt/drink_pos`. Wenn die Instanz in einem anderen Pfad liegt,
`WorkingDirectory` und `ExecStart` in `deploy/drink-pos-update.service` entsprechend anpassen.

## Agenten-REST-Interface

Aktiviere das Interface mit:

```dotenv
DRINK_POS_AGENT_TOKEN=change-this-long-random-token
```

Agenten authentifizieren sich mit einem der beiden Header:

```http
Authorization: Bearer <token>
X-Drink-Pos-Agent-Token: <token>
```

Wichtige Endpunkte:

- `GET /api/agent/capabilities`: verfuegbare Agenten-Aktionen und OpenAPI-Hinweis
- `GET /api/agent/state`: Personen, Artikel, offene Posten und offene Anfragen lesen
- `POST /api/agent/person`: offene Posten und Zahlungs-Vorschau fuer eine Person lesen
- `POST /api/agent/book-drink`: normales Getraenk buchen
- `POST /api/agent/round-request`: Rundenanfrage fuer eine Person erstellen

Admin-Aktionen wie Zahlungsabschluss, Kassensturz, PIN-Aenderung oder Artikelverwaltung bleiben
bewusst auf dem Admin-Interface bzw. den PIN-geschuetzten Admin-Endpunkten.

Beispiel:

```bash
curl -H "Authorization: Bearer $DRINK_POS_AGENT_TOKEN" \
  http://127.0.0.1:8088/api/agent/capabilities
```

```bash
curl -X POST http://127.0.0.1:8088/api/agent/book-drink \
  -H "Authorization: Bearer $DRINK_POS_AGENT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"person_id":1,"item_id":1,"quantity":1,"client_operation_id":"agent-demo-1"}'
```

Die vollstaendige FastAPI/OpenAPI-Beschreibung liegt unter `/openapi.json`.
Eine Agenten-spezifische Doku mit Auth, Limits und Beispielen liegt in
[`docs/agent-api.md`](docs/agent-api.md).

## Konfiguration

Siehe `.env.example` fuer die wichtigsten Variablen:

- `DRINK_POS_IMAGE`: Container-Image, z. B. `ghcr.io/tostman1/drink-pos:latest`
- `DRINK_POS_ENV`: `development` oder `production`
- `DRINK_POS_PIN`: Start-PIN beim ersten DB-Start; ersetzt ausserdem eine bestehende Default-PIN `1234`
- `DRINK_POS_DB`: SQLite-Dateipfad
- `DRINK_POS_BACKUP_DIR`: Zielordner fuer CSV-Backups
- `DRINK_POS_AGENT_TOKEN`: Bearer-Token fuer Agenten-REST-Zugriff

In Produktion sollte die Default-PIN `1234` nicht verwendet werden.

## Tests

```powershell
cd <repo-path>
py -m unittest discover -s tests
```

Die Backend-Tests verwenden pro Test eine temporaere SQLite-Datenbank.

## Sicherheit

Die App ist fuer ein vertrauenswuerdiges lokales Netzwerk gedacht. Fuer Zugriff per VPN
oder Reverse Proxy sollten mindestens PINs geaendert, Backups aktiviert und
externe Zugriffe zusaetzlich abgesichert werden. Der Agenten-Token sollte lang, zufaellig und
nicht identisch mit der Admin-PIN sein.
