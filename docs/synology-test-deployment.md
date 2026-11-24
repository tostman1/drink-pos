# Drink-POS: isolierter Synology-Test (RL-06)

**Nur Testinstallation, keine Produktionsfreigabe.** Ziel: DS224+, Linux AMD64,
DSM 7.2/Container Manager. NAS-/Geräte-Abnahme ist noch **OFFEN**. Diese Anleitung
ist anhand der Herstellerdokumentation geprüft; CI ersetzt keinen Test auf DSM.
Produktionsprojekt, Port 8088, `stable`, bestehende Daten/Backups/Schlüssel und
`deploy/podman-update.*`/Timer bleiben unangetastet. Keine echte SumUp-Zahlung,
Erstattung oder E-Mail; keine Produktionsdaten oder Produktions-PIN kopieren.

## 1. Was wird geliefert und wie kommt es auf das NAS?

1. GitHub → Repository → **Actions** → erfolgreicher Lauf „Verify container and
   gated publication“ des vereinbarten exakten SHA. Bei PR-Läufen ist der Checkout
   eventuell der GitHub-Merge-SHA, nicht der Branch-SHA. Beide separat notieren.
2. Unter **Artifacts** `drink-pos-test-amd64-<40-stelliger Checkout-SHA>` herunterladen.
   GitHub-Anmeldung kann erforderlich sein. Aufbewahrung 14 Tage: rechtzeitig eine
   private unabhängige Kopie archivieren. Nicht das reine Evidence-Artefakt installieren.
3. ZIP mit Windows-Bordmitteln entpacken. Enthalten: `drink-pos-test-amd64.tar`,
   `artifact.json`, `release.json`, `SHA256SUMS`, Compose, `.env.test.example`, diese
   Anleitung und ergänzende Recovery-/Migrations-/Release-Runbooks. Windows benötigt
   **kein Python, Node, Git oder Docker**. `docs/...` verweist in der ZIP auf das
   gleichnamige mitgelieferte Dokument; zusätzliche Repo-Referenzen online lesen.
4. PowerShell: `Get-FileHash .\drink-pos-test-amd64.tar -Algorithm SHA256`.
   Mit `archive_sha256` in `artifact.json` und `SHA256SUMS` vergleichen. ZIP-Checksum
   von GitHub ist eine andere Identität. Bei Abweichung abbrechen.
5. `source_sha`, `image_tag`, `image_config_id`, `release.migration_code_sha256`,
   CI-URL/Versuch und erwarteten erfolgreichen Gesamtstatus privat protokollieren.
   Archive SHA-256 = übertragene Bytes; Docker Config-ID = lokales Image;
   **kein** OCI-Registry-Digest. Schema-/Migrationschecksummen sind nochmals anders.
   Builds aus demselben SHA sind ohne Nachweis nicht bitweise reproduzierbar.

## 2. Isolierte Ordner und Image-Import

File Station: neuen ausschließlich diesem Test gewidmeten Ordner anlegen, z.B.
`/volume1/docker/drink-pos-test`. Darin leere `data`, `backups`, `recovery`,
`evidence`; Compose und private `.env.test` ablegen. Artifact/Anleitung dürfen in
einem separaten Unterordner liegen. `.env.test.example` nach `.env.test` kopieren:

- `DRINK_POS_TEST_IMAGE`: exakt `image_tag` aus Receipt, niemals `stable`.
- `DRINK_POS_TEST_HOST_ROOT`: absoluter tatsächlicher Testordner, keine Links,
  Produktionsfreigaben oder verschachtelten Produktionspfade. ACL nur Testoperator.
- `DRINK_POS_TEST_ID`: eigene `drink-pos-test-...` Identität.
- `DRINK_POS_TEST_UID`/`DRINK_POS_TEST_GID`: numerische UID/GID des Testordner-
  Eigentümers (`id TEST_OPERATOR` auf NAS), keine geratenen Standardwerte. Container
  läuft als dieser Benutzer ohne Fähigkeiten; ACL muss Lesen/Schreiben im Testroot
  erlauben, private Ordner 0700/Dateien 0600. Keine Produktion-Serviceaccounts.
- `DRINK_POS_TEST_PIN`: zufällige 10–20 Ziffern, mindestens sechs verschiedene;
  keine einfachen Zahlenfolgen. Nicht Screenshot/Log/Issue/öffentliche Konfiguration.
