<template>
  <div class="ce">
    <div class="row wrap ce-top">
      <div class="btn-group">
        <button type="button" :class="{ active: which === 'longest' }" @click="which = 'longest'">
          <Icon :path="mdiWeatherSunny" :size="16" /> {{ t("curveLongest") }}
        </button>
        <button type="button" :class="{ active: which === 'shortest' }" @click="which = 'shortest'">
          <Icon :path="mdiSnowflake" :size="16" /> {{ t("curveShortest") }}
        </button>
      </div>
      <div class="row date-sel">
        <span class="muted small">{{ t("curveDate") }}</span>
        <select v-model.number="curve.day" class="d-day">
          <option v-for="n in 31" :key="n" :value="n">{{ n }}.</option>
        </select>
        <select v-model.number="curve.month" class="d-month">
          <option v-for="m in 12" :key="m" :value="m">{{ t(`month${m - 1}`) }}</option>
        </select>
      </div>
    </div>
    <div class="hint small faint">{{ which === "longest" ? t("curveLongestHint") : t("curveShortestHint") }}</div>

    <div class="ce-chart">
      <LineChart :key="which" :datasets="datasets" :labels="labels" :time="false" :y-max="100" :y2="true" :height="220" />
    </div>
    <CurveStrip :steps="curve.steps" scale />

    <div class="row wrap presets">
      <span class="muted small">{{ t("presets") }}:</span>
      <button v-for="p in PRESETS" :key="p.id" type="button" class="chip clickable" :title="t(`preset_${p.id}_hint`)" @click="applyPreset(p.id)">
        <Icon :path="p.icon" :size="14" />{{ t(`preset_${p.id}`) }}
      </button>
      <span class="grow"></span>
      <button type="button" class="btn flat sm" :disabled="!other.steps.length" @click="copyOther">
        <Icon :path="mdiContentCopy" :size="16" />{{ which === "longest" ? t("copyFromShortest") : t("copyFromLongest") }}
      </button>
      <button type="button" class="btn flat sm danger" :disabled="!curve.steps.length" @click="curve.steps.splice(0)">
        <Icon :path="mdiEraser" :size="16" />{{ t("clearCurve") }}
      </button>
    </div>

    <div class="table-wrap ce-table-wrap">
      <table class="table ce-table">
        <thead>
          <tr>
            <th>{{ t("hour") }}</th>
            <th>{{ t("brightness") }}</th>
            <th>{{ t("colorTemp") }}</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(s, i) in curve.steps" :key="s.hour">
            <td>
              <select :value="s.hour" class="h-sel" @change="setHour(s, +($event.target as HTMLSelectElement).value)">
                <option v-for="h in hourOptions(s.hour)" :key="h" :value="h">{{ pad2(h) }}:00</option>
              </select>
            </td>
            <td>
              <div class="row cell">
                <input v-model="s.enableDimmable" type="checkbox" :title="t('useValue')" />
                <input v-model.number="s.dimmable" type="number" min="0" max="100" step="1" class="num" :disabled="!s.enableDimmable" />
                <span class="muted small">%</span>
              </div>
            </td>
            <td>
              <div class="row cell">
                <input v-model="s.enableKelvin" type="checkbox" :title="t('useValue')" />
                <span class="swatch" :style="{ background: s.enableKelvin ? kelvinToRgb(Number(s.colorKelvin) || 4000) : 'transparent' }"></span>
                <input v-model.number="s.colorKelvin" type="number" min="1000" max="20000" step="50" class="num k" :disabled="!s.enableKelvin" />
                <span class="muted small">K</span>
              </div>
            </td>
            <td class="right">
              <button type="button" class="btn icon sm" :title="t('removeHour')" @click="curve.steps.splice(i, 1)"><Icon :path="mdiClose" :size="18" /></button>
            </td>
          </tr>
          <tr v-if="!curve.steps.length">
            <td colspan="4" class="faint center">{{ t("curveEmpty") }}</td>
          </tr>
        </tbody>
      </table>
    </div>
    <button type="button" class="add-row" :disabled="curve.steps.length >= 24" @click="addStep">
      <Icon :path="mdiPlus" :size="18" />{{ t("addHour") }}
    </button>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import {
  mdiBriefcaseOutline,
  mdiClose,
  mdiContentCopy,
  mdiEraser,
  mdiPalette,
  mdiPlus,
  mdiSnowflake,
  mdiSofaOutline,
  mdiWeatherSunny,
  mdiWhiteBalanceSunny,
} from "@mdi/js";
import Icon from "../Icon.vue";
import LineChart from "../LineChart.vue";
import CurveStrip from "./CurveStrip.vue";
import { kelvinToRgb } from "../../lib/dali";
import { useAT } from "./i18n";
import { clone, curveValue, pad2, type CircadianCurve, type CircadianStep } from "./util";

