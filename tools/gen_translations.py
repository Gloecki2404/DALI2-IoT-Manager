"""Generate strings.json / translations for the dali2_iot integration.

Run: python tools/gen_translations.py
"""

import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1] / "custom_components" / "dali2_iot"

BUTTON_EV = {
    "released": ("Released", "Losgelassen"),
    "pressed": ("Pressed", "Gedrückt"),
    "short_press": ("Short press", "Kurz gedrückt"),
    "double_press": ("Double press", "Doppelt gedrückt"),
    "long_press_start": ("Long press start", "Langer Druck Start"),
    "long_press_repeat": ("Long press repeat", "Langer Druck Wiederholung"),
    "long_press_stop": ("Long press stop", "Langer Druck Ende"),
    "button_free": ("Button free", "Taster frei"),
    "button_stuck": ("Button stuck", "Taster klemmt"),
}
OCC_EV = {"occupied": ("Occupied", "Belegt"), "vacant": ("Vacant", "Frei")}


def T(en, de):
    return (en, de)


ENTITY = {
    "light": {
        "broadcast": T("Broadcast (all lights)", "Broadcast (alle Leuchten)"),
        "group": T("DALI group {number}", "DALI-Gruppe {number}"),
    },
    "binary_sensor": {
        "lamp_failure": T("Lamp failure", "Lampenfehler"),
        "gear_failure": T("Control gear failure", "Betriebsgerätefehler"),
        "limit_error": T("Limit error", "Grenzwertfehler"),
        "power_cycle_seen": T("Power cycle seen", "Netzunterbrechung erkannt"),
        "reset_state": T("Reset state", "Reset-Zustand"),
        "lamp_on": T("Lamp on", "Lampe an"),
        "reachable": T("Reachable", "Erreichbar"),
        "websocket": T("Live connection", "Live-Verbindung"),
        "line_problem": T("DALI line {line} problem", "DALI-Linie {line} Problem"),
        "diag_gear_overall_failure": T("Gear overall failure", "Betriebsgerät Gesamtfehler"),
        "diag_undervoltage": T("Supply undervoltage", "Unterspannung Versorgung"),
        "diag_overvoltage": T("Supply overvoltage", "Überspannung Versorgung"),
        "diag_power_limitation": T("Output power limitation", "Leistungsbegrenzung"),
        "diag_gear_thermal_derating": T("Gear thermal derating", "Betriebsgerät thermische Reduktion"),
        "diag_gear_thermal_shutdown": T("Gear thermal shutdown", "Betriebsgerät Übertemperaturabschaltung"),
        "diag_light_overall_failure": T("Light source failure", "Leuchtmittel Gesamtfehler"),
        "diag_short_circuit": T("Light source short circuit", "Leuchtmittel Kurzschluss"),
        "diag_open_circuit": T("Light source open circuit", "Leuchtmittel Leerlauf"),
        "diag_light_thermal_derating": T("Light source thermal derating", "Leuchtmittel thermische Reduktion"),
        "diag_light_thermal_shutdown": T("Light source thermal shutdown", "Leuchtmittel Übertemperaturabschaltung"),
    },
    "sensor": {
        "active_energy": T("Energy", "Energie"),
        "active_power": T("Power", "Leistung"),
        "apparent_energy": T("Apparent energy", "Scheinenergie"),
        "apparent_power": T("Apparent power", "Scheinleistung"),
        "loadside_energy": T("Load side energy", "Energie lastseitig"),
        "loadside_power": T("Load side power", "Leistung lastseitig"),
        "gear_operating_time": T("Gear operating time", "Betriebszeit Betriebsgerät"),
        "gear_start_counter": T("Gear starts", "Starts Betriebsgerät"),
        "supply_voltage": T("Supply voltage", "Versorgungsspannung"),
        "supply_frequency": T("Supply frequency", "Netzfrequenz"),
        "power_factor": T("Power factor", "Leistungsfaktor"),
        "gear_temperature": T("Gear temperature", "Temperatur Betriebsgerät"),
        "output_current": T("Output current", "Ausgangsstrom"),
        "light_start_counter": T("Light source starts", "Starts Leuchtmittel"),
        "light_start_counter_resettable": T("Light source starts (resettable)", "Starts Leuchtmittel (rücksetzbar)"),
        "light_on_time": T("Light source on time", "Brenndauer Leuchtmittel"),
        "light_on_time_resettable": T("Light source on time (resettable)", "Brenndauer Leuchtmittel (rücksetzbar)"),
        "light_voltage": T("Light source voltage", "Spannung Leuchtmittel"),
        "light_current": T("Light source current", "Strom Leuchtmittel"),
        "light_temperature": T("Light source temperature", "Temperatur Leuchtmittel"),
        "rated_life": T("Rated median useful life", "Nennlebensdauer"),
        "rated_starts": T("Rated light source starts", "Nennschaltzyklen"),
        "line_status": T("DALI line {line} status", "DALI-Linie {line} Status"),
        "scan_status": T("DALI scan", "DALI-Scan"),
        "scan_progress": T("DALI scan progress", "DALI-Scan Fortschritt"),
        "devices_total": T("DALI devices", "DALI-Geräte"),
        "devices_unavailable": T("Unreachable devices", "Nicht erreichbare Geräte"),
        "devices_failure": T("Devices with failure", "Geräte mit Fehler"),
        "lights_on": T("Lights on", "Eingeschaltete Leuchten"),
    },
    "switch": {
        "dali_ping": T("DALI ping", "DALI-Ping"),
        "log_file": T("Log file", "Logdatei"),
        "automation_sequence": T("Sequence {name}", "Sequenz {name}"),
        "automation_scheduler": T("Schedule {name}", "Zeitplan {name}"),
        "automation_circadian": T("Circadian {name}", "Circadian {name}"),
        "automation_triggerAction": T("Trigger action {name}", "Trigger-Aktion {name}"),
    },
    "button": {
        "refresh": T("Refresh", "Aktualisieren"),
        "refresh_sensors": T("Refresh sensors", "Sensoren aktualisieren"),
        "scan": T("Start DALI scan", "DALI-Scan starten"),
    },
    "event": {
        "push_button": T("Button {instance}", "Taster {instance}"),
        "occupancy_event": T("Occupancy {instance}", "Präsenz {instance}"),
        "light_event": T("Light sensor {instance}", "Lichtsensor {instance}"),
        "generic_event": T("Input {instance}", "Eingang {instance}"),
    },
}
STATES = {
    ("sensor", "line_status"): {
        "ok": T("OK", "OK"),
        "lowPower": T("Low bus power", "Geringe Busspannung"),
        "noPower": T("No bus power", "Keine Busspannung"),
        "notReachable": T("Not reachable", "Nicht erreichbar"),
    },
    ("sensor", "scan_status"): {
        "not_started": T("Not started", "Nicht gestartet"),
        "cancelled": T("Cancelled", "Abgebrochen"),
        "done": T("Done", "Fertig"),
        "addressing": T("Addressing", "Adressierung"),
        "in_progress": T("In progress", "Läuft"),
        "bus_error": T("Bus error", "Busfehler"),
    },
}
EVENT_STATES = {"push_button": BUTTON_EV, "occupancy_event": OCC_EV}

