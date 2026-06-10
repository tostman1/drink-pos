# SumUp Solo Self-Checkout

Die Mitglieder-Selbstzahlung läuft über die normale Listenansicht. Name antippen, offene Posten prüfen und unten `Kartenzahlung starten` öffnen. `/self-pay` bleibt als Test- und Fallbackseite erhalten.

Der SumUp API Key liegt nur auf dem Server. Das Frontend bekommt nur öffentliche Statusinformationen und startet keine direkte SumUp-API-Anfrage.

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

1. SumUp Solo mit dem Internet verbinden und im Solo-Menü den API-/Pairing-Code anzeigen.
2. Server-ENV mindestens mit `PAYMENT_PROVIDER=sumup`, `SUMUP_API_KEY` und `SUMUP_MERCHANT_CODE` starten.
3. Pairing-Code an `POST /api/admin/sumup/pair-reader` senden.
4. Die zurückgegebene Reader-ID als `SUMUP_READER_ID` in `.env` setzen und Container neu starten.

Im Kartenzahlungs-Popup wird automatisch `Kartenzahlung +3 % (min. 0,20 €)` als zusätzliche
Zeile addiert. Danach muss eine Rundungsoption gewählt werden: `Nicht aufrunden` oder, sofern
sinnvoll, ein dynamisch berechnetes Ziel auf volle Euro, den nächsten 5er oder den nächsten 10er.
Der Button `Mit Karte zahlen` startet SumUp erst nach dieser Auswahl.

Die Kassaansicht `/kassa` zeigt dieselbe Kartenabrechnung im Zahlungsdialog für Kassierer.
`Bar buchen` bleibt eine normale Kassa-/Barbuchung ohne Kartengebühr, `Mit Karte zahlen`
startet die SumUp-Zahlung mit Gebühr und optionalem Aufrunden.

Eine Zahlung legt lokal eine `self_payment_sessions`-Zeile an. Doppelklicks oder wiederholte Requests mit derselben `client_payment_id` verwenden diese bestehende Session und starten keine zweite SumUp-Zahlung.

Nur ein eindeutig erfolgreicher SumUp-Status führt zu `PAID_SUMUP` und setzt die offenen Posten in einer SQLite-Transaktion auf bezahlt. Bei Fehler, Abbruch, Timeout oder unklarem Status bleiben die Posten offen.
