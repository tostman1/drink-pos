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

Standardliste: http://127.0.0.1:8088/

Admin: http://127.0.0.1:8088/admin

Interne Kassa: http://127.0.0.1:8088/kassa

Mitglieder-Selbstzahlung: http://127.0.0.1:8088/self-pay

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
   http://<NAS-IP>:8088/self-pay
   ```

   Mitglieder/Kassierer verwenden fuer die SumUp-Selbstzahlung die normale Listenansicht und
   starten die Kartenzahlung im Personenfenster. `/self-pay` bleibt als Test-/Fallbackseite
   erhalten. Die interne Kassaansicht `/kassa` bleibt fuer Kassierer und braucht weiterhin die
   Admin-PIN zum Zahlungsabschluss.

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

## SumUp Solo Self-Checkout

Der vorgesehene Bedienweg liegt in der normalen Listenansicht:

```text
http://<NAS-IP>:8088/
```

Name antippen, Rechnung prüfen und unten im Personenfenster `Mit SumUp zahlen`
wählen. Die separate Selbstzahl-Seite bleibt als Test-/Fallbackseite erhalten:

```text
http://<NAS-IP>:8088/self-pay
```

Das iPad ruft nur den Drink-POS-Server auf der DiskStation auf. Mitglieder brauchen keinen
direkten Zugriff auf `/kassa`. Die Zahlung wird aus der App gestartet und am SumUp Solo mit
Karte oder Smartphone bezahlt. Das SumUp Solo muss online sein.

Benötigt werden SumUp Solo, API Key, Merchant Code und Reader ID. Optional können Affiliate
Key und App ID gesetzt werden, falls SumUp sie für den Cloud-API-Checkout verlangt. Diese Werte
werden nur serverseitig per ENV gesetzt:

```dotenv
PAYMENT_PROVIDER=sumup
SUMUP_API_BASE=https://api.sumup.com
SUMUP_API_KEY=<serverseitig-setzen>
SUMUP_MERCHANT_CODE=<merchant-code>
SUMUP_READER_ID=<reader-id>
SUMUP_AFFILIATE_KEY=<optional-affiliate-key>
SUMUP_AFFILIATE_APP_ID=<optional-app-id>
SUMUP_CURRENCY=EUR
SUMUP_TIMEOUT_SECONDS=120
```

Die `SUMUP_READER_ID` ist nicht die Seriennummer. Sie entsteht beim Koppeln des SumUp Solo:
Am Solo einen frischen Pairing-Code anzeigen, dann PIN-geschützt `POST /api/admin/sumup/pair-reader`
aufrufen. Die Antwort liefert eine Reader-ID der Form `rdr_...`; diese wird als
`SUMUP_READER_ID` in `.env` gesetzt. `POST /api/admin/sumup/readers` listet bereits gekoppelte
Reader, `POST /api/admin/sumup/status` prüft den Reader-Status.

Im Kartenzahlungs-Popup wird automatisch `Kartenzahlung +3 %` als zusätzliche Zeile addiert,
mindestens jedoch `0,20 €`. Der Endbetrag kann optional nicht aufgerundet, auf volle Euro,
auf den nächsten 5er oder auf den nächsten 10er aufgerundet werden. SumUp erhält immer den
serverseitig berechneten Endbetrag inklusive Gebühr und Aufrundung.

Die interne Kassaansicht `/kassa` bietet dieselbe Kartenzahlungslogik im Zahlungsdialog für
Kassierer an. `Bar buchen` schließt weiterhin nur den offenen Originalbetrag, `Mit SumUp zahlen`
startet den SumUp-Vorgang inklusive Kartengebühr und optionaler Aufrundung.

Eine Self-Pay-Zahlung sperrt die gewählte Person während der Terminalfreigabe gegen
parallele Buchungen. Das iPad erzeugt für jeden Zahlungsversuch eine eindeutige
`client_payment_id`; der Server legt dazu genau eine `self_payment_sessions`-Zeile an. Wenn
derselbe Request wegen Verbindungsabbruch oder Doppeltippen erneut gesendet wird, startet der
Server keine zweite SumUp-Zahlung, sondern liefert den gespeicherten Status zurück.

Die Listenansicht und die separate Testseite speichern eine laufende Zahlung lokal im Browser und fragen nach Reload oder
Netzunterbruch `/api/self-pay/payment/{client_payment_id}` ab. Solange der Status `created`,
`sent_to_reader` oder `pending` ist, bleibt die Zahlung gesperrt. Nur bei eindeutig
erfolgreichem SumUp-Status wird lokal `PAID_SUMUP` gebucht. Bei Timeout, Fehler, Abbruch oder
unklarem Status bleiben die Posten offen und müssen geprüft werden.

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
- `PAYMENT_PROVIDER`: `sumup` aktiviert SumUp Solo Self-Checkout
- `SUMUP_API_BASE`: SumUp API-Basis, Standard `https://api.sumup.com`
- `SUMUP_API_KEY`: SumUp API Key, nur serverseitig setzen
- `SUMUP_MERCHANT_CODE`: SumUp Merchant Code
- `SUMUP_READER_ID`: SumUp Solo Reader ID
- `SUMUP_AFFILIATE_KEY`, `SUMUP_AFFILIATE_APP_ID`: optionale Affiliate-Werte fuer Cloud-API-Tracking
- `SUMUP_CURRENCY`: Waehrung, Standard `EUR`
- `SUMUP_TIMEOUT_SECONDS`: Wartezeit fuer SumUp-Zahlungen, Standard `120`

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

Mitglieder-Selbstzahlung ist fuer ein iPad im lokalen Vereinsnetz gedacht. Die Mitgliederseite
ist bewusst getrennt von `/kassa`; Zahlungsabschluss per SumUp erfolgt serverseitig und wird
ueber `client_payment_id` idempotent abgesichert.