- `DRINK_POS_TEST_TZ`: `Europe/Zurich`, `Europe/Berlin`, `Europe/Vienna` oder `UTC`.
- Standard `127.0.0.1:8089`: nur NAS-Reverse-Proxy. Für abgeschotteten LAN-HTTP-Test
  kann die konkrete NAS-LAN-IP gesetzt werden; nie ohne Firewall öffentlich binden.
- `DRINK_POS_TEST_STATE=data`: feste DB `/test/data/database.db`, eigene Messages,
  Events/CSV/PDF unter diesem Testzustand. Kein Host-Code über `/app`.

Container Manager → **Image → Add/Hinzufügen → Add from file/Aus Datei**:
TAR importieren, nicht ZIP; dokumentierte Formate `.tar`, `.tar.gz`, `.tgz`.
Name/Tag und Architektur prüfen. GUI-Felder/Versionen unterscheiden sich; die
exakte Config-ID ist per NAS-CLI zuverlässig kontrollierbar:

```sh
cd /volume1/docker/drink-pos-test
sudo docker load --input /volume1/docker/drink-pos-test/artifact/drink-pos-test-amd64.tar
sudo docker image inspect --format '{{.Id}} {{.Os}}/{{.Architecture}}' drink-pos-test:EXACT_SHA
sudo docker run --rm --pull never --network none --entrypoint python drink-pos-test:EXACT_SHA -B /app/synology_test.py identity
```

`docker load` nur statt GUI-Import, nicht zusätzlich erforderlich. ID muss genau
`image_config_id`, Plattform `linux/amd64`, Runtime-SHA `source_sha` entsprechen.
CLI-Befehle **auf dem NAS** via zeitlich begrenztem SSH ausführen; Docker nicht auf
Windows installieren. DSM unterstützt abhängig von Paketversion `docker compose`
oder `docker-compose`; zuerst `sudo docker compose version` bzw.
`sudo docker-compose version` prüfen. Bei nicht unterstützten Compose-Feldern
**abbrechen**, nicht `internal`, `pull_policy` oder Sicherheitsfelder entfernen.

## 3. Einmalige ausdrückliche v2-Initialisierung und Projektstart

Der reguläre Start initialisiert/seedet **niemals**. Er verlangt Testmarker,
exakte v2-Struktur und abgeschaltete Fresh-/Adoption-Berechtigung. Erst auf leeren
Ordnern mit eigener zufälliger PIN bewusst synthetische Demo-Daten erzeugen:

```sh
sudo docker compose --env-file .env.test -p drink-pos-test -f compose.synology.test.yaml config --quiet
sudo docker compose --env-file .env.test -p drink-pos-test -f compose.synology.test.yaml run --rm --no-deps -e DRINK_POS_ALLOW_FRESH=1 drink-pos-test python -B /app/synology_test.py initialize --synthetic-only
sudo docker compose --env-file .env.test -p drink-pos-test -f compose.synology.test.yaml run --rm --no-deps drink-pos-test python -B /app/synology_test.py inspect
sudo docker compose --env-file .env.test -p drink-pos-test -f compose.synology.test.yaml up -d --no-build --pull never
```

Fresh-Erlaubnis gilt nur dem Einmal-Container; `.env.test` enthält sie nicht,
Compose setzt `DRINK_POS_ALLOW_FRESH=0`, `DRINK_POS_ADOPT_LEGACY=0`,
`DRINK_POS_MIGRATION_MODE=versioned`. Keine allgemeine Legacy-Adoption einschalten.
Wiederholung/Nicht-Leer/abgebrochene Initialisierung blockiert: Zustand sichern,
untersuchen; kein „Reset“-Befehl und keine automatische Reparatur.
Demo Person 01–12 und Standardgetränke stammen vom bestehenden Initializer; die
normalen Artikel sind in Produktionsmodus nicht automatisch Demo-Zahlungen.

