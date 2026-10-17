<template>
  <div class="lc">
    <div class="row power">
      <button class="bulb" :class="{ on }" :style="bulbStyle" :title="on ? t('off') : t('on')" @click="toggle">
        <Icon :path="on ? mdiLightbulbOn : mdiLightbulbOutline" :size="28" />
      </button>
      <div class="grow">
        <div class="big">{{ on ? `${Math.round(levelShown)} %` : t("off") }}</div>
        <div v-if="hasCT && kelvinShown" class="muted small">{{ kelvinShown }} K</div>
      </div>
      <div class="row">
        <button v-if="'dimDown' in features" class="btn icon" :title="t('dimDown')" @click="send({ dimDown: 1 })"><Icon :path="mdiBrightness5" /></button>
        <button v-if="'dimUp' in features" class="btn icon" :title="t('dimUp')" @click="send({ dimUp: 1 })"><Icon :path="mdiBrightness7" /></button>
        <button v-if="'gotoLastActive' in features" class="btn icon" :title="t('last')" @click="send({ gotoLastActive: true })"><Icon :path="mdiHistory" /></button>
      </div>
    </div>

    <div v-if="'dimmable' in features" class="field mt">
      <span class="row between"><span>{{ t("brightness") }}</span><span class="mono">{{ Math.round(levelShown) }} %</span></span>
      <input type="range" min="0" max="100" step="1" :value="levelShown" :style="{ '--track': brightnessTrack }"
             @input="dragLevel = +($event.target as HTMLInputElement).value" @change="commitLevel" />
    </div>

    <div v-if="hasCT" class="field mt">
      <span class="row between"><span>{{ t("colorTemp") }}</span><span class="mono">{{ kelvinShown ?? "–" }} K</span></span>
      <input type="range" :min="kMin" :max="kMax" step="50" :value="kelvinShown ?? 4000" :style="{ '--track': ctTrack }"
             @input="dragKelvin = +($event.target as HTMLInputElement).value" @change="commitKelvin" />
      <div class="row wrap presets">
        <button v-for="k in [2700, 3000, 4000, 5000, 6500]" :key="k" class="chip clickable" @click="setKelvin(k)">
          <span class="swatch" :style="{ background: kelvinToRgb(k) }"></span>{{ k }} K
        </button>
      </div>
    </div>

    <div v-if="hasRGBc" class="field mt">
      <span>{{ t("color") }} (RGB)</span>
      <div class="row">
        <input type="color" :value="rgbHex" @change="setRgb(($event.target as HTMLInputElement).value)" />
        <button v-for="c in ['#ff0000', '#ff8000', '#ffff00', '#00ff00', '#00ffff', '#0000ff', '#ff00ff', '#ffffff']" :key="c"
                class="swatch clickable big-swatch" :style="{ background: c }" @click="setRgb(c)"></button>
      </div>
    </div>

    <div v-if="hasXYc" class="form-grid mt">
      <label class="field"><span>CIE x</span><input v-model.number="xy.x" type="number" step="0.001" min="0" max="0.8" /></label>
      <label class="field"><span>CIE y</span><input v-model.number="xy.y" type="number" step="0.001" min="0" max="0.9" /></label>
      <div class="field"><span>&nbsp;</span><button class="btn outline" @click="send({ colorXY: { x: xy.x, y: xy.y } })">{{ t("apply") }}</button></div>
    </div>

    <div v-if="hasWAFc" class="mt">
      <div class="small muted">WAF ({{ t("waf") }})</div>
      <div v-for="ch in (['w', 'a', 'f'] as const)" :key="ch" class="row">
        <span class="mono waf-label">{{ ch.toUpperCase() }}</span>
        <input type="range" min="0" max="1" step="0.01" v-model.number="waf[ch]" @change="send({ colorWAF: { ...waf } })" />
        <span class="mono small">{{ Math.round(waf[ch] * 100) }}%</span>
      </div>
    </div>

    <div v-if="'scene' in features && showScenes" class="mt">
      <div class="small muted mb">{{ t("scenes") }}</div>
      <div class="scene-grid">
        <button v-for="n in 16" :key="n" class="btn gray sm" @click="send({ scene: n - 1 })">{{ n - 1 }}</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from "vue";
import { mdiBrightness5, mdiBrightness7, mdiHistory, mdiLightbulbOn, mdiLightbulbOutline } from "@mdi/js";
import Icon from "./Icon.vue";
import { gw } from "../lib/api";
import { run, sentKelvin } from "../lib/store";
import { useT } from "../lib/i18n";
import { hasColorTemp, hasRGB, hasWAF, hasXY, hexToRgb, isOn, kelvin, kelvinToRgb, level, rgbToHex, status } from "../lib/dali";

