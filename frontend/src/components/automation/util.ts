// Types and helpers shared by the automation views (gateway-side automations).
import { gw } from "../../lib/api";
import { run, state, type Target } from "../../lib/store";
import { kelvinToRgb, rgbToHex, targetLabel } from "../../lib/dali";
import { lang } from "../../lib/i18n";

export type Features = Record<string, any>;
export type Tr = (k: string, p?: Record<string, unknown>) => string;

// ------------------------------------------------------------------ API types
export interface SequenceStep {
  enabled: boolean;
  type: "features";
  data: { targets: Target[]; features: Features };
  delay: number;
}
export interface SequenceItem {
  id: number;
  active: boolean;
  name: string;
  enabled: boolean;
  loop: boolean;
  repeat: number | null;
  steps: SequenceStep[];
  isMacro: boolean;
}
export interface SchedTime {
  hour: number;
  minute: number;
  second: number;
}
export type RecallMode = "timeOfDay" | "beforeSunrise" | "afterSunrise" | "beforeSunset" | "afterSunset";
export interface ActivePeriod {
  startMonth: number;
  endMonth: number;
  startDay: number;
  endDay: number;
}
export interface SchedulerItem {
  id: number;
  name: string;
  targets: Target[];
  enabled: boolean;
  activePeriod?: ActivePeriod | null;
  activeMonths?: Record<string, boolean> | null;
  activeWeekdays?: Record<string, boolean> | null;
  activeDays?: { days: number[] } | null;
  recallMode: RecallMode;
  recallTime: SchedTime;
  action: { type: "features"; data: Features };
}
export interface CircadianStep {
  hour: number;
  dimmable?: number;
  enableDimmable?: boolean;
  colorKelvin?: number;
  enableKelvin?: boolean;
}
export interface CircadianCurve {
  day: number;
  month: number;
  steps: CircadianStep[];
}
export interface CircadianItem {
  id: number;
  name: string;
  targets: Target[];
  enabled: boolean;
  longest: CircadianCurve;
  shortest: CircadianCurve;
}
export type SourceType = "device" | "group" | "broadcast" | "d16gear" | "d16group";
export interface TriggerSource {
  type: SourceType;
  id?: number;
  address?: number;
  line?: number;
}
export interface TriggerActionItem {
  id: number;
  enabled: boolean;
  name: string;
  sources: TriggerSource[];
  targets: Target[];
}
export interface EventTriggerItem {
  id: number;
  enabled: boolean;
  name: string;
  source_line: number;
  target_lines: number[];
  filters: Record<string, number[]>;
}
export interface LineConfig {
  delayBetweenQueries: number;
  queryStatus: boolean;
  queryActualLevel: boolean;
}

export const WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"] as const;
export const MONTHS = [
  "january",
  "february",
  "march",
  "april",
  "may",
  "june",
  "july",
  "august",
  "september",
  "october",
  "november",
  "december",
] as const;

// ------------------------------------------------------------------ helpers
export function clone<T>(x: T): T {
  return x === undefined ? x : JSON.parse(JSON.stringify(x));
}

export function lineCount(): number {
  const n = Number(state.info?.descriptor?.lines);
  return Number.isFinite(n) && n > 0 ? n : 1;
}

export function fmtNum(n: number, maxDigits = 1): string {
  return new Intl.NumberFormat(lang.value === "de" ? "de-DE" : "en-GB", { maximumFractionDigits: maxDigits }).format(n);
}

/** Human readable duration from seconds ("0,5 s", "2 min 30 s", "1 h 5 min"). */
export function fmtSec(sec: number | null | undefined): string {
  if (sec === null || sec === undefined || Number.isNaN(sec)) return "–";
  if (!Number.isFinite(sec)) return "∞";
  if (sec < 60) return `${fmtNum(sec, sec < 10 ? 2 : 1)} s`;
  const total = Math.round(sec);
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  if (h) return `${h} h${m ? ` ${m} min` : ""}`;
  return `${m} min${s ? ` ${s} s` : ""}`;
}

export const pad2 = (n: number) => String(Math.max(0, Math.floor(n || 0))).padStart(2, "0");

