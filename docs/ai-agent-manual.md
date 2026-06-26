# AI Agent Manual

This manual is for AI agents or MCP wrappers that operate Drink POS through the
Agent REST API.

## Contract

Use the Agent REST API only. Treat all other endpoints as out of scope unless a
human explicitly authorizes a separate workflow.

Base URL examples:

```text
http://127.0.0.1:8088
http://drink-pos.tailnet-name.ts.net:8088
```

Required auth:

```http
Authorization: Bearer <DRINK_POS_AGENT_TOKEN>
```

Alternative auth:

```http
X-Drink-Pos-Agent-Token: <DRINK_POS_AGENT_TOKEN>
```

## Safe Tool Mapping

### `drink_pos_capabilities`

Call:

```http
GET /api/agent/capabilities
```

Use before other actions to confirm that the interface is enabled.

### `drink_pos_state`

Call:

```http
GET /api/agent/state
```

Use to list people, available user drinks, totals, pending requests, and sync
revision. Do not cache this for long-running decisions; refresh before writing.

### `drink_pos_person`

Call:

```http
POST /api/agent/person
Content-Type: application/json

{"person_id": 1}
```

Use before booking if the user names a person ambiguously or asks for a current
bill.

### `drink_pos_book_drink`

Call:

```http
POST /api/agent/book-drink
Content-Type: application/json

{
  "person_id": 1,
  "item_id": 1,
  "quantity": 1,
  "client_operation_id": "agent-unique-id",
  "device_info": "agent-name",
  "note": "optional short note"
}
```

Rules:

- Only book when the person and item are clear.
- Prefer `item_id` from `drink_pos_state`; use `drink` only as a fallback.
- Set `client_operation_id` for every write to avoid duplicate bookings.
- Quantity must be `1` to `50`.
- Do not book admin-only or system items.
- On HTTP `409`, stop and tell the human a payment or conflict is active.

### `drink_pos_round_request`

Call:

```http
POST /api/agent/round-request
Content-Type: application/json

{"person_id": 1, "quantity": 1, "reason": "optional"}
```

Rules:

- Quantity must be `1` to `20`.
- This creates a request; it does not approve or charge a round.

## Not Allowed

Do not use the Agent API for:

- cash payments,
- SumUp checkout start, cancel, or confirmation,
- cashup,
- admin login,
- people or drink management,
- delete request decisions,
- direct database edits,
- reading or changing secrets.

## Error Handling

| HTTP status | Agent behavior |
| --- | --- |
| `400` | Explain invalid input or unavailable item. |
| `403` | Stop; token or action is not allowed. |
| `404` | Stop; API disabled, person missing, or route unavailable. |
| `409` | Stop; active payment/conflict must be handled by a human. |

Return the server `detail` value to the human when available.

## Response Style

For successful writes, summarize:

- person,
- drink/item,
- quantity,
- transaction id,
- whether the call was a duplicate replay.

For reads, summarize totals and open items without dumping full JSON unless the
human asks for raw data.
