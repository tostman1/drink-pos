# Agenten-REST-Interface

Drink POS stellt fuer KI-Agenten ein kleines REST-Interface bereit. Es ist bewusst schmal gehalten:
Agenten duerfen den Strichlisten-Stand lesen, normale Getraenke buchen und Rundenanfragen anlegen.
Admin-Aktionen bleiben im Admin-UI beziehungsweise bei PIN-geschuetzten Admin-Endpunkten.
Die SumUp-Selbstzahlung fuer Mitglieder ist in der normalen Listenansicht integriert; `/self-pay`
bleibt nur als Test-/Fallbackseite erhalten. Der Zahlungsflow gehoert nicht zur Agenten-API.

Die API eignet sich direkt fuer Agenten und kann bei Bedarf von einem MCP-Server als Tool-Backend
gewrappt werden. Ein nativer MCP-Server ist aktuell nicht Teil dieses Repos; siehe
`docs/mcp.md` und `docs/ai-agent-manual.md`.

## Aktivierung und Auth

Das Interface ist deaktiviert, solange kein Token gesetzt ist:

```dotenv
DRINK_POS_AGENT_TOKEN=change-this-long-random-token
```

Agenten senden den Token mit einem dieser Header:

```http
Authorization: Bearer <token>
X-Drink-Pos-Agent-Token: <token>
```

Der Token gehoert nur in lokale `.env`-Dateien, Secret Stores oder Deployment-Umgebungen. Er soll
nicht in Git committed werden und nicht identisch mit der Admin-PIN sein.

## Basis

Beispiel-Basis-URL auf einer lokalen Instanz:

```text
http://127.0.0.1:8088
```

Die FastAPI/OpenAPI-Beschreibung ist unter `/openapi.json` verfuegbar.

## Endpunkte

| Methode | Pfad | Zweck |
| --- | --- | --- |
| `GET` | `/api/agent/capabilities` | Interface, Auth-Info, Endpunkte und Limits lesen |
| `GET` | `/api/agent/state` | Personen, Artikel, offene Posten und offene Anfragen lesen |
| `POST` | `/api/agent/person` | Kassenansicht fuer eine Person lesen |
| `POST` | `/api/agent/book-drink` | Normales Benutzergetraenk buchen |
| `POST` | `/api/agent/round-request` | Rundenanfrage fuer eine Person erstellen |

## Limits

- `book-drink`: `quantity` muss zwischen `1` und `50` liegen.
- `round-request`: `quantity` muss zwischen `1` und `20` liegen.
- Agenten duerfen keine inaktiven, Admin-only- oder Systemartikel buchen.
- Zahlungsabschluss, Kassensturz, PIN-Aenderung, Artikelverwaltung und Entscheidungen ueber
  Loeschanfragen sind nicht Teil der Agenten-API.
- Wenn fuer eine Person gerade eine SumUp-Selbstzahlung mit Status `CREATED`, `SENT_TO_READER`
  oder `PENDING` laeuft, blockiert der Server neue Agentenbuchungen fuer diese Person mit HTTP `409`. Dadurch kann die Terminalzahlung
  nicht durch parallele Buchungen veraltet oder doppelt verarbeitet werden.

## Beispiele

Capabilities lesen:

```bash
curl -H "Authorization: Bearer $DRINK_POS_AGENT_TOKEN" \
  http://127.0.0.1:8088/api/agent/capabilities
```

Gesamtzustand lesen:

```bash
curl -H "Authorization: Bearer $DRINK_POS_AGENT_TOKEN" \
  http://127.0.0.1:8088/api/agent/state
```

Person lesen:

```bash
curl -X POST http://127.0.0.1:8088/api/agent/person \
  -H "Authorization: Bearer $DRINK_POS_AGENT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"person_id":1}'
```

Getraenk buchen:

```bash
curl -X POST http://127.0.0.1:8088/api/agent/book-drink \
  -H "Authorization: Bearer $DRINK_POS_AGENT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "person_id": 1,
    "item_id": 1,
    "quantity": 1,
    "client_operation_id": "agent-demo-001",
    "device_info": "local-agent",
    "note": "optional"
  }'
```

Alternativ kann `drink` statt `item_id` verwendet werden:

```json
{
  "person_id": 1,
  "drink": "Getraenk",
  "quantity": 1
}
```

Rundenanfrage erstellen:

```bash
curl -X POST http://127.0.0.1:8088/api/agent/round-request \
  -H "Authorization: Bearer $DRINK_POS_AGENT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"person_id":1,"quantity":2,"reason":"Teamrunde"}'
```

## Idempotenz

Bei `/api/agent/book-drink` kann `client_operation_id` gesetzt werden. Die ID wird bereinigt,
auf maximal 80 Zeichen gekuerzt und verhindert doppelte Buchungen bei Wiederholungen. Wenn dieselbe
ID erneut gesendet wird, antwortet die API mit `duplicate: true` und der vorhandenen
`transaction_id`.

## Fehler

| Status | Bedeutung |
| --- | --- |
| `400` | Ungueltige Menge oder Artikel nicht gefunden |
| `403` | Falscher Token oder nicht erlaubter Artikel |
| `404` | Agenten-API deaktiviert oder Person nicht gefunden |
| `409` | Konflikt, z. B. laufende SumUp-Selbstzahlung fuer diese Person |

Antworten enthalten ueblicherweise ein `detail`-Feld mit einer menschenlesbaren Meldung.
