# Changelog

## 1.1.0

- Neuer Reiter **Direktsteuerung**: findet DALI-2-Taster/-Melder (IEC 62386-103), zeigt pro Gerät, ob es ausfallsicher (Application Controller aktiv) arbeitet, und schaltet Direktmodus und Ereignismeldungen je Eingang
- Busversorgungs-Check (eigenes DALI-Netzteil oder über das Gateway)
- „Mitgelesene Direktbefehle“: zeigt Befehle anderer Busteilnehmer (Taster im Direktmodus) mit Ziel und Häufigkeit
- Geräteidentifikation über Memory Bank 0 (Hersteller, GTIN, Firmware, Seriennummer)
- Proxy: schnelle, verständliche Fehlermeldung, wenn das Gateway nicht erreichbar ist
- Oberfläche lädt nach einem Add-on-Update automatisch neu

## 1.0.0

- Erste Version: Verwaltungsoberfläche (DE/EN) für das Lunatone DALI-2 IoT (FW 1.17.1/1.4.6)
- Live-Busmonitor mit IEC 62386-Dekodierung, Buslast- und Kommunikationsanalyse
- Gateway-Automationen (Sequenzen, Zeitpläne, Circadian, Trigger-Aktionen, Event-Weiterleitung)
- Automatische Erkennung von DALI-2-Tastern/-Meldern aus Bus-Events
- Supervisor-Discovery für die Integration `lunatone_dali`
