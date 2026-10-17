<template>
  <div class="usage">
    <div class="row wrap head-row">
      <span class="small muted">{{ t("hint") }}</span>
      <span class="grow"></span>
      <span v-if="loading" class="spinner"></span>
    </div>

    <div v-if="error && !rows.length" class="banner err">
      <Icon :path="mdiAlertCircle" :size="18" /><div>{{ error }}</div>
    </div>
    <Empty v-else-if="!loading && !rows.length" class="card" :icon="mdiLightbulbOutline" :text="t('noData')" />

    <template v-if="rows.length">
      <div class="grid cols-4 kpis">
        <StatCard :icon="mdiLightbulbOnOutline" :label="t('onTotal')" :value="fmtDuration(totals.on, lang)" :sub="t('onTotalSub', { n: totals.used, total: rows.length })" />
        <StatCard :icon="mdiPowerSettings" :label="t('switchesTotal')" :value="fmtNum(totals.switches, lang)" :sub="t('perDay', { n: fmtNum(totals.switchesPerDay, lang, 1) })" kind="off" />
        <StatCard :icon="mdiBrightness6" :label="t('avgLevel')" :value="totals.avgLevel === null ? '–' : fmtPct(totals.avgLevel, lang, 0)" :sub="t('avgLevelSub')" kind="off" />
        <StatCard
          :icon="mdiLanDisconnect"
          :label="t('downtime')"
          :value="fmtDuration(totals.down, lang)"
          :sub="t('downSub', { n: totals.downDevices })"
          :kind="totals.down ? 'err' : 'ok'"
        />
      </div>

      <div class="grid cols-2 mt-lg">
        <Card :title="t('onChart')" :icon="mdiChartBar" :subtitle="t('onChartSub')">
          <LineChart type="bar" :time="false" :labels="chartLabels" :datasets="onDatasets" :height="250" :y-max="100" y-unit="%" :legend="false" />
        </Card>
        <Card :title="t('swChart')" :icon="mdiPowerSettings" :subtitle="t('swChartSub')">
          <LineChart type="bar" :time="false" :labels="chartLabels" :datasets="swDatasets" :height="250" :legend="false" />
        </Card>
      </div>

      <Card :title="t('table')" :icon="mdiFormatListBulleted" :subtitle="t('tableSub')" class="mt-lg" flush>
        <template #actions>
          <input v-model="search" type="search" class="search" :placeholder="t('search')" />
        </template>
        <div class="table-wrap">
          <table class="table">
            <thead>
              <tr>
                <th v-for="c in cols" :key="c.key" :class="[c.cls, 'sortable']" @click="toggleSort(c.key)">
                  {{ c.label }}
                  <Icon v-if="sortKey === c.key" :path="sortDir === 1 ? mdiChevronUp : mdiChevronDown" :size="14" />
                </th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="r in sorted" :key="r.device_id" class="clickable" @click="open(r)">
                <td>
                  <div class="row nowrap">
                    <span class="dot" :class="dotOf(r)"></span>
                    <span class="name">{{ r.name || `#${r.device_id}` }}</span>
                  </div>
                </td>
                <td class="mono small nowrap">L{{ r.line }} · A{{ r.address }}</td>
                <td class="right nowrap">{{ fmtDuration(r.on_s, lang) }}</td>
                <td class="pct-cell">
                  <div class="row">
                    <div class="progress grow"><div :style="{ width: `${r.on_pct ?? 0}%` }"></div></div>
                    <span class="mono small pv">{{ fmtPct(r.on_pct, lang) }}</span>
                  </div>
                </td>
                <td class="right mono">{{ r.avg_level === null ? "–" : `${Math.round(r.avg_level)} %` }}</td>
                <td class="right mono">{{ r.switches }}</td>
                <td class="right nowrap" :class="{ bad: r.unavailable_s > 0 }">{{ r.unavailable_s ? fmtDuration(r.unavailable_s, lang) : "–" }}</td>
                <td class="right mono" :class="{ bad: r.failures > 0 }">{{ r.failures || "–" }}</td>
                <td class="right nowrap faint small">{{ fmtDuration(r.tracked_s, lang) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </Card>
      <p class="small faint">{{ t("footnote") }}</p>
    </template>

    <DeviceHistoryModal
      :open="modalId !== null"
      :device-id="modalId"
      :hours="hours"
      :summary="modalRow"
      :name="modalRow?.name"
      @close="modalId = null"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import {
  mdiAlertCircle,
  mdiBrightness6,
  mdiChartBar,
  mdiChevronDown,
  mdiChevronUp,
  mdiFormatListBulleted,
  mdiLanDisconnect,
  mdiLightbulbOnOutline,
  mdiLightbulbOutline,
  mdiPowerSettings,
} from "@mdi/js";
import Card from "../Card.vue";
import Icon from "../Icon.vue";
import Empty from "../Empty.vue";
import StatCard from "../StatCard.vue";
import LineChart from "../LineChart.vue";
import DeviceHistoryModal from "./DeviceHistoryModal.vue";
import { api } from "../../lib/api";
import { state } from "../../lib/store";
import { lang, useT } from "../../lib/i18n";
import { fmtDuration } from "../../lib/dali";
import { PALETTE, alpha, fmtNum, fmtPct, sortBy, type SortDir } from "./util";

const props = defineProps<{ hours: number; refresh: number }>();

const t = useT({
  de: {
    hint: "Einschaltdauer, Schaltzyklen und Ausfallzeiten je Gerät – Zeile anklicken für den Verlauf.",
    noData: "Noch keine Nutzungsdaten vorhanden.",
    onTotal: "Einschaltdauer gesamt",
    onTotalSub: "{n} von {total} Geräten genutzt",
    switchesTotal: "Einschaltvorgänge",
    perDay: "Ø {n} pro Tag",
    avgLevel: "Ø Helligkeit",
    avgLevelSub: "gewichtet nach Einschaltdauer",
    downtime: "Ausfallzeit",
    downSub: "{n} Gerät(e) betroffen",
    onChart: "Einschaltdauer",
    onChartSub: "Anteil der erfassten Zeit, in der das Gerät eingeschaltet war",
    swChart: "Schaltzyklen",
    swChartSub: "Anzahl der Einschaltvorgänge im Zeitraum",
    onPct: "Eingeschaltet",
    switches: "Einschaltvorgänge",
    table: "Geräte",
    tableSub: "Spalten anklicken zum Sortieren",
    search: "Filtern…",
    c_name: "Gerät",
    c_addr: "Adresse",
    c_on: "An",
    c_pct: "Anteil",
    c_level: "Ø Hell.",
    c_sw: "Zyklen",
    c_down: "Ausfall",
    c_fail: "Fehler",
    c_tracked: "Erfasst",
    footnote: "Die Werte beruhen auf den Zustandsänderungen, die das Add-on seit Beginn der Aufzeichnung protokolliert. „Erfasst“ ist der Zeitraum, für den Daten vorliegen.",
  },
  en: {
    hint: "On time, switch cycles and downtime per device – click a row for the history.",
    noData: "No usage data yet.",
    onTotal: "Total on time",
    onTotalSub: "{n} of {total} devices used",
    switchesTotal: "Switch-on cycles",
    perDay: "Avg {n} per day",
    avgLevel: "Avg brightness",
    avgLevelSub: "weighted by on time",
    downtime: "Downtime",
    downSub: "{n} device(s) affected",
    onChart: "On time",
    onChartSub: "Share of the recorded time the device was switched on",
    swChart: "Switch cycles",
    swChartSub: "Number of switch-on operations in the period",
    onPct: "Switched on",
    switches: "Switch-on cycles",
    table: "Devices",
    tableSub: "Click a column to sort",
    search: "Filter…",
    c_name: "Device",
    c_addr: "Address",
    c_on: "On",
    c_pct: "Share",
    c_level: "Avg lvl",
    c_sw: "Cycles",
    c_down: "Down",
    c_fail: "Failures",
    c_tracked: "Recorded",
    footnote: "Values are based on the state changes the add-on has logged since recording started. “Recorded” is the period for which data exists.",
  },
});

interface URow {
  device_id: number;
  name: string;
  address: number;
  line: number;
  tracked_s: number;
  on_s: number;
  on_pct: number | null;
  avg_level: number | null;
  switches: number;
  unavailable_s: number;
  failures: number;
}

const rows = ref<URow[]>([]);
const loading = ref(false);
const error = ref("");
const search = ref("");

async function load() {
  loading.value = true;
  try {
    rows.value = (await api<URow[]>("GET", `analytics/devices?hours=${props.hours}`)) || [];
    error.value = "";
  } catch (e: any) {
    error.value = e?.message || String(e);
  } finally {
    loading.value = false;
  }
}
watch(() => [props.hours, props.refresh], load, { immediate: true });

const totals = computed(() => {
  const r = rows.value;
  const on = r.reduce((s, x) => s + (x.on_s || 0), 0);
  const levelInt = r.reduce((s, x) => s + (x.avg_level ?? 0) * (x.on_s || 0), 0);
  const maxTracked = r.reduce((m, x) => Math.max(m, x.tracked_s || 0), 0);
  const switches = r.reduce((s, x) => s + (x.switches || 0), 0);
  return {
    on,
    used: r.filter((x) => x.on_s > 0).length,
    switches,
    switchesPerDay: maxTracked ? switches / Math.max(maxTracked / 86400, 1 / 24) : 0,
    avgLevel: on ? levelInt / on : null,
    down: r.reduce((s, x) => s + (x.unavailable_s || 0), 0),
    downDevices: r.filter((x) => x.unavailable_s > 0).length,
  };
});

const chartRows = computed(() => [...rows.value].sort((a, b) => a.line - b.line || a.address - b.address));
const chartLabels = computed(() => chartRows.value.map((r) => shortName(r)));
function shortName(r: URow) {
  const n = r.name || `#${r.device_id}`;
  return n.length > 18 ? `${n.slice(0, 16)}…` : n;
}
const onDatasets = computed(() => [
  {
    label: t("onPct"),
    data: chartRows.value.map((r) => r.on_pct ?? 0),
    backgroundColor: alpha(PALETTE[1], 0.85),
    borderRadius: 4,
    maxBarThickness: 36,
  },
]);
const swDatasets = computed(() => [
  {
    label: t("switches"),
    data: chartRows.value.map((r) => r.switches),
    backgroundColor: alpha(PALETTE[0], 0.85),
    borderRadius: 4,
    maxBarThickness: 36,
  },
]);

const cols = computed(() => [
  { key: "name", label: t("c_name"), cls: "" },
  { key: "address", label: t("c_addr"), cls: "" },
  { key: "on_s", label: t("c_on"), cls: "right" },
  { key: "on_pct", label: t("c_pct"), cls: "" },
  { key: "avg_level", label: t("c_level"), cls: "right" },
  { key: "switches", label: t("c_sw"), cls: "right" },
  { key: "unavailable_s", label: t("c_down"), cls: "right" },
  { key: "failures", label: t("c_fail"), cls: "right" },
  { key: "tracked_s", label: t("c_tracked"), cls: "right" },
]);
const sortKey = ref("on_s");
const sortDir = ref<SortDir>(-1);
function toggleSort(k: string) {
  if (sortKey.value === k) sortDir.value = (sortDir.value * -1) as SortDir;
  else {
    sortKey.value = k;
    sortDir.value = k === "name" || k === "address" ? 1 : -1;
  }
}
const sorted = computed(() => {
  const q = search.value.trim().toLowerCase();
  const list = q ? rows.value.filter((r) => `${r.name} a${r.address}`.toLowerCase().includes(q)) : rows.value;
  return sortBy(list, (r: URow) => (sortKey.value === "address" ? r.line * 100 + r.address : (r as any)[sortKey.value]), sortDir.value);
});

function dotOf(r: URow) {
  const d = state.devices[r.device_id];
  if (!d) return "";
  if (!d.available) return "err";
  if (d.status?.lampFailure || d.status?.controlGearFailure) return "warn";
  return "ok";
}

const modalId = ref<number | null>(null);
const modalRow = computed(() => rows.value.find((r) => r.device_id === modalId.value));
function open(r: URow) {
  modalId.value = r.device_id;
}
</script>

<style scoped>
.head-row { margin-bottom: 12px; min-height: 30px; }
.kpis :deep(.stat) { padding: 12px 14px; }
.kpis :deep(.stat .value) { font-size: 20px; }
.search { width: 160px; height: 32px; }
.sortable { cursor: pointer; user-select: none; }
.sortable:hover { color: var(--text); }
.name { font-weight: 500; }
.pct-cell { min-width: 150px; }
.pv { width: 54px; text-align: right; }
td.bad { color: var(--error); font-weight: 500; }
@media (max-width: 700px) {
  .search { width: 120px; }
}
</style>
