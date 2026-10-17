<template>
  <div class="busload">
    <div class="row wrap head-row">
      <span class="small muted">{{ data ? t("resolution", { m: data.bucket_minutes }) : "" }}</span>
      <span class="grow"></span>
      <select v-if="lineCount > 1" v-model="line" class="line-sel">
        <option :value="null">{{ t("allLines") }}</option>
        <option v-for="l in lineCount" :key="l" :value="l - 1">{{ t("line") }} {{ l - 1 }}</option>
      </select>
      <span v-if="loading" class="spinner"></span>
    </div>

    <div v-if="error && !data" class="banner err">
      <Icon :path="mdiAlertCircle" :size="18" /><div>{{ error }}</div>
    </div>

    <template v-if="data">
      <div class="grid cols-4 kpis">
        <StatCard :icon="mdiSpeedometer" :label="t('avgLoad')" :value="fmtPct(kpi.avgLoad, lang)" :sub="t('avgLoadSub')" :kind="loadKind(kpi.avgLoad)" />
        <StatCard :icon="mdiChartLine" :label="t('peakLoad')" :value="fmtPct(kpi.peakLoad, lang)" :sub="kpi.peakAt ? fmtDateTime(kpi.peakAt, lang) : '–'" :kind="loadKind(kpi.peakLoad / 2)" />
        <StatCard :icon="mdiSwapVertical" :label="t('frames')" :value="fmtNum(data.totals.frames, lang)" :sub="t('perMin', { n: fmtNum(kpi.perMin, lang, 1) })" />
        <StatCard :icon="mdiRadar" :label="t('pollShare')" :value="fmtPct(kpi.pollShare, lang, 0)" :sub="t('queries', { n: fmtNum(data.totals.queries, lang) })" kind="off" />
        <StatCard :icon="mdiGestureTapButton" :label="t('events')" :value="fmtNum(data.totals.events, lang)" :sub="t('eventsSub')" :kind="data.totals.events ? '' : 'off'" />
        <StatCard
          :icon="mdiCloseCircle"
          :label="t('noAnswer')"
          :value="fmtNum(data.totals.no_answer, lang)"
          :sub="t('ofQueries', { p: fmtPct(kpi.noAnswerPct, lang) })"
          :kind="kpi.noAnswerPct > 5 ? 'err' : kpi.noAnswerPct > 1 ? 'warn' : 'ok'"
        />
        <StatCard :icon="mdiAccessPoint" :label="t('external')" :value="fmtNum(kpi.extForward, lang)" :sub="t('externalSub')" kind="off" />
        <StatCard :icon="mdiReply" :label="t('answers')" :value="fmtNum(data.totals.backward, lang)" :sub="t('answersSub')" kind="off" />
      </div>

      <div v-if="insights.length" class="insights mt-lg">
        <div v-for="(i, k) in insights" :key="k" class="banner small" :class="i.kind">
          <Icon :path="i.kind === 'warn' || i.kind === 'err' ? mdiAlertOutline : mdiLightbulbOnOutline" :size="18" />
          <div>{{ i.text }}</div>
        </div>
      </div>

      <Empty v-if="!data.rows.length" class="card mt-lg" :icon="mdiChartLine" :text="t('noData')" />
      <template v-else>
        <Card :title="t('loadChart')" :icon="mdiSpeedometer" :subtitle="t('loadChartSub')" class="mt-lg">
          <LineChart :datasets="loadDatasets" :height="230" y-unit="%" :y-min="0" />
        </Card>
        <div class="grid cols-2 mt-lg">
          <Card :title="t('byType')" :icon="mdiChartBar" :subtitle="t('byTypeSub', { m: data.bucket_minutes })">
            <LineChart type="bar" :datasets="typeDatasets" :height="240" stacked />
          </Card>
          <Card :title="t('noAnswerChart')" :icon="mdiCloseCircle" :subtitle="t('noAnswerChartSub')">
            <LineChart type="bar" :datasets="noAnswerDatasets" :height="240" y2 />
          </Card>
        </div>
      </template>
    </template>

    <LiveRateChart class="mt-lg" />
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import {
  mdiAccessPoint,
  mdiAlertCircle,
  mdiAlertOutline,
  mdiChartBar,
  mdiChartLine,
  mdiCloseCircle,
  mdiGestureTapButton,
  mdiLightbulbOnOutline,
  mdiRadar,
  mdiReply,
  mdiSpeedometer,
  mdiSwapVertical,
} from "@mdi/js";
import Card from "../Card.vue";
import Icon from "../Icon.vue";
import Empty from "../Empty.vue";
import StatCard from "../StatCard.vue";
import LineChart from "../LineChart.vue";
import LiveRateChart from "./LiveRateChart.vue";
import { api } from "../../lib/api";
import { state } from "../../lib/store";
import { lang, useT } from "../../lib/i18n";
import { C, alpha, fmtDateTime, fmtNum, fmtPct, themeColors } from "./util";

