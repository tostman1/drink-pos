"""Event mode services for Drink POS."""

from __future__ import annotations

import csv
import io
import os
import re
import socket
import smtplib
import sqlite3
import ssl
from dataclasses import asdict, dataclass
from datetime import date
from email.message import EmailMessage
from pathlib import Path
from typing import Any

try:
    from app.utils.helpers import get_setting, now_text, set_setting
except ImportError:
    from utils.helpers import get_setting, now_text, set_setting

try:
    import qrcode
    from qrcode.constants import ERROR_CORRECT_M
except ImportError:  # pragma: no cover - dependency is installed in the container image.
    qrcode = None
    ERROR_CORRECT_M = None


INVOICE_SETTING_DEFAULTS = {
    "invoice_cashier_email": "",
    "invoice_recipient": "Musikverein Harmonie Altach\nz.Hd. Kassier",
    "invoice_sender_name": "MVH Altach Wirtschaft",
    "invoice_sender_address": "",
    "invoice_number_prefix": "EVENT",
    "invoice_iban": "",
    "invoice_logo_text": "MVH",
    "invoice_footer_text": "Uf a feines Beisammensein: zum Wohle!",
    "invoice_place": "Altach",
    "invoice_notes": "",
}

MAIL_SETTING_DEFAULTS = {
    "mail_test_recipient": "",
    "mail_smtp_provider": "custom",
    "mail_smtp_host": "",
    "mail_smtp_port": "",
    "mail_smtp_username": "",
    "mail_smtp_password": "",
    "mail_smtp_from": "",
    "mail_smtp_encryption": "",
}

MAIL_PROVIDER_PRESETS = {
    "custom": {"host": "", "port": "", "encryption": "starttls"},
    "ionos": {"host": "smtp.ionos.com", "port": "587", "encryption": "starttls"},
    "magenta": {"host": "mail.mymagenta.business", "port": "465", "encryption": "ssl"},
    "world4you": {"host": "smtp.world4you.com", "port": "587", "encryption": "starttls"},
}

EVENT_CSV_HEADERS = [
    "Veranstaltungsname",
    "Startzeit",
    "Endzeit",
    "Getraenkename",
    "Verkaufte Menge",
    "Einzelpreis",
    "Positionssumme",
    "Positionsrabatt %",
    "Positionsrabatt Betrag",
    "Gesamtrabatt %",
    "Gesamtrabatt Betrag",
    "Endsumme",
]


@dataclass(slots=True)
class EventArtifacts:
    csv_path: str
    pdf_path: str | None = None
    mail_sent: bool = False
    mail_copy_sent: bool = False


def data_dir_for_db(db_path: str | os.PathLike[str]) -> Path:
    """Return the server-side data directory next to the active DB."""

    return Path(db_path).resolve().parent


def event_output_dir(db_path: str | os.PathLike[str]) -> Path:
    path = data_dir_for_db(db_path) / "events"
    path.mkdir(parents=True, exist_ok=True)
    return path


def clean_filename_part(value: str) -> str:
    safe = "".join(ch if ch.isalnum() else "_" for ch in str(value or "").strip().lower())
    safe = "_".join(part for part in safe.split("_") if part)
    return safe[:80] or "veranstaltung"


def event_file_base(event: dict[str, Any]) -> str:
    timestamp = str(event.get("start_time") or now_text()).replace(":", "").replace("-", "").replace(" ", "_")
    return f"event_{event.get('id')}_{timestamp}_{clean_filename_part(str(event.get('name') or ''))}"


def money(value: float) -> float:
    return round(float(value or 0), 2)


def get_invoice_settings(conn: sqlite3.Connection) -> dict[str, str]:
    return {key: str(get_setting(conn, key, default) or "") for key, default in INVOICE_SETTING_DEFAULTS.items()}


def normalize_iban(value: Any) -> str:
    text = "".join(str(value or "").split()).upper()
    if not text:
        return ""
    if not re.fullmatch(r"[A-Z]{2}[0-9]{2}[A-Z0-9]{11,30}", text):
        raise ValueError("IBAN ist ungueltig. Bitte die vollstaendige IBAN pruefen.")
    rearranged = text[4:] + text[:4]
    digits = "".join(str(ord(ch) - 55) if ch.isalpha() else ch for ch in rearranged)
    if int(digits) % 97 != 1:
        raise ValueError("IBAN-Pruefziffer ist ungueltig. Bitte die IBAN pruefen.")
    return " ".join(text[idx : idx + 4] for idx in range(0, len(text), 4))


def invoice_qr_available(settings: dict[str, str]) -> bool:
    try:
        return bool(normalize_iban(settings.get("invoice_iban")))
    except ValueError:
        return False


def normalize_external_recipient(
    name: Any,
    email: Any = "",
    address: Any = "",
    require_email: bool = False,
) -> dict[str, str]:
    clean_name = " ".join(str(name or "").strip().split())[:180]
    if not clean_name:
        raise ValueError("Name/Firma des externen Empfängers fehlt")
    clean_email = " ".join(str(email or "").strip().split())[:240]
    if require_email and not clean_email:
        raise ValueError("E-Mail-Adresse des externen Empfängers fehlt")
    if clean_email and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", clean_email):
        raise ValueError("E-Mail-Adresse des externen Empfängers ist ungültig")
    clean_address = "\n".join(
        " ".join(line.strip().split()) for line in str(address or "").splitlines() if line.strip()
    )[:900]
    return {"name": clean_name, "email": clean_email, "address": clean_address}


def invoice_settings_for_recipient(settings: dict[str, str], recipient: dict[str, str] | None) -> dict[str, str]:
    if not recipient:
        return dict(settings)
    recipient_lines = [recipient["name"]]
    if recipient.get("address"):
        recipient_lines.append(recipient["address"])
    updated = dict(settings)
    updated["invoice_recipient"] = "\n".join(recipient_lines)
    return updated