export function fmtClock(t: Partial<SchedTime> | null | undefined): string {
  const h = t?.hour ?? 0;
  const m = t?.minute ?? 0;
  const s = t?.second ?? 0;
  return `${pad2(h)}:${pad2(m)}${s ? `:${pad2(s)}` : ""}`;
}

/** "30 min", "1 h 15 min" – used for sun offsets. */
export function fmtOffset(t: Partial<SchedTime> | null | undefined): string {
  const h = t?.hour ?? 0;
  const m = t?.minute ?? 0;
  const s = t?.second ?? 0;
  const parts: string[] = [];
  if (h) parts.push(`${h} h`);
  if (m) parts.push(`${m} min`);
  if (s) parts.push(`${s} s`);
  return parts.join(" ");
}

export function targetsText(targets: Target[] | undefined, t: Tr, max = 3): string {
  if (!targets?.length) return t("noTargetsShort");
  const names = targets.map((tg) => targetLabel(tg, state.devices, state.zones, t));
  if (names.length <= max) return names.join(", ");
  return `${names.slice(0, max).join(", ")} +${names.length - max}`;
}

function fade(v: any): string {
  const n = Number(v);
  return Number.isFinite(n) && n > 0 ? ` (${fmtNum(n, 1)} s)` : "";
}

/** Short text for a ControlData object, e.g. "80 % · 3000 K". */
export function actionSummary(f: Features | null | undefined, t: Tr): string {
  if (!f || !Object.keys(f).length) return t("noAction");
  const parts: string[] = [];
  for (const [k, v] of Object.entries(f)) {
    switch (k) {
      case "switchable":
        parts.push(v ? t("actOnShort") : t("actOffShort"));
        break;
      case "dimmable":
        parts.push(`${fmtNum(Number(v))} %`);
        break;
      case "dimmableWithFade":
        parts.push(`${fmtNum(Number(v?.dimValue))} %${fade(v?.fadeTime)}`);
        break;
      case "gotoLastActive":
        parts.push(t("actLastShort"));
        break;
      case "gotoLastActiveWithFade":
        parts.push(`${t("actLastShort")}${fade(v?.fadeTime)}`);
        break;
      case "dimUp":
        parts.push(`${t("actDimUpShort")} ×${v}`);
        break;
      case "dimDown":
        parts.push(`${t("actDimDownShort")} ×${v}`);
        break;
      case "scene":
        parts.push(`${t("scene")} ${v}`);
        break;
      case "sceneWithFade":
        parts.push(`${t("scene")} ${v?.scene}${fade(v?.fadeTime)}`);
        break;
      case "colorKelvin":
        parts.push(`${Math.round(Number(v))} K`);
        break;
      case "colorKelvinWithFade":
        parts.push(`${Math.round(Number(v?.color))} K${fade(v?.fadeTime)}`);
        break;
      case "dimmableKelvin":
        parts.push(`${fmtNum(Number(v?.dimmable))} % · ${Math.round(Number(v?.kelvin))} K`);
        break;
      case "colorRGB":
        parts.push(`RGB ${rgbToHex(v?.r ?? 0, v?.g ?? 0, v?.b ?? 0)}`);
        break;
      case "dimmableRGB":
        parts.push(`${fmtNum(Number(v?.dimmable))} % · RGB ${rgbToHex(v?.r ?? 0, v?.g ?? 0, v?.b ?? 0)}`);
        break;
      default:
        parts.push(typeof v === "object" ? k : `${k}: ${v}`);
    }
  }
  return parts.join(" + ");
}

