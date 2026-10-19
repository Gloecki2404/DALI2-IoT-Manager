// Shared DALI frame helpers for the bus views (monitor, commands, analyses).
import { onBeforeUnmount, reactive, ref, toRaw } from "vue";
import { onMonitor, state, type MonitorFrame } from "../../lib/store";
import { DALI_TYPES, FADE_RATES, FADE_TIMES } from "../../lib/dali";

export type Lang = "de" | "en";
type L = { de: string; en: string };

export interface Frame extends MonitorFrame {
  id?: number;
  db?: boolean;
}

// ------------------------------------------------------------------ kinds
export const KINDS = ["command", "query", "backward", "dapc", "event", "special", "edali", "unknown"] as const;

export const KIND_META: Record<string, { color: string; de: string; en: string; hintDe: string; hintEn: string }> = {
  command: { color: "#1e88e5", de: "Befehl", en: "Command", hintDe: "Vorwärtsframe: Steuer- oder Konfigurationsbefehl", hintEn: "Forward frame: control or configuration command" },
  query: { color: "#ab47bc", de: "Abfrage", en: "Query", hintDe: "Vorwärtsframe, der eine Antwort erwartet", hintEn: "Forward frame that expects an answer" },
  backward: { color: "#43a047", de: "Antwort", en: "Answer", hintDe: "Rückwärtsframe (8 Bit) eines Busteilnehmers", hintEn: "Backward frame (8 bit) from a bus participant" },
  dapc: { color: "#0097a7", de: "DAPC", en: "DAPC", hintDe: "Direct Arc Power Control – direkter Dimmwert", hintEn: "Direct arc power control – direct dim level" },
  event: { color: "#ef6c00", de: "Ereignis", en: "Event", hintDe: "Ereignis eines Eingabegeräts (Taster, Sensor)", hintEn: "Event of an input device (button, sensor)" },
  special: { color: "#d81b60", de: "Spezial", en: "Special", hintDe: "Spezialbefehl (DTR, Initialisierung, Adressierung …)", hintEn: "Special command (DTR, initialisation, addressing …)" },
  edali: { color: "#6d4c41", de: "eDALI", en: "eDALI", hintDe: "25-Bit-Frame (eDALI, herstellerspezifisch)", hintEn: "25 bit frame (eDALI, manufacturer specific)" },
  reserved: { color: "#546e7a", de: "Reserviert", en: "Reserved", hintDe: "32-Bit-Frame (in IEC 62386 reserviert)", hintEn: "32 bit frame (reserved in IEC 62386)" },
  unknown: { color: "#78909c", de: "Unbekannt", en: "Unknown", hintDe: "Nicht dekodierbarer Frame", hintEn: "Frame that could not be decoded" },
};

export function kindKey(k: string | undefined): string {
  return k && k in KIND_META ? k : "unknown";
}
export function kindLabel(k: string | undefined, lang: Lang): string {
  return KIND_META[kindKey(k)][lang];
}
export function kindStyle(k: string | undefined): Record<string, string> {
  const c = KIND_META[kindKey(k)].color;
  return { color: `color-mix(in srgb, ${c} 78%, var(--text))`, background: `color-mix(in srgb, ${c} 15%, transparent)` };
}

// ------------------------------------------------------------- formatting
const p2 = (n: number) => String(n).padStart(2, "0");

/** HH:MM:SS.mmm (optionally with date). */
export function fmtMs(ts: number | null | undefined, withDate = false, lang: Lang = "de"): string {
  if (!ts) return "–";
  const d = new Date(ts * 1000);
  const time = `${p2(d.getHours())}:${p2(d.getMinutes())}:${p2(d.getSeconds())}.${String(d.getMilliseconds()).padStart(3, "0")}`;
  if (!withDate) return time;
  const date =
    lang === "de"
      ? `${p2(d.getDate())}.${p2(d.getMonth() + 1)}.${d.getFullYear()}`
      : `${d.getFullYear()}-${p2(d.getMonth() + 1)}-${p2(d.getDate())}`;
  return `${date} ${time}`;
}

export const hex2 = (b: number) => (b & 0xff).toString(16).toUpperCase().padStart(2, "0");
export const bin8 = (b: number) => (b & 0xff).toString(2).padStart(8, "0");
export const bytesHex = (bytes: number[]) => bytes.map(hex2).join(" ");

/** Parses "FF 05", "0x0B 0x90", "C1 06, 0B F0" (several frames separated by , ; | or newline). */
export function parseHexFrames(s: string): { frames: number[][]; error?: "odd" | "len" | "mixed" | "empty" } {
  const parts = s
    .split(/[,;|\n]+/)
    .map((x) => x.trim())
    .filter(Boolean);
  if (!parts.length) return { frames: [], error: "empty" };
  const frames: number[][] = [];
  for (const part of parts) {
    const clean = part.replace(/0x/gi, "").replace(/[^0-9a-f]/gi, "");
    if (clean.length % 2) return { frames: [], error: "odd" };
    const bytes = (clean.match(/../g) || []).map((h) => parseInt(h, 16));
    if (bytes.length !== 2 && bytes.length !== 3) return { frames: [], error: "len" };
    frames.push(bytes);
  }
  if (!frames.every((f) => f.length === frames[0].length)) return { frames: [], error: "mixed" };
  return { frames };
}

