<template>
  <div class="quality">
    <div class="row wrap head-row">
      <span class="small muted">{{ t("period", { d: days }) }}</span>
      <span class="grow"></span>
      <span v-if="loading" class="spinner"></span>
    </div>

    <div v-if="error && !rows.length" class="banner err">
      <Icon :path="mdiAlertCircle" :size="18" /><div>{{ error }}</div>
    </div>
    <Empty v-else-if="!loading && !rows.length" class="card" :icon="mdiCableData" :text="t('noData')" />

    <template v-if="rows.length">
      <div class="grid cols-4 kpis">
        <StatCard :icon="mdiCheckAll" :label="t('overall')" :value="fmtPct(overall, lang)" :sub="t('overallSub')" :kind="ratioKind(overall)" />
        <StatCard :icon="mdiSwapVertical" :label="t('queries')" :value="fmtNum(totalQueries, lang)" :sub="t('answered', { n: fmtNum(totalAnswered, lang) })" kind="off" />
        <StatCard :icon="mdiCableData" :label="t('addresses')" :value="shortRows.length" :sub="t('addressesSub')" kind="off" />
        <StatCard :icon="mdiAlertCircle" :label="t('bad')" :value="badRows.length" :sub="t('badSub')" :kind="badRows.length ? 'err' : 'ok'" />
      </div>

      <div v-if="badRows.length" class="banner warn mt-lg">
        <Icon :path="mdiAlertOutline" :size="18" />
        <div>
          <b>{{ t("badTitle", { n: badRows.length }) }}</b>
          {{ badRows.map((r) => `${r.target}${r.name ? ` (${r.name})` : ""}: ${fmtPct(r.ratio, lang)}`).join(" · ") }}.
          {{ t("badHint") }}
        </div>
      </div>
      <div v-else class="banner info mt-lg">
        <Icon :path="mdiCheckCircle" :size="18" />
        <div>{{ t("allGood") }}</div>
      </div>

      <Card :title="t('chart')" :icon="mdiChartBar" :subtitle="t('chartSub')" class="mt-lg">
        <LineChart type="bar" :time="false" :labels="chartLabels" :datasets="chartDatasets" :height="240" :y-max="100" y-unit="%" :legend="false" />
      </Card>

      <Card :title="t('table')" :icon="mdiFormatListBulleted" class="mt-lg" flush>
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
              <tr v-for="r in sorted" :key="`${r.line}-${r.target}`" :class="{ bad: isShort(r) && r.ratio !== null && r.ratio < 98, na: !isShort(r) }">
                <td>{{ r.line }}</td>
                <td class="mono b">{{ r.target }}</td>
                <td>
                  <span v-if="r.name">{{ r.name }}</span>
                  <span v-else-if="!isShort(r)" class="faint small">{{ t("multiTarget") }}</span>
                  <span v-else class="faint small">{{ t("unknownDevice") }}</span>
                </td>
                <td class="right mono">{{ fmtNum(r.queries, lang) }}</td>
                <td class="right mono">{{ fmtNum(r.answered, lang) }}</td>
                <td class="ratio-cell">
                  <div class="row">
                    <div class="progress grow">
                      <div :style="{ width: `${r.ratio ?? 0}%`, background: barColor(r) }"></div>
                    </div>
                    <span class="mono small ratio-val">{{ fmtPct(r.ratio, lang) }}</span>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </Card>
      <p class="small faint">{{ t("footnote") }}</p>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import {
  mdiAlertCircle,
  mdiAlertOutline,
  mdiCableData,
  mdiChartBar,
  mdiCheckAll,
  mdiCheckCircle,
  mdiChevronDown,
  mdiChevronUp,
  mdiFormatListBulleted,
  mdiSwapVertical,
} from "@mdi/js";
import Card from "../Card.vue";
import Icon from "../Icon.vue";
import Empty from "../Empty.vue";
import StatCard from "../StatCard.vue";
import LineChart from "../LineChart.vue";
import { api } from "../../lib/api";
import { lang, useT } from "../../lib/i18n";
import { alpha, fmtNum, fmtPct, sortBy, themeColors, type SortDir } from "./util";

const props = defineProps<{ hours: number; refresh: number }>();

