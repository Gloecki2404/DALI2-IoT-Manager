<template>
  <div class="chart-wrap" :style="{ height: `${height}px` }">
    <canvas ref="canvas"></canvas>
  </div>
</template>
<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from "vue";
import {
  BarController,
  BarElement,
  CategoryScale,
  Chart,
  Filler,
  Legend,
  LinearScale,
  LineController,
  LineElement,
  PointElement,
  Tooltip,
  type ChartDataset,
} from "chart.js";
import { lang } from "../lib/i18n";

Chart.register(LineController, BarController, LineElement, BarElement, PointElement, LinearScale, CategoryScale, Filler, Tooltip, Legend);

const props = withDefaults(
  defineProps<{
    datasets: ChartDataset<any, any>[];
    labels?: (string | number)[];
    type?: "line" | "bar";
    height?: number;
    time?: boolean; // x values are unix seconds
    stacked?: boolean;
    yMax?: number;
    yMin?: number;
    yUnit?: string;
    y2?: boolean;
    step?: boolean;
    legend?: boolean;
  }>(),
  { type: "line", height: 240, time: true, legend: true },
);

const canvas = ref<HTMLCanvasElement>();
let chart: Chart | null = null;

function css(name: string, fallback: string) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim() || fallback;
}

function fmtTs(v: number) {
  const d = new Date(v * 1000);
  const loc = lang.value === "de" ? "de-DE" : "en-GB";
  return d.toLocaleString(loc, { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });
}

function build() {
  if (!canvas.value) return;
  chart?.destroy();
  const text2 = css("--text2", "#666");
  const divider = css("--divider", "rgba(0,0,0,.1)");
  chart = new Chart(canvas.value, {
    type: props.type,
    data: { labels: props.labels, datasets: props.datasets.map((d) => ({ ...d })) },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: false,
      parsing: props.time ? false : undefined,
      normalized: true,
      interaction: { mode: "index", intersect: false },
      elements: { point: { radius: 0, hitRadius: 6 }, line: { tension: props.step ? 0 : 0.25, borderWidth: 2, stepped: props.step ? "before" : false } as any },
      plugins: {
        legend: { display: props.legend && props.datasets.length > 1, labels: { color: text2, boxWidth: 12, usePointStyle: true } },
        tooltip: {
          callbacks: {
            title: (items: any[]) => (props.time && items.length ? fmtTs(items[0].parsed.x) : items[0]?.label ?? ""),
            label: (item: any) => `${item.dataset.label}: ${item.formattedValue}${props.yUnit ? " " + props.yUnit : ""}`,
          },
        },
      },
      scales: {
        x: props.time
          ? {
              type: "linear",
              stacked: props.stacked,
              ticks: { color: text2, maxTicksLimit: 8, callback: (v: any) => fmtTs(Number(v)) },
              grid: { color: divider },
            }
          : { stacked: props.stacked, ticks: { color: text2 }, grid: { display: false } },
        y: {
          stacked: props.stacked,
          min: props.yMin,
          max: props.yMax,
          beginAtZero: true,
          ticks: { color: text2, callback: (v: any) => `${v}${props.yUnit ? " " + props.yUnit : ""}` },
          grid: { color: divider },
        },
        ...(props.y2 ? { y2: { position: "right", beginAtZero: true, ticks: { color: text2 }, grid: { display: false } } } : {}),
      } as any,
    },
  });
}

onMounted(build);
watch(() => [props.datasets, props.labels], build, { deep: false });
onBeforeUnmount(() => chart?.destroy());
</script>
<style scoped>
.chart-wrap { position: relative; width: 100%; }
</style>