// --------------------------------------------------- IEC 62386 command tables
export const GEAR_COMMANDS: Record<number, string> = {
  0: "OFF",
  1: "UP",
  2: "DOWN",
  3: "STEP UP",
  4: "STEP DOWN",
  5: "RECALL MAX LEVEL",
  6: "RECALL MIN LEVEL",
  7: "STEP DOWN AND OFF",
  8: "ON AND STEP UP",
  9: "ENABLE DAPC SEQUENCE",
  10: "GO TO LAST ACTIVE LEVEL",
  11: "CONTINUOUS UP",
  12: "CONTINUOUS DOWN",
  32: "RESET",
  33: "STORE ACTUAL LEVEL IN DTR0",
  34: "SAVE PERSISTENT VARIABLES",
  35: "SET OPERATING MODE (DTR0)",
  36: "RESET MEMORY BANK (DTR0)",
  37: "IDENTIFY DEVICE",
  42: "SET MAX LEVEL (DTR0)",
  43: "SET MIN LEVEL (DTR0)",
  44: "SET SYSTEM FAILURE LEVEL (DTR0)",
  45: "SET POWER ON LEVEL (DTR0)",
  46: "SET FADE TIME (DTR0)",
  47: "SET FADE RATE (DTR0)",
  48: "SET EXTENDED FADE TIME (DTR0)",
  128: "SET SHORT ADDRESS (DTR0)",
  129: "ENABLE WRITE MEMORY",
  144: "QUERY STATUS",
  145: "QUERY CONTROL GEAR PRESENT",
  146: "QUERY LAMP FAILURE",
  147: "QUERY LAMP POWER ON",
  148: "QUERY LIMIT ERROR",
  149: "QUERY RESET STATE",
  150: "QUERY MISSING SHORT ADDRESS",
  151: "QUERY VERSION NUMBER",
  152: "QUERY CONTENT DTR0",
  153: "QUERY DEVICE TYPE",
  154: "QUERY PHYSICAL MINIMUM",
  155: "QUERY POWER FAILURE",
  156: "QUERY CONTENT DTR1",
  157: "QUERY CONTENT DTR2",
  158: "QUERY OPERATING MODE",
  159: "QUERY LIGHT SOURCE TYPE",
  160: "QUERY ACTUAL LEVEL",
  161: "QUERY MAX LEVEL",
  162: "QUERY MIN LEVEL",
  163: "QUERY POWER ON LEVEL",
  164: "QUERY SYSTEM FAILURE LEVEL",
  165: "QUERY FADE TIME/FADE RATE",
  166: "QUERY MANUFACTURER SPECIFIC MODE",
  167: "QUERY NEXT DEVICE TYPE",
  168: "QUERY EXTENDED FADE TIME",
  170: "QUERY CONTROL GEAR FAILURE",
  192: "QUERY GROUPS 0-7",
  193: "QUERY GROUPS 8-15",
  194: "QUERY RANDOM ADDRESS (H)",
  195: "QUERY RANDOM ADDRESS (M)",
  196: "QUERY RANDOM ADDRESS (L)",
  197: "READ MEMORY LOCATION (DTR1, DTR0)",
};
for (let n = 0; n < 16; n++) {
  GEAR_COMMANDS[16 + n] = `GO TO SCENE ${n}`;
  GEAR_COMMANDS[64 + n] = `SET SCENE ${n} (DTR0)`;
  GEAR_COMMANDS[80 + n] = `REMOVE FROM SCENE ${n}`;
  GEAR_COMMANDS[96 + n] = `ADD TO GROUP ${n}`;
  GEAR_COMMANDS[112 + n] = `REMOVE FROM GROUP ${n}`;
  GEAR_COMMANDS[176 + n] = `QUERY SCENE LEVEL ${n}`;
}

// Application extended commands (224…255) – valid after ENABLE DEVICE TYPE n
export const EXTENDED_COMMANDS: Record<number, Record<number, string>> = {
  6: {
    224: "REFERENCE SYSTEM POWER",
    225: "SELECT DIMMING CURVE (DTR0)",
    226: "SET FAST FADE TIME (DTR0)",
    237: "QUERY CONTROL GEAR TYPE",
    238: "QUERY DIMMING CURVE",
    240: "QUERY FEATURES",
    241: "QUERY FAILURE STATUS",
    242: "QUERY SHORT CIRCUIT",
    243: "QUERY OPEN CIRCUIT",
    244: "QUERY LOAD DECREASE",
    245: "QUERY LOAD INCREASE",
    246: "QUERY CURRENT PROTECTOR ACTIVE",
    247: "QUERY THERMAL SHUTDOWN",
    248: "QUERY THERMAL OVERLOAD",
    249: "QUERY REFERENCE RUNNING",
    250: "QUERY REFERENCE MEASUREMENT FAILED",
    251: "QUERY CURRENT PROTECTOR ENABLED",
    252: "QUERY OPERATING MODE",
    253: "QUERY FAST FADE TIME",
    254: "QUERY MIN FAST FADE TIME",
    255: "QUERY EXTENDED VERSION NUMBER",
  },
  8: {
    224: "SET TEMPORARY X-COORDINATE (DTR1:DTR0)",
    225: "SET TEMPORARY Y-COORDINATE (DTR1:DTR0)",
    226: "ACTIVATE",
    227: "X-COORDINATE STEP UP",
    228: "X-COORDINATE STEP DOWN",
    229: "Y-COORDINATE STEP UP",
    230: "Y-COORDINATE STEP DOWN",
    231: "SET TEMPORARY COLOUR TEMPERATURE (DTR1:DTR0)",
    232: "COLOUR TEMPERATURE STEP COOLER",
    233: "COLOUR TEMPERATURE STEP WARMER",
    234: "SET TEMPORARY PRIMARY N DIMLEVEL",
    235: "SET TEMPORARY RGB DIMLEVEL",
    236: "SET TEMPORARY WAF DIMLEVEL",
    237: "SET TEMPORARY RGBWAF CONTROL",
    238: "COPY REPORT TO TEMPORARY",
    240: "STORE TY PRIMARY N",
    241: "STORE XY-COORDINATE PRIMARY N",
    242: "STORE COLOUR TEMPERATURE LIMIT",
    243: "STORE GEAR FEATURES/STATUS",
    245: "ASSIGN COLOUR TO LINKED CHANNEL",
    246: "START AUTO CALIBRATION",
    247: "QUERY GEAR FEATURES/STATUS",
    248: "QUERY COLOUR STATUS",
    249: "QUERY COLOUR TYPE FEATURES",
    250: "QUERY COLOUR VALUE (DTR0)",
    251: "QUERY RGBWAF CONTROL",
    252: "QUERY ASSIGNED COLOUR",
    255: "QUERY EXTENDED VERSION NUMBER",
  },
};

export const SPECIAL_COMMANDS_16: Record<number, string> = {
  0xa1: "TERMINATE",
  0xa3: "DTR0",
  0xa5: "INITIALISE",
  0xa7: "RANDOMISE",
  0xa9: "COMPARE",
  0xab: "WITHDRAW",
  0xad: "PING",
  0xb1: "SEARCHADDRH",
  0xb3: "SEARCHADDRM",
  0xb5: "SEARCHADDRL",
  0xb7: "PROGRAM SHORT ADDRESS",
  0xb9: "VERIFY SHORT ADDRESS",
  0xbb: "QUERY SHORT ADDRESS",
  0xc1: "ENABLE DEVICE TYPE",
  0xc3: "DTR1",
  0xc5: "DTR2",
  0xc7: "WRITE MEMORY LOCATION",
  0xc9: "WRITE MEMORY LOCATION - NO REPLY",
};
const SPECIAL_QUERIES_16 = new Set([0xa9, 0xb9, 0xbb, 0xc7]);

