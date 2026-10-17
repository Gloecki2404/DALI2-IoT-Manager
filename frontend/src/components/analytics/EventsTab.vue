<template>
  <div class="events">
    <div class="card tb">
      <div class="row wrap cats">
        <button class="chip clickable cat" :class="{ primary: !category }" @click="category = ''">
          {{ t("all") }} <span class="cnt">{{ merged.length }}</span>
        </button>
        <button v-for="c in CATEGORIES" :key="c" class="chip clickable cat" :class="{ primary: category === c }" @click="category = category === c ? '' : c">
          <Icon :path="catIcon(c)" :size="14" />{{ catLabel(c) }} <span class="cnt">{{ catCounts[c] || 0 }}</span>
        </button>
      </div>
      <div class="row wrap filters">
        <div class="btn-group">
          <button v-for="l in LEVELS" :key="l" :class="{ active: levels.includes(l) }" @click="toggleLevel(l)">
            <span class="dot" :class="levelDot(l)"></span>&nbsp;{{ t(`lv_${l}`) }}
          </button>
        </div>
        <input v-model="search" type="search" class="search" :placeholder="t('search')" />
        <span class="grow"></span>
        <span v-if="loading" class="spinner"></span>
        <button class="btn flat sm" :disabled="!filtered.length" :title="t('exportHint')" @click="exportJson">
          <Icon :path="mdiCodeJson" :size="16" />{{ t("export") }}
        </button>
      </div>
    </div>

    <div v-if="error && !rows.length" class="banner err mt">
      <Icon :path="mdiAlertCircle" :size="18" /><div>{{ error }}</div>
    </div>

    <Card v-if="merged.length" :title="t('chart')" :icon="mdiChartBar" :subtitle="t('chartSub', { b: bucketLabel })" class="mt">
      <LineChart type="bar" :datasets="chartDatasets" :height="170" stacked />
    </Card>

    <Empty v-if="!loading && !filtered.length" class="card mt" :icon="mdiTimelineClockOutline" :text="merged.length ? t('noMatch') : t('noEvents')" />

    <div v-else class="timeline mt">
      <template v-for="g in grouped" :key="g.day">
        <div class="section-title day">{{ g.label }} <span class="faint norm">· {{ g.items.length }}</span></div>
        <div class="card">
          <div class="list">
            <div v-for="(e, i) in g.items" :key="`${e.ts}-${i}`" class="list-item ev" :class="`lv-${e.level}`">
              <span class="icon-bubble sm" :class="levelCls(e.level)"><Icon :path="levelIcon(e.level)" :size="18" /></span>
              <div class="grow minw">
                <div class="title msg">{{ message(e) }}</div>
                <div class="row wrap sub meta">
                  <span class="mono">{{ fmtTime(e.ts, lang, false) }}</span>
                  <span class="chip mini"><Icon :path="catIcon(e.category)" :size="12" />{{ catLabel(e.category) }}</span>
                  <span v-if="e.device_id !== null && e.device_id !== undefined" class="dev">{{ devName(e.device_id) }}</span>
                  <span v-if="e.live" class="chip ok mini">{{ t("live") }}</span>
                </div>
                <details v-if="e.data && typeof e.data === 'object' && Object.keys(e.data).length" class="data">
                  <summary class="small">{{ t("data") }}</summary>
                  <pre class="mono small">{{ JSON.stringify(e.data, null, 2) }}</pre>
                </details>
              </div>
            </div>
          </div>
        </div>
      </template>
      <div v-if="filtered.length > shownCount" class="center mt">
        <button class="btn outline sm" @click="shownCount += 200">{{ t("more", { n: filtered.length - shownCount }) }}</button>
      </div>
    </div>

    <Card v-if="state.expert" :title="t('clearTitle')" :icon="mdiDatabaseRemove" icon-class="err" :subtitle="t('clearSub')" class="mt-lg">
      <div class="clear-grid">
        <div v-for="w in WHATS" :key="w" class="clear-item">
          <div class="grow">
            <div class="title-s">{{ t(`w_${w}`) }}</div>
            <div class="small muted">{{ t(`w_${w}_d`) }}</div>
          </div>
          <button class="btn danger outline sm" :disabled="clearing" @click="clearHistory(w)">
            <Icon :path="mdiTrashCanOutline" :size="16" />{{ t("clearBtn") }}
          </button>
        </div>
      </div>
    </Card>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import {
  mdiAlert,
  mdiAlertCircle,
  mdiChartBar,
  mdiChip,
  mdiCodeJson,
  mdiDatabaseRemove,
  mdiGestureTapButton,
  mdiInformation,
  mdiLanConnect,
  mdiLightbulbAlert,
  mdiRouterNetwork,
  mdiTag,
  mdiTimelineClockOutline,
  mdiTrashCanOutline,
} from "@mdi/js";
import Card from "../Card.vue";
import Icon from "../Icon.vue";
import Empty from "../Empty.vue";
import LineChart from "../LineChart.vue";
import { api } from "../../lib/api";
import { confirmDialog, run, state, type AddonEvent } from "../../lib/store";
import { lang, useT } from "../../lib/i18n";
import { fmtTime } from "../../lib/dali";
import { downloadJson, fmtDay, themeColors, alpha } from "./util";

