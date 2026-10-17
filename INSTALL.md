# Lunatone DALI-2 IoT für Home Assistant – Installation

Dieses Paket enthält zwei Teile, die unabhängig voneinander funktionieren, aber zusammen am meisten bringen:

| Teil | Ordner | Zweck |
|------|--------|-------|
| **Add-on „Lunatone DALI-2 IoT Manager“** | `lunatone_dali_manager/` | Oberfläche in der HA-Seitenleiste: alle Einstellungen, Gruppen/Zonen, Szenen, Gateway-Automationen, DALI-Scan, Busmonitor, Analysen, Backup, Firmware |
| **Integration „Lunatone DALI-2 IoT“** (`lunatone_dali`) | `custom_components/lunatone_dali/` | Stellt alle DALI-Teilnehmer automatisch als Entitäten bereit: Leuchten, Gruppen, Sensoren, Taster/Melder, Energie & Diagnose, Gateway-Status |

Voraussetzungen: Home Assistant OS oder Supervised (für das Add-on), HA 2025.1 oder neuer (getestet mit 2026.9), Gateway Lunatone DALI-2 IoT (getestet mit FW v1.17.1/1.4.6).

---

## Variante 0 – über GitHub (empfohlen, mit Updates per Klick)

- **Add-on:** *Einstellungen → Add-ons → Add-on-Store → ⋮ → Repositories* → `https://github.com/Gloecki2404/Lunatone-Dali-Addon` hinzufügen, dann *Lunatone DALI-2 IoT Manager* installieren.
- **Integration:** in HACS *⋮ → Benutzerdefinierte Repositories* → dieselbe URL, Typ *Integration* → *Lunatone DALI-2 IoT* herunterladen → HA neu starten.
- Neue Versionen erscheinen danach automatisch unter *Einstellungen → Updates*.

Die folgenden Varianten sind für eine Installation ohne GitHub.

## Variante A – mit Skript (Windows)

1. In Home Assistant das offizielle Add-on **Samba share** installieren, ein Passwort setzen und starten.
2. PowerShell im Projektordner öffnen und ausführen:
   ```powershell
   .\install.ps1 -HaHost homeassistant.local
   ```
   Fragt Windows nach Zugangsdaten, alternativ `-User homeassistant` angeben (Benutzer/Passwort aus dem Samba-Add-on).
3. Weiter mit **„Nach dem Kopieren“**.

## Variante B – manuell kopieren

Mit Samba, dem Add-on „File editor“/„Studio Code Server“ oder per SSH:

- Ordner `lunatone_dali_manager` → nach **`/addons/lunatone_dali_manager`**
- Ordner `custom_components/lunatone_dali` → nach **`/config/custom_components/lunatone_dali`**

Eine fertige ZIP-Datei mit genau dieser Struktur erzeugt `.\install.ps1 -Zip` (→ `dist/lunatone_dali_ha.zip`).

## Nach dem Kopieren

1. **Add-on installieren:** *Einstellungen → Add-ons → Add-on-Store* → Menü (⋮) → **Nach Updates suchen**.
   Unter **Lokale Add-ons** erscheint *Lunatone DALI-2 IoT Manager* → **Installieren** (das Image wird lokal gebaut, ca. 1–3 Minuten).
2. Optional im Reiter *Konfiguration* die **Gateway-Adresse** eintragen (z. B. `192.168.0.236`). Leer lassen = automatische Suche im Netzwerk.
3. Add-on **starten**, *In Seitenleiste anzeigen* aktivieren → Menüpunkt **DALI-2 IoT**.
4. **Home Assistant neu starten** (nötig, damit die Integration geladen wird).
5. Unter *Einstellungen → Geräte & Dienste* wird **Lunatone DALI-2 IoT** als *Entdeckt* angeboten (vom Add-on gemeldet) → **Konfigurieren**.
   Ohne Add-on: *Integration hinzufügen* → „Lunatone DALI-2 IoT“ → *Netzwerk durchsuchen* oder IP eingeben.