export const DEVICE_COMMANDS: Record<number, string> = {
  0x00: "IDENTIFY DEVICE",
  0x01: "RESET POWER CYCLE SEEN",
  0x10: "RESET",
  0x11: "RESET MEMORY BANK (DTR0)",
  0x14: "SET SHORT ADDRESS (DTR0)",
  0x15: "ENABLE WRITE MEMORY",
  0x16: "ENABLE APPLICATION CONTROLLER",
  0x17: "DISABLE APPLICATION CONTROLLER",
  0x18: "SET OPERATING MODE (DTR0)",
  0x19: "ADD TO DEVICE GROUPS 0-15",
  0x1a: "ADD TO DEVICE GROUPS 16-31",
  0x1b: "REMOVE FROM DEVICE GROUPS 0-15",
  0x1c: "REMOVE FROM DEVICE GROUPS 16-31",
  0x1d: "START QUIESCENT MODE",
  0x1e: "STOP QUIESCENT MODE",
  0x1f: "ENABLE POWER CYCLE NOTIFICATION",
  0x20: "DISABLE POWER CYCLE NOTIFICATION",
  0x21: "SAVE PERSISTENT VARIABLES",
  0x30: "QUERY DEVICE STATUS",
  0x31: "QUERY APPLICATION CONTROLLER ERROR",
  0x32: "QUERY INPUT DEVICE ERROR",
  0x33: "QUERY MISSING SHORT ADDRESS",
  0x34: "QUERY VERSION NUMBER",
  0x35: "QUERY NUMBER OF INSTANCES",
  0x36: "QUERY CONTENT DTR0",
  0x37: "QUERY CONTENT DTR1",
  0x38: "QUERY CONTENT DTR2",
  0x39: "QUERY RANDOM ADDRESS (H)",
  0x3a: "QUERY RANDOM ADDRESS (M)",
  0x3b: "QUERY RANDOM ADDRESS (L)",
  0x3c: "READ MEMORY LOCATION",
  0x3d: "QUERY APPLICATION CONTROL ENABLED",
  0x3e: "QUERY OPERATING MODE",
  0x3f: "QUERY MANUFACTURER SPECIFIC MODE",
  0x40: "QUERY QUIESCENT MODE",
  0x41: "QUERY DEVICE GROUPS 0-7",
  0x42: "QUERY DEVICE GROUPS 8-15",
  0x43: "QUERY DEVICE GROUPS 16-23",
  0x44: "QUERY DEVICE GROUPS 24-31",
  0x45: "QUERY POWER CYCLE NOTIFICATION",
  0x46: "QUERY DEVICE CAPABILITIES",
  0x47: "QUERY EXTENDED VERSION NUMBER",
  0x48: "QUERY RESET STATE",
  0x49: "QUERY APPLICATION CONTROLLER ALWAYS ACTIVE",
  0x61: "SET EVENT PRIORITY (DTR0)",
  0x62: "ENABLE INSTANCE",
  0x63: "DISABLE INSTANCE",
  0x64: "SET PRIMARY INSTANCE GROUP (DTR0)",
  0x65: "SET INSTANCE GROUP 1 (DTR0)",
  0x66: "SET INSTANCE GROUP 2 (DTR0)",
  0x67: "SET EVENT SCHEME (DTR0)",
  0x68: "SET EVENT FILTER (DTR2:DTR1:DTR0)",
  0x80: "QUERY INSTANCE TYPE",
  0x81: "QUERY RESOLUTION",
  0x82: "QUERY INSTANCE ERROR",
  0x83: "QUERY INSTANCE STATUS",
  0x84: "QUERY EVENT PRIORITY",
  0x86: "QUERY INSTANCE ENABLED",
  0x88: "QUERY PRIMARY INSTANCE GROUP",
  0x89: "QUERY INSTANCE GROUP 1",
  0x8a: "QUERY INSTANCE GROUP 2",
  0x8b: "QUERY EVENT SCHEME",
  0x8c: "QUERY INPUT VALUE",
  0x8d: "QUERY INPUT VALUE LATCH",
  0x8e: "QUERY FEATURE TYPE",
  0x8f: "QUERY NEXT FEATURE TYPE",
  0x90: "QUERY EVENT FILTER 0-7",
  0x91: "QUERY EVENT FILTER 8-15",
  0x92: "QUERY EVENT FILTER 16-23",
};

// Instance commands (instance byte != 0xFE). 0x00-0x3F depend on the instance
// type: 0x0_ IEC 62386-301, 0x1_ 302, 0x2_ 303, 0x3_ 304.
export const INSTANCE_COMMANDS: Record<number, string> = {
  0x00: "SET SHORT TIMER (DTR0) [301]",
  0x01: "SET DOUBLE TIMER (DTR0) [301]",
  0x02: "SET REPEAT TIMER (DTR0) [301]",
  0x03: "SET STUCK TIMER (DTR0) [301]",
  0x0a: "QUERY SHORT TIMER [301]",
  0x0b: "QUERY SHORT TIMER MIN [301]",
  0x0c: "QUERY DOUBLE TIMER [301]",
  0x0d: "QUERY DOUBLE TIMER MIN [301]",
  0x0e: "QUERY REPEAT TIMER [301]",
  0x0f: "QUERY STUCK TIMER [301]",
  0x10: "SET REPORT TIMER (DTR0) [302]",
  0x11: "SET DEADTIME TIMER (DTR0) [302]",
  0x1d: "QUERY DEADTIME TIMER [302]",
  0x1e: "QUERY REPORT TIMER [302]",
  0x1f: "QUERY SWITCH [302]",
  0x20: "CATCH MOVEMENT [303]",
  0x21: "SET HOLD TIMER (DTR0) [303]",
  0x22: "SET REPORT TIMER (DTR0) [303]",
  0x23: "SET DEADTIME TIMER (DTR0) [303]",
  0x24: "CANCEL HOLD TIMER [303]",
  0x2c: "QUERY DEADTIME TIMER [303]",
  0x2d: "QUERY HOLD TIMER [303]",
  0x2e: "QUERY REPORT TIMER [303]",
  0x2f: "QUERY CATCHING [303]",
  0x30: "SET REPORT TIMER (DTR0) [304]",
  0x31: "SET HYSTERESIS (DTR0) [304]",
  0x32: "SET DEADTIME TIMER (DTR0) [304]",
  0x33: "SET HYSTERESIS MIN (DTR0) [304]",
  0x3c: "QUERY HYSTERESIS MIN [304]",
  0x3d: "QUERY DEADTIME TIMER [304]",
  0x3e: "QUERY REPORT TIMER [304]",
  0x3f: "QUERY HYSTERESIS [304]",
};
for (let op = 0x40; op <= 0x46; op++) INSTANCE_COMMANDS[op] = `MANUFACTURER SPECIFIC 0x${hex2(op)} (reserved, e.g. Lunatone)`;
for (const [op, name] of Object.entries(DEVICE_COMMANDS)) {
  const n = Number(op);
  if ((n >= 0x61 && n <= 0x68) || (n >= 0x80 && n <= 0x92)) INSTANCE_COMMANDS[n] = name;
}

const ANSWERING_SPECIAL_24 = new Set([0x03, 0x09, 0x0a, 0x20]);

