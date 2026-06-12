# Agent Task: Fix findings from code review of drink-pos

Ziel: Behebe die wichtigsten Probleme in `tostman1/drink-pos` (Code-Qualität, Architektur, Tests, Dokumentation) und erstelle einen PR mit klaren Commit-Schritten.

Aufgabenbeschreibung (für einen Dev/Agent):

1) Vorbereitung
- Erstelle einen neuen Branch: `fix/qa-architecture-tests-<initialen>` (z. B. `fix/qa-architecture-tests-tm`).
- Installiere Abhängigkeiten aus `requirements.txt` in einer virtuellen Umgebung.

2) Code-Qualität & Stil
- Führe `ruff` oder `flake8` und `black`/`isort` über das Repo aus und behebe offensichtliche PEP8/Styling-Fehler.
- Ergänze fehlende Typannotationen in den Kernmodulen (insbesondere `app/main.py`): füge Typen für öffentliche Funktionen und Datentypen hinzu.
- Zerlege sehr große Dateien (z. B. `app/main.py`) in drei Module:
  - `app/api.py` — HTTP-Route-Handlers (wenn FastAPI verwendet wird) oder die API-Eintrittspunkte
  - `app/core.py` — Business-Logik (Kassen- / Self-pay-Logik)
  - `app/db.py` — Datenbank-Verbindung, Schema und DB-Hilfsfunktionen
- Extrahiere Payment-Provider-Interface in `app/payments/__init__.py` und implementiere `SumUpProvider` und `TestCardProvider` in `app/payments/sumup.py` und `app/payments/test_provider.py`.

3) Architektur & Design
- Entkopple Konfiguration (ENV-Parsing) in `app/config.py` mit Pydantic `BaseSettings` (oder ein einfaches Config-Objekt). Alle Funktionen sollen `config` oder `settings` als Parameter erhalten anstatt direkt `os.environ` zu lesen.
- Implementiere eine leicht testbare `PaymentService`-Klasse, die als einzige Komponente Netzwerkaufrufe zu SumUp tätigt.
- Stelle sicher, dass DB-Verbindungsfunktionen `get_conn()` kontextuell/rücksetzbar sind und keine globalen Zustände nutzen.

4) Tests & CI
- Ergänze GitHub Actions Workflow `.github/workflows/ci.yml` mit Jobs:
  - Test (python-version matrix)
  - Lint (ruff/flake8 + black check)
  - Coverage (run pytest and upload coverage report)
- Schreibe zusätzliche Unit-Tests für:
  - PaymentService error handling (SumUp API error, timeout)
  - Config parsing behavior (production vs development)
  - Split/isolated tests for DB helpers using tmp sqlite files
- Stelle sicher, dass `tests/test_backend.py` und neue Tests laufen sauber im CI.

5) Fehlerbehandlung & Robustheit
- Implementiere retry/backoff (z. B. tenacity) bei SumUp-API-Aufrufen bei temporären Fehlern.
- Verbessere Ausnahme-Typen: spezifische Exceptions (SumUpError, PaymentTimeoutError) und konsistente HTTPException-Mappings.
- Füge Health-Check-Endpunkt `/health` zurück (oder neu), der DB-Verbindung und optionales Payment-API-Status prüft.

6) Logging & Observability
- Füge strukturiertes Logging (logging.getLogger(__name__)) mit sinnvollen Log-Levels hinzu.
- Instrumentiere wichtige Pfade mit INFO logs (payments started/finished) und WARN/ERROR bei Ausnahmen.

7) Dokumentation
- Ergänze README.md Setup- & Deployment-Abschnitt mit:
  - Quickstart: how to run locally, env vars required
  - How to run tests & linters
  - How to contribute and run the agent prompt
- Aktualisiere `docs/agent-api.md` falls sich die Agent-API ändert.

8) PR & Commit-Strategie (erwarte Output vom Agent)
- Erstelle atomare Commits mit klaren Nachrichten:
  - `chore: add linting config and format code`
  - `refactor: split main.py into api/core/db modules`
  - `feat(payments): add PaymentProvider interface and Test provider`
  - `fix(payment): add retry/backoff for SumUp requests and better error handling`
  - `test: add unit tests for PaymentService and config`
  - `ci: add GitHub Actions workflow for test + lint + coverage`
  - `docs: update README with setup and run instructions`
- Öffne einen Pull Request mit Beschreibung der Änderungen, die Test- und CI-Details, und eine Checkliste von geänderten/erstellten Dateien.

Akzeptanzkriterien (was muss erfüllt sein, damit PR gemergt werden kann)
- Alle Tests in `tests/` laufen lokal und im CI ohne Fehler.
- Linter/Formatter-Checks bestehen in CI.
- Keine vertraulichen Daten (API keys etc.) im Repo.
- README und docs enthalten Hinweise zum lokalen Setup und CI.
- Payment-Provider-Interface ist verwendbar und SumUp-Aufrufe sind entkoppelt und testbar.

Zeit-Aufwand Schätzung: 6–16 Stunden (abhängig vom gewünschten Detaillierungsgrad der Refactorings).

Wenn du möchtest, übernehme ich diese Änderungen automatisch und öffne einen PR — bestätige nur den Branch-Namen und ob ich direkt in dieses Repo committen darf.
