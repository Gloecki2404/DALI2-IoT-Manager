import { reactive, ref } from "vue";

export interface DeviceStatus {
  raw: number;
  controlGearFailure: boolean;
  lampFailure: boolean;
  lampOn: boolean;
  limitError: boolean;
  fadeRunning: boolean;
  resetState: boolean;
  isUnaddressed: boolean;
  powerCycleSeen: boolean;
}

export interface Device {
  id: number;
  name: string;
  type: string;
  available: boolean;
  status: DeviceStatus;
  features: Record<string, any>;
  groups: number[];
  address: number;
  line: number;
  daliTypes: number[];
}

export interface Target {
  type: "device" | "group" | "zone" | "broadcast" | "daliGear";
  id: number | null;
}

export interface Zone {
  id: number;
  name: string;
  targets: Target[];
  features: Record<string, any>;
}

export interface Sensor {
  id: number;
  name: string;
  unit: string;
  type: string;
  value: number;
  timestamp: string;
  addressType: string;
  daliSensorAddress?: { line: number; address: number; instanceNumber: number };
}

export interface MonitorFrame {
  line: number;
  bits: number;
  data: number[];
  hex: string;
  external: boolean;
  query: boolean;
  timestamp: number;
  kind: string;
  target: string;
  text: string;
  event?: any;
  answer_to?: string;
}

export interface AddonEvent {
  ts: number;
  level: string;
  category: string;
  device_id: number | null;
  message: string;
  data?: any;
}

export const state = reactive({
  wsConnected: false,
  status: null as any,
  info: {} as any,
  devices: {} as Record<number, Device>,
  zones: {} as Record<number, Zone>,
  sensors: {} as Record<number, Sensor>,
  scan: null as any,
  monitor: [] as MonitorFrame[],
  events: [] as AddonEvent[],
  expert: false,
  loaded: false,
});

try {
  state.expert = localStorage.getItem("lunatone.expert") === "1";
} catch {
  /* ignore */
}

export function setExpert(v: boolean) {
  state.expert = v;
  try {
    localStorage.setItem("lunatone.expert", v ? "1" : "0");
  } catch {
    /* ignore */
  }
}

const MONITOR_MAX = 3000;
type MonitorListener = (f: MonitorFrame) => void;
const monitorListeners = new Set<MonitorListener>();
export function onMonitor(fn: MonitorListener) {
  monitorListeners.add(fn);
  return () => monitorListeners.delete(fn);
}

function deepMerge(base: any, update: any) {
  for (const [k, v] of Object.entries(update)) {
    if (v && typeof v === "object" && !Array.isArray(v) && base[k] && typeof base[k] === "object" && !Array.isArray(base[k])) {
      deepMerge(base[k], v);
    } else {
      base[k] = v;
    }
  }
  return base;
}

function normalize(dev: any) {
  if (dev?.status && "shortAddress" in dev.status) {
    if (!("isUnaddressed" in dev.status)) dev.status.isUnaddressed = dev.status.shortAddress;
    delete dev.status.shortAddress;
  }
  return dev;
}

function applySnapshot(data: any) {
  state.info = data.info || {};
  state.devices = Object.fromEntries((data.devices || []).map((d: Device) => [d.id, normalize(d)]));
  state.zones = Object.fromEntries((data.zones || []).map((z: Zone) => [z.id, z]));
  state.sensors = Object.fromEntries((data.sensors || []).map((s: Sensor) => [s.id, s]));
  state.loaded = true;
}

export const monitorPaused = ref(false);

function handle(msg: any) {
  const { type, data } = msg;
  switch (type) {
    case "addon_status":
      state.status = { ...(state.status || {}), ...data, gateway: data.gateway ?? data };
      break;
    case "snapshot":
      applySnapshot(data);
      break;
    case "info":
      state.info = data;
      break;
    case "devices":
      for (const d of data.devices || []) {
        if (state.devices[d.id]) deepMerge(state.devices[d.id], normalize(d));
      }
      break;
    case "zones":
      for (const z of data.zones || []) {
        if (state.zones[z.id]) deepMerge(state.zones[z.id], z);
      }
      break;
    case "sensors":
      for (const s of data.sensors || []) {
        if (state.sensors[s.id]) deepMerge(state.sensors[s.id], s);
        else state.sensors[s.id] = s;
      }
      break;
    case "scan":
      state.scan = deepMerge(state.scan || {}, data);
      break;
    case "monitor":
      for (const fn of monitorListeners) fn(data);
      if (!monitorPaused.value) {
        state.monitor.push(data);
        if (state.monitor.length > MONITOR_MAX) state.monitor.splice(0, state.monitor.length - MONITOR_MAX);
      }
      break;
    case "addon_event":
      state.events.unshift(data);
      if (state.events.length > 500) state.events.length = 500;
      break;
    default:
      break;
  }
}

let socket: WebSocket | null = null;
let retry = 1000;

export function connect() {
  const url = new URL("api/ws", window.location.href);
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  socket = new WebSocket(url.toString());
  socket.onopen = () => {
    state.wsConnected = true;
    retry = 1000;
  };
  socket.onmessage = (ev) => {
    try {
      handle(JSON.parse(ev.data));
    } catch (e) {
      console.warn("bad message", e);
    }
  };
  socket.onclose = () => {
    state.wsConnected = false;
    setTimeout(connect, retry);
    retry = Math.min(retry * 2, 15000);
  };
}

export function gatewayOnline(): boolean {
  return !!state.status?.gateway?.connected;
}

// ---------------------------------------------------------------- toasts
export interface Toast {
  id: number;
  text: string;
  kind: "info" | "success" | "error";
}
export const toasts = reactive<Toast[]>([]);
let toastId = 0;
export function toast(text: string, kind: Toast["kind"] = "info", ms = 3500) {
  const id = ++toastId;
  toasts.push({ id, text, kind });
  setTimeout(() => {
    const i = toasts.findIndex((t) => t.id === id);
    if (i >= 0) toasts.splice(i, 1);
  }, ms);
}

export async function run<T>(fn: () => Promise<T>, success?: string): Promise<T | undefined> {
  try {
    const r = await fn();
    if (success) toast(success, "success");
    return r;
  } catch (e: any) {
    toast(e?.message || String(e), "error", 6000);
    return undefined;
  }
}

// --------------------------------------------------------------- confirm
export interface ConfirmRequest {
  title: string;
  message: string;
  danger?: boolean;
  confirmText?: string;
  typeToConfirm?: string;
  resolve: (v: boolean) => void;
}
export const confirmState = reactive<{ current: ConfirmRequest | null }>({ current: null });

export function confirmDialog(opts: Omit<ConfirmRequest, "resolve">): Promise<boolean> {
  return new Promise((resolve) => {
    confirmState.current = { ...opts, resolve };
  });
}

// The gateway does not always report colour temperature back → remember what we sent.
export const sentKelvin = reactive(new Map<string, { k: number; reported: number | null }>());
