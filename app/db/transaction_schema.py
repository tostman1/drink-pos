"""RL-05 additive durable provenance; never reconstruct existing operations."""

SQL = (
    """CREATE TABLE IF NOT EXISTS operation_receipts (
        operation_id TEXT PRIMARY KEY,
        endpoint TEXT NOT NULL,
        payload_json TEXT NOT NULL,
        result_json TEXT NOT NULL,
        transaction_id INTEGER,
        created_at TEXT NOT NULL,
        FOREIGN KEY(transaction_id) REFERENCES transactions(id)
    )""",
    """CREATE TABLE IF NOT EXISTS booking_sources (
        transaction_item_id INTEGER PRIMARY KEY,
        original_order_line_id INTEGER NOT NULL,
        consumed_date TEXT NOT NULL,
        FOREIGN KEY(transaction_item_id) REFERENCES transaction_items(id),
        FOREIGN KEY(original_order_line_id) REFERENCES order_lines(id)
    )""",
    """CREATE TABLE IF NOT EXISTS correction_details (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        operation_id TEXT NOT NULL,
        original_order_line_id INTEGER NOT NULL,
        source_transaction_item_id INTEGER NOT NULL,
        transaction_item_id INTEGER NOT NULL UNIQUE,
        change_request_id INTEGER,
        purpose TEXT NOT NULL CHECK(purpose='erroneous_booking'),
        reason TEXT NOT NULL,
        authorized_by TEXT NOT NULL,
        consumed_date TEXT NOT NULL,
        corrected_at TEXT NOT NULL,
        FOREIGN KEY(operation_id) REFERENCES operation_receipts(operation_id) DEFERRABLE INITIALLY DEFERRED,
        FOREIGN KEY(original_order_line_id) REFERENCES order_lines(id),
        FOREIGN KEY(source_transaction_item_id) REFERENCES booking_sources(transaction_item_id),
        FOREIGN KEY(transaction_item_id) REFERENCES transaction_items(id),
        FOREIGN KEY(change_request_id) REFERENCES change_requests(id)
    )""",
    """CREATE TABLE IF NOT EXISTS round_units (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        original_order_line_id INTEGER NOT NULL,
        booking_transaction_item_id INTEGER NOT NULL,
        unit_number INTEGER NOT NULL CHECK(unit_number>0),
        event_start_transaction_id INTEGER,
        cancelled_operation_id TEXT,
        closed_transaction_id INTEGER,
        UNIQUE(booking_transaction_item_id,unit_number),
        FOREIGN KEY(original_order_line_id) REFERENCES order_lines(id),
        FOREIGN KEY(booking_transaction_item_id) REFERENCES transaction_items(id),
        FOREIGN KEY(event_start_transaction_id) REFERENCES transactions(id),
        FOREIGN KEY(cancelled_operation_id) REFERENCES operation_receipts(operation_id) DEFERRABLE INITIALLY DEFERRED,
        FOREIGN KEY(closed_transaction_id) REFERENCES transactions(id)
    )""",
    """CREATE TABLE IF NOT EXISTS round_unit_payments (
        round_unit_id INTEGER PRIMARY KEY,
        paid_round_unit_id INTEGER NOT NULL UNIQUE,
        FOREIGN KEY(round_unit_id) REFERENCES round_units(id),
        FOREIGN KEY(paid_round_unit_id) REFERENCES paid_round_units(id)
    )""",
    """CREATE TABLE IF NOT EXISTS round_deductions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        round_unit_id INTEGER NOT NULL,
        person_id INTEGER NOT NULL,
        original_order_line_id INTEGER NOT NULL,
        transaction_item_id INTEGER NOT NULL UNIQUE,
        round_event_id INTEGER NOT NULL,
        consumed_date TEXT NOT NULL,
        UNIQUE(round_unit_id,person_id),
        FOREIGN KEY(round_unit_id) REFERENCES round_units(id),
        FOREIGN KEY(person_id) REFERENCES people(id),
        FOREIGN KEY(original_order_line_id) REFERENCES order_lines(id),
        FOREIGN KEY(transaction_item_id) REFERENCES transaction_items(id),
        FOREIGN KEY(round_event_id) REFERENCES round_events(id)
    )""",
    """CREATE TABLE IF NOT EXISTS round_reversals (
        deduction_id INTEGER PRIMARY KEY,
        operation_id TEXT NOT NULL,
        transaction_item_id INTEGER NOT NULL UNIQUE,
        round_event_id INTEGER NOT NULL,
        reversed_at TEXT NOT NULL,
        FOREIGN KEY(deduction_id) REFERENCES round_deductions(id),
        FOREIGN KEY(operation_id) REFERENCES operation_receipts(operation_id) DEFERRABLE INITIALLY DEFERRED,
        FOREIGN KEY(transaction_item_id) REFERENCES transaction_items(id),
        FOREIGN KEY(round_event_id) REFERENCES round_events(id)
    )""",
    """CREATE TABLE IF NOT EXISTS round_cancellations (
        round_unit_id INTEGER PRIMARY KEY,
        operation_id TEXT NOT NULL,
        transaction_item_id INTEGER NOT NULL UNIQUE,
        change_request_id INTEGER,
        reason TEXT NOT NULL,
        authorized_by TEXT NOT NULL,
        cancelled_at TEXT NOT NULL,
        FOREIGN KEY(round_unit_id) REFERENCES round_units(id),
        FOREIGN KEY(operation_id) REFERENCES operation_receipts(operation_id) DEFERRABLE INITIALLY DEFERRED,
        FOREIGN KEY(transaction_item_id) REFERENCES transaction_items(id),
        FOREIGN KEY(change_request_id) REFERENCES change_requests(id)
    )""",
    "CREATE INDEX IF NOT EXISTS idx_booking_sources_line ON booking_sources(original_order_line_id)",
    "CREATE INDEX IF NOT EXISTS idx_correction_details_date ON correction_details(consumed_date)",
    "CREATE INDEX IF NOT EXISTS idx_round_units_line ON round_units(original_order_line_id)",
    """CREATE TRIGGER IF NOT EXISTS correction_detail_source_guard BEFORE INSERT ON correction_details
        BEGIN
          SELECT CASE WHEN NOT EXISTS(
            SELECT 1 FROM booking_sources bs JOIN transaction_items source ON source.id=bs.transaction_item_id
              JOIN transaction_items correction ON correction.id=NEW.transaction_item_id
            WHERE bs.transaction_item_id=NEW.source_transaction_item_id
              AND bs.original_order_line_id=NEW.original_order_line_id
              AND bs.consumed_date=NEW.consumed_date AND source.kind='CONSUME'
              AND correction.kind='CONSUMPTION_CORRECTION' AND correction.quantity<0
              AND correction.person_id=source.person_id AND correction.item_id IS source.item_id
              AND correction.unit_price_eur=source.unit_price_eur
              AND correction.unit_purchase_price_eur=source.unit_purchase_price_eur
              AND source.quantity + correction.quantity + COALESCE((
                SELECT SUM(ti.quantity) FROM correction_details cd JOIN transaction_items ti ON ti.id=cd.transaction_item_id
                WHERE cd.source_transaction_item_id=source.id),0)>=0
          ) THEN RAISE(ABORT,'invalid correction source or quantity') END;
        END""",
    """CREATE TRIGGER IF NOT EXISTS round_deduction_state_guard BEFORE INSERT ON round_deductions
        BEGIN
          SELECT CASE WHEN NOT EXISTS(SELECT 1 FROM round_units ru
            JOIN order_lines ol ON ol.id=NEW.original_order_line_id
            JOIN transaction_items ti ON ti.id=NEW.transaction_item_id
            WHERE ru.id=NEW.round_unit_id AND ru.cancelled_operation_id IS NULL AND ru.closed_transaction_id IS NULL
              AND ol.person_id=NEW.person_id AND ol.consumed_date=NEW.consumed_date
              AND ti.kind='ROUND_DEDUCTED' AND ti.quantity=-1 AND ti.person_id=NEW.person_id
              AND ti.item_id IS ol.item_id AND ti.unit_price_eur=ol.unit_price_eur
              AND ti.unit_purchase_price_eur=ol.unit_purchase_price_eur)
          THEN RAISE(ABORT,'invalid round deduction source or state') END;
        END""",
    """CREATE TRIGGER IF NOT EXISTS round_original_guard BEFORE UPDATE OF original_order_line_id,booking_transaction_item_id,unit_number,event_start_transaction_id ON round_units
        BEGIN SELECT RAISE(ABORT,'round original is immutable'); END""",
    """CREATE TRIGGER IF NOT EXISTS round_cancellation_permanent BEFORE UPDATE OF cancelled_operation_id ON round_units
        WHEN OLD.cancelled_operation_id IS NOT NULL
        BEGIN SELECT RAISE(ABORT,'round cancellation is permanent'); END""",
    """CREATE TRIGGER IF NOT EXISTS round_unit_no_delete BEFORE DELETE ON round_units
        BEGIN SELECT RAISE(ABORT,'round original is immutable'); END""",
)

AUDIT_TABLES = (
    "operation_receipts",
    "booking_sources",
    "correction_details",
    "round_unit_payments",
    "round_deductions",
    "round_reversals",
    "round_cancellations",
)
# These SQL statements are part of the frozen additive migration checksum.
SQL += tuple(
    f"CREATE TRIGGER IF NOT EXISTS {table}_immutable_{action.lower()} BEFORE {action} ON {table} BEGIN SELECT RAISE(ABORT,'audit provenance is immutable'); END"
    for table in AUDIT_TABLES
    for action in ("UPDATE", "DELETE")
)


def initialize(conn):
    for statement in SQL:
        conn.execute(statement)