SERVICES = {
    "recall_scene": (
        T("Recall scene", "Szene aufrufen"),
        T("Recall a DALI scene (0-15).", "Ruft eine DALI-Szene (0-15) auf."),
        {"scene": T("Scene", "Szene"), "transition": T("Transition", "Überblendzeit")},
    ),
    "save_scene": (
        T("Save scene", "Szene speichern"),
        T("Store the current level/colour as DALI scene.", "Speichert den aktuellen Zustand als DALI-Szene."),
        {"scene": T("Scene", "Szene")},
    ),
    "dim_up": (T("Dim up", "Heller"), T("Send DALI UP commands.", "Sendet DALI-UP-Befehle."), {"steps": T("Steps", "Schritte")}),
    "dim_down": (T("Dim down", "Dunkler"), T("Send DALI DOWN commands.", "Sendet DALI-DOWN-Befehle."), {"steps": T("Steps", "Schritte")}),
    "goto_last_active": (
        T("Go to last active level", "Letzten Wert wiederherstellen"),
        T("Restore the last active level.", "Stellt den letzten aktiven Dimmwert wieder her."),
        {"transition": T("Transition", "Überblendzeit")},
    ),
    "set_fade_time": (
        T("Set fade time", "Fadezeit setzen"),
        T("Configure the DALI fade time of the gear.", "Setzt die DALI-Fadezeit im Betriebsgerät."),
        {"fade_time": T("Fade time", "Fadezeit")},
    ),
    "set_fade_rate": (
        T("Set fade rate", "Faderate setzen"),
        T("Configure the DALI fade rate (steps/s).", "Setzt die DALI-Faderate (Schritte/s)."),
        {"fade_rate": T("Fade rate", "Faderate")},
    ),
    "set_color_waf": (
        T("Set WAF colour", "WAF-Farbe setzen"),
        T("Set white/amber/free colour channels.", "Setzt die Farbkanäle Weiß/Amber/Frei."),
        {
            "white": T("White", "Weiß"),
            "amber": T("Amber", "Amber"),
            "free": T("Free colour", "Freie Farbe"),
            "brightness_pct": T("Brightness", "Helligkeit"),
        },
    ),
    "send_raw_control": (
        T("Send raw control", "Rohen Steuerbefehl senden"),
        T("Send a raw control payload (Lunatone ControlData).", "Sendet einen rohen Steuerbefehl (Lunatone ControlData)."),
        {"data": T("Data", "Daten")},
    ),
    "start_scan": (
        T("Start DALI scan", "DALI-Scan starten"),
        T("Search the DALI bus for devices.", "Durchsucht den DALI-Bus nach Geräten."),
        {
            "config_entry_id": T("Gateway", "Gateway"),
            "new_installation": T("New installation (re-address all)", "Neuinstallation (alle neu adressieren)"),
            "no_addressing": T("No addressing", "Ohne Adressierung"),
            "lines": T("Lines", "Linien"),
        },
    ),
    "send_dali16": (
        T("Send DALI 16 bit frame", "DALI-16-Bit-Frame senden"),
        T("Send a raw forward frame to control gear (IEC 62386-102).", "Sendet einen rohen Frame an Betriebsgeräte (IEC 62386-102)."),
        {
            "config_entry_id": T("Gateway", "Gateway"),
            "line": T("Line", "Linie"),
            "address": T("Address byte", "Adressbyte"),
            "command": T("Command byte", "Befehlsbyte"),
        },
    ),
    "send_dali24": (
        T("Send DALI 24 bit frame", "DALI-24-Bit-Frame senden"),
        T("Send a raw forward frame to control devices (IEC 62386-103).", "Sendet einen rohen Frame an Steuergeräte (IEC 62386-103)."),
        {
            "config_entry_id": T("Gateway", "Gateway"),
            "line": T("Line", "Linie"),
            "address": T("Address byte", "Adressbyte"),
            "instance": T("Instance byte", "Instanzbyte"),
            "command": T("Opcode byte", "Opcode-Byte"),
        },
    ),
    "refresh": (
        T("Refresh", "Aktualisieren"),
        T("Reload all data including energy and diagnostics.", "Lädt alle Daten inkl. Energie und Diagnose neu."),
        {"config_entry_id": T("Gateway", "Gateway")},
    ),
}