const props = defineProps<{ hours: number; refresh: number }>();

const t = useT({
  de: {
    resolution: "Auflösung: {m} min je Messpunkt",
    allLines: "Alle Linien",
    avgLoad: "Ø Buslast",
    avgLoadSub: "im erfassten Zeitraum",
    peakLoad: "Spitzenlast",
    frames: "Frames gesamt",
    perMin: "Ø {n} pro Minute",
    pollShare: "Polling-Anteil",
    queries: "{n} Abfragen",
    events: "Ereignisse",
    eventsSub: "Taster & Sensoren",
    noAnswer: "Ohne Antwort",
    ofQueries: "{p} der Abfragen",
    external: "Fremd-Befehle",
    externalSub: "von anderen Steuergeräten",
    answers: "Antworten",
    answersSub: "Rückwärtsframes",
    noData: "Für diesen Zeitraum liegen noch keine Busstatistiken vor. Sie werden minütlich aus dem Busmonitor erfasst.",
    loadChart: "Buslast",
    loadChartSub: "Belegung der DALI-Leitung (1200 bit/s) in Prozent",
    loadPct: "Buslast",
    byType: "Frames nach Typ",
    byTypeSub: "Anzahl je {m}-Minuten-Intervall",
    commands: "Befehle",
    queriesDs: "Abfragen",
    answersDs: "Antworten",
    eventsDs: "Ereignisse",
    noAnswerChart: "Unbeantwortete Abfragen",
    noAnswerChartSub: "Anzahl (Balken) und Anteil in % (Linie, rechte Achse)",
    noAnswerDs: "Ohne Antwort",
    ratioDs: "Anteil (%)",
    in_load_low: "Die Buslast ist mit Ø {avg} sehr gering – der Bus hat reichlich Reserven.",
    in_load_ok: "Die Buslast ist mit Ø {avg} unkritisch.",
    in_load_high: "Die Buslast ist mit Ø {avg} erhöht – Befehle können verzögert werden. Polling-Intervall oder Anzahl der Automationen prüfen.",
    in_load_crit: "Die Buslast ist mit Ø {avg} sehr hoch – Befehle werden spürbar verzögert oder gehen verloren.",
    in_peak: "Spitzenlast von {p} am {t} – kurzzeitige Engpässe möglich (z. B. durch Szenenaufrufe, Scans oder viele gleichzeitige Befehle).",
    in_poll: "{p} des Busverkehrs sind zyklische Statusabfragen des Gateways (Polling). Das ist normal und dient der Zustandserkennung.",
    in_noanswer: "{p} der Abfragen blieben unbeantwortet ({n}×). Ursache sind meist nicht erreichbare Geräte – siehe Tabs „Gesundheit“ und „Kommunikation“.",
    in_external: "{n} Befehle stammen von anderen Steuergeräten am Bus (z. B. Taster-Koppler, Präsenzmelder oder ein zweiter DALI-Controller).",
    in_events: "{n} Ereignisse von Tastern/Sensoren wurden empfangen.",
  },
  en: {
    resolution: "Resolution: {m} min per data point",
    allLines: "All lines",
    avgLoad: "Avg bus load",
    avgLoadSub: "over the recorded period",
    peakLoad: "Peak load",
    frames: "Total frames",
    perMin: "Avg {n} per minute",
    pollShare: "Polling share",
    queries: "{n} queries",
    events: "Events",
    eventsSub: "buttons & sensors",
    noAnswer: "Unanswered",
    ofQueries: "{p} of queries",
    external: "Foreign commands",
    externalSub: "from other control devices",
    answers: "Answers",
    answersSub: "backward frames",
    noData: "No bus statistics for this period yet. They are recorded every minute from the bus monitor.",
    loadChart: "Bus load",
    loadChartSub: "Occupancy of the DALI line (1200 bit/s) in percent",
    loadPct: "Bus load",
    byType: "Frames by type",
    byTypeSub: "Count per {m} minute interval",
    commands: "Commands",
    queriesDs: "Queries",
    answersDs: "Answers",
    eventsDs: "Events",
    noAnswerChart: "Unanswered queries",
    noAnswerChartSub: "Count (bars) and share in % (line, right axis)",
    noAnswerDs: "Unanswered",
    ratioDs: "Share (%)",
    in_load_low: "The bus load is very low at avg {avg} – plenty of reserve.",
    in_load_ok: "The bus load is uncritical at avg {avg}.",
    in_load_high: "The bus load is elevated at avg {avg} – commands may be delayed. Check the polling interval or the number of automations.",
    in_load_crit: "The bus load is very high at avg {avg} – commands are noticeably delayed or lost.",
    in_peak: "Peak load of {p} at {t} – short bottlenecks are possible (e.g. scene recalls, scans or many simultaneous commands).",
    in_poll: "{p} of the bus traffic are cyclic status queries of the gateway (polling). This is normal and used for state detection.",
    in_noanswer: "{p} of the queries were not answered ({n}×). Usually caused by unreachable devices – see the “Health” and “Communication” tabs.",
    in_external: "{n} commands were sent by other control devices on the bus (e.g. button couplers, presence detectors or a second DALI controller).",
    in_events: "{n} events from buttons/sensors were received.",
  },
});