const props = defineProps<{ hours: number; refresh: number }>();

const t = useT({
  de: {
    search: "Meldungen durchsuchen…",
    export: "JSON",
    exportHint: "Gefilterte Ereignisse als JSON herunterladen",
    lv_error: "Fehler",
    lv_warning: "Warnung",
    lv_info: "Info",
    cat_availability: "Erreichbarkeit",
    cat_lamp_failure: "Lampenfehler",
    cat_gear_failure: "Betriebsgerät",
    cat_gateway: "Gateway",
    cat_input: "Eingänge",
    chart: "Ereignisse im Zeitverlauf",
    chartSub: "je {b}, nach Schweregrad",
    hour: "Stunde",
    day: "Tag",
    noEvents: "Im gewählten Zeitraum sind keine Ereignisse aufgetreten.",
    noMatch: "Keine Ereignisse passen zu den Filtern.",
    data: "Daten",
    more: "{n} weitere anzeigen",
    clearTitle: "Verlauf löschen",
    clearSub: "Expertenmodus – gelöschte Daten können nicht wiederhergestellt werden",
    clearBtn: "Löschen",
    w_monitor: "Busmonitor",
    w_monitor_d: "Alle aufgezeichneten DALI-Frames (Monitor-Verlauf, CSV-Export).",
    w_bus: "Busstatistik",
    w_bus_d: "Buslast und Antwortquoten (Tabs „Buslast“ und „Kommunikation“).",
    w_events: "Ereignisse",
    w_events_d: "Das Ereignisprotokoll dieser Seite.",
    w_all: "Alles",
    w_all_d: "Sämtliche Verläufe inkl. Gerätezustände, Messwerte und Sensorwerte.",
    confirmTitle: "Verlauf „{w}“ löschen?",
    confirmMsg: "{d}\n\nDie Daten werden endgültig aus der Datenbank des Add-ons gelöscht.",
    confirmWord: "LÖSCHEN",
    cleared: "Verlauf gelöscht",
  },
  en: {
    search: "Search messages…",
    export: "JSON",
    exportHint: "Download the filtered events as JSON",
    lv_error: "Error",
    lv_warning: "Warning",
    lv_info: "Info",
    cat_availability: "Availability",
    cat_lamp_failure: "Lamp failure",
    cat_gear_failure: "Control gear",
    cat_gateway: "Gateway",
    cat_input: "Inputs",
    chart: "Events over time",
    chartSub: "per {b}, by severity",
    hour: "hour",
    day: "day",
    noEvents: "No events occurred in the selected period.",
    noMatch: "No events match the filters.",
    data: "Data",
    more: "Show {n} more",
    clearTitle: "Clear history",
    clearSub: "Expert mode – deleted data cannot be restored",
    clearBtn: "Delete",
    w_monitor: "Bus monitor",
    w_monitor_d: "All recorded DALI frames (monitor history, CSV export).",
    w_bus: "Bus statistics",
    w_bus_d: "Bus load and answer ratios (tabs “Bus load” and “Communication”).",
    w_events: "Events",
    w_events_d: "The event log on this page.",
    w_all: "Everything",
    w_all_d: "All histories incl. device states, measurements and sensor values.",
    confirmTitle: "Delete history “{w}”?",
    confirmMsg: "{d}\n\nThe data is permanently removed from the add-on's database.",
    confirmWord: "DELETE",
    cleared: "History cleared",
  },
});

