# Editable Message Catalog

Payment and self-payment texts are centralized in one JSON file.

Default source file:

```text
app/messages.json
```

Runtime file on the Raspberry Pi:

```text
/home/admin/drink-pos/data/messages.json
```

The app copies the default file to the data folder on startup if it does not
exist. Edit the runtime file to change wording without searching through source
code. Keep the JSON keys unchanged; edit only the values.

Example:

```json
"card_visual_waiting_title": "Warten auf Kartenterminal"
```

Placeholders like `{provider}`, `{payment_label}`, `{total}`, and `{open_items}`
are replaced by the app.