**GUI-Alternative nach Initialisierung:** Container Manager → Project/Projekt →
Create/Erstellen → Name `drink-pos-test`, Testpfad und Compose-Datei auswählen.
Synology dokumentiert Compose-Datei-Upload/Eingabe, nicht zuverlässig einen
Schalter für `--env-file .env.test`. Wenn diese Paketversion nur `.env` verwendet,
die private `.env.test` ausschließlich im isolierten Projektordner zusätzlich als
`.env` ablegen (gleiche Werte), Vorschau prüfen. Nicht im Repository/Produktionspfad!
Nie `docker compose config` vollständig in öffentliche Logs kopieren (PIN).
Wenn Variablen/Dateien nicht wie erwartet aufgelöst werden, **CLI-Variante oben**
verwenden statt ein Produktionsprojekt anzupassen. Bestehendes CLI-Projekt nicht
parallel als zweites GUI-Projekt starten. Einmal-Initializer bevorzugt CLI;
GUI-Terminal ist ohne gestarteten Service nicht als Initialisierung vorausgesetzt.
GUI **Stop** hält an; **Clean/Bereinigen** und **Delete/Löschen** sind keine
Stop-/Update-Abkürzungen (Hersteller nennt Entfernung von Ressourcen bzw. Daten).
Bei schon angelegtem Projekt bezeichnet **Build** auch `up --build --no-start`,
**Start** dagegen `compose start` vorhandener Container. Hier gibt es absichtlich
keinen `build:`-Abschnitt: niemals ein anderes Image bauen oder Registry-Pull zulassen.

Kontrolle: Container `drink-pos-test`, Image-ID exakt, ein Bind-Mount nur Testroot
→ `/test`, Read-only Root-FS, `cap_drop=ALL`, kein Socket/privileged/Agent/SMTP/
Payment-Provider, internes Testnetz. `/health` = ok; `/api/config` zeigt Build-SHA
und Datenbankpfad `hidden`. Restart-policy bewusst `no`: nach NAS-Neustart bewusst
prüfen/starten; keine automatische Update-/Pull-/Backup-Aktivierung.
Backup/Evidence liegen ebenfalls im Testroot, **nicht** automatisch unabhängig.
Schlüssel privat außerhalb Testroot/Container aufbewahren, nie Produktionsschlüssel.

## 4. HTTPS, Reverse Proxy und PWA

Für PWA/Offline ist ein **vertrauenswürdiger sicherer Ursprung** erforderlich.
`http://NAS-IP:8089` ist für entfernte Browser kein localhost; dort kein vollständiger
PWA-/Offline-Erfolg behaupten. Drei mögliche Wege, jeweils separate Operatorwahl:

1. DSM **Systemsteuerung → Anmeldeportal/Login Portal → Erweitert → Reverse Proxy**:
   eigene Testadresse `https://drink-pos-test.<private-domain>`:443 →
   `http://127.0.0.1:8089`, ausschließlich vertrauenswürdiges LAN/VPN. DNS muss auf
   NAS zeigen; keine öffentliche Portfreigabe nötig. Zertifikat unter
   **Sicherheit → Zertifikat → Einstellungen** dieser Testadresse zuweisen.
2. Interne CA: Zertifikat für exakt den Testhost, CA auf Desktop/Android/iPad/iPhone
   vertrauenswürdig installieren (iOS Vollvertrauen prüfen). Kein Klick-durch-Fehler
   als PWA-Abnahme zählen. Testzertifikat/-schlüssel nicht ins Image/Testarchiv.
3. Eigentümerverwaltete echte Domain/öffentlich vertrauenswürdiges Zertifikat mit
   LAN-DNS/VPN, Ausstellung/Erneuerung separat genehmigen. Let's Encrypt kann je
   nach Methode DNS-/Port-Voraussetzungen haben; nicht ungefragt NAS exponieren.

DSM-Zertifikat für einen anderen Namen, QuickConnect oder Browser-Ausnahme
garantieren keinen sicheren App-Ursprung. Keine Mischinhalte; Cookies/Storage/Cache
an **eigener Testadresse**. NAS-Firewall sperrt Testport außer nötigen LAN-Adressen;
internes Docker-Netz verhindert ausgehende Provider-/SMTP-Verbindungen auch bei
späteren UI-Einträgen. Reale Credentials trotzdem niemals eintragen.

## 5. Kontrolliertes Update — kein Automatismus

1. Alten und Kandidaten-Receipt/Archive privat behalten; CI für **exakten** Kandidaten
   erfolgreich, Tag/Config-ID/Archivchecksum kontrolliert. Kandidat nur importieren,
   nicht schon starten oder `.env.test` umstellen. Kein Pull, Updater, Timer oder Prune.
2. Wartung bekanntgeben; **alle** Browser/PWA/Offline-Warteschlangen schließen/drainen,
   Kassa/Admin/Importer/Datei-Editoren stoppen. Keine neue Buchung nach Backupgrenze.
   Projekt stoppen, Zustand und UTC-Zeit/Operator notieren:

```sh
sudo docker compose --env-file .env.test -p drink-pos-test -f compose.synology.test.yaml stop
sudo docker compose --env-file .env.test -p drink-pos-test -f compose.synology.test.yaml run --rm --no-deps drink-pos-test python -B /app/synology_test.py backup --quiesced
```