// The backend writes German messages – translate the known ones for English users.
const EN_MESSAGES: [RegExp, string][] = [
  [/Gerät nicht mehr erreichbar/, "device no longer reachable"],
  [/Gerät wieder erreichbar/, "device reachable again"],
  [/Lampenfehler erkannt/, "lamp failure detected"],
  [/Lampenfehler behoben/, "lamp failure cleared"],
  [/Betriebsgerätefehler erkannt/, "control gear failure detected"],
  [/Betriebsgerätefehler behoben/, "control gear failure cleared"],
  [/Verbindung zum Gateway unterbrochen/, "Connection to the gateway lost"],
  [/Neuer DALI-Eingang erkannt/, "New DALI input detected"],
];

const CATEGORIES = ["availability", "lamp_failure", "gear_failure", "gateway", "input"];
const LEVELS = ["error", "warning", "info"];
const LEVEL_SET: Record<string, true> = { error: true, warning: true, info: true };
const WHATS = ["monitor", "bus", "events", "all"];

interface Ev extends AddonEvent {
  live?: boolean;
}

const rows = ref<Ev[]>([]);
const loading = ref(false);
const error = ref("");
const category = ref("");
const levels = ref<string[]>([...LEVELS]);
const search = ref("");
const shownCount = ref(200);
const clearing = ref(false);

async function load() {
  loading.value = true;
  try {
    rows.value = (await api<Ev[]>("GET", `events?hours=${props.hours}&limit=2000`)) || [];
    error.value = "";
  } catch (e: any) {
    error.value = e?.message || String(e);
  } finally {
    loading.value = false;
  }
}
watch(() => [props.hours, props.refresh], load, { immediate: true });
watch([category, levels, search], () => (shownCount.value = 200));

/** DB rows + live websocket events not yet in the DB result (deduplicated). */
const merged = computed<Ev[]>(() => {
  const since = Date.now() / 1000 - props.hours * 3600;
  const key = (e: AddonEvent) => `${Math.round(e.ts * 1000)}|${e.message}`;
  const seen = new Set(rows.value.map(key));
  const live = state.events.filter((e) => e.ts >= since && !seen.has(key(e))).map((e) => ({ ...e, live: true }));
  return [...live, ...rows.value].sort((a, b) => b.ts - a.ts);
});

const catCounts = computed(() => {
  const c: Record<string, number> = {};
  for (const e of merged.value) c[e.category] = (c[e.category] || 0) + 1;
  return c;
});

const filtered = computed(() => {
  const q = search.value.trim().toLowerCase();
  return merged.value.filter(
    (e) =>
      (!category.value || e.category === category.value) &&
      levels.value.includes(e.level in LEVEL_SET ? e.level : "info") &&
      (!q || `${message(e)} ${devName(e.device_id)}`.toLowerCase().includes(q)),
  );
});

const grouped = computed(() => {
  const out: { day: string; label: string; items: Ev[] }[] = [];
  for (const e of filtered.value.slice(0, shownCount.value)) {
    const d = new Date(e.ts * 1000);
    const day = `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}`;
    let g = out[out.length - 1];
    if (!g || g.day !== day) {
      g = { day, label: fmtDay(e.ts, lang.value), items: [] };
      out.push(g);
    }
    g.items.push(e);
  }
  return out;
});

function toggleLevel(l: string) {
  levels.value = levels.value.includes(l) ? levels.value.filter((x) => x !== l) : [...levels.value, l];
  if (!levels.value.length) levels.value = [...LEVELS];
}

function catLabel(c: string) {
  const k = `cat_${c}`;
  const s = t(k);
  return s === k ? c : s;
}
function catIcon(c: string) {
  return (
    { availability: mdiLanConnect, lamp_failure: mdiLightbulbAlert, gear_failure: mdiChip, gateway: mdiRouterNetwork, input: mdiGestureTapButton }[c] || mdiTag
  );
}
function levelIcon(l: string) {
  return l === "error" ? mdiAlertCircle : l === "warning" ? mdiAlert : mdiInformation;
}
function levelCls(l: string) {
  return l === "error" ? "err" : l === "warning" ? "warn" : "";
}
function levelDot(l: string) {
  return l === "error" ? "err" : l === "warning" ? "warn" : "ok";
}
function devName(id: number | null | undefined) {
  if (id === null || id === undefined) return "";
  const d = state.devices[id];
  return d ? `${d.name} (A${d.address})` : `#${id}`;
}
function message(e: AddonEvent) {
  let m = e.message || "";
  if (lang.value === "en") for (const [re, s] of EN_MESSAGES) m = m.replace(re, s);
  return m;
}