/** INITIALISE parameter, IEC 62386-102 (16 bit): 0x00 all gear, 0xFF gear without address. */
function initialise16(c: number): [string, boolean] {
  if (c === 0x00) return ["ALL control gear", true];
  if (c === 0xff) return ["gear without short address", false];
  if ((c & 0x81) === 0x01) return [`gear A${(c >> 1) & 0x3f}`, false];
  return [`0x${hex2(c)} (invalid)`, false];
}

/** PROGRAM SHORT ADDRESS parameter. Gear (102): 0AAAAAA1; control devices
 * (103:2020 9.14.1): the plain number 0..63. 0xFF deletes the address. */
function programAddress(c: number, bits = 16): string {
  if (c === 0xff) return "(delete short address)";
  if (bits === 24) return c < 0x40 ? `D${c}` : `0x${hex2(c)} (invalid)`;
  return (c & 0x81) === 0x01 ? `A${(c >> 1) & 0x3f}` : `0x${hex2(c)}`;
}

/** INITIALISE parameter, IEC 62386-103 (24 bit): 0x7F devices without address, 0xFF all devices. */
function initialise24(c: number): [string, boolean] {
  if (c === 0x7f) return ["devices without short address", false];
  if (c === 0xff) return ["ALL control devices", true];
  if (c <= 0x3f) return [`device D${c}`, false];
  return [`0x${hex2(c)} (invalid)`, false];
}

export const SPECIAL_COMMANDS_24: Record<number, string> = {
  0x00: "TERMINATE",
  0x01: "INITIALISE",
  0x02: "RANDOMISE",
  0x03: "COMPARE",
  0x04: "WITHDRAW",
  0x05: "SEARCHADDRH",
  0x06: "SEARCHADDRM",
  0x07: "SEARCHADDRL",
  0x08: "PROGRAM SHORT ADDRESS",
  0x09: "VERIFY SHORT ADDRESS",
  0x0a: "QUERY SHORT ADDRESS",
  0x20: "WRITE MEMORY LOCATION",
  0x21: "WRITE MEMORY LOCATION - NO REPLY",
  0x30: "DTR0",
  0x31: "DTR1",
  0x32: "DTR2",
  0x33: "SEND TESTFRAME",
};

export const INSTANCE_TYPES: Record<number, L> = {
  0: { de: "Generisch", en: "Generic" },
  1: { de: "Taster", en: "Push button" },
  2: { de: "Absolutwertgeber", en: "Absolute input" },
  3: { de: "Präsenzmelder", en: "Occupancy sensor" },
  4: { de: "Lichtsensor", en: "Light sensor" },
  5: { de: "Farbsensor", en: "Colour sensor" },
  6: { de: "Universalsensor", en: "General purpose sensor" },
};

export const EVENT_TYPES: Record<string, L> = {
  released: { de: "losgelassen", en: "released" },
  pressed: { de: "gedrückt", en: "pressed" },
  short_press: { de: "kurz gedrückt", en: "short press" },
  double_press: { de: "doppelt gedrückt", en: "double press" },
  long_press_start: { de: "lang gedrückt (Start)", en: "long press (start)" },
  long_press_repeat: { de: "lang gedrückt (Wiederholung)", en: "long press (repeat)" },
  long_press_stop: { de: "lang gedrückt (Ende)", en: "long press (stop)" },
  button_free: { de: "Taster frei", en: "button free" },
  button_stuck: { de: "Taster klemmt", en: "button stuck" },
  occupied: { de: "belegt", en: "occupied" },
  vacant: { de: "frei", en: "vacant" },
  illuminance: { de: "Helligkeitswert", en: "illuminance" },
  position: { de: "Position", en: "position" },
  event: { de: "Ereignis", en: "event" },
  power_cycle: { de: "Netzwiederkehr", en: "power cycle" },
};

export function levelPct(v: number): string {
  return `${Math.round((v * 1000) / 254) / 10} %`;
}

function instance24(i: number): string {
  if (i === 0xfe) return "device";
  if (i === 0xff) return "all instances";
  if (i === 0xfd) return "feature on device";
  if (i === 0xfc) return "feature broadcast";
  const n = i & 0x1f;
  switch (i & 0xe0) {
    case 0x00: return `instance ${n}`;
    case 0x80: return `instance group ${n}`;
    case 0xc0: return `instance type ${n}`;
    case 0x20: return `feature on instance ${n}`;
    case 0xa0: return `feature on instance group ${n}`;
    case 0xe0: return `feature on instance type ${n}`;
  }
  return `0x${hex2(i)}`;
}

export function address16Label(a: number): { kind: string; label: string } {
  if (a <= 0x7f) return { kind: "short", label: `A${a >> 1}` };
  if (a <= 0x9f) return { kind: "group", label: `G${(a >> 1) & 0x0f}` };
  if (a === 0xfe || a === 0xff) return { kind: "broadcast", label: "BC" };
  if (a === 0xfc || a === 0xfd) return { kind: "broadcast_unaddressed", label: "BC-unaddr" };
  return { kind: "special", label: "" };
}

function address24Label(a: number): string {
  if (a === 0xfe || a === 0xff) return "BC";
  if (a === 0xfc || a === 0xfd) return "BC-unaddr";
  if (!(a & 0x80)) return `D${(a >> 1) & 0x3f}`;
  if ((a & 0xc0) === 0x80) return `DG${(a >> 1) & 0x1f}`;
  return `0x${hex2(a)}`;
}

export interface Described {
  kind: string;
  target: string;
  name: string;
  text: string;
  query: boolean;
  /** "addressing": RANDOMISE / PROGRAM SHORT ADDRESS – short addresses are (re)assigned */
  warning?: string;
}

/** Description of a 16 bit forward frame (as the add-on decoder does it); dt = device type enabled before. */
export function describe16(a: number, c: number, dt?: number | null): Described {
  const { kind, label } = address16Label(a);
  if (kind === "special" || (a & 0x01 && a >= 0xa0 && a <= 0xcb)) {
    let name = SPECIAL_COMMANDS_16[a] || `SPECIAL 0x${hex2(a)}`;
    let warning: string | undefined;
    if (a === 0xc1) name = `ENABLE DEVICE TYPE ${c}`;
    else if (a === 0xa5) name = `INITIALISE ${c} (${initialise16(c)[0]})`;
    else if (a === 0xa7) {
      name = "RANDOMISE";
      warning = "addressing";
    } else if (a === 0xb7) {
      name = `PROGRAM SHORT ADDRESS ${programAddress(c)}`;
      warning = "addressing";
    } else if (a === 0xa3 || a === 0xc3 || a === 0xc5) name = `${name} = ${c}`;
    else name = `${name} ${c}`;
    return { kind: "special", target: "", name, text: name, query: SPECIAL_QUERIES_16.has(a), warning };
  }
  if (!(a & 0x01)) {
    const name = c === 0xff ? "DAPC MASK (stop fading)" : `DAPC ${c} (${levelPct(c)})`;
    return { kind: "dapc", target: label, name, text: `${label}: ${name}`, query: false };
  }
  const name =
    c >= 224
      ? EXTENDED_COMMANDS[dt ?? -1]?.[c] || `EXTENDED COMMAND ${c}${dt != null ? ` (DT${dt})` : ""}`
      : GEAR_COMMANDS[c] || `COMMAND ${c}`;
  // READ MEMORY LOCATION (197) answers although it is not named QUERY
  const query = name.startsWith("QUERY") || (c === 197 && dt == null);
  return { kind: query ? "query" : "command", target: label, name, text: `${label}: ${name}`, query };
}