3. Ergebnis enthält `/test/backups/drink_pos_application_...`. Vollständiges EF-08b:
   DB samt Ledger/Receipts, Messages, Event-CSV/PDF/Verweise und allowlisted
   nicht-geheime Konfiguration. Marker/PIN/HTTPS/Docker-Receipt separat privat sichern.
   Gesamtes Bundle zu unabhängiger Testkopie transferieren, nicht nur CSV/DB.
4. Verifikation in unabhängigem schreibgeschütztem Mount/Container, kein App-Start:

```sh
sudo docker run --rm --pull never --network none --read-only --mount type=bind,source=/ABSOLUTE/INDEPENDENT-TEST-COPY,target=/evidence,readonly --entrypoint python drink-pos-test:OLD_EXACT_SHA -B /app/synology_test.py verify /evidence/BUNDLE
```

5. Exact current/candidate `identity` separat exportieren (wie Abschnitt 2). Für
   EF-08b Preflight kompatible `drink-pos-upgrade-evidence` nach
   `docs/release-safety.md`: `deployment_id`, Hashes beider JSON-Identitäten
   (kanonisches JSON SHA-256), echter Source-/Target-Schemahash aus Manifest,
   `supported`, namentlicher Reviewer, `permitted_changes=[]`, unveränderte
   `candidate_configuration`, `target_python=3.12`, private Test-PIN-Wiederherstellung
   nachgewiesen und explizite Verschlüsselungspolitik. Nicht pauschal `true` setzen.
   **Gleiche v2-Struktur allein beweist keine Code-Kompatibilität.**
6. Isolierte Bundle-Kopie, current/candidate/evidence read-only nach `/evidence`
   mounten; Preflight mit **Kandidatenimage**, niemals Live-DB:

```sh
sudo docker run --rm --pull never --network none --read-only --mount type=bind,source=/ABSOLUTE/INDEPENDENT-TEST-COPY,target=/evidence,readonly --entrypoint python drink-pos-test:CANDIDATE_EXACT_SHA -B /app/synology_test.py preflight --bundle /evidence/BUNDLE --current /evidence/current.json --candidate /evidence/candidate.json --evidence /evidence/compatibility.json --isolated-copy
```

Bei `encryption_required=true` zusätzlich `--key-receipt /evidence/KEY-RECEIPT.json`
für unabhängige vollständige Decrypt/Verify-Evidenz; fehlende Evidenz blockiert.
Exit 0 = **rehearsal-ready**, `deployment_authorized=false`; unbekannt/unsicher/
Intervention ist kein Erfolg. Wrapper unterstützt nur exact-v2/same-schema/no-change,
keine generische Schema-Migration/Downgrade. Startet/migriert nichts.
Kandidatenstart zuerst gegen separat ausdrücklich restaurierte isolierte Testkopie
mit anderem Testport/Projekt/Container durchführen; keine doppelte Live-Mount-Nutzung.
EF-08b Restore benötigt zunächst das exakte **alte** Image; anschließend bewusster
Kandidaten-Rehearsal. Prüfen: Integrity/FKs, Ledger, alle Finanz-/Auditzeilen,
Receipts, Nettoverbrauch, Runde/Zahlhistorie, Artifacts und Replay. Bei ausstehenden
externen Ergebnissen keine Provider-Anrufe/Wiederholungen.
7. Operator genehmigt danach exakt alten/neuen SHA+ID+Backup+Preflight-Rehearsal.
   `.env.test` Image ändern (auch private GUI-`.env` synchron), Fresh/Adopt bleiben 0.
   `up -d --no-build --pull never --force-recreate`; health und Geräte-Smoke prüfen.
8. Private Ergebnisdatei `evidence/update-YYYYMMDD.json`: UTC/Wartungsgrenze,
   Operator/Approval, alte/neue Archivchecksum/SHA/Config-ID, Backup-ID,
   unabhängige Verifikation/Preflight/Rehearsal, Schema/Ledger, health/Finanz-/Replay-/
   Gerätechecks, Erfolg/Fehler und akzeptierte neue Aktivität. Erst dann öffnen.

**Restart ≠ Image-Rollback ≠ vollständige Wiederherstellung.** Älteres Image auf
neuerem Schema bleibt gesperrt/unsupported; keine Ledger-Manipulation. Kompatibler
Image-Rollback nur bei separat bewiesenem gleichen Schema **und** Code-Verhalten.
Bei Fehler Container stoppen, Logs privat, fehlgeschlagene DB/Artefakte und jede
nach Backup entstandene finanzielle Aktivität bewahren. Nicht einfach altes Backup
über Live-Daten kopieren oder Verlust als „Rollback erfolgreich“ verkaufen.