def update_invoice_settings(conn: sqlite3.Connection, values: dict[str, Any]) -> dict[str, str]:
    if "invoice_number_prefix" in values:
        format_invoice_prefix(str(values["invoice_number_prefix"] or "").strip()[:180], date(2000, 1, 1))
    for key in INVOICE_SETTING_DEFAULTS:
        if key not in values:
            continue
        value = "" if values[key] is None else str(values[key]).strip()
        if key == "invoice_cashier_email":
            value = value[:180]
        elif key == "invoice_iban":
            value = normalize_iban(value)
        elif key in {"invoice_recipient", "invoice_sender_address", "invoice_footer_text", "invoice_notes"}:
            value = value[:900]
        else:
            value = value[:180]
        set_setting(conn, key, value)
    return get_invoice_settings(conn)


def env_mail_settings() -> dict[str, str]:
    env_port = (os.getenv("DRINK_POS_SMTP_PORT") or "").strip()
    explicit_starttls = os.getenv("DRINK_POS_SMTP_STARTTLS")
    explicit_encryption = (os.getenv("DRINK_POS_SMTP_ENCRYPTION") or "").strip().lower()
    if explicit_encryption in {"ssl", "starttls", "none"}:
        encryption = explicit_encryption
    elif explicit_starttls is not None:
        encryption = "starttls" if explicit_starttls.strip().lower() not in {"0", "false", "no", "off"} else "none"
    elif env_port == "465":
        encryption = "ssl"
    else:
        encryption = "starttls"
    return {
        "mail_smtp_provider": "custom",
        "mail_smtp_host": (os.getenv("DRINK_POS_SMTP_HOST") or "").strip(),
        "mail_smtp_port": env_port,
        "mail_smtp_username": (os.getenv("DRINK_POS_SMTP_USERNAME") or "").strip(),
        "mail_smtp_password": os.getenv("DRINK_POS_SMTP_PASSWORD") or "",
        "mail_smtp_from": (os.getenv("DRINK_POS_SMTP_FROM") or "").strip(),
        "mail_smtp_encryption": encryption,
    }


def get_mail_settings(conn: sqlite3.Connection, include_secret: bool = False) -> dict[str, Any]:
    env = env_mail_settings()
    raw = {key: str(get_setting(conn, key, default) or "") for key, default in MAIL_SETTING_DEFAULTS.items()}
    username = raw["mail_smtp_username"] or env["mail_smtp_username"]
    settings = {
        "mail_test_recipient": raw["mail_test_recipient"],
        "mail_smtp_provider": raw["mail_smtp_provider"] or env["mail_smtp_provider"] or "custom",
        "mail_smtp_host": raw["mail_smtp_host"] or env["mail_smtp_host"],
        "mail_smtp_port": raw["mail_smtp_port"] or env["mail_smtp_port"] or "587",
        "mail_smtp_username": username,
        "mail_smtp_from": username or raw["mail_smtp_from"] or env["mail_smtp_from"],
        "mail_smtp_encryption": raw["mail_smtp_encryption"] or env["mail_smtp_encryption"] or "starttls",
    }
    password = raw["mail_smtp_password"] or env["mail_smtp_password"]
    settings["mail_smtp_password_set"] = bool(password)
    settings["mail_smtp_configured"] = bool(settings["mail_smtp_host"])
    if include_secret:
        settings["mail_smtp_password"] = password
    return settings


