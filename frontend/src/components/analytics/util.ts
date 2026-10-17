// Small helpers shared by the analytics tabs.
import { onBeforeUnmount } from "vue";

export const PALETTE = ["#03a9f4", "#ff9800", "#4caf50", "#e91e63", "#9c27b0", "#607d8b", "#00acc1", "#8d6e63"];

// consistent with the bus monitor kind colours
export const C = {
  command: "#1e88e5",
  query: "#ab47bc",
  backward: "#43a047",
  event: "#ef6c00",
  load: "#03a9f4",
};

export function cssVar(name: string, fallback: string): string {
  try {
    return getComputedStyle(document.documentElement).getPropertyValue(name).trim() || fallback;
  } catch {
    return fallback;
  }
}

/** Semantic colours from the (HA) theme, resolved for canvas use. */
export function themeColors() {
  return {
    primary: cssVar("--primary", "#03a9f4"),
    success: cssVar("--success", "#2e9e5b"),
    warning: cssVar("--warning", "#f5a623"),
    error: cssVar("--error", "#db4437"),
    text2: cssVar("--text2", "#5f6b7a"),
    text3: cssVar("--text3", "#9aa4b1"),
  };
}

/** Adds alpha to a #rgb/#rrggbb colour (other formats are returned unchanged). */
export function alpha(color: string, a: number): string {
  const m = color.trim().match(/^#([0-9a-f]{3}|[0-9a-f]{6})$/i);
  if (!m) {
    const rgb = color.match(/^rgba?\(([^)]+)\)$/i);
    if (rgb) {
      const [r, g, b] = rgb[1].split(",").map((x) => x.trim());
      return `rgba(${r}, ${g}, ${b}, ${a})`;
    }
    return color;
  }
  let h = m[1];
  if (h.length === 3) h = h.split("").map((c) => c + c).join("");
  const n = parseInt(h, 16);
  return `rgba(${(n >> 16) & 255}, ${(n >> 8) & 255}, ${n & 255}, ${a})`;
}

export function locale(lang: string) {
  return lang === "de" ? "de-DE" : "en-GB";
}

export function fmtNum(v: number | null | undefined, lang: string, digits = 0): string {
  if (v === null || v === undefined || Number.isNaN(v)) return "–";
  return v.toLocaleString(locale(lang), { minimumFractionDigits: digits, maximumFractionDigits: digits });
}

export function fmtPct(v: number | null | undefined, lang: string, digits = 1): string {
  if (v === null || v === undefined || Number.isNaN(v)) return "–";
  return `${fmtNum(v, lang, digits)} %`;
}

export function fmtDateTime(ts: number, lang: string): string {
  return new Date(ts * 1000).toLocaleString(locale(lang), { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });
}

export function fmtDay(ts: number, lang: string): string {
  const d = new Date(ts * 1000);
  const today = new Date();
  const yesterday = new Date(Date.now() - 86400000);
  const same = (a: Date, b: Date) => a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate();
  if (same(d, today)) return lang === "de" ? "Heute" : "Today";
  if (same(d, yesterday)) return lang === "de" ? "Gestern" : "Yesterday";
  return d.toLocaleDateString(locale(lang), { weekday: "long", day: "2-digit", month: "2-digit", year: "numeric" });
}

/** Runs fn every ms while the page is visible; stops on unmount. */
export function useInterval(fn: () => void, ms: number) {
  const id = window.setInterval(() => {
    if (document.visibilityState === "visible") fn();
  }, ms);
  onBeforeUnmount(() => clearInterval(id));
}

/** Download data as a file (client side). */
export function downloadJson(name: string, data: unknown) {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 2000);
}

/** Boolean flags of DiagnosticsMaintenanceData (IEC 62386-253) with their counters. */
export const DIAG_FLAGS: Record<string, { de: string; en: string; counter?: string }> = {
  controlGearOverallFailureCondition: { de: "Betriebsgerät: Sammelfehler", en: "Control gear: overall failure", counter: "controlGearOverallFailureConditionCounter" },
  controlGearExternalSupplyUndervoltage: { de: "Betriebsgerät: Unterspannung", en: "Control gear: supply undervoltage", counter: "controlGearExternalSupplyUndervoltageCounter" },
  controlGearExternalSupplyOvervoltage: { de: "Betriebsgerät: Überspannung", en: "Control gear: supply overvoltage", counter: "controlGearExternalSupplyOvervoltageCounter" },
  controlGearOutputPowerLimitation: { de: "Betriebsgerät: Leistungsbegrenzung", en: "Control gear: output power limitation", counter: "controlGearOutputPowerLimitationCounter" },
  controlGearThermalDerating: { de: "Betriebsgerät: thermische Leistungsreduktion", en: "Control gear: thermal derating", counter: "controlGearThermalDeratingCounter" },
  controlGearThermalShutdown: { de: "Betriebsgerät: thermische Abschaltung", en: "Control gear: thermal shutdown", counter: "controlGearThermalShutdownCounter" },
  lightSourceOverallFailureCondition: { de: "Leuchtmittel: Sammelfehler", en: "Light source: overall failure", counter: "lightSourceOverallFailureConditionCounter" },
  lightSourceShortCircuit: { de: "Leuchtmittel: Kurzschluss", en: "Light source: short circuit", counter: "lightSourceShortCircuitCounter" },
  lightSourceOpenCircuit: { de: "Leuchtmittel: Unterbrechung", en: "Light source: open circuit", counter: "lightSourceOpenCircuitCounter" },
  lightSourceThermalDerating: { de: "Leuchtmittel: thermische Leistungsreduktion", en: "Light source: thermal derating", counter: "lightSourceThermalDeratingCounter" },
  lightSourceThermalShutdown: { de: "Leuchtmittel: thermische Abschaltung", en: "Light source: thermal shutdown", counter: "lightSourceThermalShutdownCounter" },
};

export type SortDir = 1 | -1;
export function sortBy<T>(rows: T[], key: keyof T | ((r: T) => any), dir: SortDir): T[] {
  const get = typeof key === "function" ? key : (r: T) => (r as any)[key];
  return [...rows].sort((a, b) => {
    const va = get(a);
    const vb = get(b);
    if (va === vb) return 0;
    if (va === null || va === undefined) return 1;
    if (vb === null || vb === undefined) return -1;
    if (typeof va === "string" || typeof vb === "string") return String(va).localeCompare(String(vb), undefined, { numeric: true }) * dir;
    return (va < vb ? -1 : 1) * dir;
  });
}