/** Describes a sequence of frames, tracking ENABLE DEVICE TYPE for extended commands. */
export function describeFrames(frames: number[][]): Described[] {
  let dt: number | null = null;
  return frames.map((f) => {
    if (f.length !== 2) {
      dt = null;
      return describeFrame(f);
    }
    const d = describe16(f[0], f[1], dt);
    dt = f[0] === 0xc1 ? f[1] : d.kind === "special" ? dt : null;
    return d;
  });
}

/** Stateless description of a 24 bit forward frame. */
export function describe24(a: number, i: number, c: number): Described {
  if (!(a & 0x01)) {
    // bit 16 = 0 → event frame (incl. power cycle notification 0xFE…)
    const evt = decodeEvent([a, i, c]);
    let src = evt?.short_address != null ? `D${evt.short_address}` : evt?.device_group != null ? `DG${evt.device_group}` : evt?.instance_group != null ? `IG${evt.instance_group}` : evt?.instance_type != null ? `T${evt.instance_type}` : "";
    if (evt?.instance_number != null) src += `#${evt.instance_number}`;
    const name = evt?.scheme === "power_cycle" ? "POWER CYCLE NOTIFICATION" : `EVENT ${src}: info ${evt?.info ?? "?"}`;
    return { kind: "event", target: src, name, text: name, query: false };
  }
  if (a === 0xc1) {
    let name = `${SPECIAL_COMMANDS_24[i] || `SPECIAL 0x${hex2(i)}`} ${c}`;
    let warning: string | undefined;
    if (i === 0x01) name += ` (${initialise24(c)[0]})`;
    else if (i === 0x08) name = `PROGRAM SHORT ADDRESS ${programAddress(c, 24)}`;
    if (i === 0x02 || i === 0x08) warning = "addressing";
    return { kind: "special", target: "", name, text: name, query: ANSWERING_SPECIAL_24.has(i), warning };
  }
  if (a === 0xc5 || a === 0xc7 || a === 0xc9) {
    // IEC 62386-103 special commands with two parameter bytes
    const name = a === 0xc5 ? `DIRECT WRITE MEMORY offset ${i} = ${c}` : a === 0xc7 ? `DTR1:DTR0 = ${i}:${c}` : `DTR2:DTR1 = ${i}:${c}`;
    return { kind: "special", target: "", name, text: name, query: a === 0xc5 };
  }
  const label = address24Label(a);
  const name = i === 0xfe ? DEVICE_COMMANDS[c] || `COMMAND 0x${hex2(c)}` : INSTANCE_COMMANDS[c] || `INSTANCE COMMAND 0x${hex2(c)}`;
  const query = name.startsWith("QUERY") || (i === 0xfe && c === 0x3c);
  return { kind: query ? "query" : "command", target: label, name, text: `${label} [${instance24(i)}]: ${name}`, query };
}

export function describeFrame(bytes: number[]): Described {
  return bytes.length === 3 ? describe24(bytes[0], bytes[1], bytes[2]) : describe16(bytes[0], bytes[1]);
}

// -------------------------------------------------------------- 24 bit events
export interface DecodedEvent {
  scheme: string;
  info: number;
  short_address?: number | null;
  instance_type?: number | null;
  instance_number?: number | null;
  device_group?: number | null;
  instance_group?: number | null;
  event_type?: string | null;
  kind?: string;
  source_key?: string | null;
  attributes?: Record<string, any>;
}

export function decodeEvent(data: number[]): DecodedEvent | null {
  if (data.length !== 3) return null;
  const frame = (data[0] << 16) | (data[1] << 8) | data[2];
  if (frame & 0x010000) return null;
  const info = frame & 0x3ff;
  const b23 = !!(frame & 0x800000);
  const b22 = !!(frame & 0x400000);
  const b15 = !!(frame & 0x008000);
  const f5 = (frame >> 10) & 0x1f;
  // power cycle notification: bits 23..13 = 0x7F7; bit 12 group valid (11..7),
  // bit 6 address valid (5..0) - layout as in python-dali
  if ((frame & 0xffe000) === 0xfee000) {
    const attributes: Record<string, number> = {};
    if (frame & 0x1000) attributes.device_group = (frame >> 7) & 0x1f;
    if (frame & 0x40) attributes.short_address = frame & 0x3f;
    return { scheme: "power_cycle", info: frame & 0x1fff, event_type: "power_cycle", attributes };
  }
  // IEC 62386-103 event addressing schemes (bits 23, 22, 15)
  if (!b23) {
    const short = (frame >> 17) & 0x3f;
    return b15
      ? { scheme: "device_instance", info, short_address: short, instance_number: f5 }
      : { scheme: "device", info, short_address: short, instance_type: f5 };
  }
  const upper = (frame >> 17) & 0x1f;
  if (!b22) {
    return b15
      ? { scheme: "instance", info, instance_type: upper, instance_number: f5 }
      : { scheme: "device_group", info, device_group: upper, instance_type: f5 };
  }
  return b15 ? null : { scheme: "instance_group", info, instance_group: upper, instance_type: f5 };
}

// ------------------------------------------------------------- bit breakdown
export interface BitField {
  hi: number;
  lo: number;
  label: string;
  value: string;
  color: string;
}

const FIELD_COLORS = ["#1e88e5", "#43a047", "#ef6c00", "#ab47bc", "#d81b60", "#0097a7", "#6d4c41", "#546e7a"];

function fieldsFor(defs: [number, number, string, string][]): BitField[] {
  return defs.map(([hi, lo, label, value], i) => ({ hi, lo, label, value, color: FIELD_COLORS[i % FIELD_COLORS.length] }));
}