def normalize_mail_port(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    try:
        port = int(text)
    except ValueError as exc:
        raise ValueError("SMTP-Port ist keine gültige Zahl") from exc
    if port <= 0 or port > 65535:
        raise ValueError("SMTP-Port muss zwischen 1 und 65535 liegen")
    return str(port)


def normalize_mail_encryption(value: Any) -> str:
    text = str(value or "").strip().lower()
    if text in {"", "starttls", "ssl", "none"}:
        return text
    raise ValueError("SMTP-Verschlüsselung ist ungültig")


def normalize_test_recipient(value: Any, required: bool = False) -> str:
    recipient = str(value or "").strip()
    if not recipient:
        if required:
            raise ValueError("Test-Empfänger fehlt")
        return ""
    if len(recipient) > 240 or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", recipient):
        raise ValueError("E-Mail-Adresse des Test-Empfängers ist ungültig")
    return recipient


def update_mail_settings(conn: sqlite3.Connection, values: dict[str, Any]) -> dict[str, Any]:
    if "mail_test_recipient" in values:
        values = {**values, "mail_test_recipient": normalize_test_recipient(values["mail_test_recipient"])}
    if "mail_smtp_clear_password" in values and bool(values["mail_smtp_clear_password"]):
        set_setting(conn, "mail_smtp_password", "")
    for key in MAIL_SETTING_DEFAULTS:
        if key not in values:
            continue
        if key == "mail_smtp_password":
            password = "" if values[key] is None else str(values[key])
            if password:
                set_setting(conn, key, password[:500])
            continue
        value = "" if values[key] is None else str(values[key]).strip()
        if key == "mail_smtp_provider":
            value = value if value in MAIL_PROVIDER_PRESETS else "custom"
        elif key == "mail_smtp_port":
            value = normalize_mail_port(value)
        elif key == "mail_smtp_encryption":
            value = normalize_mail_encryption(value)
        elif key in {"mail_smtp_host", "mail_smtp_username", "mail_smtp_from"}:
            value = value[:240]
        set_setting(conn, key, value)
    return get_mail_settings(conn)


def active_event(conn: sqlite3.Connection) -> sqlite3.Row | None:
    return conn.execute(
        """
        SELECT *
        FROM event_sessions
        WHERE status = 'ACTIVE'
        ORDER BY id DESC
        LIMIT 1
        """
    ).fetchone()


def require_active_event(conn: sqlite3.Connection, expected_event_id: int | None = None) -> sqlite3.Row:
    event = active_event(conn)
    if not event:
        raise ValueError("Keine laufende Veranstaltung")
    if expected_event_id is not None and int(event["id"]) != expected_event_id:
        raise ValueError("Die Veranstaltung hat sich geändert. Bitte die Ansicht aktualisieren.")
    return event


def start_event(conn: sqlite3.Connection, name: str) -> sqlite3.Row:
    clean_name = " ".join(str(name or "").strip().split())
    if not clean_name:
        raise ValueError("Veranstaltungsname fehlt")
    if active_event(conn):
        raise ValueError("Es läuft bereits eine Veranstaltung")
    now = now_text()
    cur = conn.execute(
        """
        INSERT INTO event_sessions (
            name, start_time, end_time, status, created_at, updated_at,
            csv_path, pdf_path, invoice_created, invoice_mail_sent,
            invoice_mail_to, total_eur, discount_total_eur
        ) VALUES (?, ?, NULL, 'ACTIVE', ?, ?, NULL, NULL, 0, 0, NULL, 0, 0)
        """,
        (clean_name, now, now, now),
    )
    return conn.execute("SELECT * FROM event_sessions WHERE id = ?", (int(cur.lastrowid),)).fetchone()


def serialize_event_line(row: sqlite3.Row | dict[str, Any], line_discount_percent: float = 0.0) -> dict[str, Any]:
    quantity = int(row["quantity"] or 0)
    unit_price = money(float(row["unit_price_eur"] or 0))
    subtotal = money(quantity * unit_price)
    percent = max(0.0, min(float(line_discount_percent or 0), 100.0))
    discount = money(subtotal * percent / 100.0)
    return {
        "id": int(row["id"]),
        "line_id": int(row["id"]),
        "item_id": row["item_id"],
        "item": row["item_name_snapshot"],
        "name": row["item_name_snapshot"],
        "short_label": row["item_short_label_snapshot"],
        "quantity": quantity,
        "unit_price_eur": unit_price,
        "price": unit_price,
        "subtotal_eur": subtotal,
        "line_discount_percent": percent,
        "line_discount_eur": discount,
        "line_total_eur": money(subtotal - discount),
    }


def event_lines(conn: sqlite3.Connection, event_id: int) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT *
        FROM event_lines
        WHERE event_id = ? AND quantity > 0
        ORDER BY id ASC
        """,
        (event_id,),
    ).fetchall()


def event_payload(
    conn: sqlite3.Connection,
    event: sqlite3.Row | dict[str, Any] | None = None,
    discounts: dict[str, Any] | None = None,
    end_time: str | None = None,
) -> dict[str, Any] | None:
    if event is None:
        event = active_event(conn)
    if not event:
        return None
    line_discounts = normalize_line_discounts(discounts or {})
    lines = event_lines(conn, int(event["id"]))
    return build_event_summary(dict(event), lines, line_discounts, end_time=end_time)


def add_event_item(
    conn: sqlite3.Connection,
    item_id: int,
    quantity: int = 1,
    event: sqlite3.Row | None = None,
    expected_event_id: int | None = None,
) -> dict[str, Any]:
    event = event or require_active_event(conn, expected_event_id)
    qty = int(quantity)
    if qty <= 0:
        raise ValueError("Menge muss positiv sein")
    item = conn.execute(
        """
        SELECT *
        FROM items
        WHERE id = ? AND active = 1 AND admin_only = 0 AND archived_at IS NULL
        """,
        (int(item_id),),
    ).fetchone()
    if not item:
        raise ValueError("Artikel nicht gefunden oder nicht aktiv")
    price = money(float(item["price_eur"] or 0))
    purchase = money(float(item["purchase_price_eur"] if "purchase_price_eur" in item.keys() else 0))
    existing = conn.execute(
        """
        SELECT id
        FROM event_lines
        WHERE event_id = ?
          AND item_id = ?
          AND unit_price_eur = ?
          AND unit_purchase_price_eur = ?
          AND item_name_snapshot = ?
          AND item_short_label_snapshot = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (
            int(event["id"]),
            int(item["id"]),
            price,
            purchase,
            item["name"],
            item["short_label"],
        ),
    ).fetchone()
    now = now_text()
    if existing:
        conn.execute(
            "UPDATE event_lines SET quantity = quantity + ?, updated_at = ? WHERE id = ?",
            (qty, now, int(existing["id"])),
        )
        line_id = int(existing["id"])
    else:
        cur = conn.execute(
            """
            INSERT INTO event_lines (
                event_id, item_id, item_name_snapshot, item_short_label_snapshot,
                quantity, unit_price_eur, unit_purchase_price_eur, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                int(event["id"]),
                int(item["id"]),
                item["name"],
                item["short_label"],
                qty,
                price,
                purchase,
                now,
                now,
            ),
        )
        line_id = int(cur.lastrowid)
    conn.execute("UPDATE event_sessions SET updated_at = ? WHERE id = ?", (now, int(event["id"])))
    line = conn.execute("SELECT * FROM event_lines WHERE id = ?", (line_id,)).fetchone()
    return {
        "status": "ok",
        "line": serialize_event_line(line),
        "event": event_payload(conn, event),
    }


def remove_event_item(conn: sqlite3.Connection, item_id: int, expected_event_id: int | None = None) -> dict[str, Any]:
    event = require_active_event(conn, expected_event_id)
    # Correct the latest positive price snapshot without using today's item price.
    line = conn.execute(
        """
        SELECT * FROM event_lines
        WHERE event_id = ? AND item_id = ? AND quantity > 0
        ORDER BY id DESC LIMIT 1
        """,
        (int(event["id"]), int(item_id)),
    ).fetchone()
    if not line:
        raise ValueError("Für dieses Getränk sind keine Striche zum Abziehen vorhanden.")
    now = now_text()
    changed = conn.execute(
        "UPDATE event_lines SET quantity = quantity - 1, updated_at = ? WHERE id = ? AND quantity > 0",
        (now, int(line["id"])),
    )
    if changed.rowcount != 1:
        raise ValueError("Der Strich wurde bereits abgezogen. Bitte die Ansicht aktualisieren.")
    conn.execute("UPDATE event_sessions SET updated_at = ? WHERE id = ?", (now, int(event["id"])))
    updated_line = conn.execute("SELECT * FROM event_lines WHERE id = ?", (int(line["id"]),)).fetchone()
    return {"status": "ok", "line": serialize_event_line(updated_line), "event": event_payload(conn, event)}


def normalize_percent(value: Any, field_name: str) -> float:
    if value is None or value == "":
        return 0.0
    if isinstance(value, (int, float)):
        percent = float(value)
    else:
        text = str(value).strip().replace("%", "").replace(" ", "").replace("\u00a0", "")
        if "," in text and "." in text:
            text = (
                text.replace(".", "").replace(",", ".") if text.rfind(",") > text.rfind(".") else text.replace(",", "")
            )
        else:
            text = text.replace(",", ".")
        try:
            percent = float(text)
        except ValueError as exc:
            raise ValueError(f"{field_name} ist keine gültige Zahl") from exc
    if percent < 0:
        raise ValueError(f"{field_name} darf nicht negativ sein")
    if percent > 100:
        raise ValueError(f"{field_name} darf maximal 100 % sein")
    return money(percent)


def normalize_line_discounts(values: dict[str, Any]) -> dict[int, float]:
    discounts: dict[int, float] = {}
    for key, value in (values or {}).items():
        line_id = int(key)
        discounts[line_id] = normalize_percent(value, "Positionsrabatt")
    return discounts


def build_event_summary(
    event: dict[str, Any],
    lines: list[sqlite3.Row],
    line_discounts: dict[int, float] | None = None,
    total_discount_percent: Any = 0,
    end_time: str | None = None,
) -> dict[str, Any]:
    discounts = line_discounts or {}
    serialized = []
    subtotal = 0.0
    line_discount_total = 0.0
    for row in lines:
        raw_subtotal = money(int(row["quantity"] or 0) * float(row["unit_price_eur"] or 0))
        discount_percent = max(0.0, min(float(discounts.get(int(row["id"]), 0.0) or 0), 100.0))
        line = serialize_event_line(row, discount_percent)
        serialized.append(line)
        subtotal += raw_subtotal
        line_discount_total += line["line_discount_eur"]
    subtotal = money(subtotal)
    line_discount_total = money(line_discount_total)
    after_line_discounts = money(subtotal - line_discount_total)
    clean_total_discount_percent = normalize_percent(total_discount_percent, "Gesamtrabatt")
    clean_total_discount_eur = money(after_line_discounts * clean_total_discount_percent / 100.0)
    final_total = money(after_line_discounts - clean_total_discount_eur)
    return {
        "id": int(event["id"]),
        "name": event["name"],
        "status": event["status"],
        "start_time": event["start_time"],
        "end_time": end_time or event.get("end_time"),
        "lines": serialized,
        "subtotal_eur": subtotal,
        "line_discount_total_eur": line_discount_total,
        "total_discount_percent": clean_total_discount_percent,
        "total_discount_eur": clean_total_discount_eur,
        "discount_total_eur": money(line_discount_total + clean_total_discount_eur),
        "final_total_eur": final_total,
        "total_eur": final_total,
        "quantity": sum(int(line["quantity"] or 0) for line in serialized),
        "csv_path": event.get("csv_path"),
        "pdf_path": event.get("pdf_path"),
        "invoice_created": bool(event.get("invoice_created", 0)),
        "invoice_mail_sent": bool(event.get("invoice_mail_sent", 0)),
    }


def csv_rows_for_event(summary: dict[str, Any]) -> list[list[object]]:
    rows = []
    event_name = summary["name"]
    start_time = summary["start_time"]
    end_time = summary["end_time"] or ""
    total_discount_percent = f"{summary['total_discount_percent']:.2f}"
    total_discount_eur = f"{summary['total_discount_eur']:.2f}"
    final_total = f"{summary['final_total_eur']:.2f}"
    for line in summary.get("lines") or []:
        rows.append(
            [
                event_name,
                start_time,
                end_time,
                line["item"],
                int(line["quantity"]),
                f"{line['unit_price_eur']:.2f}",
                f"{line['subtotal_eur']:.2f}",
                f"{line['line_discount_percent']:.2f}",
                f"{line['line_discount_eur']:.2f}",
                total_discount_percent,
                total_discount_eur,
                final_total,
            ]
        )
    if not rows:
        rows.append(
            [
                event_name,
                start_time,
                end_time,
                "",
                0,
                "0.00",
                "0.00",
                "0.00",
                "0.00",
                total_discount_percent,
                total_discount_eur,
                final_total,
            ]
        )
    return rows


def save_event_csv(db_path: str | os.PathLike[str], event: dict[str, Any], summary: dict[str, Any]) -> str:
    output = io.StringIO(newline="")
    writer = csv.writer(output, delimiter=";")
    writer.writerow(EVENT_CSV_HEADERS)
    writer.writerows(csv_rows_for_event(summary))
    path = event_output_dir(db_path) / f"{event_file_base(event)}.csv"
    path.write_bytes(output.getvalue().encode("utf-8-sig"))
    return str(path)


def pdf_escape(value: Any) -> str:
    text = str(value or "")
    replacements = {
        "€": "EUR",
        "ä": "ae",
        "ö": "oe",
        "ü": "ue",
        "Ä": "Ae",
        "Ö": "Oe",
        "Ü": "Ue",
        "ß": "ss",
        "→": "->",
        "–": "-",
        "—": "-",
        "\u00a0": " ",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def pdf_text_line(x: float, y: float, text: Any, size: int = 11, font: str = "F1") -> str:
    return f"BT /{font} {size} Tf {x:.1f} {y:.1f} Td ({pdf_escape(text)}) Tj ET\n"


def pdf_rect(x: float, y: float, width: float, height: float, gray: float = 0.94) -> str:
    return f"{gray:.2f} g {x:.1f} {y:.1f} {width:.1f} {height:.1f} re f 0 g\n"


def pdf_wrapped_lines(value: Any, max_lines: int, max_chars: int = 72) -> list[str]:
    lines: list[str] = []
    for raw in str(value or "").splitlines():
        text = " ".join(raw.split())
        if not text:
            continue
        while len(text) > max_chars and len(lines) < max_lines:
            cut = text.rfind(" ", 0, max_chars + 1)
            if cut < 18:
                cut = max_chars
            lines.append(text[:cut].strip())
            text = text[cut:].strip()
        if text and len(lines) < max_lines:
            lines.append(text[:max_chars].strip())
        if len(lines) >= max_lines:
            break
    return lines


def format_invoice_prefix(prefix: str, invoice_date: date) -> str:
    tokens = {
        "YYYY": f"{invoice_date.year:04d}",
        "YY": f"{invoice_date.year % 100:02d}",
        "MM": f"{invoice_date.month:02d}",
        "dd": f"{invoice_date.day:02d}",
    }
    token_pattern = r"YYYY|YY|MM|dd"
    error = (
        "Ungueltiger Datumsplatzhalter im Rechnungsnummer-Praefix. "
        "Erlaubt sind YYYY, YY, MM und dd in geschweiften Klammern, "
        "getrennt durch - . / _ oder Leerzeichen, z. B. EVENT-{YYYY-MM-dd}."
    )

    def replace_placeholder(match: re.Match[str]) -> str:
        pattern = match.group(1)
        separators = re.sub(token_pattern, "", pattern)
        if not re.search(token_pattern, pattern) or not re.fullmatch(r"[-./_ ]*", separators):
            raise ValueError(error)
        return re.sub(token_pattern, lambda token: tokens[token.group()], pattern)

    formatted = re.sub(r"\{([^{}]*)\}", replace_placeholder, prefix)
    if "{" in formatted or "}" in formatted:
        raise ValueError(error)
    return formatted


def invoice_number_for_summary(summary: dict[str, Any], settings: dict[str, str]) -> str:
    prefix = (settings.get("invoice_number_prefix") or "EVENT").strip()
    invoice_date = date.fromisoformat(str(summary.get("end_time") or now_text())[:10])
    prefix = format_invoice_prefix(prefix, invoice_date)
    number = int(summary.get("id") or 0)
    return f"{prefix}-{number:04d}" if prefix else f"{number:04d}"


def invoice_payment_lines(summary: dict[str, Any], settings: dict[str, str]) -> list[str]:
    iban = str(settings.get("invoice_iban") or "").strip()
    if not iban:
        return []
    invoice_number = invoice_number_for_summary(summary, settings)
    return [
        f"Bitte den Rechnungsbetrag von EUR {summary['final_total_eur']:.2f} per SEPA-Ueberweisung begleichen:",
        f"Empfaenger: {settings.get('invoice_sender_name') or 'Drink POS'}",
        f"IBAN {iban}",
        f"Verwendungszweck: Rechnung {invoice_number}",
    ]


def compact_iban(value: Any) -> str:
    return "".join(ch for ch in str(value or "").upper() if ch.isalnum())


def epc_qr_field(value: Any, max_chars: int) -> str:
    text = " ".join(str(value or "").split())
    return text[:max_chars]


def sepa_qr_payload(summary: dict[str, Any], settings: dict[str, str]) -> str:
    iban = compact_iban(normalize_iban(settings.get("invoice_iban")))
    if not iban:
        raise ValueError(
            "Fuer die Rechnung mit SEPA-QR-Code fehlt die IBAN. "
            "Bitte unter Admin > Rechnung / Veranstaltung die IBAN eintragen und Einstellungen speichern."
        )
    invoice_number = invoice_number_for_summary(summary, settings)
    amount = max(0.0, float(summary.get("final_total_eur") or 0))
    payload = "\n".join(
        [
            "BCD",
            "002",
            "1",
            "SCT",
            "",
            epc_qr_field(settings.get("invoice_sender_name") or "Drink POS", 70),
            iban,
            f"EUR{amount:.2f}" if amount > 0 else "",
            "",
            "",
            epc_qr_field(f"Rechnung {invoice_number}", 140),
            epc_qr_field(f"Veranstaltung {summary.get('name') or ''}", 70),
        ]
    )
    if amount > 999999999.99 or len(payload.encode("utf-8")) > 331:
        raise ValueError("Zahlungsdaten sind fuer einen SEPA-QR-Code zu lang oder der Betrag ist zu hoch.")
    return payload


def sepa_qr_matrix(summary: dict[str, Any], settings: dict[str, str]) -> list[list[bool]]:
    payload = sepa_qr_payload(summary, settings)
    if qrcode is None:
        raise RuntimeError("SEPA-QR-Code konnte nicht erzeugt werden: Die QR-Code-Bibliothek fehlt auf dem Server.")
    qr = qrcode.QRCode(error_correction=ERROR_CORRECT_M, border=4)
    qr.add_data(payload.encode("utf-8"))
    qr.make(fit=True)
    return qr.get_matrix()


def pdf_qr_code(x: float, y: float, size: float, matrix: list[list[bool]]) -> str:
    if not matrix:
        return ""
    rows = len(matrix)
    if rows <= 0:
        return ""
    module = size / rows
    parts = [pdf_rect(x, y, size, size, 1.0)]
    for row_idx, row in enumerate(matrix):
        for col_idx, dark in enumerate(row):
            if not dark:
                continue
            cell_x = x + col_idx * module
            cell_y = y + size - (row_idx + 1) * module
            parts.append(pdf_rect(cell_x, cell_y, module + 0.05, module + 0.05, 0.0))
    return "".join(parts)


def write_simple_invoice_pdf(
    path: Path, summary: dict[str, Any], settings: dict[str, str], include_qr_code: bool = False
) -> None:
    qr_matrix = sepa_qr_matrix(summary, settings) if include_qr_code else []
    width = 595.32
    height = 841.92
    y = 780.0
    content = []
    content.append(pdf_rect(56, 748, 480, 62, 0.95))
    content.append(pdf_text_line(72, 776, settings.get("invoice_logo_text") or "MVH", 28, "F2"))
    content.append(pdf_text_line(156, 769, settings.get("invoice_sender_name") or "Drink POS", 12, "F2"))
    sender_address = pdf_wrapped_lines(settings.get("invoice_sender_address"), 3, 56)
    sender_y = 753
    for line in sender_address:
        content.append(pdf_text_line(156, sender_y, line, 9))
        sender_y -= 12
    y = 690
    recipient_lines = pdf_wrapped_lines(settings.get("invoice_recipient"), 5, 48)
    for line in recipient_lines[:5]:
        content.append(pdf_text_line(72, y, line, 11))
        y -= 17
    place = settings.get("invoice_place") or ""
    invoice_number = invoice_number_for_summary(summary, settings)
    today = str(summary.get("end_time") or now_text())[:10]
    content.append(pdf_text_line(330, 724, "Rechnungsnummer", 9))
    content.append(pdf_text_line(330, 708, invoice_number, 11, "F2"))
    content.append(pdf_text_line(330, 690, "Rechnungsdatum", 11))
    content.append(pdf_text_line(466, 690, today, 11))
    content.append(pdf_text_line(330, 672, "Veranstaltung", 11))
    content.append(pdf_text_line(466, 672, summary.get("name") or "", 11))
    content.append(pdf_text_line(330, 654, "Zeitraum", 11))
    content.append(pdf_text_line(466, 654, str(summary.get("start_time") or "")[:16], 11))
    content.append(pdf_text_line(330, 630, f"{place},", 11))
    content.append(pdf_text_line(466, 630, today, 11))
    content.append(pdf_text_line(72, 580, f"Abrechnung {summary.get('name') or ''}", 14, "F2"))
    note_y = 558
    for line in pdf_wrapped_lines(settings.get("invoice_notes"), 2, 78):
        content.append(pdf_text_line(72, note_y, line, 9))
        note_y -= 13
    content.append(pdf_text_line(72, 506, "Folgende Getraenke wurden konsumiert:", 12))
    content.append(pdf_rect(72, 454, 464, 18, 0.93))
    content.append(pdf_text_line(74, 459, "Pos.", 11, "F2"))
    content.append(pdf_text_line(118, 459, "Bezeichnung", 11, "F2"))
    content.append(pdf_text_line(310, 459, "Menge", 11, "F2"))
    content.append(pdf_text_line(370, 459, "Einzelpreis", 11, "F2"))
    content.append(pdf_text_line(466, 459, "Gesamtpreis", 11, "F2"))
    y = 430
    for idx, line in enumerate(summary.get("lines") or [], start=1):
        if y < 180:
            break
        content.append(pdf_text_line(84, y, idx, 10))
        content.append(pdf_text_line(118, y, line["item"], 10))
        content.append(pdf_text_line(324, y, line["quantity"], 10))
        content.append(pdf_text_line(376, y, f"EUR {line['unit_price_eur']:.2f}", 10))
        content.append(pdf_text_line(468, y, f"EUR {line['subtotal_eur']:.2f}", 10))
        y -= 18
        if float(line.get("line_discount_eur", 0) or 0) > 0:
            content.append(pdf_text_line(118, y, f"Positionsrabatt {line.get('line_discount_percent', 0):.2f}%", 9))
            content.append(pdf_text_line(468, y, f"-EUR {line['line_discount_eur']:.2f}", 9))
            y -= 15
    totals_y = 270
    content.append(pdf_text_line(118, totals_y, "Zwischensumme", 11))
    content.append(pdf_text_line(468, totals_y, f"EUR {summary['subtotal_eur']:.2f}", 11))
    content.append(pdf_text_line(118, totals_y - 18, "Positionsrabatte", 11))
    content.append(pdf_text_line(468, totals_y - 18, f"-EUR {summary['line_discount_total_eur']:.2f}", 11))
    content.append(pdf_text_line(118, totals_y - 36, f"Gesamtrabatt {summary['total_discount_percent']:.2f}%", 11))
    content.append(pdf_text_line(468, totals_y - 36, f"-EUR {summary['total_discount_eur']:.2f}", 11))
    content.append(pdf_rect(72, totals_y - 78, 464, 22, 0.93))
    content.append(pdf_text_line(118, totals_y - 72, "Rechnungsbetrag", 15, "F2"))
    content.append(pdf_text_line(430, totals_y - 72, "EUR", 14, "F2"))
    content.append(pdf_text_line(484, totals_y - 72, f"{summary['final_total_eur']:.2f}", 14, "F2"))
    payment_lines = invoice_payment_lines(summary, settings)
    if payment_lines:
        if qr_matrix:
            content.append(pdf_qr_code(72, 78, 96, qr_matrix))
            content.append(pdf_text_line(72, 182, "SEPA-QR-Code", 9, "F2"))
        payment_x = 184 if qr_matrix else 118
        payment_y = 172
        payment_chars = 64 if qr_matrix else 78
        remaining = 7
        for line in payment_lines:
            for wrapped in pdf_wrapped_lines(line, remaining, payment_chars):
                content.append(pdf_text_line(payment_x, payment_y, wrapped, 9))
                payment_y -= 13
                remaining -= 1
                if remaining <= 0:
                    break
            if remaining <= 0:
                break
    footer_name_y = 54 if payment_lines else 90
    footer_sender_y = footer_name_y - 15
    content.append(pdf_text_line(72, footer_name_y, settings.get("invoice_sender_name") or "Drink POS", 11))
    for line in sender_address[:2]:
        content.append(pdf_text_line(72, footer_sender_y, line, 8))
        footer_sender_y -= 10
    footer = settings.get("invoice_footer_text") or ""
    if footer:
        content.append(pdf_text_line(72, 14 if payment_lines else 48, footer, 9))
    stream = "".join(content).encode("latin-1", errors="replace")
    objects: list[bytes] = []
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    objects.append(b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>")
    objects.append(
        f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {width:.2f} {height:.2f}] "
        "/Resources << /Font << /F1 4 0 R /F2 5 0 R >> >> /Contents 6 0 R >>".encode("ascii")
    )
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>")
    objects.append(b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"endstream")
    pdf = io.BytesIO()
    pdf.write(b"%PDF-1.4\n")
    offsets = [0]
    for i, obj in enumerate(objects, start=1):
        offsets.append(pdf.tell())
        pdf.write(f"{i} 0 obj\n".encode("ascii"))
        pdf.write(obj)
        pdf.write(b"\nendobj\n")
    xref_pos = pdf.tell()
    pdf.write(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    pdf.write(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.write(f"{offset:010d} 00000 n \n".encode("ascii"))
    pdf.write(f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF\n".encode("ascii"))
    path.write_bytes(pdf.getvalue())


def generate_event_invoice_pdf(
    db_path: str | os.PathLike[str],
    event: dict[str, Any],
    summary: dict[str, Any],
    settings: dict[str, str],
    include_qr_code: bool = False,
) -> str:
    path = event_output_dir(db_path) / f"{event_file_base(event)}.pdf"
    write_simple_invoice_pdf(path, summary, settings, include_qr_code=include_qr_code)
    return str(path)


def smtp_configured(conn: sqlite3.Connection | None = None) -> bool:
    if conn is None:
        return bool(env_mail_settings()["mail_smtp_host"])
    return bool(get_mail_settings(conn)["mail_smtp_configured"])


def smtp_error_text(error: Any) -> str:
    if isinstance(error, bytes):
        return error.decode("utf-8", errors="replace")
    return str(error or "").strip()


def mail_exception_message(exc: Exception) -> str:
    if isinstance(exc, smtplib.SMTPAuthenticationError):
        return f"SMTP-Login fehlgeschlagen: Benutzername oder Passwort ist falsch oder der Anbieter blockiert den Login ({exc.smtp_code} {smtp_error_text(exc.smtp_error)})."
    if isinstance(exc, smtplib.SMTPConnectError):
        return f"Verbindung zum SMTP-Server fehlgeschlagen: {exc.smtp_code} {smtp_error_text(exc.smtp_error)}."
    if isinstance(exc, smtplib.SMTPRecipientsRefused):
        return f"Empfängeradresse wurde vom Mailserver abgelehnt: {exc.recipients}."
    if isinstance(exc, smtplib.SMTPSenderRefused):
        return f"Absenderadresse wurde vom Mailserver abgelehnt: {exc.smtp_code} {smtp_error_text(exc.smtp_error)}."
    if isinstance(exc, smtplib.SMTPDataError):
        return f"Mailserver hat die Nachricht abgelehnt: {exc.smtp_code} {smtp_error_text(exc.smtp_error)}."
    if isinstance(exc, smtplib.SMTPServerDisconnected):
        return "SMTP-Server hat die Verbindung getrennt. Bitte Server, Port und Verschlüsselung prüfen."
    if isinstance(exc, smtplib.SMTPException):
        return f"SMTP-Fehler: {exc}."
    if isinstance(exc, ssl.SSLError):
        return f"TLS/SSL-Fehler: Verschlüsselung passt wahrscheinlich nicht zum Port ({exc})."
    if isinstance(exc, (TimeoutError, socket.timeout)):
        return "Timeout beim SMTP-Server. Bitte Serveradresse, Port und Firewall prüfen."
    if isinstance(exc, OSError):
        return f"Netzwerk-/DNS-Fehler beim SMTP-Server: {exc}."
    return str(exc) or "Mailversand fehlgeschlagen."


def clean_mail_addresses(addresses: list[str] | None) -> list[str]:
    return [str(address or "").strip() for address in addresses or [] if str(address or "").strip()]


def send_smtp_message(
    settings: dict[str, Any],
    recipient: str,
    subject: str,
    body: str,
    attachments: list[Path] | None = None,
    cc: list[str] | None = None,
    bcc: list[str] | None = None,
) -> None:
    host = str(settings.get("mail_smtp_host") or "").strip()
    if not host:
        raise RuntimeError("SMTP-Server fehlt")
    try:
        port = int(str(settings.get("mail_smtp_port") or "587").strip())
    except ValueError as exc:
        raise RuntimeError("SMTP-Port ist ungültig") from exc
    username = str(settings.get("mail_smtp_username") or "").strip()
    password = str(settings.get("mail_smtp_password") or "")
    sender = str(username or settings.get("mail_smtp_from") or "").strip()
    if not sender:
        raise RuntimeError("Absenderadresse fehlt")
    encryption = str(settings.get("mail_smtp_encryption") or "starttls").strip().lower()
    if encryption not in {"ssl", "starttls", "none"}:
        raise RuntimeError("SMTP-Verschlüsselung ist ungültig")
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = recipient
    cc_addresses = clean_mail_addresses(cc)
    bcc_addresses = clean_mail_addresses(bcc)
    if cc_addresses:
        msg["Cc"] = ", ".join(cc_addresses)
    if bcc_addresses:
        msg["Bcc"] = ", ".join(bcc_addresses)
    msg.set_content(body)
    for attachment in attachments or []:
        data = attachment.read_bytes()
        msg.add_attachment(data, maintype="application", subtype="pdf", filename=attachment.name)
    smtp_class = smtplib.SMTP_SSL if encryption == "ssl" else smtplib.SMTP
    with smtp_class(host, port, timeout=20) as smtp:
        if encryption == "starttls":
            smtp.starttls()
        if username:
            smtp.login(username, password)
        smtp.send_message(msg)


def send_event_invoice_email(
    pdf_path: str,
    summary: dict[str, Any],
    settings: dict[str, Any],
    copy_to_sender: bool = False,
    send_to_cashier: bool = True,
    recipient: str | None = None,
) -> bool:
    if not send_to_cashier and not copy_to_sender:
        return False
    cashier = str(settings.get("invoice_cashier_email") or "").strip()
    sender = str(settings.get("mail_smtp_username") or settings.get("mail_smtp_from") or "").strip()
    target = str(recipient or "").strip()
    if not target and send_to_cashier:
        target = cashier
    if not target and copy_to_sender:
        target = sender
    if not target:
        raise RuntimeError("Empfänger-Mailadresse fehlt")
    if send_to_cashier and not cashier and not recipient:
        raise RuntimeError("Kassier-Mailadresse fehlt")
    if not sender:
        raise RuntimeError("Absenderadresse fehlt")
    bcc = [sender] if copy_to_sender and sender.lower() != target.lower() else []
    send_smtp_message(
        settings,
        target,
        f"Rechnung {summary['name']}",
        f"Anbei die Rechnung zur Veranstaltung {summary['name']}.",
        [Path(pdf_path)],
        bcc=bcc,
    )
    return bool(copy_to_sender)


def send_test_email(settings: dict[str, Any], recipient: str) -> None:
    clean_recipient = normalize_test_recipient(recipient, required=True)
    send_smtp_message(
        settings,
        clean_recipient,
        "Drink POS Testmail",
        f"Das ist eine Testmail aus Drink POS vom {now_text()}.",
    )


def close_event(
    conn: sqlite3.Connection,
    db_path: str | os.PathLike[str],
    event: sqlite3.Row,
    line_discounts: dict[int, float] | None = None,
    total_discount_percent: Any = 0,
    create_invoice: bool = False,
    email_invoice: bool = False,
    copy_invoice_to_sender: bool = False,
    include_invoice_qr: bool = False,
    external_recipient: bool = False,
    external_recipient_name: Any = "",
    external_recipient_email: Any = "",
    external_recipient_address: Any = "",
) -> dict[str, Any]:
    end_time = now_text()
    summary = build_event_summary(
        dict(event),
        event_lines(conn, int(event["id"])),
        line_discounts or {},
        total_discount_percent,
        end_time,
    )
    external = None
    if external_recipient:
        external = normalize_external_recipient(
            external_recipient_name,
            external_recipient_email,
            external_recipient_address,
            require_email=bool(email_invoice),
        )
    event_dict = dict(event)
    csv_path = save_event_csv(db_path, event_dict, summary)
    pdf_path = None
    mail_sent = False
    mail_copy_sent = False
    invoice_settings = get_invoice_settings(conn)
    invoice_settings = invoice_settings_for_recipient(invoice_settings, external)
    mail_settings = get_mail_settings(conn, include_secret=True)
    settings = {**invoice_settings, **mail_settings}
    should_mail = bool(email_invoice or copy_invoice_to_sender)
    should_invoice = bool(create_invoice or should_mail or include_invoice_qr)
    if should_invoice:
        pdf_path = generate_event_invoice_pdf(
            db_path, event_dict, summary, invoice_settings, include_qr_code=include_invoice_qr
        )
    if should_mail:
        if not pdf_path:
            raise RuntimeError("PDF wurde nicht erzeugt")
        try:
            mail_copy_sent = send_event_invoice_email(
                pdf_path,
                summary,
                settings,
                copy_to_sender=bool(copy_invoice_to_sender),
                send_to_cashier=bool(email_invoice),
                recipient=external.get("email") if external and email_invoice else None,
            )
        except Exception as exc:
            raise RuntimeError(mail_exception_message(exc)) from exc
        mail_sent = True
    recipients = []
    if email_invoice:
        recipients.append(
            external.get("email") if external else str(settings.get("invoice_cashier_email") or "").strip()
        )
    if mail_copy_sent:
        recipients.append(str(settings.get("mail_smtp_username") or settings.get("mail_smtp_from") or "").strip())
    conn.execute(
        """
        UPDATE event_sessions
        SET status = 'CLOSED',
            end_time = ?,
            updated_at = ?,
            csv_path = ?,
            pdf_path = ?,
            invoice_created = ?,
            invoice_mail_sent = ?,
            invoice_mail_to = ?,
            total_eur = ?,
            discount_total_eur = ?
        WHERE id = ? AND status = 'ACTIVE'
        """,
        (
            end_time,
            now_text(),
            csv_path,
            pdf_path,
            1 if should_invoice else 0,
            1 if mail_sent else 0,
            ", ".join(clean_mail_addresses(recipients)) if mail_sent else None,
            summary["final_total_eur"],
            summary["discount_total_eur"],
            int(event["id"]),
        ),
    )
    summary.update(
        {
            "status": "CLOSED",
            "end_time": end_time,
            "csv_path": csv_path,
            "pdf_path": pdf_path,
            "invoice_created": should_invoice,
            "invoice_mail_sent": mail_sent,
        }
    )
    return {
        "status": "ok",
        "event": summary,
        "artifacts": asdict(EventArtifacts(csv_path, pdf_path, mail_sent, mail_copy_sent)),
    }
