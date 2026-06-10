from __future__ import annotations

import json
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass


@dataclass(frozen=True)
class SumUpConfig:
    api_base: str
    api_key: str
    merchant_code: str
    reader_id: str = ""
    currency: str = "EUR"
    timeout_seconds: int = 120
    affiliate_key: str = ""
    affiliate_app_id: str = ""


class SumUpError(Exception):
    def __init__(self, category: str, message: str, status_code: int | None = None, raw_response: dict | None = None):
        super().__init__(message)
        self.category = category
        self.message = message
        self.status_code = status_code
        self.raw_response = raw_response or {}


def _json_or_empty(data: bytes) -> dict:
    if not data:
        return {}
    try:
        parsed = json.loads(data.decode("utf-8"))
    except Exception:
        return {"raw": data.decode("utf-8", errors="replace")}
    return parsed if isinstance(parsed, dict) else {"raw": parsed}


def _error_message(payload: dict, fallback: str) -> str:
    for key in ("message", "detail", "title", "error"):
        value = payload.get(key)
        if value:
            return str(value)
    return fallback


def _map_http_error(status_code: int, payload: dict) -> str:
    if status_code == 401:
        return "invalid_api_key"
    if status_code == 404:
        return "reader_offline"
    if status_code == 409:
        return "reader_busy"
    if status_code == 408:
        return "timeout"
    if status_code == 422:
        return "api_error"
    return "api_error"


def _request(cfg: SumUpConfig, method: str, path: str, body: dict | None = None, timeout: int = 15) -> dict:
    base = cfg.api_base.rstrip("/")
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = urllib.request.Request(
        f"{base}{path}",
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {cfg.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return _json_or_empty(response.read())
    except urllib.error.HTTPError as exc:
        payload = _json_or_empty(exc.read())
        category = _map_http_error(exc.code, payload)
        raise SumUpError(category, _error_message(payload, f"SumUp API Fehler {exc.code}"), exc.code, payload) from exc
    except (urllib.error.URLError, TimeoutError, socket.timeout) as exc:
        raise SumUpError("unknown", f"SumUp API nicht erreichbar: {exc}") from exc


def _response_data(payload: dict) -> dict:
    data = payload.get("data")
    return data if isinstance(data, dict) else payload


def list_readers(cfg: SumUpConfig) -> dict:
    path = f"/v0.1/merchants/{urllib.parse.quote(cfg.merchant_code)}/readers"
    return _request(cfg, "GET", path, timeout=min(15, max(5, cfg.timeout_seconds)))


def pair_reader(cfg: SumUpConfig, pairing_code: str, name: str = "Drink POS") -> dict:
    code = "".join(ch for ch in str(pairing_code or "").strip().upper() if ch.isalnum())
    if not code:
        raise SumUpError("api_error", "Pairing-Code fehlt")
    path = f"/v0.1/merchants/{urllib.parse.quote(cfg.merchant_code)}/readers"
    return _request(
        cfg,
        "POST",
        path,
        {"pairing_code": code, "name": (name or "Drink POS")[:120]},
        timeout=min(20, max(5, cfg.timeout_seconds)),
    )


def reader_status(cfg: SumUpConfig) -> dict:
    path = f"/v0.1/merchants/{urllib.parse.quote(cfg.merchant_code)}/readers/{urllib.parse.quote(cfg.reader_id)}/status"
    return _request(cfg, "GET", path, timeout=min(15, max(5, cfg.timeout_seconds)))


def create_reader_checkout(
    cfg: SumUpConfig,
    amount_cents: int,
    description: str = "",
    foreign_transaction_id: str | None = None,
) -> dict:
    if amount_cents <= 0:
        raise SumUpError("api_error", "Betrag muss groesser als 0 sein")

    status_response = reader_status(cfg)
    status = _response_data(status_response)
    if str(status.get("status") or "").upper() == "OFFLINE":
        raise SumUpError("reader_offline", "SumUp Solo ist offline oder nicht erreichbar.", raw_response=status_response)
    state = str(status.get("state") or "IDLE").upper()
    if state and state != "IDLE":
        raise SumUpError("reader_busy", f"SumUp Solo ist beschaeftigt ({state}).", raw_response=status_response)

    path = f"/v0.1/merchants/{urllib.parse.quote(cfg.merchant_code)}/readers/{urllib.parse.quote(cfg.reader_id)}/checkout"
    payload: dict[str, object] = {
        "total_amount": {
            "currency": cfg.currency,
            "minor_unit": 2,
            "value": int(amount_cents),
        }
    }
    if cfg.affiliate_key and cfg.affiliate_app_id:
        payload["affiliate"] = {
            "app_id": cfg.affiliate_app_id,
            "foreign_transaction_id": (foreign_transaction_id or description or str(time.time()))[:120],
            "key": cfg.affiliate_key,
        }
    if description:
        payload["description"] = description[:128]
    result = _request(cfg, "POST", path, payload, timeout=min(20, max(5, cfg.timeout_seconds)))
    data = _response_data(result)
    checkout_id = str(data.get("client_transaction_id") or data.get("id") or data.get("checkout_id") or "").strip()
    if not checkout_id:
        raise SumUpError("unknown", "SumUp hat keine Checkout-ID geliefert.", raw_response=result)
    return {
        "provider_checkout_id": checkout_id,
        "status": "sent_to_reader",
        "reader_status": status_response,
        "raw_response": result,
    }


def get_transaction(cfg: SumUpConfig, client_transaction_id: str) -> dict | None:
    query = urllib.parse.urlencode({"client_transaction_id": client_transaction_id})
    path = f"/v2.1/merchants/{urllib.parse.quote(cfg.merchant_code)}/transactions?{query}"
    try:
        return _request(cfg, "GET", path, timeout=min(15, max(5, cfg.timeout_seconds)))
    except SumUpError as exc:
        if exc.status_code == 404:
            return None
        raise


def _amount_to_cents(value: object) -> int | None:
    try:
        return int(round(float(value) * 100))
    except (TypeError, ValueError):
        return None


def poll_checkout_status(cfg: SumUpConfig, client_transaction_id: str, timeout_seconds: int | None = None) -> dict:
    deadline = time.monotonic() + max(1, int(timeout_seconds or cfg.timeout_seconds))
    last_response: dict | None = None
    while time.monotonic() < deadline:
        transaction = get_transaction(cfg, client_transaction_id)
        if transaction:
            last_response = transaction
            status = str(transaction.get("status") or "").upper()
            if status == "SUCCESSFUL":
                return {
                    "status": "paid",
                    "provider_checkout_id": client_transaction_id,
                    "transaction_id": transaction.get("id") or transaction.get("transaction_id"),
                    "transaction_code": transaction.get("transaction_code"),
                    "auth_code": transaction.get("auth_code"),
                    "currency": transaction.get("currency"),
                    "amount_cents": _amount_to_cents(transaction.get("amount")),
                    "raw_response": transaction,
                }
            if status in {"FAILED", "FAILURE", "UNSUCCESSFUL"}:
                return {"status": "failed", "provider_checkout_id": client_transaction_id, "raw_response": transaction}
            if status in {"CANCELLED", "CANCELED"}:
                return {"status": "cancelled", "provider_checkout_id": client_transaction_id, "raw_response": transaction}
        time.sleep(2)

    return {
        "status": "timeout",
        "provider_checkout_id": client_transaction_id,
        "raw_response": last_response or {},
        "message": "Zeitlimit fuer SumUp-Zahlung ueberschritten.",
    }