CONFIG = {
    "flow_title": T("{name}", "{name}"),
    "menu": T("How do you want to add the gateway?", "Wie soll das Gateway hinzugefügt werden?"),
    "manual": T("Enter address manually", "Adresse manuell eingeben"),
    "scan": T("Search the network", "Netzwerk durchsuchen"),
    "host": T("Host / IP address", "Host / IP-Adresse"),
    "host_desc": T(
        "IP address or hostname of the Lunatone DALI-2 IoT gateway, e.g. 192.168.0.236",
        "IP-Adresse oder Hostname des Lunatone DALI-2 IoT Gateways, z. B. 192.168.0.236",
    ),
    "scan_title": T("Gateways found", "Gefundene Gateways"),
    "gateway": T("Gateway", "Gateway"),
    "hassio_title": T("DALI-2 IoT Manager (via add-on)", "DALI-2 IoT Manager (über Add-on)"),
    "hassio_desc": T(
        "The DALI-2 IoT Manager add-on found the gateway **{name}** at {host}. Add it to Home Assistant?",
        "Das Add-on DALI-2 IoT Manager hat das Gateway **{name}** unter {host} gefunden. Zu Home Assistant hinzufügen?",
    ),
    "reconf_title": T("Change gateway address", "Gateway-Adresse ändern"),
    "cannot_connect": T(
        "Cannot connect to a DALI-2 IoT gateway at this address.",
        "Unter dieser Adresse ist kein DALI-2 IoT Gateway erreichbar.",
    ),
    "already_configured": T("This gateway is already configured.", "Dieses Gateway ist bereits eingerichtet."),
    "no_devices_found": T(
        "No DALI-2 IoT gateway found in the local network. Please enter the address manually.",
        "Im lokalen Netzwerk wurde kein DALI-2 IoT Gateway gefunden. Bitte die Adresse manuell eingeben.",
    ),
    "wrong_device": T("This is a different gateway.", "Das ist ein anderes Gateway."),
    "reconfigure_successful": T("The address was updated.", "Die Adresse wurde aktualisiert."),
    "opt_title": T("Options", "Optionen"),
    "expose_groups": T("DALI groups as lights", "DALI-Gruppen als Leuchten"),
    "expose_broadcast": T("Broadcast (all lights) as light", "Broadcast (alle Leuchten) als Leuchte"),
    "learn_inputs": T("Learn push buttons & sensors from bus events", "Taster & Sensoren aus Bus-Events lernen"),
    "default_transition": T("Default transition (0 = gateway fade time)", "Standard-Überblendzeit (0 = Fadezeit des Geräts)"),
    "min_kelvin": T("Warmest colour temperature", "Wärmste Farbtemperatur"),
    "max_kelvin": T("Coldest colour temperature", "Kälteste Farbtemperatur"),
    "scan_interval": T("Polling interval (fallback)", "Abfrageintervall (Fallback)"),
}