/** Splits a frame into its IEC 62386 bit fields for the detail view. */
export function frameFields(f: Frame, lang: Lang): BitField[] {
  const de = lang === "de";
  const d = f.data || [];
  const S = (bit: number) => (bit ? (de ? "1 = Befehl" : "1 = command") : de ? "0 = DAPC (Dimmwert)" : "0 = DAPC (level)");
  if (d.length === 1) {
    return fieldsFor([[7, 0, de ? "Antwortwert" : "Answer value", `${d[0]} · 0x${hex2(d[0])}`]]);
  }
  if (d.length === 2) {
    const [a, c] = d;
    const desc = describe16(a, c);
    if (desc.kind === "special") {
      return fieldsFor([
        [15, 8, de ? "Spezialbefehl (Opcode)" : "Special command (opcode)", `0x${hex2(a)} ${SPECIAL_COMMANDS_16[a] || ""}`],
        [7, 0, de ? "Datenbyte" : "Data byte", `${c} · 0x${hex2(c)}`],
      ]);
    }
    const s = a & 1;
    const second: [number, number, string, string] = s
      ? [7, 0, "Opcode", `${c} · ${desc.name}`]
      : [7, 0, de ? "Dimmwert (Arc Power)" : "Arc power level", c === 255 ? "MASK" : `${c} ≙ ${levelPct(c)}`];
    if (a <= 0x7f) {
      return fieldsFor([
        [15, 15, de ? "Adresstyp" : "Address type", de ? "0 = Kurzadresse" : "0 = short address"],
        [14, 9, de ? "Kurzadresse" : "Short address", `${a >> 1} (A${a >> 1})`],
        [8, 8, de ? "Selektor S" : "Selector S", S(s)],
        second,
      ]);
    }
    if (a <= 0x9f) {
      return fieldsFor([
        [15, 13, de ? "Adresstyp" : "Address type", de ? "100 = Gruppe" : "100 = group"],
        [12, 9, de ? "Gruppe" : "Group", `${(a >> 1) & 0x0f} (G${(a >> 1) & 0x0f})`],
        [8, 8, de ? "Selektor S" : "Selector S", S(s)],
        second,
      ]);
    }
    const unaddr = a === 0xfc || a === 0xfd;
    return fieldsFor([
      [15, 9, de ? "Adresstyp" : "Address type", unaddr ? (de ? "1111110 = Broadcast an Unadressierte" : "1111110 = broadcast unaddressed") : de ? "1111111 = Broadcast" : "1111111 = broadcast"],
      [8, 8, de ? "Selektor S" : "Selector S", S(s)],
      second,
    ]);
  }
  if (d.length === 3) {
    const [a, i, c] = d;
    const evt = decodeEvent(d);
    if (evt) {
      const info: [number, number, string, string] = [9, 0, de ? "Ereignisinformation" : "Event information", `${evt.info} · 0b${evt.info.toString(2).padStart(10, "0")}`];
      const typeName = (t: number | null | undefined) => (t == null ? "" : `${t} (${INSTANCE_TYPES[t]?.[lang] ?? "?"})`);
      if (evt.scheme === "power_cycle") {
        const pa = evt.attributes || {};
        return fieldsFor([
          [23, 13, de ? "Power-Cycle-Benachrichtigung" : "Power cycle notification", "0x7F7"],
          [12, 12, de ? "Gruppe gültig" : "Group valid", pa.device_group != null ? "1" : "0"],
          [11, 7, de ? "Gerätegruppe" : "Device group", pa.device_group != null ? String(pa.device_group) : "–"],
          [6, 6, de ? "Adresse gültig" : "Address valid", pa.short_address != null ? "1" : "0"],
          [5, 0, de ? "Kurzadresse" : "Short address", pa.short_address != null ? `D${pa.short_address}` : "–"],
        ]);
      }
      if (evt.scheme === "device" || evt.scheme === "device_instance") {
        const byNumber = evt.scheme === "device_instance";
        return fieldsFor([
          [23, 23, de ? "Schema" : "Scheme", de ? "0 = Kurzadresse" : "0 = short address"],
          [22, 17, de ? "Kurzadresse" : "Short address", `${evt.short_address} (D${evt.short_address})`],
          [16, 16, "Frame", de ? "0 = Ereignis" : "0 = event"],
          [15, 15, de ? "Instanz-Schema" : "Instance scheme", byNumber ? (de ? "1 = Instanznummer" : "1 = instance number") : de ? "0 = Instanztyp" : "0 = instance type"],
          [14, 10, byNumber ? (de ? "Instanznummer" : "Instance number") : de ? "Instanztyp" : "Instance type", byNumber ? String(evt.instance_number) : typeName(evt.instance_type)],
          info,
        ]);
      }
      if (evt.scheme === "instance") {
        return fieldsFor([
          [23, 22, de ? "Schema" : "Scheme", de ? "10 + Bit 15 = 1: Instanz (ohne Adresse)" : "10 + bit 15 = 1: instance (no address)"],
          [21, 17, de ? "Instanztyp" : "Instance type", typeName(evt.instance_type)],
          [16, 16, "Frame", de ? "0 = Ereignis" : "0 = event"],
          [15, 15, "Bit 15", "1"],
          [14, 10, de ? "Instanznummer" : "Instance number", String(evt.instance_number)],
          info,
        ]);
      }
      return fieldsFor([
        [23, 22, de ? "Schema" : "Scheme", evt.scheme === "device_group" ? (de ? "10 = Gerätegruppe" : "10 = device group") : de ? "11 = Instanzgruppe" : "11 = instance group"],
        [21, 17, de ? "Gruppe" : "Group", String(evt.device_group ?? evt.instance_group)],
        [16, 16, "Frame", de ? "0 = Ereignis" : "0 = event"],
        [15, 15, "Bit 15", "0"],
        [14, 10, de ? "Instanztyp" : "Instance type", typeName(evt.instance_type)],
        info,
      ]);
    }
    const desc = describe24(a, i, c);
    if (a === 0xc5 || a === 0xc7 || a === 0xc9) {
      return fieldsFor([
        [23, 16, de ? "Spezialbefehl" : "Special command", `0x${hex2(a)} ${a === 0xc5 ? "DIRECT WRITE MEMORY" : a === 0xc7 ? "DTR1:DTR0" : "DTR2:DTR1"}`],
        [15, 8, a === 0xc5 ? "Offset" : a === 0xc7 ? "DTR1" : "DTR2", `${i} · 0x${hex2(i)}`],
        [7, 0, a === 0xc5 ? (de ? "Wert" : "Value") : a === 0xc7 ? "DTR0" : "DTR1", `${c} · 0x${hex2(c)}`],
      ]);
    }
    if (a === 0xc1) {
      return fieldsFor([
        [23, 16, de ? "Spezialbefehl-Kennung" : "Special command marker", "0xC1"],
        [15, 8, de ? "Spezialbefehl" : "Special command", `0x${hex2(i)} ${SPECIAL_COMMANDS_24[i] || ""}`],
        [7, 0, de ? "Datenbyte" : "Data byte", `${c} · 0x${hex2(c)}`],
      ]);
    }
    const addrField: [number, number, string, string][] =
      !(a & 0x80)
        ? [
            [23, 23, de ? "Adresstyp" : "Address type", de ? "0 = Kurzadresse" : "0 = short address"],
            [22, 17, de ? "Kurzadresse" : "Short address", `${(a >> 1) & 0x3f} (D${(a >> 1) & 0x3f})`],
          ]
        : (a & 0xc0) === 0x80
          ? [
              [23, 22, de ? "Adresstyp" : "Address type", de ? "10 = Gerätegruppe" : "10 = device group"],
              [21, 17, de ? "Gerätegruppe" : "Device group", `${(a >> 1) & 0x1f}`],
            ]
          : [[23, 17, de ? "Adresstyp" : "Address type", a >= 0xfe ? "Broadcast" : a >= 0xfc ? (de ? "Broadcast unadressiert" : "Broadcast unaddressed") : `0x${hex2(a)}`]];
    return fieldsFor([
      ...addrField,
      [16, 16, "Frame", de ? "1 = Befehl" : "1 = command"],
      [15, 8, de ? "Instanzbyte" : "Instance byte", `0x${hex2(i)} (${instance24(i)})`],
      [7, 0, "Opcode", `0x${hex2(c)} · ${desc.name}`],
    ]);
  }
  return fieldsFor([[d.length * 8 - 1, 0, "Frame", bytesHex(d)]]);
}