const props = defineProps<{ longest: CircadianCurve; shortest: CircadianCurve }>();
const t = useAT();

const which = ref<"longest" | "shortest">("longest");
const curve = computed(() => (which.value === "longest" ? props.longest : props.shortest));
const other = computed(() => (which.value === "longest" ? props.shortest : props.longest));

const labels = Array.from({ length: 24 }, (_, h) => `${pad2(h)}:00`);

function series(steps: CircadianStep[], key: "dimmable" | "colorKelvin") {
  const flag = key === "dimmable" ? "enableDimmable" : "enableKelvin";
  const arr: (number | null)[] = Array(24).fill(null);
  for (const s of steps || []) {
    const v = Number(s[key]);
    if (s[flag] !== false && s[key] !== undefined && s[key] !== null && Number.isFinite(v) && s.hour >= 0 && s.hour < 24) arr[s.hour] = v;
  }
  return arr;
}

const datasets = computed(() => {
  const mine = which.value === "longest" ? t("summerShort") : t("winterShort");
  const theirs = which.value === "longest" ? t("winterShort") : t("summerShort");
  return [
    {
      label: `${t("brightness")} % (${mine})`,
      data: series(curve.value.steps, "dimmable"),
      borderColor: "#ffa000",
      backgroundColor: "#ffa000",
      spanGaps: true,
      tension: 0,
      pointRadius: 4,
      pointHoverRadius: 6,
      yAxisID: "y",
    },
    {
      label: `${t("colorTemp")} K (${mine})`,
      data: series(curve.value.steps, "colorKelvin"),
      borderColor: "#039be5",
      backgroundColor: "#039be5",
      spanGaps: true,
      tension: 0,
      pointRadius: 4,
      pointHoverRadius: 6,
      yAxisID: "y2",
    },
    {
      label: `% (${theirs})`,
      data: series(other.value.steps, "dimmable"),
      borderColor: "rgba(255,160,0,.45)",
      backgroundColor: "rgba(255,160,0,.45)",
      borderDash: [5, 4],
      borderWidth: 1.5,
      spanGaps: true,
      tension: 0,
      pointRadius: 0,
      yAxisID: "y",
    },
    {
      label: `K (${theirs})`,
      data: series(other.value.steps, "colorKelvin"),
      borderColor: "rgba(3,155,229,.45)",
      backgroundColor: "rgba(3,155,229,.45)",
      borderDash: [5, 4],
      borderWidth: 1.5,
      spanGaps: true,
      tension: 0,
      pointRadius: 0,
      yAxisID: "y2",
    },
  ];
});

function hourOptions(own: number) {
  const used = new Set(curve.value.steps.map((s) => s.hour));
  return Array.from({ length: 24 }, (_, h) => h).filter((h) => h === own || !used.has(h));
}

function sortSteps() {
  curve.value.steps.sort((a, b) => a.hour - b.hour);
}

function setHour(s: CircadianStep, h: number) {
  s.hour = h;
  sortSteps();
}

