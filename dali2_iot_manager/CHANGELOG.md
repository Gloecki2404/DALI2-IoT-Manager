# Changelog

## 2.1.0

**Gerätenamen und Entitäten überstehen einen DALI-Scan**

- Ein Scan kann Geräten neue Kurzadressen geben – auch ohne Neuinstallation, weil das Gateway doppelt vergebene Adressen auflöst. Das Add-on sichert deshalb vor jedem Scan die Gerätenamen, zugeordnet über die Seriennummer im Gerät (Speicherbank 0: GTIN + Identifikationsnummer), und gibt jedem Gerät danach seinen Namen zurück. Auch manuell unter *DALI-Bus → Scan*.
- Integration: Leuchten werden über GTIN + Identifikationsnummer identifiziert statt über Linie/Adresse. Entitäten, Namen, Räume und Automationen bleiben am physischen Gerät, wenn es eine neue Adresse bekommt. Bestehende Installationen werden automatisch umgestellt (Entitäts-IDs bleiben gleich).

**Ausfallsicherheit**

- Neu: *Verhalten der Leuchten bei Ausfall* (Reiter Direktsteuerung) – Level bei Busausfall und nach Netzwiederkehr für alle Leuchten lesen und setzen. In der Integration als Attribute `system_failure_level` / `power_on_level` und Aktion `dali2_iot.set_failsafe_levels`.
- Direktsteuerung: **alle genormten Einstellungen der Taster und Melder** – derselbe Umfang wie in DALI Cockpit (IEC 62386-103/301/303/304):
  - je Eingang: Ereignisse an/aus, Ereignisschema, Priorität, Instanzgruppen, Ereignisfilter sowie die Zeiten (Taster: kurzer Druck, Doppelklick, Wiederholrate, Klemmen; Präsenz: Halte-, Report-, Totzeit; Licht: Report-, Totzeit, Hysterese, Hysterese-Minimum) in ms/s statt Rohwerten
  - je Gerät: Power-Cycle-Meldung, alle Eingänge an/aus, Gerätegruppen 0–31, Kurzadresse ändern (mit Prüfung an der neuen Adresse) und RESET auf Standardwerte (Expertenmodus)
  - Eingänge, deren Ereignisse nicht unterscheidbar sind, werden markiert; „Ereignisse an Gateway/HA“ berücksichtigt Ereignisfilter und Ruhemodus
- Integration: sucht DALI-2-Taster und -Melder selbst (Button *Steuergeräte suchen*, automatisch beim ersten Start und nach jedem Scan), legt ihre Ereignis-Entitäten schon vor dem ersten Tastendruck an und zeigt je Gerät *Ausfallsichere Direktsteuerung* an.
- Integration: Präsenzmelder mit Ereignisschema „Instanz“ (ohne Adresse) aktualisieren jetzt auch den Präsenz-Sensor des Gateways, der sonst stehen bleibt.

**Korrekturen nach IEC 62386 (Abgleich mit der Norm)**

- Busmonitor: Instanzbefehle (Taster-, Präsenz-, Lichtsensor-Timer usw.) werden richtig benannt statt als Gerätebefehle; Instanzbyte nach Tabelle 9 dekodiert; Power-Cycle-Meldungen über die Bitmaske erkannt (vorher teilweise mit Instanzgruppen-Ereignissen verwechselt); DIRECT WRITE MEMORY, DTR1:DTR0, DTR2:DTR1; READ MEMORY LOCATION wird als Abfrage erkannt und seine Antwort zugeordnet; 25-Bit-Frames als eDALI.
- Adressierung auf dem Bus (RANDOMISE, PROGRAM SHORT ADDRESS) wird im Busmonitor rot markiert und im Ereignisprotokoll gewarnt – egal ob vom Gateway oder einem anderen Werkzeug. Ein bloßes INITIALISE (sendet z. B. DALI Cockpit vor jedem Auslesen) löst keine Warnung aus.
- „Identifizieren“ in der Gerätedetailansicht wird wie vorgeschrieben doppelt gesendet.
- Präsenzmelder: Bewegung zählt als „belegt“; Wiederholungen und Bewegungsmeldungen ohne Zustandswechsel erzeugen keine HA-Ereignisse mehr. Ereignisse im Schema „Gerät + Instanz“ (ohne Instanztyp) werden über eine einmalige Abfrage zugeordnet.
- Buslast: Pausen zwischen den Abfragen der Steuergeräte-Suche; höchstens 16 Befehle pro Gateway-Anfrage.
- Hersteller-Erkennung über GTIN: Tridonic ergänzt.
- Einstellungen an Steuergeräten werden wie bei DALI Cockpit mit SAVE PERSISTENT VARIABLES sofort dauerhaft gespeichert.
- Busmonitor: Ereignisse im Schema „Gerät + Instanz“ zeigen den Instanztyp (z. B. „Präsenzmelder: frei“) aus der Steuergeräte-Suche.

## 2.0.1

- **Wichtig:** Ein-/Ausschalten der Ereignismeldungen je Eingang (Reiter Direktsteuerung) hat den falschen DALI-Befehl gesendet (SET EVENT PRIORITY statt ENABLE/DISABLE INSTANCE). Korrigiert nach IEC 62386-103; „Identifizieren“ wird jetzt wie vorgeschrieben doppelt gesendet.
- Ereignisse ohne Geräteadresse (Ereignisschema „Instanz“, z. B. bei vielen Präsenzmeldern) werden korrekt dekodiert – vorher als „Gerätegruppe“ fehlinterpretiert
- Präsenz-Ereignisse zeigen zusätzlich Wiederholung und Sensortyp
- Integration: lernt nur noch Taster und Präsenzmelder als Ereignisse (keine sekündlichen Helligkeitswerte), überspringt wiederholte Präsenzmeldungen und ordnet adresslose Ereignisse über die Sensorliste des Gateways dem richtigen Gerät zu

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
