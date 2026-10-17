import { ref } from "vue";

export type Lang = "de" | "en";
type Dict = Record<string, string>;
export type Messages = { de: Dict; en: Dict };

function detectLang(): Lang {
  try {
    const stored = localStorage.getItem("lunatone.lang");
    if (stored === "de" || stored === "en") return stored;
  } catch {
    /* storage unavailable */
  }
  try {
    const hass = (window.parent?.document?.querySelector("home-assistant") as any)?.hass;
    const l = hass?.language || hass?.locale?.language;
    if (l) return String(l).startsWith("de") ? "de" : "en";
  } catch {
    /* not same origin */
  }
  return navigator.language?.startsWith("de") ? "de" : "en";
}

export const lang = ref<Lang>(detectLang());

export function setLang(l: Lang) {
  lang.value = l;
  try {
    localStorage.setItem("lunatone.lang", l);
  } catch {
    /* ignore */
  }
}

const common: Messages = {
  de: {
    save: "Speichern",
    cancel: "Abbrechen",
    close: "Schließen",
    delete: "Löschen",
    edit: "Bearbeiten",
    add: "Hinzufügen",
    create: "Anlegen",
    refresh: "Aktualisieren",
    confirm: "Bestätigen",
    on: "Ein",
    off: "Aus",
    yes: "Ja",
    no: "Nein",
    name: "Name",
    enabled: "Aktiv",
    disabled: "Inaktiv",
    start: "Start",
    stop: "Stopp",
    loading: "Lade…",
    saved: "Gespeichert",
    error: "Fehler",
    none: "Keine",
    all: "Alle",
    line: "Linie",
    address: "Adresse",
    group: "Gruppe",
    groups: "Gruppen",
    device: "Gerät",
    devices: "Geräte",
    zone: "Zone",
    zones: "Zonen",
    broadcast: "Broadcast",
    brightness: "Helligkeit",
    colorTemp: "Farbtemperatur",
    color: "Farbe",
    scene: "Szene",
    scenes: "Szenen",
    fadeTime: "Fadezeit",
    fadeRate: "Faderate",
    available: "Erreichbar",
    unavailable: "Nicht erreichbar",
    status: "Status",
    search: "Suchen…",
    noData: "Keine Daten vorhanden",
    seconds: "s",
    hours: "Std.",
    days: "Tage",
    minutes: "Min.",
    actions: "Aktionen",
    targets: "Ziele",
    details: "Details",
    type: "Typ",
    value: "Wert",
    time: "Zeit",
    expertMode: "Expertenmodus",
    reconnecting: "Verbindung wird aufgebaut…",
    gatewayOffline: "Gateway nicht erreichbar",
    live: "Live",
  },
  en: {
    save: "Save",
    cancel: "Cancel",
    close: "Close",
    delete: "Delete",
    edit: "Edit",
    add: "Add",
    create: "Create",
    refresh: "Refresh",
    confirm: "Confirm",
    on: "On",
    off: "Off",
    yes: "Yes",
    no: "No",
    name: "Name",
    enabled: "Enabled",
    disabled: "Disabled",
    start: "Start",
    stop: "Stop",
    loading: "Loading…",
    saved: "Saved",
    error: "Error",
    none: "None",
    all: "All",
    line: "Line",
    address: "Address",
    group: "Group",
    groups: "Groups",
    device: "Device",
    devices: "Devices",
    zone: "Zone",
    zones: "Zones",
    broadcast: "Broadcast",
    brightness: "Brightness",
    colorTemp: "Colour temperature",
    color: "Colour",
    scene: "Scene",
    scenes: "Scenes",
    fadeTime: "Fade time",
    fadeRate: "Fade rate",
    available: "Reachable",
    unavailable: "Unreachable",
    status: "Status",
    search: "Search…",
    noData: "No data available",
    seconds: "s",
    hours: "h",
    days: "days",
    minutes: "min",
    actions: "Actions",
    targets: "Targets",
    details: "Details",
    type: "Type",
    value: "Value",
    time: "Time",
    expertMode: "Expert mode",
    reconnecting: "Connecting…",
    gatewayOffline: "Gateway not reachable",
    live: "Live",
  },
};

function format(s: string, params?: Record<string, unknown>): string {
  if (!params) return s;
  return s.replace(/\{(\w+)\}/g, (_, k) => (params[k] !== undefined ? String(params[k]) : `{${k}}`));
}

/** Returns a translate function; local messages override the common ones. */
export function useT(local?: Messages) {
  return (key: string, params?: Record<string, unknown>): string => {
    const l = lang.value;
    const s = local?.[l]?.[key] ?? common[l][key] ?? local?.en?.[key] ?? common.en[key] ?? key;
    return format(s, params);
  };
}
