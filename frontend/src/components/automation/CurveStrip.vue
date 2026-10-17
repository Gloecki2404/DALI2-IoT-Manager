<template>
  <div class="cs">
    <div class="cs-row">
      <span v-if="label" class="cs-label" :title="label"><Icon v-if="icon" :path="icon" :size="14" />{{ label }}</span>
      <div class="cs-cells">
        <span
          v-for="c in cells"
          :key="c.h"
          class="cs-cell"
          :class="{ step: c.step, empty: c.empty }"
          :style="{ background: c.bg }"
          :title="c.title"
        ></span>
      </div>
    </div>
    <div v-if="scale" class="cs-scale" :style="{ marginLeft: label ? 'var(--cs-label-w)' : '0' }">
      <span v-for="h in [0, 6, 12, 18, 24]" :key="h" :style="{ left: `${(h / 24) * 100}%` }">{{ h }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import Icon from "../Icon.vue";
import { kelvinToRgb } from "../../lib/dali";
import { useAT } from "./i18n";
import { curveValue, pad2, type CircadianStep } from "./util";

const props = defineProps<{ steps: CircadianStep[]; label?: string; icon?: string; scale?: boolean }>();
const t = useAT();

const cells = computed(() =>
  Array.from({ length: 24 }, (_, h) => {
    const lvl = curveValue(props.steps, h, "dimmable");
    const k = curveValue(props.steps, h, "colorKelvin");
    const empty = lvl === null && k === null;
    const col = k !== null ? kelvinToRgb(k) : "#ffc107";
    const pct = lvl === null ? 85 : Math.round(12 + Math.max(0, Math.min(100, lvl)) * 0.88);
    const parts = [`${pad2(h)}:00`];
    if (lvl !== null) parts.push(`${Math.round(lvl)} %`);
    if (k !== null) parts.push(`${Math.round(k)} K`);
    return {
      h,
      empty,
      step: props.steps?.some((s) => s.hour === h),
      bg: empty ? "var(--bg2)" : `color-mix(in srgb, ${col} ${pct}%, #1a1a1a)`,
      title: empty ? `${pad2(h)}:00 · ${t("noValue")}` : parts.join(" · "),
    };
  }),
);
</script>

<style scoped>
.cs { --cs-label-w: 70px; display: flex; flex-direction: column; gap: 2px; }
.cs-row { display: flex; align-items: center; }
.cs-label { width: var(--cs-label-w); flex-shrink: 0; font-size: 11.5px; color: var(--text2); display: inline-flex; align-items: center; gap: 3px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; padding-right: 4px; }
.cs-cells { flex: 1; display: grid; grid-template-columns: repeat(24, 1fr); gap: 1px; height: 18px; border-radius: 5px; overflow: hidden; }
.cs-cell { display: block; position: relative; }
.cs-cell.step::after { content: ""; position: absolute; left: 50%; bottom: 2px; width: 4px; height: 4px; margin-left: -2px; border-radius: 50%; background: rgba(255, 255, 255, .85); box-shadow: 0 0 0 1px rgba(0, 0, 0, .25); }
.cs-scale { position: relative; height: 13px; font-size: 10px; color: var(--text3); }
.cs-scale span { position: absolute; transform: translateX(-50%); }
.cs-scale span:first-child { transform: none; }
.cs-scale span:last-child { transform: translateX(-100%); }
</style>
