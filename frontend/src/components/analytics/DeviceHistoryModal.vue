<template>
  <Modal :open="open" :title="title" :subtitle="subtitle" :icon="mdiChartTimelineVariant" wide @close="$emit('close')">
    <div v-if="loading" class="center pad"><span class="spinner"></span></div>
    <div v-else-if="error" class="banner err">
      <Icon :path="mdiAlertCircle" :size="18" /><div>{{ error }}</div>
    </div>
    <Empty v-else-if="!rows.length" :icon="mdiChartTimelineVariant" :text="t('noData')" />
    <template v-else>
      <div v-if="summary" class="kpis">
        <div class="kpi">
          <div class="kv-v">{{ fmtDuration(summary.on_s, lang) }}</div>
          <div class="small muted">{{ t("onTime") }} ({{ fmtPct(summary.on_pct, lang) }})</div>
        </div>
        <div class="kpi">
          <div class="kv-v">{{ summary.switches }}</div>
          <div class="small muted">{{ t("switches") }}</div>
        </div>
        <div class="kpi">
          <div class="kv-v">{{ summary.avg_level === null ? "–" : fmtPct(summary.avg_level, lang, 0) }}</div>
          <div class="small muted">{{ t("avgLevel") }}</div>
        </div>
        <div class="kpi" :class="{ bad: summary.unavailable_s > 0 }">
          <div class="kv-v">{{ fmtDuration(summary.unavailable_s, lang) }}</div>
          <div class="small muted">{{ t("downtime") }}</div>
        </div>
        <div class="kpi" :class="{ bad: summary.failures > 0 }">
          <div class="kv-v">{{ summary.failures }}</div>
          <div class="small muted">{{ t("failures") }}</div>
        </div>
      </div>

      <div class="section-title">{{ t("levelChart") }}</div>
      <LineChart :datasets="levelDatasets" :height="220" step :y-max="100" :y2="hasKelvin" />

      <div class="section-title">{{ t("stateChart") }}</div>
      <LineChart :datasets="stateDatasets" :height="140" step :y-max="1.05" />

      <div class="section-title">{{ t("changes", { n: rows.length }) }}</div>
      <div class="table-wrap changes">
        <table class="table small">
          <thead>
            <tr>
              <th>{{ t("time") }}</th>
              <th>{{ t("status") }}</th>
              <th class="right">{{ t("brightness") }}</th>
              <th v-if="hasKelvin" class="right">K</th>
              <th>{{ t("available") }}</th>
              <th>{{ t("faults") }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(r, i) in changes" :key="i">
              <td class="mono nowrap">{{ fmtTime(r.ts, lang) }}</td>
              <td><span class="chip" :class="r.is_on ? 'primary' : ''">{{ r.is_on ? t("on") : t("off") }}</span></td>
              <td class="right mono">{{ r.level === null ? "–" : `${Math.round(r.level)} %` }}</td>
              <td v-if="hasKelvin" class="right mono">{{ r.kelvin ?? "–" }}</td>
              <td><span class="dot" :class="r.available ? 'ok' : 'err'"></span></td>
              <td>
                <span v-if="r.lamp_failure" class="chip err">{{ t("lamp") }}</span>
                <span v-if="r.gear_failure" class="chip err">{{ t("gear") }}</span>
                <span v-if="!r.lamp_failure && !r.gear_failure" class="faint">–</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-if="rows.length > changes.length" class="small faint mt">{{ t("more", { n: rows.length - changes.length }) }}</div>
    </template>
  </Modal>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { mdiAlertCircle, mdiChartTimelineVariant } from "@mdi/js";
import Modal from "../Modal.vue";
import Icon from "../Icon.vue";
import Empty from "../Empty.vue";
import LineChart from "../LineChart.vue";
import { api } from "../../lib/api";
import { lang, useT } from "../../lib/i18n";
import { fmtDuration, fmtTime } from "../../lib/dali";
import { PALETTE, alpha, fmtPct, themeColors } from "./util";

const props = defineProps<{ open: boolean; deviceId: number | null; hours: number; summary?: any; name?: string }>();
defineEmits<{ (e: "close"): void }>();

const t = useT({
  de: {
    noData: "Für diesen Zeitraum sind keine Zustandsdaten vorhanden.",
    onTime: "Einschaltdauer",
    switches: "Einschaltvorgänge",
    avgLevel: "Ø Helligkeit (an)",
    downtime: "Nicht erreichbar",
    failures: "Fehlerereignisse",
    levelChart: "Helligkeit & Farbtemperatur",
    stateChart: "Erreichbarkeit & Fehler",
    changes: "Zustandsänderungen ({n})",
    level: "Helligkeit (%)",
    kelvin: "Farbtemperatur (K)",
    reach: "Erreichbar",
    lamp: "Lampenfehler",
    gear: "Betriebsgerät",
    faults: "Fehler",
    more: "… und {n} ältere Einträge",
    range: "Letzte {h}",
  },
  en: {
    noData: "No state data for this period.",
    onTime: "On time",
    switches: "Switch-on cycles",
    avgLevel: "Avg level (on)",
    downtime: "Unreachable",
    failures: "Failure events",
    levelChart: "Brightness & colour temperature",
    stateChart: "Availability & failures",
    changes: "State changes ({n})",
    level: "Brightness (%)",
    kelvin: "Colour temperature (K)",
    reach: "Reachable",
    lamp: "Lamp failure",
    gear: "Control gear",
    faults: "Failures",
    more: "… and {n} older entries",
    range: "Last {h}",
  },
});

interface StateRow {
  ts: number;
  device_id: number;
  is_on: number;
  level: number | null;
  kelvin: number | null;
  available: number;
  lamp_failure: number;
  gear_failure: number;
}

const rows = ref<StateRow[]>([]);
const loading = ref(false);
const error = ref("");

const title = computed(() => props.name || `#${props.deviceId}`);
const subtitle = computed(() => t("range", { h: props.hours < 48 ? `${props.hours} h` : `${Math.round(props.hours / 24)} ${lang.value === "de" ? "Tage" : "days"}` }));

async function load() {
  if (!props.open || props.deviceId === null) return;
  loading.value = true;
  error.value = "";
  try {
    rows.value = (await api<StateRow[]>("GET", `analytics/device/${props.deviceId}?hours=${props.hours}`)) || [];
  } catch (e: any) {
    error.value = e?.message || String(e);
    rows.value = [];
  } finally {
    loading.value = false;
  }
}
watch(() => [props.open, props.deviceId, props.hours], load, { immediate: true });

const hasKelvin = computed(() => rows.value.some((r) => r.kelvin !== null && r.kelvin !== undefined));
const withNow = computed(() => {
  if (!rows.value.length) return [];
  const last = rows.value[rows.value.length - 1];
  return [...rows.value, { ...last, ts: Date.now() / 1000 }];
});

const levelDatasets = computed(() => {
  const pts = withNow.value;
  const ds: any[] = [
    {
      label: t("level"),
      data: pts.map((r) => ({ x: r.ts, y: r.is_on ? (r.level ?? 100) : 0 })),
      borderColor: PALETTE[1],
      backgroundColor: alpha(PALETTE[1], 0.2),
      fill: "origin",
      yAxisID: "y",
    },
  ];
  if (hasKelvin.value) {
    ds.push({
      label: t("kelvin"),
      data: pts.filter((r) => r.kelvin !== null).map((r) => ({ x: r.ts, y: r.kelvin })),
      borderColor: PALETTE[0],
      borderDash: [5, 4],
      borderWidth: 1.5,
      yAxisID: "y2",
    });
  }
  return ds;
});

const stateDatasets = computed(() => {
  const pts = withNow.value;
  const c = themeColors();
  return [
    { label: t("reach"), data: pts.map((r) => ({ x: r.ts, y: r.available ? 1 : 0 })), borderColor: c.success, backgroundColor: alpha(c.success, 0.15), fill: "origin" },
    { label: t("lamp"), data: pts.map((r) => ({ x: r.ts, y: r.lamp_failure ? 1 : 0 })), borderColor: c.error, borderWidth: 1.5 },
    { label: t("gear"), data: pts.map((r) => ({ x: r.ts, y: r.gear_failure ? 1 : 0 })), borderColor: c.warning, borderWidth: 1.5, borderDash: [4, 3] },
  ];
});

const changes = computed(() => [...rows.value].reverse().slice(0, 100));
</script>

<style scoped>
.pad { padding: 40px 0; }
.kpis { display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 8px; }
.kpi { background: var(--bg2); border-radius: 10px; padding: 10px 12px; }
.kpi.bad { background: color-mix(in srgb, var(--error) 12%, transparent); }
.kv-v { font-size: 18px; font-weight: 500; }
.changes { max-height: 280px; overflow: auto; }
</style>
