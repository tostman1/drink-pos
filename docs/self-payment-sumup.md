# SumUp Solo Self-Checkout

Die Mitglieder-Selbstzahlung laeuft ueber die normale Listenansicht. Name antippen, offene Posten pruefen und unten `Mit SumUp zahlen` starten. `/self-pay` bleibt als Test- und Fallbackseite erhalten.

Der SumUp API Key liegt nur auf dem Server. Das Frontend bekommt nur oeffentliche Statusinformationen und startet keine direkte SumUp-API-Anfrage.

Serverseitige ENV-Variablen:

```dotenv
PAYMENT_PROVIDER=sumup
SUMUP_API_BASE=https://api.sumup.com
SUMUP_API_KEY=
SUMUP_MERCHANT_CODE=
SUMUP_READER_ID=
SUMUP_AFFILIATE_KEY=
SUMUP_AFFILIATE_APP_ID=
SUMUP_CURRENCY=EUR
SUMUP_TIMEOUT_SECONDS=120
```

Reader koppeln:

1. SumUp Solo mit dem Internet verbinden und im Solo-Menue den API-/Pairing-Code anzeigen.
2. Server-ENV mindestens mit `PAYMENT_PROVIDER=sumup`, `SUMUP_API_KEY` und `SUMUP_MERCHANT_CODE` starten.
3. Pairing-Code an `POST /api/admin/sumup/pair-reader` senden.
4. Die zurueckgegebene Reader-ID als `SUMUP_READER_ID` in `.env` setzen und Container neu starten.

Eine Zahlung legt lokal eine `self_payment_sessions`-Zeile an. Doppelklicks oder wiederholte Requests mit derselben `client_payment_id` verwenden diese bestehende Session und starten keine zweite SumUp-Zahlung.

Nur ein eindeutig erfolgreicher SumUp-Status fuehrt zu `PAID_SUMUP` und setzt die offenen Posten in einer SQLite-Transaktion auf bezahlt. Bei Fehler, Abbruch, Timeout oder unklarem Status bleiben die Posten offen.