/** Representative colour of an action (used for timeline segments and swatches). */
export function actionColor(f: Features | null | undefined): string {
  if (!f) return "var(--bg2)";
  if ("colorKelvin" in f) return kelvinToRgb(Number(f.colorKelvin) || 4000);
  if ("colorKelvinWithFade" in f) return kelvinToRgb(Number(f.colorKelvinWithFade?.color) || 4000);
  if ("dimmableKelvin" in f) return kelvinToRgb(Number(f.dimmableKelvin?.kelvin) || 4000);
  const rgb = f.colorRGB ?? f.dimmableRGB;
  if (rgb) return rgbToHex(rgb.r ?? 0, rgb.g ?? 0, rgb.b ?? 0);
  if (f.switchable === false) return "var(--text3)";
  const lvl = "dimmable" in f ? Number(f.dimmable) : "dimmableWithFade" in f ? Number(f.dimmableWithFade?.dimValue) : null;
  if (lvl !== null && Number.isFinite(lvl)) {
    if (lvl <= 0) return "var(--text3)";
    return `color-mix(in srgb, #ffc107 ${Math.round(35 + lvl * 0.65)}%, var(--bg2))`;
  }
  if ("scene" in f || "sceneWithFade" in f) return "color-mix(in srgb, var(--primary) 55%, var(--bg2))";
  return "#ffd54f";
}

// ------------------------------------------------------------------ feature support
/** Feature sets of the given targets (unknown targets are skipped). */
function targetFeatureSets(targets: Target[]): Set<string>[] {
  const devs = Object.values(state.devices);
  const out: Set<string>[] = [];
  for (const tg of targets || []) {
    let feats: Record<string, any>[] = [];
    if (tg.type === "device") {
      const d = state.devices[tg.id as number];
      if (d) feats = [d.features];
    } else if (tg.type === "zone") {
      const z = state.zones[tg.id as number];
      if (z) feats = [z.features];
    } else if (tg.type === "group") {
      // Multi-line gateways encode groups as group + 16 · line.
      const id = Number(tg.id) || 0;
      const line = Math.floor(id / 16);
      const g = id % 16;
      feats = devs.filter((d) => Number(d.line ?? 0) === line && d.groups?.includes(g)).map((d) => d.features);
    } else if (tg.type === "broadcast") {
      // Broadcast id = line (multi-line) or null (all lines).
      feats = devs.filter((d) => tg.id === null || tg.id === undefined || Number(d.line ?? 0) === tg.id).map((d) => d.features);
    }
    const s = new Set<string>();
    for (const f of feats) for (const k of Object.keys(f || {})) s.add(k);
    if (s.size) out.push(s);
  }
  return out;
}

/** Whether all / some / none of the targets support every key of the action. */
export function actionSupport(targets: Target[], f: Features | null | undefined): "all" | "some" | "none" | "unknown" {
  const keys = Object.keys(f || {});
  const sets = targetFeatureSets(targets);
  if (!keys.length || !sets.length) return "unknown";
  const ok = sets.filter((s) => keys.every((k) => s.has(k))).length;
  if (ok === sets.length) return "all";
  return ok ? "some" : "none";
}

/** Send an action to targets right now (to try it out). */
export async function tryAction(targets: Target[], features: Features, okMsg?: string) {
  const usable = (targets || []).filter((tg) => ["device", "group", "zone", "broadcast"].includes(tg.type));
  await run(async () => {
    for (const tg of usable) await gw.control(tg.type, tg.id, features);
  }, okMsg);
}

/** Label of a trigger-action source. */
export function sourceLabel(s: TriggerSource, t: Tr): string {
  const multi = lineCount() > 1;
  switch (s.type) {
    case "device":
      return state.devices[s.id as number]?.name ?? `${t("device")} #${s.id}`;
    case "group":
      // Same encoding as targets (group + 16 · line) → same label.
      return targetLabel({ type: "group", id: Number(s.id) || 0 }, state.devices, state.zones, t);
    case "broadcast":
      return multi ? targetLabel({ type: "broadcast", id: Number(s.id) || 0 }, state.devices, state.zones, t) : t("broadcast");
    case "d16gear":
      return `DALI A${s.address}${multi ? ` · ${t("line")} ${s.line}` : ""}`;
    case "d16group":
      return `DALI G${s.address}${multi ? ` · ${t("line")} ${s.line}` : ""}`;
  }
  return JSON.stringify(s);
}

/** Targets as plain {type,id} objects (strip anything else). */
export function plainTargets(targets: Target[]): Target[] {
  return (targets || []).map((tg) => ({ type: tg.type, id: tg.type === "broadcast" ? (tg.id ?? null) : tg.id }));
}