OPTION_KEYS = (
    "expose_groups",
    "expose_broadcast",
    "learn_inputs",
    "default_transition",
    "min_kelvin",
    "max_kelvin",
    "scan_interval",
)
ABORT_KEYS = ("already_configured", "cannot_connect", "no_devices_found", "wrong_device", "reconfigure_successful")


def build(i: int) -> dict:
    c = {k: v[i] for k, v in CONFIG.items()}
    host_step = {"data": {"host": c["host"]}, "data_description": {"host": c["host_desc"]}}
    out = {
        "config": {
            "flow_title": c["flow_title"],
            "step": {
                "user": {
                    "title": "DALI-2 IoT Manager",
                    "description": c["menu"],
                    "menu_options": {"manual": c["manual"], "scan": c["scan"]},
                },
                "manual": {"title": c["manual"], **host_step},
                "scan": {"title": c["scan_title"], "data": {"host": c["gateway"]}},
                "hassio_confirm": {"title": c["hassio_title"], "description": c["hassio_desc"]},
                "reconfigure": {"title": c["reconf_title"], **host_step},
            },
            "error": {"cannot_connect": c["cannot_connect"]},
            "abort": {k: c[k] for k in ABORT_KEYS},
        },
        "options": {"step": {"init": {"title": c["opt_title"], "data": {k: c[k] for k in OPTION_KEYS}}}},
        "entity": {},
        "services": {},
        "device_automation": {
            "trigger_type": {
                **{k: v[i] for k, v in BUTTON_EV.items()},
                **{k: v[i] for k, v in OCC_EV.items()},
                "event": ("Event", "Ereignis")[i],
            },
        },
    }
    for platform, items in ENTITY.items():
        out["entity"][platform] = {}
        for key, names in items.items():
            ent: dict = {"name": names[i]}
            if (platform, key) in STATES:
                ent["state"] = {s: v[i] for s, v in STATES[(platform, key)].items()}
            if platform == "event" and key in EVENT_STATES:
                ent["state_attributes"] = {
                    "event_type": {"state": {s: v[i] for s, v in EVENT_STATES[key].items()}}
                }
            out["entity"][platform][key] = ent
    for svc, (name, desc, fields) in SERVICES.items():
        out["services"][svc] = {
            "name": name[i],
            "description": desc[i],
            "fields": {f: {"name": n[i], "description": n[i]} for f, n in fields.items()},
        }
    return out


def main() -> None:
    en, de = build(0), build(1)
    (ROOT / "translations").mkdir(exist_ok=True)
    for path, data in (
        (ROOT / "strings.json", en),
        (ROOT / "translations" / "en.json", en),
        (ROOT / "translations" / "de.json", de),
    ):
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("ok")


if __name__ == "__main__":
    main()
