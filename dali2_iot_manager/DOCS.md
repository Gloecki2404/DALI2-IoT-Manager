# DALI-2 IoT Manager

Verwaltungsoberfläche für DALI-2-Anlagen direkt in Home Assistant. Unterstütztes Gateway: **Lunatone DALI-2 IoT**.

## Funktionen

- **Übersicht** – Status, Fehler, Live-Busaktivität, Schnellsteuerung, letzte Ereignisse
- **Geräte** – Steuerung (Helligkeit, Farbtemperatur, Farbe), Name, Gruppen, Fadezeit/-rate, Szenen 0–15, DALI-Parameter (Min/Max/Einschalt-/Notlevel), Identifizieren
- **Gruppen & Zonen** – Gruppen-Matrix (Geräte × 16 Gruppen), Zonen anlegen/bearbeiten
- **Sensoren & Taster** – Gateway-Sensoren mit Verlauf, automatisch gelernte DALI-2-Eingänge
- **Direktsteuerung** – Taster/Melder, die Leuchten direkt über den Bus steuern (auch bei Ausfall von Gateway/HA): Ausfallsicherheits-Check, Direktmodus (Application Controller) und Ereignismeldungen je Eingang schalten, mitgelesene Direktbefehle. Die Zuordnung Taster → Gruppe/Befehl ist herstellerspezifisch und wird mit dem Herstellerwerkzeug gesetzt (Lunatone: DALI Cockpit über dieses Gateway oder NFC-App).
- **Automationen** – Sequenzen, Zeitpläne (inkl. Sonnenzeiten), Circadian-Verläufe, Trigger-Aktionen, Event-Weiterleitung, Statusabfragen
- **DALI-Bus** – Live-Busmonitor mit Dekodierung nach IEC 62386, CSV-Export, Scan, Linienstatus, Rohbefehle (Expertenmodus)
- **Analysen** – Gesundheitsbericht, Buslast, Kommunikationsqualität je Adresse, Einschaltdauer & Schaltzyklen, Energie & Diagnose, Ereignisprotokoll
- **System** – Name, Datum/Zeitzone, Standort, Einstellungen, Sicherung & Wiederherstellung, Neustart
- **Expertenbereich** – Netzwerk, Firmware-Update, DALI-Makros, Löschen, Werksreset (mit doppelter Bestätigung)

## Konfiguration

| Option | Beschreibung |
|--------|--------------|
| `gateway_host` | IP/Hostname des Gateways. Leer = automatische Suche im lokalen Netz. |
| `history_days` | Aufbewahrung von Verlauf, Statistiken und Messwerten (Standard 30 Tage). |
| `monitor_buffer` | Anzahl gespeicherter Busframes für den Busmonitor (Standard 100 000). |
| `log_level` | Log-Ausführlichkeit. |

Nach dem Verbinden meldet das Add-on das Gateway an Home Assistant – die Integration **DALI-2 IoT Manager** erscheint dann unter *Geräte & Dienste* als „Entdeckt“ (die Integration muss dafür nach `/config/custom_components/dali2_iot` kopiert sein).

## Daten

Alle Verlaufsdaten liegen in `/data/lunatone.db` (SQLite) und sind in HA-Backups des Add-ons enthalten.