## Was man danach bekommt

**Integration (Entitäten):**
- `light.*` für jedes DALI-Betriebsgerät (an/aus, Helligkeit, Farbtemperatur bei DT8, RGB/XY falls unterstützt, Überblendzeit)
- `light.*` für jede belegte DALI-Gruppe; Broadcast (alle Leuchten) optional
- Diagnose-Binärsensoren je Leuchte: Lampenfehler, Betriebsgerätefehler, Erreichbar (+ optional Grenzwertfehler, Netzunterbrechung, …)
- Gateway-Sensoren (Präsenz, Helligkeit, Temperatur, Feuchte, CO₂, VOC …) als `sensor`/`binary_sensor`
- DALI-2-Taster und -Melder werden **automatisch gelernt**, sobald sie ein Ereignis senden → `event.*`-Entitäten + Geräte-Auslöser im Automations-Editor (kurz, doppelt, lang …)
- Energie (DT51, fürs Energie-Dashboard) und Diagnose/Wartung (DT52: Betriebsstunden, Temperaturen, Spannung …), falls die Geräte das können
- Gateway: Live-Verbindung, Linienstatus, Scan-Status, Anzahl Geräte/Fehler/eingeschaltet, Schalter für DALI-Ping und Gateway-Automationen, Buttons (Aktualisieren, Scan, Neustart)
- Aktionen (Services): `lunatone_dali.recall_scene`, `save_scene`, `dim_up`, `dim_down`, `goto_last_active`, `set_fade_time`, `set_fade_rate`, `set_color_waf`, `send_raw_control`, `start_scan`, `send_dali16`, `send_dali24` (mit Antwort), `refresh`

**Add-on (Oberfläche):** Übersicht, Geräte (Steuerung, Name, Gruppen, Fade, Szenen 0–15, DALI-Parameter wie Min/Max/Einschaltlevel, Identifizieren), Gruppen-Matrix & Zonen, Sensoren & gelernte Taster, Gateway-Automationen (Sequenzen, Zeitpläne, Circadian, Trigger-Aktionen, Event-Weiterleitung, Statusabfragen), DALI-Bus (Live-Busmonitor mit Klartext-Dekodierung, Scan, Linien, Rohbefehle), Analysen (Gesundheit, Buslast, Kommunikationsqualität, Nutzung/Einschaltdauer, Energie & Diagnose, Ereignisse), System (Name, Zeit/Zeitzone, Standort, Einstellungen, Backup/Restore), Expertenbereich (Netzwerk, Firmware, Makros, Löschen, Werksreset).

## Hinweise

- Die offizielle HA-Integration **„Lunatone“** nicht zusätzlich für dasselbe Gateway einrichten (doppelte Entitäten).
- Die **Farbtemperatur** meldet das Gateway bei manchen DT8-Geräten nicht zurück – die Integration zeigt dann den zuletzt gesendeten Wert an.
- **Zeitzone:** Viele Gateways stehen ab Werk auf `Etc/UTC`. Das Add-on zeigt unter *System → Datum & Uhrzeit* einen Hinweis und übernimmt auf Wunsch die HA-Zeitzone (wichtig für Zeitpläne mit Sonnenauf-/-untergang).
- Updates: neue Version genauso kopieren; beim Add-on anschließend *Neu erstellen* (Rebuild), bei der Integration HA neu starten.

## Checkliste für den ersten Test auf HA OS

- [ ] Add-on startet, Log zeigt „Connected to gateway websocket …“
- [ ] Seitenleiste „DALI-2 IoT“ öffnet die Oberfläche im HA-Design (hell/dunkel)
- [ ] Integration wird als „Entdeckt“ angeboten und lässt sich einrichten
- [ ] Leuchten schalten/dimmen aus HA; Änderungen am Wandtaster erscheinen sofort in HA
- [ ] Taster einmal drücken → erscheint unter *Sensoren & Taster* und als `event.*`-Entität