interface BusRow {
  t: number;
  frames: number;
  forward: number;
  backward: number;
  events: number;
  queries: number;
  no_answer: number;
  external: number;
  bits: number;
  load_pct: number;
}
interface BusData {
  bucket_minutes: number;
  rows: BusRow[];
  totals: Record<string, number>;
}

const data = ref<BusData | null>(null);
const loading = ref(false);
const error = ref("");
const line = ref<number | null>(null);
const lineCount = computed(() => Number(state.info?.descriptor?.lines) || Object.keys(state.info?.lines || {}).length || 1);

async function load() {
  loading.value = true;
  try {
    data.value = await api("GET", `analytics/bus?hours=${props.hours}${line.value !== null ? `&line=${line.value}` : ""}`);
    error.value = "";
  } catch (e: any) {
    error.value = e?.message || String(e);
  } finally {
    loading.value = false;
  }
}
watch(() => [props.hours, props.refresh, line.value], load, { immediate: true });

const kpi = computed(() => {
  const d = data.value;
  const rows = d?.rows ?? [];
  const tot = d?.totals ?? {};
  const avgLoad = rows.length ? rows.reduce((s, r) => s + (r.load_pct || 0), 0) / rows.length : 0;
  let peak = rows[0];
  for (const r of rows) if (!peak || r.load_pct > peak.load_pct) peak = r;
  const minutes = rows.length * (d?.bucket_minutes || 1);
  const extForward = Math.max(0, (tot.external || 0) - (tot.backward || 0));
  return {
    avgLoad,
    peakLoad: peak?.load_pct ?? 0,
    peakAt: peak?.t,
    perMin: minutes ? (tot.frames || 0) / minutes : 0,
    pollShare: tot.frames ? (100 * ((tot.queries || 0) + (tot.backward || 0))) / tot.frames : 0,
    noAnswerPct: tot.queries ? (100 * (tot.no_answer || 0)) / tot.queries : 0,
    extForward,
  };
});
function loadKind(v: number) {
  return v >= 50 ? "err" : v >= 25 ? "warn" : "ok";
}