// ------------------------------------------------------------------ sun position
/** Sunrise / sunset for a date and position (algorithm as used by suncalc). */
export function sunTimes(date: Date, lat: number, lon: number): { sunrise: Date | null; sunset: Date | null } {
  const rad = Math.PI / 180;
  const dayMs = 86400000;
  const J1970 = 2440588;
  const J2000 = 2451545;
  const toDays = (d: Date) => d.valueOf() / dayMs - 0.5 + J1970 - J2000;
  const fromJulian = (j: number) => new Date((j + 0.5 - J1970) * dayMs);
  const lw = rad * -lon;
  const phi = rad * lat;
  const d = toDays(date);
  const n = Math.round(d - 0.0009 - lw / (2 * Math.PI));
  const ds = 0.0009 + lw / (2 * Math.PI) + n;
  const M = rad * (357.5291 + 0.98560028 * ds);
  const C = rad * (1.9148 * Math.sin(M) + 0.02 * Math.sin(2 * M) + 0.0003 * Math.sin(3 * M));
  const L = M + C + rad * 102.9372 + Math.PI;
  const dec = Math.asin(Math.sin(rad * 23.4397) * Math.sin(L));
  const jNoon = J2000 + ds + 0.0053 * Math.sin(M) - 0.0069 * Math.sin(2 * L);
  const cosW = (Math.sin(rad * -0.833) - Math.sin(phi) * Math.sin(dec)) / (Math.cos(phi) * Math.cos(dec));
  if (cosW < -1 || cosW > 1) return { sunrise: null, sunset: null };
  const w = Math.acos(cosW);
  const a = 0.0009 + (w + lw) / (2 * Math.PI) + n;
  const jSet = J2000 + a + 0.0053 * Math.sin(M) - 0.0069 * Math.sin(2 * L);
  const jRise = jNoon - (jSet - jNoon);
  return { sunrise: fromJulian(jRise), sunset: fromJulian(jSet) };
}

export function fmtDateTime(d: Date | null, withSeconds = false): string {
  if (!d) return "–";
  return d.toLocaleTimeString(lang.value === "de" ? "de-DE" : "en-GB", {
    hour: "2-digit",
    minute: "2-digit",
    ...(withSeconds ? { second: "2-digit" } : {}),
  });
}

// ------------------------------------------------------------------ circadian
/** Linear interpolation of a circadian curve at a given hour (wraps around midnight). */
export function curveValue(steps: CircadianStep[], hour: number, key: "dimmable" | "colorKelvin"): number | null {
  const flag = key === "dimmable" ? "enableDimmable" : "enableKelvin";
  const pts = (steps || [])
    .filter((s) => s[flag] !== false && typeof s[key] === "number")
    .map((s) => ({ h: s.hour, v: s[key] as number }))
    .sort((a, b) => a.h - b.h);
  if (!pts.length) return null;
  if (pts.length === 1) return pts[0].v;
  const exact = pts.find((p) => p.h === hour);
  if (exact) return exact.v;
  let prev = pts[pts.length - 1];
  let next = pts[0];
  for (let i = 0; i < pts.length; i++) {
    if (pts[i].h > hour) {
      next = pts[i];
      prev = i > 0 ? pts[i - 1] : pts[pts.length - 1];
      break;
    }
    if (i === pts.length - 1) {
      prev = pts[i];
      next = pts[0];
    }
  }
  const span = (next.h - prev.h + 24) % 24 || 24;
  const pos = (hour - prev.h + 24) % 24;
  return prev.v + ((next.v - prev.v) * pos) / span;
}

export function isRestrictiveDays(days: number[] | undefined | null): boolean {
  if (!Array.isArray(days) || !days.length) return false;
  const uniq = new Set(days.filter((d) => d >= 1 && d <= 31));
  return uniq.size < 31;
}

export function isRestrictivePeriod(p: ActivePeriod | null | undefined): boolean {
  if (!p || !p.startMonth || !p.endMonth || !p.startDay || !p.endDay) return false;
  return !(p.startMonth === 1 && p.startDay === 1 && p.endMonth === 12 && p.endDay === 31);
}