// ---------------------------------------------------------- answer decoding
export interface BitInfo {
  bit: number;
  label: string;
  set: boolean;
  severity: "err" | "warn" | "info" | "";
}
export interface AnswerExplain {
  summary: string;
  bits?: BitInfo[];
}

export const GEAR_STATUS_BITS: { de: string; en: string; sev: BitInfo["severity"] }[] = [
  { de: "Betriebsgerätefehler", en: "Control gear failure", sev: "err" },
  { de: "Lampenfehler", en: "Lamp failure", sev: "err" },
  { de: "Lampe an", en: "Lamp on", sev: "" },
  { de: "Grenzwertfehler (Limit Error)", en: "Limit error", sev: "warn" },
  { de: "Fading läuft", en: "Fade running", sev: "" },
  { de: "Reset-Zustand", en: "Reset state", sev: "info" },
  { de: "Kurzadresse fehlt", en: "Short address missing", sev: "warn" },
  { de: "Netzunterbrechung erkannt (Power Cycle)", en: "Power cycle seen", sev: "info" },
];

const DEVICE_STATUS_BITS: { de: string; en: string; sev: BitInfo["severity"] }[] = [
  { de: "Eingabegerätefehler", en: "Input device error", sev: "err" },
  { de: "Ruhemodus (Quiescent)", en: "Quiescent mode", sev: "info" },
  { de: "Kurzadresse fehlt", en: "Short address missing", sev: "warn" },
  { de: "Application Controller aktiv", en: "Application active", sev: "" },
  { de: "Application-Controller-Fehler", en: "Application controller error", sev: "err" },
  { de: "Netzunterbrechung erkannt (Power Cycle)", en: "Power cycle seen", sev: "info" },
  { de: "Reset-Zustand", en: "Reset state", sev: "info" },
  { de: "reserviert", en: "reserved", sev: "" },
];

const LIGHT_SOURCE: Record<number, L> = {
  0: { de: "Niederdruck-Entladungslampe", en: "Low pressure fluorescent" },
  2: { de: "Hochdruck-Entladungslampe", en: "High intensity discharge" },
  3: { de: "NV-Halogen", en: "Low voltage halogen" },
  4: { de: "Glühlampe", en: "Incandescent" },
  6: { de: "LED", en: "LED" },
  7: { de: "OLED", en: "OLED" },
  252: { de: "Andere", en: "Other" },
  253: { de: "Unbekannt", en: "Unknown" },
  254: { de: "Keine", en: "None" },
  255: { de: "Mehrere", en: "Multiple" },
};

const YES_NO = [
  "QUERY CONTROL GEAR PRESENT",
  "QUERY LAMP FAILURE",
  "QUERY LAMP POWER ON",
  "QUERY LIMIT ERROR",
  "QUERY RESET STATE",
  "QUERY MISSING SHORT ADDRESS",
  "QUERY POWER FAILURE",
  "QUERY CONTROL GEAR FAILURE",
  "QUERY QUIESCENT MODE",
  "QUERY INSTANCE ENABLED",
  "QUERY APPLICATION CONTROL ENABLED",
  "QUERY POWER CYCLE NOTIFICATION",
  "QUERY APPLICATION CONTROLLER ALWAYS ACTIVE",
  "QUERY APPLICATION CONTROLLER ERROR",
  "QUERY INPUT DEVICE ERROR",
  "COMPARE",
  "VERIFY SHORT ADDRESS",
];

function statusBits(v: number, defs: typeof GEAR_STATUS_BITS, lang: Lang): BitInfo[] {
  return defs.map((d, bit) => ({ bit, label: d[lang], set: !!(v & (1 << bit)), severity: d.sev }));
}