## 6. Vollständige unabhängige Wiederherstellung

Original stoppen und bewahren. Vollständiges verifiziertes EF-08b Bundle mit
Deployment-ID, exaktem alten Image/SHA, erwarteter Struktur und privater Test-PIN
nach `/test` oder read-only unabhängiger Quelle bereitstellen. Nur bewusst neues
nicht existierendes Ziel; weder Reset noch Überschreiben:

```sh
sudo docker compose --env-file .env.test -p drink-pos-test -f compose.synology.test.yaml run --rm --no-deps drink-pos-test python -B /app/synology_test.py restore /test/backups/BUNDLE pre-update --approve-full-recovery
```

Ergebnis **recovered-not-started**: `recovery/pre-update/state`, vollständige DB/
Messages/Events, begrenzte dokumentierte Eventpfad-Relokation, neuer Testmarker.
Erst nach Reconciliation `DRINK_POS_TEST_STATE=recovery/pre-update/state` und
exaktes altes Image einstellen; `inspect`, dann ausdrücklich starten.
Original `data/` unverändert aufbewahren; neue Aktivität nie automatisch nachspielen.
Nach-Backup-Buchungen/Zahlungen/Requests gesondert abgleichen, keine blind erneut
ausgeführten Payment-Calls. SQL-Historie/Receipts nicht per Hand „reparieren“.

Verschlüsselte Source-Loss-Rehearsals verwenden unveränderte EF-08c:
`docs/disaster-recovery.md`/`app/independent_recovery.py`. Externes checksum-gepinntes
`age`, eigener **Test**-Recipient, private Keys auf unabhängiger Escrow-Verifikation,
Producer nur öffentlicher Recipient, unabhängige vollständige Decrypt+EF-08b-
Prüfung mit Receipt; Transferchecksum allein ist keine Restore-Evidenz.
CI probt diesen Weg inklusive ursprünglichem Imageverlust und Finanz-/Runden-
Replay. NAS-RTO/RPO, externes/offsite/immutable Medium, ACL, Schlüsselabruf und
Operator-Reconciliation bleiben offen. Kein Scheduler/Encryption-Service in diesem
einzelnen App-Projekt. Ergänzende Repository-Runbooks vor Operatorübung lesen.

## 7. Geräte-/Finanzabnahme (alle zunächst OFFEN)

Je Szenario Gerät/OS/Browser, HTTPS-Origin, Build-SHA, UTC, Beobachtung, Screenshot
ohne PIN/personenbezogene echte Daten und Pass/Fail protokollieren. Nur synthetisch.

| Prüfpunkt | Erwartung |
| --- | --- |
| Desktop Chrome/Edge/Firefox, Tablet iPad/Android, Handy iPhone/Android | Touch, Suche/Scroll, Dialoge, Tastatur, Portrait/Landscape, keine abgeschnittenen Schaltflächen |
| Liste/Admin/Kassa/Self-pay | Deutsch, EUR, Dezimalkomma, berechtigte Aktionen; SumUp/SMTP/Agent deaktiviert, kein echter Versand |
| Getränk 5 buchen, Fehlerkorrektur 2 | netto 3, originale Buchungszeit/-preise/-kosten und unveränderte Originale; Replay ohne zweite Wirkung |
| Runde **vor Abzug** stornieren | nur sichere offene Runde einmal neutralisiert, keine neu erfundene Gratiszuordnung |
| Runde **nach Abzug**, verschiedene Mitglieder/Originalpreise | exakt ursprüngliche Mengen/Tally/Preissnapshots zurück; Rundengewinn/Abzugsbericht netto null; Originale bestehen, eindeutige Reversal; Replay wirkungslos |
| Zwei überlappende Runden, nur eine stornieren | nur deren exakte Zuordnung zurück; andere bleibt unverändert, kein Doppelabzug/zusätzliche Gratisgetränke |
| Bezahlte/geschlossene/abgerechnete Runde, später bezahlte abgezogene Getränke | Storno blockiert ohne Teiländerung; kein Provider-Refund |
| Unsichere Zahlung/aktive Session/fehlende historische Attribution | fail-closed, offene Schuld bleibt, keine geratenen Legacy-Links; ausschließlich synthetische Fixtures, nie echte Provider-Ungewissheit erzeugen |
| Vollbackup → unabhängige Restore → Replay | Ledger, Netto/Originale, Round-Allocation/Storno/Reversal, PAID-Historie, Receipts, Messages, CSV/PDF/Verweise vollständig; idempotent |
| Kontrolliertes Update + fehlgeschlagener Kandidat | kein Pull/Reseed, exakte Identitäten, Backup/Rehearsal/Approval/Receipt; Failed-State und Nach-Backup-Aktivität erhalten |
| Installierte PWA | vertrauenswürdiges HTTPS, eigener Testname/Ursprung, Start vom Homescreen, neue Shell nach Update; keine Produktions-App ersetzen |
| Offline gewöhnliche Mitgliedsgetränke | sichtbare Queue, nach Online genau einmal, Browser-Restart/Mehrfachretry; keine Runde/Korrektur/Zahlung/Event-/Admin-Queue |
| Offline Kassa/Self-pay/Admin/Runde/Korrektur | gesperrt/Fehler, nie falscher bezahlter Erfolg oder spätere Online-Mutation |
| Cache | Shell `drink-pos-shell-v109` geprüft; RL-06 ändert keine UI-Dateien, daher kein willkürlicher Versionsbump; für spätere UI-Updates Version/Upgrade auf allen Geräten prüfen |