function addStep() {
  const steps = curve.value.steps;
  const used = new Set(steps.map((s) => s.hour));
  if (used.size >= 24) return;
  const last = steps.length ? Math.max(...steps.map((s) => s.hour)) : 6;
  let h = steps.length ? (last + 2) % 24 : 7;
  for (let i = 0; i < 24 && used.has(h); i++) h = (h + 1) % 24;
  const lvl = curveValue(steps, h, "dimmable");
  const k = curveValue(steps, h, "colorKelvin");
  steps.push({
    hour: h,
    dimmable: lvl === null ? 80 : Math.round(lvl),
    enableDimmable: true,
    colorKelvin: k === null ? 4000 : Math.round(k / 50) * 50,
    enableKelvin: true,
  });
  sortSteps();
}

function copyOther() {
  curve.value.steps.splice(0, curve.value.steps.length, ...clone(other.value.steps));
}

// ------------------------------------------------------------------ presets
type P = [number, number | null, number | null];
const mk = (pts: P[]): CircadianStep[] =>
  pts.map(([hour, d, k]) => ({
    hour,
    dimmable: d ?? 100,
    enableDimmable: d !== null,
    colorKelvin: k ?? 4000,
    enableKelvin: k !== null,
  }));

const PRESETS = [
  {
    id: "daylight",
    icon: mdiWhiteBalanceSunny,
    longest: mk([[5, 10, 2700], [7, 60, 3500], [9, 90, 4500], [12, 100, 6000], [15, 100, 5500], [18, 80, 4000], [20, 50, 3000], [22, 20, 2700]]),
    shortest: mk([[7, 10, 2700], [9, 60, 3500], [12, 100, 5000], [14, 90, 4500], [16, 70, 3500], [18, 40, 2700], [21, 15, 2700]]),
  },
  {
    id: "colorOnly",
    icon: mdiPalette,
    longest: mk([[5, null, 2700], [8, null, 4000], [12, null, 6500], [16, null, 5000], [19, null, 3500], [22, null, 2700]]),
    shortest: mk([[7, null, 2700], [10, null, 4000], [12, null, 5500], [14, null, 4500], [17, null, 3000], [20, null, 2700]]),
  },
  {
    id: "office",
    icon: mdiBriefcaseOutline,
    longest: mk([[6, 40, 3500], [8, 100, 5000], [12, 100, 6000], [16, 100, 5000], [18, 60, 3500], [20, 30, 3000]]),
    shortest: mk([[6, 50, 3500], [8, 100, 5000], [12, 100, 5500], [15, 100, 4500], [17, 70, 3500], [20, 30, 3000]]),
  },
  {
    id: "living",
    icon: mdiSofaOutline,
    longest: mk([[7, 60, 3500], [12, 100, 4500], [17, 80, 3500], [20, 50, 2700], [23, 20, 2200]]),
    shortest: mk([[7, 50, 3000], [12, 90, 4000], [16, 70, 3000], [19, 45, 2700], [22, 20, 2200]]),
  },
];

function applyPreset(id: string) {
  const p = PRESETS.find((x) => x.id === id);
  if (!p) return;
  props.longest.steps.splice(0, props.longest.steps.length, ...clone(p.longest));
  props.shortest.steps.splice(0, props.shortest.steps.length, ...clone(p.shortest));
}
</script>

<style scoped>
.ce { display: flex; flex-direction: column; gap: 10px; }
.ce-top { gap: 10px 16px; justify-content: space-between; }
.date-sel { gap: 6px; }
.d-day { width: 72px !important; }
.d-month { width: 140px !important; }
.ce-chart { margin-top: 4px; }
.presets { gap: 6px; }
.presets .chip { border: 0; cursor: pointer; }
.ce-table-wrap { border: 1px solid var(--divider); border-radius: 12px; max-height: 360px; overflow: auto; }
.ce-table td { padding: 5px 10px; }
.ce-table th { padding: 8px 10px; }
.h-sel { width: 96px !important; height: 34px; }
.cell { gap: 6px; flex-wrap: nowrap; }
.num { width: 72px !important; height: 34px; }
.num.k { width: 86px !important; }
.num:disabled { opacity: .45; }
</style>
