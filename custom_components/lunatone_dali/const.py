"""Constants for the Lunatone DALI-2 IoT integration."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "lunatone_dali"
MANUFACTURER: Final = "Lunatone"

CONF_EXPOSE_GROUPS: Final = "expose_groups"
CONF_EXPOSE_BROADCAST: Final = "expose_broadcast"
CONF_SCAN_INTERVAL: Final = "scan_interval"
CONF_DEFAULT_TRANSITION: Final = "default_transition"
CONF_MIN_KELVIN: Final = "min_kelvin"
CONF_MAX_KELVIN: Final = "max_kelvin"
CONF_LEARN_INPUTS: Final = "learn_inputs"

DEFAULT_SCAN_INTERVAL: Final = 60  # seconds, fallback polling while websocket is up
DISCONNECTED_SCAN_INTERVAL: Final = 10  # seconds, polling while websocket is down
DEFAULT_MIN_KELVIN: Final = 2700
DEFAULT_MAX_KELVIN: Final = 6500
EXTRAS_INTERVAL: Final = 900  # seconds, energy/diagnostics refresh

# DALI device types (IEC 62386-2xx) → readable names
DALI_TYPES: Final[dict[int, str]] = {
    0: "Fluorescent lamp",
    1: "Emergency lighting",
    2: "Discharge lamp",
    3: "Low voltage halogen",
    4: "Incandescent dimmer",
    5: "1-10 V converter",
    6: "LED module",
    7: "Switching function",
    8: "Colour control",
    15: "Load referencing",
    16: "Thermal gear protection",
    17: "Dimming curve selection",
    20: "Demand response",
    21: "Thermal lamp protection",
    49: "Integrated bus power supply",
    50: "Memory bank 1 extension",
    51: "Energy reporting",
    52: "Diagnostics & maintenance",
    53: "Control gear load",
}

DT_ENERGY: Final = 51
DT_DIAGNOSTICS: Final = 52

SIGNAL_INPUT_EVENT: Final = f"{DOMAIN}_input_event_{{}}"
SIGNAL_NEW_INPUT: Final = f"{DOMAIN}_new_input_{{}}"
EVENT_DALI_INPUT: Final = f"{DOMAIN}_input"

STORAGE_VERSION: Final = 1