/** Human readable interpretation of an 8 bit answer to the given query (name or "A3: NAME"). */
export function explainAnswer(query: string | undefined | null, v: number, lang: Lang): AnswerExplain | null {
  if (!query || v == null || v < 0 || v > 255) return null;
  const de = lang === "de";
  const name = query.includes(": ") ? query.slice(query.lastIndexOf(": ") + 2).trim() : query.trim();
  const base = name.replace(/\s+\d+$/, "");
  if (name === "QUERY STATUS") {
    const bits = statusBits(v, GEAR_STATUS_BITS, lang);
    const active = bits.filter((b) => b.set).map((b) => b.label);
    return { summary: active.length ? active.join(", ") : de ? "Keine Statusbits gesetzt – Lampe aus, alles in Ordnung" : "No status bits set – lamp off, all fine", bits };
  }
  if (name === "QUERY DEVICE STATUS") {
    const bits = statusBits(v, DEVICE_STATUS_BITS, lang).slice(0, 7);
    const active = bits.filter((b) => b.set).map((b) => b.label);
    return { summary: active.length ? active.join(", ") : de ? "Keine Statusbits gesetzt" : "No status bits set", bits };
  }
  if (
    ["QUERY ACTUAL LEVEL", "QUERY MAX LEVEL", "QUERY MIN LEVEL", "QUERY POWER ON LEVEL", "QUERY SYSTEM FAILURE LEVEL", "QUERY PHYSICAL MINIMUM", "QUERY CONTENT DTR0"].includes(name) ||
    base === "QUERY SCENE LEVEL"
  ) {
    if (v === 255) return { summary: de ? "MASK (255) – kein Wert / nicht Teil der Szene" : "MASK (255) – no value / not part of the scene" };
    if (name === "QUERY CONTENT DTR0") return { summary: `DTR0 = ${v}` };
    return { summary: de ? `Dimmwert ${v} von 254 ≙ ${levelPct(v)}` : `Level ${v} of 254 ≙ ${levelPct(v)}` };
  }
  if (name === "QUERY DEVICE TYPE" || name === "QUERY NEXT DEVICE TYPE") {
    if (v === 255) return { summary: de ? "Mehrere Gerätetypen – mit QUERY NEXT DEVICE TYPE einzeln abfragen" : "Multiple device types – use QUERY NEXT DEVICE TYPE" };
    if (v === 254) return { summary: de ? "Kein (weiterer) Gerätetyp" : "No (further) device type" };
    return { summary: `DT${v} – ${DALI_TYPES[v]?.[lang] ?? (de ? "unbekannt" : "unknown")}` };
  }
  const groupRange = name.match(/GROUPS (\d+)-(\d+)$/);
  if (groupRange) {
    const start = Number(groupRange[1]);
    const groups = Array.from({ length: 8 }, (_, i) => i).filter((i) => v & (1 << i)).map((i) => start + i);
    return {
      summary: groups.length ? `${de ? "Mitglied in Gruppe" : "Member of group"} ${groups.join(", ")}` : de ? "In keiner dieser Gruppen" : "Not a member of these groups",
      bits: Array.from({ length: 8 }, (_, i) => ({ bit: i, label: `${de ? "Gruppe" : "Group"} ${start + i}`, set: !!(v & (1 << i)), severity: "" as const })),
    };
  }
  if (name === "QUERY FADE TIME/FADE RATE") {
    const ft = v >> 4;
    const fr = v & 0x0f;
    const time = ft === 0 ? (de ? "keine (Extended Fade Time)" : "none (extended fade time)") : `${FADE_TIMES[ft]} s`;
    const rate = fr === 0 ? "–" : `${FADE_RATES[fr - 1]} ${de ? "Schritte/s" : "steps/s"}`;
    return { summary: `${de ? "Fadezeit" : "Fade time"} ${ft} → ${time} · ${de ? "Faderate" : "Fade rate"} ${fr} → ${rate}` };
  }
  if (name === "QUERY VERSION NUMBER") return { summary: `${de ? "Version" : "Version"} ${v >> 2}.${v & 3} (IEC 62386 ${de ? "Edition" : "edition"} ${v >> 2})` };
  if (name === "QUERY LIGHT SOURCE TYPE") return { summary: LIGHT_SOURCE[v]?.[lang] ?? `${de ? "Typ" : "Type"} ${v}` };
  if (name === "QUERY OPERATING MODE") return { summary: v === 0 ? (de ? "Normalbetrieb (0)" : "Normal operation (0)") : v >= 0x80 ? (de ? `Herstellerspezifischer Modus ${v}` : `Manufacturer specific mode ${v}`) : `${de ? "Modus" : "Mode"} ${v}` };
  if (name === "QUERY INSTANCE TYPE") return { summary: `${de ? "Instanztyp" : "Instance type"} ${v} – ${INSTANCE_TYPES[v]?.[lang] ?? "?"}` };
  if (name === "QUERY NUMBER OF INSTANCES") return { summary: de ? `${v} Instanz(en)` : `${v} instance(s)` };
  if (name.startsWith("QUERY SHORT ADDRESS")) return { summary: v === 255 ? (de ? "Keine Kurzadresse (MASK)" : "No short address (MASK)") : `${de ? "Kurzadresse" : "Short address"} ${v >> 1}` };
  if (name.startsWith("QUERY RANDOM ADDRESS")) return { summary: `0x${hex2(v)}` };
  if (name.startsWith("QUERY CONTENT DTR")) return { summary: `${name.replace("QUERY CONTENT ", "")} = ${v}` };
  if (YES_NO.some((q) => name.startsWith(q))) {
    return { summary: v === 255 ? (de ? "JA (0xFF)" : "YES (0xFF)") : de ? `Antwort vorhanden (${v}) ≙ JA` : `Answer present (${v}) ≙ YES` };
  }
  return null;
}

/** Extracts the query a backward frame answers ("A7: QUERY STATUS"). */
export function answerTo(f: Frame): string | undefined {
  if (f.answer_to) return f.answer_to;
  const i = f.text?.indexOf("← ") ?? -1;
  return i >= 0 ? f.text.slice(i + 2).trim() : undefined;
}

/** Normalises a row of GET /api/monitor?before=… (DB) to the live frame shape. */
export function fromDbRow(r: any): Frame {
  const data: number[] = Array.isArray(r.data) ? r.data : [];
  const f: Frame = {
    id: r.id,
    db: true,
    line: r.line ?? 0,
    bits: r.bits ?? data.length * 8,
    data,
    hex: bytesHex(data),
    external: !!r.external,
    query: r.kind === "query" && !r.external,
    timestamp: r.timestamp ?? r.ts,
    kind: r.kind || "unknown",
    target: r.target || "",
    text: r.text || "",
  };
  const a = answerTo(f);
  if (a) f.answer_to = a;
  if (/^(RANDOMISE|PROGRAM SHORT ADDRESS)/.test(f.text)) f.warning = "addressing";
  return f;
}

// ------------------------------------------------------------ frame rate
/** Frames per second over a sliding window, fed by the live monitor stream. */
export function useFrameRate(windowSec = 10) {
  const arrivals: number[] = [];
  const rate = ref(0);
  // seed from frames already received (gateway timestamps) so the value is right immediately
  const nowS = Date.now() / 1000;
  const perfNow = performance.now();
  for (const f of toRaw(state.monitor)) {
    const age = nowS - (f.timestamp || 0);
    if (age >= 0 && age <= windowSec) arrivals.push(perfNow - age * 1000);
  }
  arrivals.sort((a, b) => a - b);
  const update = () => {
    const cut = performance.now() - windowSec * 1000;
    let i = 0;
    while (i < arrivals.length && arrivals[i] < cut) i++;
    if (i) arrivals.splice(0, i);
    rate.value = arrivals.length / windowSec;
  };
  update();
  const off = onMonitor(() => arrivals.push(performance.now()));
  const timer = window.setInterval(update, 1000);
  onBeforeUnmount(() => {
    off();
    clearInterval(timer);
  });
  return rate;
}

// --------------------------------------------------- command tab session state
export interface CommandHistoryEntry {
  id: number;
  ts: number;
  line: number;
  bits: 16 | 24;
  frames: number[][];
  text: string;
  answers: number[];
  ms: number;
  error?: string;
  query: boolean;
  queryName?: string;
}

/** Commands sent in this browser session (kept while navigating between views). */
export const commandHistory = reactive<CommandHistoryEntry[]>([]);

/** A frame handed over from the monitor to the command builder. */
export const commandDraft = ref<{ line: number; frames: number[][] } | null>(null);