Legacy-/uncertain-Blocks nicht durch Live-SQL provozieren: vorhandene synthetische
CI-Regressionen bzw. separat freigegebene Fixture-Übung verwenden. Wenn GUI für
einen Block keinen passenden Vorgang bietet, API-Test-Evidenz und manuelle GUI-
Sperranzeige getrennt festhalten, nicht „manuell getestet“ erfinden.

## 8. Fehlerbilder / Stop-Regeln

- **Image nicht gefunden / Pull vorgeschlagen**: exakten Tag importieren/ID prüfen;
  keine Registry als Abkürzung. Archive/Checksum aus erfolgreichem Lauf holen.
- **blocked-preserve-state**: Fresh/Adopt/PIN/Timezone/Marker/DB/Links/Permissions
  prüfen. Erstinitialisierung einmal leer; kein Delete/Reseed bei bestehendem Zustand.
- **Port belegt**: Testport ändern, Produktions-8088 nicht verdrängen. Interne
  Netzwerkveröffentlichung auf installierter Docker-Version wirklich prüfen.
- **GUI Variablen/Compose unbekannt**: separate `.env`-Kopie oder NAS-CLI wie oben;
  sicherheitsrelevante Felder nicht entfernen. Paket-/DSM-Version protokollieren.
- **Healthfehler / fehlende Messages / Migration blockiert**: stoppen, alle Dateien
  bewahren, private Logs; kein `ALLOW_FRESH`/`ADOPT_LEGACY` als Reparatur.
- **PWA fehlt/Offline geht nicht**: Zertifikatskette, Name, Vollvertrauen, Origin,
  Browser-PWA-Unterstützung/Storage prüfen; HTTP-LAN ist keine HTTPS-Abnahme.
- **Backup/Restore-/age-Fehler**: unvollständige Staging-/Lock-Dateien bewahren;
  keine beliebigen Retries/Reparatur. Bekannter EF-08a Windows `WinError 5` ist nicht
  durch Linux-CI behoben. Produktions-/authentische Legacy-Kompatibilität nicht bewiesen.

## Herstellerreferenzen und Freigabegrenze

Geprüft 2026-11-24 über Synology Knowledge Center (Version 7; Bezeichnungen können
lokalisiert/versionsabhängig sein):

- [Container Manager Image: Dateiimport/Details](https://kb.synology.com/en-global/DSM/help/ContainerManager/docker_image?version=7)
- [Container Manager Project: Compose-Projekte](https://kb.synology.com/en-global/DSM/help/ContainerManager/docker_project?version=7)
- [DSM Login Portal Advanced: Reverse Proxy](https://kb.synology.com/en-global/DSM/help/DSM/AdminCenter/system_login_portal_advanced?version=7)

Automatische Gates sind synthetische Software-/Container-Evidenz. Erst Operator
bestätigt echte DS224+/DSM-/GUI-/Netzwerk-/HTTPS-/Geräte-/Restore-/Key-Abnahme.
PR bleibt **OFFEN/UNMERGED**; NAS-Installation und Produktion brauchen gesonderte
Freigabe. Keine automatische Aktualisierung, Imageveröffentlichung oder Aktivierung.