const props = withDefaults(
  defineProps<{ features: Record<string, any>; target: string; targetId: number | null; showScenes?: boolean; kMin?: number; kMax?: number }>(),
  { showScenes: true, kMin: 2700, kMax: 6500 },
);

const t = useT({
  de: { dimUp: "Heller", dimDown: "Dunkler", last: "Letzter Wert", apply: "Übernehmen", waf: "Weiß / Amber / Frei" },
  en: { dimUp: "Brighter", dimDown: "Darker", last: "Last level", apply: "Apply", waf: "White / Amber / Free" },
});

const key = computed(() => `${props.target}:${props.targetId}`);

const on = computed(() => isOn(props.features));
const dragLevel = ref<number | null>(null);
const dragKelvin = ref<number | null>(null);
const levelShown = computed(() => dragLevel.value ?? level(props.features));
const hasCT = computed(() => hasColorTemp(props.features));
const hasRGBc = computed(() => hasRGB(props.features));
const hasXYc = computed(() => hasXY(props.features));
const hasWAFc = computed(() => hasWAF(props.features));
const kelvinReported = computed(() => kelvin(props.features));
const kelvinShown = computed(() => {
  if (dragKelvin.value) return dragKelvin.value;
  const s = sentKelvin.get(key.value);
  if (s && s.reported === kelvinReported.value) return s.k;
  return kelvinReported.value;
});
const rgbHex = computed(() => {
  const c = status(props.features, "colorRGB");
  return c && c.r !== null ? rgbToHex(c.r, c.g, c.b) : "#ffffff";
});
const xy = reactive({ x: 0.3127, y: 0.329 });
const waf = reactive({ w: 0, a: 0, f: 0 });
watch(
  () => props.features,
  (f) => {
    const x = status(f, "colorXY");
    if (x?.x != null) Object.assign(xy, x);
    const w = status(f, "colorWAF");
    if (w) Object.assign(waf, { w: w.w ?? 0, a: w.a ?? 0, f: w.f ?? 0 });
  },
  { immediate: true },
);

const bulbStyle = computed(() => {
  if (!on.value) return {};
  const col = hasCT.value && kelvinShown.value ? kelvinToRgb(kelvinShown.value) : hasRGBc.value ? rgbHex.value : "#ffc107";
  return { color: col, background: `color-mix(in srgb, ${col} 22%, transparent)` };
});
const brightnessTrack = computed(() => `linear-gradient(90deg, #444, ${hasCT.value && kelvinShown.value ? kelvinToRgb(kelvinShown.value) : "#ffd54f"})`);
const ctTrack = computed(() => `linear-gradient(90deg, ${kelvinToRgb(props.kMin)}, ${kelvinToRgb(props.kMax)})`);

async function send(data: Record<string, unknown>) {
  await run(() => gw.control(props.target, props.targetId, data));
}
async function toggle() {
  if (on.value) await send({ switchable: false });
  else if ("gotoLastActive" in props.features) await send({ gotoLastActive: true });
  else await send({ switchable: true });
}
async function commitLevel() {
  const v = dragLevel.value;
  if (v === null) return;
  await send({ dimmable: v });
  setTimeout(() => (dragLevel.value = null), 1500);
}
async function setKelvin(k: number) {
  sentKelvin.set(key.value, { k, reported: kelvinReported.value });
  await send({ colorKelvin: k });
}
async function commitKelvin() {
  const v = dragKelvin.value;
  if (v === null) return;
  await setKelvin(v);
  dragKelvin.value = null;
}
async function setRgb(hex: string) {
  await send({ colorRGB: hexToRgb(hex) });
}
</script>

<style scoped>
.power { gap: 14px; }
.bulb { width: 56px; height: 56px; border-radius: 50%; border: 0; cursor: pointer; background: var(--bg2); color: var(--text2); display: flex; align-items: center; justify-content: center; transition: all .2s; }
.bulb:hover { filter: brightness(1.05); }
.big { font-size: 22px; font-weight: 500; }
.presets { margin-top: 4px; gap: 6px; }
.scene-grid { display: grid; grid-template-columns: repeat(8, 1fr); gap: 6px; }
.big-swatch { width: 26px; height: 26px; cursor: pointer; padding: 0; }
.waf-label { width: 16px; }
@media (max-width: 700px) { .scene-grid { grid-template-columns: repeat(4, 1fr); } }
</style>
