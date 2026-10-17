// DALI related constants and helpers used across views.

export const DALI_TYPES: Record<number, { de: string; en: string }> = {
  0: { de: "Leuchtstofflampe", en: "Fluorescent lamp" },
  1: { de: "Notlicht", en: "Emergency lighting" },
  2: { de: "Entladungslampe", en: "Discharge lamp" },
  3: { de: "NV-Halogen", en: "Low voltage halogen" },
  4: { de: "Glühlampendimmer", en: "Incandescent dimmer" },
  5: { de: "1-10 V Wandler", en: "1-10 V converter" },
  6: { de: "LED-Modul", en: "LED module" },
  7: { de: "Schaltfunktion", en: "Switching function" },
  8: { de: "Farbsteuerung", en: "Colour control" },
  15: { de: "Lastreferenzierung", en: "Load referencing" },
  16: { de: "Thermischer Geräteschutz", en: "Thermal gear protection" },
  17: { de: "Dimmkurvenauswahl", en: "Dimming curve selection" },
  20: { de: "Demand Response", en: "Demand response" },
  21: { de: "Thermischer Lampenschutz", en: "Thermal lamp protection" },
  49: { de: "Integrierte Busversorgung", en: "Integrated bus power supply" },
  50: { de: "Speicherbank 1", en: "Memory bank 1 extension" },
  51: { de: "Energiemessung", en: "Energy reporting" },
  52: { de: "Diagnose & Wartung", en: "Diagnostics & maintenance" },
  53: { de: "Betriebsgerätelast", en: "Control gear load" },
};

// IEC 62386-102 fade time codes (seconds)
export const FADE_TIMES = [0, 0.7, 1.0, 1.4, 2.0, 2.8, 4.0, 5.7, 8.0, 11.3, 16.0, 22.6, 32.0, 45.3, 64.0, 90.5];
// IEC 62386-102 fade rate codes (steps per second)
export const FADE_RATES = [358, 253, 179, 127, 89.4, 63.3, 44.7, 31.6, 22.4, 15.8, 11.2, 7.9, 5.6, 4.0, 2.8];

export function status(features: Record<string, any> | undefined, key: string): any {
  const v = features?.[key];
  return v && typeof v === "object" ? v.status : undefined;
}

export function isOn(features: Record<string, any> | undefined): boolean {
  const sw = status(features, "switchable");
  if (sw !== undefined && sw !== null) return !!sw;
  return (status(features, "dimmable") ?? 0) > 0;
}

export function level(features: Record<string, any> | undefined): number {
  const l = status(features, "dimmable");
  if (typeof l === "number") return l;
  const dk = status(features, "dimmableKelvin");
  return typeof dk?.dimmable === "number" ? dk.dimmable : 0;
}

export function kelvin(features: Record<string, any> | undefined): number | null {
  const k = status(features, "colorKelvin");
  if (typeof k === "number") return k;
  const dk = status(features, "dimmableKelvin");
  return typeof dk?.kelvin === "number" ? dk.kelvin : null;
}

export function hasColorTemp(f: Record<string, any> | undefined) {
  return !!f && ("colorKelvin" in f || "dimmableKelvin" in f);
}
export function hasRGB(f: Record<string, any> | undefined) {
  return !!f && ("colorRGB" in f || "dimmableRGB" in f);
}
export function hasXY(f: Record<string, any> | undefined) {
  return !!f && ("colorXY" in f || "dimmableXY" in f);
}
export function hasWAF(f: Record<string, any> | undefined) {
  return !!f && ("colorWAF" in f || "dimmableWAF" in f);
}

/** Approximate colour of a colour temperature (for UI swatches). */
export function kelvinToRgb(k: number): string {
  const t = k / 100;
  let r: number, g: number, b: number;
  if (t <= 66) {
    r = 255;
    g = 99.47 * Math.log(t) - 161.12;
    b = t <= 19 ? 0 : 138.52 * Math.log(t - 10) - 305.04;
  } else {
    r = 329.7 * Math.pow(t - 60, -0.1332);
    g = 288.12 * Math.pow(t - 60, -0.0755);
    b = 255;
  }
  const c = (x: number) => Math.max(0, Math.min(255, Math.round(x)));
  return `rgb(${c(r)}, ${c(g)}, ${c(b)})`;
}

export function rgbToHex(r: number, g: number, b: number): string {
  const h = (x: number) => Math.round(Math.max(0, Math.min(1, x)) * 255).toString(16).padStart(2, "0");
  return `#${h(r)}${h(g)}${h(b)}`;
}

export function hexToRgb(hex: string): { r: number; g: number; b: number } {
  const m = hex.replace("#", "");
  return {
    r: parseInt(m.slice(0, 2), 16) / 255,
    g: parseInt(m.slice(2, 4), 16) / 255,
    b: parseInt(m.slice(4, 6), 16) / 255,
  };
}

export function fmtDuration(sec: number | null | undefined, lang: string): string {
  if (sec === null || sec === undefined) return "–";
  const h = Math.floor(sec / 3600);
  const m = Math.floor((sec % 3600) / 60);
  if (h >= 48) return `${Math.round(h / 24)} ${lang === "de" ? "Tage" : "days"}`;
  if (h > 0) return `${h} h ${m} min`;
  if (m > 0) return `${m} min`;
  return `${Math.round(sec)} s`;
}

export function fmtTime(ts: number, lang: string, withDate = true): string {
  const d = new Date(ts * 1000);
  return d.toLocaleString(lang === "de" ? "de-DE" : "en-GB", {
    ...(withDate ? { day: "2-digit", month: "2-digit" } : {}),
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

export function targetLabel(
  t: { type: string; id: number | null },
  devices: Record<number, any>,
  zones: Record<number, any>,
  tr: (k: string) => string,
): string {
  switch (t.type) {
    case "broadcast":
      return t.id === null || t.id === undefined ? tr("broadcast") : `${tr("broadcast")} (${tr("line")} ${t.id})`;
    case "group": {
      const id = Number(t.id);
      return id > 15 ? `${tr("group")} ${id % 16} (${tr("line")} ${Math.floor(id / 16)})` : `${tr("group")} ${id}`;
    }
    case "device":
      return devices[t.id as number]?.name ?? `${tr("device")} #${t.id}`;
    case "zone":
      return zones[t.id as number]?.name ?? `${tr("zone")} #${t.id}`;
    default:
      return `${t.type} ${t.id ?? ""}`;
  }
}
