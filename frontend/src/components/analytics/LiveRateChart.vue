<template>
  <Card :title="t('title')" :icon="mdiPulse" :subtitle="t('sub')">
    <template #actions>
      <span class="chip" :class="{ ok: stats.current > 0 }">
        <span class="dot" :class="{ ok: stats.current > 0, pulse: stats.current > 0 }"></span>
        <b class="mono">{{ stats.current.toFixed(1) }}</b>&nbsp;{{ t("fps") }}
      </span>
    </template>
    <LineChart :datasets="datasets" :labels="labels" :time="false" :height="height" stacked />
    <div class="row wrap small muted live-stats">
      <span>{{ t("avg") }}: <b class="txt">{{ stats.avg.toFixed(2) }}</b> {{ t("fps") }}</span>
      <span>{{ t("peak") }}: <b class="txt">{{ stats.peak }}</b> {{ t("fps") }}</span>
      <span>{{ t("total") }}: <b class="txt">{{ stats.total }}</b></span>
      <span :title="t('loadHint')">{{ t("load") }}: <b class="txt">{{ stats.load.toFixed(1) }} %</b></span>
    </div>
  </Card>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, ref, toRaw } from "vue";
import { mdiPulse } from "@mdi/js";
import Card from "../Card.vue";
import LineChart from "../LineChart.vue";
import { onMonitor, state, type MonitorFrame } from "../../lib/store";
import { useT } from "../../lib/i18n";
import { C, alpha } from "./util";

withDefaults(defineProps<{ height?: number }>(), { height: 170 });

const t = useT({
  de: {
    title: "Live-Verkehr",
    sub: "Frames pro Sekunde, letzte 5 Minuten",
    fps: "Frames/s",
    avg: "Ø",
    peak: "Spitze",
    total: "Frames",
    load: "Buslast",
    loadHint: "Geschätzte Busbelegung: übertragene Bits ÷ 1200 bit/s",
    gateway: "Gateway",
    external: "Extern",
  },
  en: {
    title: "Live traffic",
    sub: "Frames per second, last 5 minutes",
    fps: "frames/s",
    avg: "Avg",
    peak: "Peak",
    total: "Frames",
    load: "Bus load",
    loadHint: "Estimated bus occupancy: transmitted bits ÷ 1200 bit/s",
    gateway: "Gateway",
    external: "External",
  },
});

const WINDOW = 300;
const gwCount = new Map<number, number>();
const extCount = new Map<number, number>();
const bitCount = new Map<number, number>();

function add(f: MonitorFrame, live: boolean) {
  const nowS = Date.now() / 1000;
  let ts = f.timestamp || nowS;
  if (live && Math.abs(ts - nowS) > 5) ts = nowS; // gateway clock off → use arrival time
  const s = Math.floor(ts);
  const m = f.external ? extCount : gwCount;
  m.set(s, (m.get(s) || 0) + 1);
  bitCount.set(s, (bitCount.get(s) || 0) + (f.bits || 0) + 3);
}
for (const f of toRaw(state.monitor)) add(f, false);
const off = onMonitor((f) => add(f, true));

const now = ref(Math.floor(Date.now() / 1000));
const timer = window.setInterval(() => {
  now.value = Math.floor(Date.now() / 1000);
  const cut = now.value - WINDOW - 10;
  for (const m of [gwCount, extCount, bitCount]) for (const k of m.keys()) if (k < cut) m.delete(k);
}, 2000);
onBeforeUnmount(() => {
  off();
  clearInterval(timer);
});

const p2 = (n: number) => String(n).padStart(2, "0");
const series = computed(() => {
  const end = now.value - 1; // last complete second
  const labels: string[] = [];
  const gw: number[] = [];
  const ext: number[] = [];
  let bits = 0;
  for (let s = end - WINDOW + 1; s <= end; s++) {
    const d = new Date(s * 1000);
    labels.push(`${p2(d.getHours())}:${p2(d.getMinutes())}:${p2(d.getSeconds())}`);
    gw.push(gwCount.get(s) || 0);
    ext.push(extCount.get(s) || 0);
    bits += bitCount.get(s) || 0;
  }
  return { labels, gw, ext, bits };
});
const labels = computed(() => series.value.labels);
const datasets = computed(() => [
  {
    label: t("gateway"),
    data: series.value.gw,
    borderColor: C.command,
    backgroundColor: alpha(C.command, 0.25),
    fill: "origin",
    borderWidth: 1.5,
    tension: 0.2,
  },
  {
    label: t("external"),
    data: series.value.ext,
    borderColor: C.event,
    backgroundColor: alpha(C.event, 0.3),
    fill: "-1",
    borderWidth: 1.5,
    tension: 0.2,
  },
]);
const stats = computed(() => {
  const { gw, ext, bits } = series.value;
  const tot = gw.map((v, i) => v + ext[i]);
  const total = tot.reduce((a, b) => a + b, 0);
  const last10 = tot.slice(-10).reduce((a, b) => a + b, 0) / 10;
  return {
    total,
    avg: total / WINDOW,
    peak: tot.length ? Math.max(...tot) : 0,
    current: last10,
    load: (100 * bits) / (1200 * WINDOW),
  };
});
</script>

<style scoped>
.live-stats { gap: 4px 16px; margin-top: 8px; }
.txt { color: var(--text); font-weight: 500; }
</style>
