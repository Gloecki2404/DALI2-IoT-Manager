// Shared, reactive cache of all gateway automations (loaded once by the page, reloaded per kind after changes).
import { reactive } from "vue";
import { gw } from "../../lib/api";
import type {
  CircadianItem,
  EventTriggerItem,
  LineConfig,
  SchedulerItem,
  SequenceItem,
  TriggerActionItem,
} from "./util";

export type AutoKind = "sequences" | "schedules" | "circadians" | "triggers" | "events" | "queries";
export const AUTO_KINDS: AutoKind[] = ["sequences", "schedules", "circadians", "triggers", "events", "queries"];

export const auto = reactive({
  loaded: false,
  loading: {} as Record<string, boolean>,
  errors: {} as Record<string, string>,
  sequences: [] as SequenceItem[],
  test: null as SequenceItem | null,
  schedules: [] as SchedulerItem[],
  circadians: [] as CircadianItem[],
  triggers: [] as TriggerActionItem[],
  events: [] as EventTriggerItem[],
  queries: {} as Record<string, LineConfig>,
  bounds: { min: 0.5, max: 3600 },
});

let boundsLoaded = false;

const loaders: Record<AutoKind, () => Promise<void>> = {
  sequences: async () => {
    const r = await gw.get("/automations/sequences");
    auto.sequences = Array.isArray(r?.sequences) ? r.sequences : [];
  },
  schedules: async () => {
    const r = await gw.get("/automations/schedules");
    auto.schedules = Array.isArray(r?.schedulers) ? r.schedulers : [];
  },
  circadians: async () => {
    const r = await gw.get("/automations/circadians");
    auto.circadians = Array.isArray(r?.circadians) ? r.circadians : [];
  },
  triggers: async () => {
    const r = await gw.get("/automations/triggerActions");
    auto.triggers = Array.isArray(r?.triggerActions) ? r.triggerActions : [];
  },
  events: async () => {
    const r = await gw.get("/automations/eventTriggerActions");
    auto.events = Array.isArray(r) ? r : Array.isArray(r?.eventTriggerActions) ? r.eventTriggerActions : [];
  },
  queries: async () => {
    const r = await gw.get("/automations/statusQueries");
    auto.queries = r && typeof r === "object" && !Array.isArray(r) ? r : {};
    if (!boundsLoaded) {
      try {
        const b = await gw.get("/automations/statusQueries/bounds");
        if (typeof b?.minDelayBetweenQueries === "number") auto.bounds.min = b.minDelayBetweenQueries;
        if (typeof b?.maxDelayBetweenQueries === "number") auto.bounds.max = b.maxDelayBetweenQueries;
        boundsLoaded = true;
      } catch {
        /* older firmware: keep documented defaults 0.5 … 3600 s */
      }
    }
  },
};

export async function load(kind: AutoKind): Promise<void> {
  auto.loading[kind] = true;
  try {
    await loaders[kind]();
    delete auto.errors[kind];
  } catch (e: any) {
    auto.errors[kind] = e?.message || String(e);
  } finally {
    auto.loading[kind] = false;
  }
}

export async function loadTest(): Promise<void> {
  try {
    auto.test = await gw.get("/automations/sequence/test");
  } catch {
    auto.test = null;
  }
}

// ------------------------------------------------------------------ running-state polling
// Sequences report "active" only on request → poll while something runs (or shortly after a start).
let pollUntil = 0;
let pollTimer: number | undefined;
let polling = false;

/** Keep polling for the next few seconds (e.g. right after a start). */
export function pollSoon(ms = 15000) {
  pollUntil = Math.max(pollUntil, Date.now() + ms);
}

async function pollTick() {
  if (polling || document.hidden) return;
  const need = auto.sequences.some((s) => s.active) || !!auto.test?.active || Date.now() < pollUntil;
  if (!need) return;
  polling = true;
  try {
    await Promise.all([load("sequences"), loadTest()]);
  } finally {
    polling = false;
  }
}

export function startPolling(intervalMs = 2500) {
  stopPolling();
  pollTimer = window.setInterval(pollTick, intervalMs);
}
export function stopPolling() {
  if (pollTimer !== undefined) window.clearInterval(pollTimer);
  pollTimer = undefined;
}

let locationPromise:Promise<{ lat: number; lon: number } | null> | null = null;
/** Gateway location (cached; null when unknown / not set). */
export function getLocation(): Promise<{ lat: number; lon: number } | null> {
  if (!locationPromise) {
    locationPromise = gw
      .get("/location")
      .then((loc) =>
        typeof loc?.lat === "number" && typeof loc?.lon === "number" && !(loc.lat === 0 && loc.lon === 0)
          ? { lat: loc.lat, lon: loc.lon }
          : null,
      )
      .catch(() => {
        locationPromise = null;
        return null;
      });
  }
  return locationPromise;
}

export async function loadAll(): Promise<void> {
  await Promise.all([...AUTO_KINDS.map(load), loadTest()]);
  auto.loaded = true;
}