// chart: events per hour (≤ 48 h) or per day, stacked by level
const bucketSec = computed(() => (props.hours <= 48 ? 3600 : 86400));
const bucketLabel = computed(() => (bucketSec.value === 3600 ? t("hour") : t("day")));
const chartDatasets = computed(() => {
  const b = bucketSec.value;
  const src = merged.value.filter((e) => !category.value || e.category === category.value);
  const tzOff = new Date().getTimezoneOffset() * 60;
  const bucketOf = (ts: number) => (b === 86400 ? Math.floor((ts - tzOff) / b) * b + tzOff : Math.floor(ts / b) * b);
  const maps: Record<string, Map<number, number>> = { error: new Map(), warning: new Map(), info: new Map() };
  for (const e of src) {
    const lv = e.level in maps ? e.level : "info";
    const k = bucketOf(e.ts);
    maps[lv].set(k, (maps[lv].get(k) || 0) + 1);
  }
  const now = Date.now() / 1000;
  const start = bucketOf(now - props.hours * 3600);
  const end = bucketOf(now);
  const xs: number[] = [];
  for (let x = start; x <= end; x += b) xs.push(x);
  const c = themeColors();
  const color: Record<string, string> = { error: c.error, warning: c.warning, info: c.primary };
  return LEVELS.map((lv) => ({
    label: t(`lv_${lv}`),
    data: xs.map((x) => ({ x: x + b / 2, y: maps[lv].get(x) || 0 })),
    backgroundColor: alpha(color[lv], 0.8),
    borderWidth: 0,
    stack: "ev",
  }));
});

function exportJson() {
  const stamp = new Date().toISOString().slice(0, 19).replace(/[:T]/g, "-");
  downloadJson(
    `dali-events-${stamp}.json`,
    filtered.value.map(({ live, ...e }) => ({ ...e, time: new Date(e.ts * 1000).toISOString() })),
  );
}

async function clearHistory(what: string) {
  const ok = await confirmDialog({
    title: t("confirmTitle", { w: t(`w_${what}`) }),
    message: t("confirmMsg", { d: t(`w_${what}_d`) }),
    danger: true,
    typeToConfirm: what === "all" ? t("confirmWord") : undefined,
    confirmText: t("clearBtn"),
  });
  if (!ok) return;
  clearing.value = true;
  const res = await run(() => api("DELETE", `history?what=${what}`), t("cleared"));
  clearing.value = false;
  if (res && (what === "events" || what === "all")) state.events.splice(0);
  await load();
}
</script>

<style scoped>
.tb { padding: 12px 14px; display: flex; flex-direction: column; gap: 10px; }
.cats { gap: 6px; }
.cat { border: 0; font-family: inherit; }
.cnt { font-family: var(--mono); font-size: 11px; font-weight: 400; opacity: .8; margin-left: 3px; }
.filters { gap: 10px; }
.search { flex: 1 1 200px; max-width: 320px; height: 34px; }
.day { display: flex; gap: 4px; }
.norm { text-transform: none; letter-spacing: 0; font-weight: 400; }
.timeline .card + .section-title { margin-top: 16px; }
.ev { align-items: flex-start; }
.icon-bubble.sm { width: 32px; height: 32px; }
.minw { min-width: 0; }
.msg { word-break: break-word; }
.meta { gap: 4px 10px; margin-top: 2px; }
.chip.mini { height: 20px; font-size: 11px; padding: 0 7px; }
.dev { color: var(--text2); }
.lv-error { box-shadow: inset 3px 0 0 var(--error); }
.lv-warning { box-shadow: inset 3px 0 0 var(--warning); }
.data summary { cursor: pointer; color: var(--text2); margin-top: 4px; }
.data pre { background: var(--bg2); border-radius: 8px; padding: 8px 10px; margin: 6px 0 0; overflow: auto; max-height: 220px; }
.clear-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 10px; }
.clear-item { display: flex; align-items: center; gap: 12px; padding: 10px 12px; border: 1px solid var(--divider); border-radius: 12px; }
.title-s { font-weight: 500; }
@media (max-width: 700px) {
  .search { max-width: none; }
}
</style>