const t = useT({
  de: {
    period: "Tageswerte – {d} Kalendertag(e) im gewählten Zeitraum",
    noData: "Noch keine Abfragestatistik vorhanden. Sie entsteht aus den Statusabfragen, die das Gateway zyklisch sendet.",
    overall: "Antwortquote",
    overallSub: "Kurzadressen gesamt",
    queries: "Abfragen",
    answered: "{n} beantwortet",
    addresses: "Adressen",
    addressesSub: "mit Abfragen",
    bad: "Unter 98 %",
    badSub: "auffällige Adressen",
    badTitle: "{n} Adresse(n) mit schlechter Antwortquote:",
    badHint: "Mögliche Ursachen: Gerät ohne Netzspannung, lose Klemme, zu lange oder zu dünne Busleitung, Störungen durch parallel verlegte Lastleitungen.",
    allGood: "Alle Geräte beantworten mindestens 98 % der Abfragen – die Buskommunikation ist stabil.",
    chart: "Antwortquote je Adresse",
    chartSub: "Rot: unter 98 %",
    table: "Details",
    line: "Linie",
    target: "Adresse",
    device: "Gerät",
    q: "Abfragen",
    a: "Beantwortet",
    ratio: "Quote",
    multiTarget: "Gruppe/Broadcast – Antworten nicht eindeutig",
    unknownDevice: "Kein bekanntes Gerät",
    footnote: "Gruppen- und Broadcast-Abfragen werden nicht bewertet, da mehrere Geräte gleichzeitig antworten können (Kollision).",
  },
  en: {
    period: "Daily values – {d} calendar day(s) in the selected period",
    noData: "No query statistics yet. They are built from the status queries the gateway sends cyclically.",
    overall: "Answer ratio",
    overallSub: "all short addresses",
    queries: "Queries",
    answered: "{n} answered",
    addresses: "Addresses",
    addressesSub: "with queries",
    bad: "Below 98 %",
    badSub: "conspicuous addresses",
    badTitle: "{n} address(es) with a poor answer ratio:",
    badHint: "Possible causes: device without mains power, loose terminal, bus cable too long or too thin, interference from parallel load cables.",
    allGood: "All devices answer at least 98 % of the queries – bus communication is stable.",
    chart: "Answer ratio per address",
    chartSub: "Red: below 98 %",
    table: "Details",
    line: "Line",
    target: "Address",
    device: "Device",
    q: "Queries",
    a: "Answered",
    ratio: "Ratio",
    multiTarget: "Group/broadcast – answers ambiguous",
    unknownDevice: "No known device",
    footnote: "Group and broadcast queries are not rated because several devices may answer at the same time (collision).",
  },
});

interface QRow {
  line: number;
  target: string;
  queries: number;
  answered: number;
  ratio: number | null;
  device_id: number | null;
  name: string | null;
}

const rows = ref<QRow[]>([]);
const loading = ref(false);
const error = ref("");
// the backend aggregates per UTC day → request every calendar day the selected window touches
const days = computed(() => {
  void props.refresh;
  const now = Date.now() / 1000;
  return Math.max(1, Math.floor(now / 86400) - Math.floor((now - props.hours * 3600) / 86400) + 1);
});

async function load() {
  loading.value = true;
  try {
    rows.value = (await api<QRow[]>("GET", `analytics/quality?days=${days.value}`)) || [];
    error.value = "";
  } catch (e: any) {
    error.value = e?.message || String(e);
  } finally {
    loading.value = false;
  }
}
watch(() => [days.value, props.refresh], load, { immediate: true });

const isShort = (r: QRow) => /^A\d+$/.test(r.target);
const shortRows = computed(() => rows.value.filter(isShort));
const badRows = computed(() => shortRows.value.filter((r) => r.ratio !== null && r.ratio < 98).sort((a, b) => (a.ratio ?? 0) - (b.ratio ?? 0)));
const totalQueries = computed(() => shortRows.value.reduce((s, r) => s + r.queries, 0));
const totalAnswered = computed(() => shortRows.value.reduce((s, r) => s + r.answered, 0));
const overall = computed(() => (totalQueries.value ? (100 * totalAnswered.value) / totalQueries.value : null));
function ratioKind(v: number | null) {
  return v === null ? "off" : v >= 98 ? "ok" : v >= 90 ? "warn" : "err";
}
function barColor(r: QRow) {
  const c = themeColors();
  if (!isShort(r)) return c.text3;
  return r.ratio !== null && r.ratio < 98 ? c.error : c.success;
}

const chartRows = computed(() =>
  [...shortRows.value].sort((a, b) => a.line - b.line || Number(a.target.slice(1)) - Number(b.target.slice(1))),
);
const chartLabels = computed(() => chartRows.value.map((r) => (rows.value.some((x) => x.line !== 0) ? `L${r.line} ${r.target}` : r.target)));
const chartDatasets = computed(() => {
  const c = themeColors();
  return [
    {
      label: t("ratio"),
      data: chartRows.value.map((r) => r.ratio ?? 0),
      backgroundColor: chartRows.value.map((r) => alpha(r.ratio !== null && r.ratio < 98 ? c.error : c.success, 0.8)),
      borderRadius: 4,
      maxBarThickness: 36,
    },
  ];
});

// table sorting
const cols = computed(() => [
  { key: "line", label: t("line"), cls: "" },
  { key: "target", label: t("target"), cls: "" },
  { key: "name", label: t("device"), cls: "" },
  { key: "queries", label: t("q"), cls: "right" },
  { key: "answered", label: t("a"), cls: "right" },
  { key: "ratio", label: t("ratio"), cls: "" },
]);
const sortKey = ref<string>("ratio");
const sortDir = ref<SortDir>(1);
function toggleSort(k: string) {
  if (sortKey.value === k) sortDir.value = (sortDir.value * -1) as SortDir;
  else {
    sortKey.value = k;
    sortDir.value = 1;
  }
}
const sorted = computed(() =>
  sortBy(rows.value, (r: QRow) => (sortKey.value === "target" ? `${r.target.replace(/\d+/, "")}${String(r.target.replace(/\D/g, "")).padStart(3, "0")}` : (r as any)[sortKey.value]), sortDir.value),
);
</script>

<style scoped>
.head-row { margin-bottom: 12px; min-height: 30px; }
.kpis :deep(.stat) { padding: 12px 14px; }
.sortable { cursor: pointer; user-select: none; }
.sortable:hover { color: var(--text); }
.b { font-weight: 600; }
tr.bad td { background: color-mix(in srgb, var(--error) 8%, transparent); }
tr.na td { color: var(--text2); }
.ratio-cell { min-width: 170px; }
.ratio-val { width: 60px; text-align: right; }
</style>
