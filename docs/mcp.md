# MCP / Agent Access Manual

Drink POS currently provides a token-protected Agent REST API. A native MCP
server is not part of this repository yet. The REST API is intentionally shaped
so an MCP server can wrap it as tools without giving an AI admin privileges.

## Current Status

- Native MCP protocol server: not implemented.
- Agent REST API: implemented and tested.
- OpenAPI description: available at `/openapi.json`.
- Recommended remote access: Tailscale or another private network.

## What Agents Can Do

Agents can:

- read the current drink list state,
- read one person's open bill,
- book normal user drinks,
- create round requests.

Agents cannot:

- close payments,
- start or confirm SumUp payments,
- run cashup,
- change the admin PIN,
- manage people or drinks,
- decide delete requests,
- access secrets.

## Enable Access

Set a long random token on the server:

```dotenv
DRINK_POS_AGENT_TOKEN=change-this-long-random-token
```

Send the token with either header:

```http
Authorization: Bearer <token>
X-Drink-Pos-Agent-Token: <token>
```

If the token is missing server-side, the Agent API responds as disabled.

## Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/agent/capabilities` | Check available actions and limits |
| `GET` | `/api/agent/state` | Read people, drinks, open totals and pending requests |
| `POST` | `/api/agent/person` | Read one person's open bill and payment preview |
| `POST` | `/api/agent/book-drink` | Book a normal drink |
| `POST` | `/api/agent/round-request` | Create a round request |

## Human Quick Test

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

## MCP Wrapper Guidance

If an MCP server is added later, it should expose only these REST actions as
tools. The wrapper should read `DRINK_POS_BASE_URL` and `DRINK_POS_AGENT_TOKEN`
from its environment, call Drink POS over Tailscale or localhost, and return the
raw JSON response plus a short human-readable summary.

Recommended MCP tool names:

- `drink_pos_capabilities`
- `drink_pos_state`
- `drink_pos_person`
- `drink_pos_book_drink`
- `drink_pos_round_request`

Do not expose admin endpoints through MCP unless a separate permission model is
designed and tested.