const insights = computed(() => {
  const d = data.value;
  if (!d || !d.rows.length) return [];
  const k = kpi.value;
  const out: { kind: string; text: string }[] = [];
  const avg = fmtPct(k.avgLoad, lang.value);
  if (k.avgLoad < 10) out.push({ kind: "info", text: t("in_load_low", { avg }) });
  else if (k.avgLoad < 30) out.push({ kind: "info", text: t("in_load_ok", { avg }) });
  else if (k.avgLoad < 60) out.push({ kind: "warn", text: t("in_load_high", { avg }) });
  else out.push({ kind: "err", text: t("in_load_crit", { avg }) });
  if (k.peakLoad >= 50 && k.peakAt) out.push({ kind: "warn", text: t("in_peak", { p: fmtPct(k.peakLoad, lang.value), t: fmtDateTime(k.peakAt, lang.value) }) });
  if (k.pollShare >= 50) out.push({ kind: "info", text: t("in_poll", { p: fmtPct(k.pollShare, lang.value, 0) }) });
  if (k.noAnswerPct > 1) out.push({ kind: k.noAnswerPct > 5 ? "err" : "warn", text: t("in_noanswer", { p: fmtPct(k.noAnswerPct, lang.value), n: fmtNum(d.totals.no_answer, lang.value) }) });
  if (k.extForward > 0) out.push({ kind: "info", text: t("in_external", { n: fmtNum(k.extForward, lang.value) }) });
  if (d.totals.events > 0) out.push({ kind: "info", text: t("in_events", { n: fmtNum(d.totals.events, lang.value) }) });
  return out;
});

const loadDatasets = computed(() => {
  const d = data.value;
  if (!d) return [];
  const step = d.bucket_minutes * 60;
  const byT = new Map(d.rows.map((r) => [r.t, r]));
  const pts: { x: number; y: number | null }[] = [];
  if (d.rows.length) {
    const first = d.rows[0].t;
    const last = d.rows[d.rows.length - 1].t;
    for (let x = first; x <= last; x += step) pts.push({ x, y: byT.has(x) ? byT.get(x)!.load_pct : null });
  }
  return [
    {
      label: t("loadPct"),
      data: pts,
      borderColor: C.load,
      backgroundColor: alpha(C.load, 0.18),
      fill: "origin",
      spanGaps: false,
    },
  ];
});

const typeDatasets = computed(() => {
  const rows = data.value?.rows ?? [];
  const mk = (label: string, color: string, f: (r: BusRow) => number) => ({
    label,
    data: rows.map((r) => ({ x: r.t, y: f(r) })),
    backgroundColor: alpha(color, 0.85),
    borderWidth: 0,
    stack: "frames",
  });
  return [
    mk(t("commands"), C.command, (r) => Math.max(0, r.forward - r.queries)),
    mk(t("queriesDs"), C.query, (r) => r.queries),
    mk(t("answersDs"), C.backward, (r) => r.backward),
    mk(t("eventsDs"), C.event, (r) => r.events),
  ];
});

const noAnswerDatasets = computed(() => {
  const rows = data.value?.rows ?? [];
  const c = themeColors();
  return [
    {
      label: t("noAnswerDs"),
      data: rows.map((r) => ({ x: r.t, y: r.no_answer })),
      backgroundColor: alpha(c.error, 0.75),
      borderWidth: 0,
      yAxisID: "y",
    },
    {
      type: "line",
      label: t("ratioDs"),
      data: rows.map((r) => ({ x: r.t, y: r.queries ? Math.round((1000 * r.no_answer) / r.queries) / 10 : 0 })),
      borderColor: c.warning,
      backgroundColor: c.warning,
      borderWidth: 1.5,
      pointRadius: 0,
      yAxisID: "y2",
    },
  ];
});
</script>

<style scoped>
.head-row { margin-bottom: 12px; min-height: 30px; }
.line-sel { width: auto; min-width: 140px; }
.kpis :deep(.stat) { padding: 12px 14px; }
.kpis :deep(.stat .value) { font-size: 21px; }
.insights { display: flex; flex-direction: column; gap: 8px; }
</style>
