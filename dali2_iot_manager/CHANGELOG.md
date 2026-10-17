# Changelog

## 2.0.0

- Neuer Name: **DALI-2 IoT Manager** (Add-on und Integration), nicht mehr herstellergebunden benannt
- Technische Kennungen geändert: Add-on-Slug `dali2_iot_manager`, Integrations-Domain `dali2_iot`
- Lizenz: MIT; Lizenzhinweise der mitgelieferten Bibliotheken in `THIRD_PARTY_NOTICES.md`

**Umstieg von 1.x** (nur nötig, wenn die alte Version schon installiert war):
1. Altes Add-on „Lunatone DALI-2 IoT Manager“ deinstallieren und *DALI-2 IoT Manager* neu installieren (Verlauf/Analysen beginnen neu).
2. Alte Integration „Lunatone DALI-2 IoT“ unter *Geräte & Dienste* löschen, den Ordner `custom_components/lunatone_dali` entfernen, *DALI-2 IoT Manager* installieren und neu einrichten. Entitäts-IDs in Automationen ggf. anpassen.

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
- Supervisor-Discovery für die Integration `dali2_iot`
