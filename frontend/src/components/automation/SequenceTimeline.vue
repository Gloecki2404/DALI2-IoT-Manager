<template>
  <div class="tl" :class="{ compact, active }">
    <div v-if="!segs.length" class="faint small">{{ t("noSteps") }}</div>
    <template v-else>
      <div class="tl-track">
        <div
          v-for="s in segs"
          :key="s.no"
          class="tl-seg"
          :class="{ disabled: !s.enabled, zero: s.enabled && s.delay === 0 }"
          :style="s.enabled ? { flexGrow: grow(s.delay), '--seg': s.color } : {}"
          :title="s.title"
          @click="$emit('select', s.no - 1)"
        >
          <span class="tl-no">{{ s.no }}</span>
          <span v-if="!compact && s.enabled" class="tl-t">{{ fmtSec(s.start) }}</span>
        </div>
        <span v-if="loop" class="tl-end" :title="t('runLoop')"><Icon :path="mdiRepeat" :size="15" /></span>
        <span v-else-if="repeat && repeat > 0" class="tl-end mono small" :title="t('runRepeat')">×{{ repeat }}</span>
      </div>
      <div class="tl-scale">
        <span>0 s</span>
        <span class="grow"></span>
        <span>{{ t("cycleDuration") }}: <b>{{ fmtSec(total) }}</b></span>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { mdiRepeat } from "@mdi/js";
import Icon from "../Icon.vue";
import { useAT } from "./i18n";
import { actionColor, actionSummary, fmtSec, targetsText, type SequenceStep } from "./util";

const props = defineProps<{ steps: SequenceStep[]; loop?: boolean; repeat?: number | null; compact?: boolean; active?: boolean }>();
defineEmits<{ (e: "select", index: number): void }>();
const t = useAT();

const segs = computed(() => {
  let acc = 0;
  return (props.steps || []).map((s, i) => {
    const delay = Math.max(0, Number(s.delay) || 0);
    const enabled = s.enabled !== false;
    const seg = {
      no: i + 1,
      start: acc,
      delay,
      enabled,
      color: actionColor(s.data?.features),
      title:
        `#${i + 1}${enabled ? ` · t = ${fmtSec(acc)}` : ` · ${t("stepDisabled")}`}\n` +
        `${actionSummary(s.data?.features, t)} → ${targetsText(s.data?.targets, t)}\n` +
        `${t("waitAfter")}: ${fmtSec(delay)}`,
    };
    if (enabled) acc += delay;
    return seg;
  });
});
const total = computed(() => segs.value.filter((s) => s.enabled).reduce((a, s) => a + s.delay, 0));

function grow(delay: number) {
  return total.value > 0 ? Math.max(delay / total.value, 0) * 100 : 1;
}
</script>

<style scoped>
.tl { display: flex; flex-direction: column; gap: 4px; min-width: 0; }
.tl-track { display: flex; align-items: stretch; gap: 2px; height: 34px; position: relative; overflow: hidden; border-radius: 8px; }
.tl.compact .tl-track { height: 20px; border-radius: 6px; }
.tl-seg {
  flex: 1 1 0; min-width: 22px; background: var(--seg, var(--primary));
  border-radius: 4px; display: flex; flex-direction: column; justify-content: center; align-items: flex-start; padding: 0 3px; overflow: hidden;
  color: #1f2328; cursor: pointer; position: relative; gap: 1px;
}
.tl-seg:hover { filter: brightness(1.06); }
.tl.compact .tl-seg { min-width: 12px; padding: 0 4px; }
.tl-seg.zero { flex: 0 0 22px; }
.tl.compact .tl-seg.zero { flex: 0 0 12px; }
.tl-seg.disabled {
  flex: 0 0 18px; min-width: 18px; color: var(--text3);
  background: repeating-linear-gradient(45deg, var(--bg2), var(--bg2) 4px, transparent 4px, transparent 8px);
}
.tl.compact .tl-seg.disabled { flex-basis: 10px; min-width: 10px; }
.tl-no { font-size: 11px; font-weight: 600; line-height: 14px; white-space: nowrap; background: rgba(255, 255, 255, .82); border-radius: 7px; padding: 0 4px; min-width: 14px; text-align: center; }
.tl.compact .tl-no { font-size: 9.5px; line-height: 12px; padding: 0 3px; }
.tl-seg.disabled .tl-no { background: transparent; color: var(--text3); }
.tl-t { font-size: 10px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; line-height: 12px; background: rgba(255, 255, 255, .6); border-radius: 6px; padding: 0 4px; max-width: 100%; }
.tl-end { display: inline-flex; align-items: center; justify-content: center; padding: 0 6px; color: var(--primary); background: var(--primary-soft); border-radius: 4px; }
.tl-scale { display: flex; font-size: 11.5px; color: var(--text3); gap: 6px; }
.tl.compact .tl-scale { font-size: 11px; }
.tl.active .tl-track::after {
  content: ""; position: absolute; inset: 0; pointer-events: none;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, .55), transparent);
  background-size: 40% 100%; background-repeat: no-repeat; animation: tl-sweep 1.8s linear infinite;
}
@keyframes tl-sweep { from { background-position: -60% 0; } to { background-position: 160% 0; } }
</style>
