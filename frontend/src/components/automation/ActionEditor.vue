<template>
  <div class="ae">
    <div class="ae-row">
      <label class="field ae-kind">
        <span>{{ t("action") }}</span>
        <select :value="kind" @change="setKind(($event.target as HTMLSelectElement).value as Kind)">
          <optgroup :label="t('grpSwitch')">
            <option value="on">{{ t("actOn") }}</option>
            <option value="off">{{ t("actOff") }}</option>
            <option value="last">{{ t("actLast") }}</option>
            <option value="lastFade">{{ t("actLastFade") }}</option>
          </optgroup>
          <optgroup :label="t('grpDim')">
            <option value="dim">{{ t("actDim") }}</option>
            <option value="dimFade">{{ t("actDimFade") }}</option>
            <option value="dimUp">{{ t("actDimUp") }}</option>
            <option value="dimDown">{{ t("actDimDown") }}</option>
          </optgroup>
          <optgroup :label="t('grpScene')">
            <option value="scene">{{ t("actScene") }}</option>
            <option value="sceneFade">{{ t("actSceneFade") }}</option>
          </optgroup>
          <optgroup :label="t('grpColor')">
            <option value="kelvin">{{ t("actKelvin") }}</option>
            <option value="kelvinFade">{{ t("actKelvinFade") }}</option>
            <option value="dimKelvin">{{ t("actDimKelvin") }}</option>
            <option value="rgb">{{ t("actRgb") }}</option>
            <option value="dimRgb">{{ t("actDimRgb") }}</option>
          </optgroup>
          <optgroup :label="t('grpExpert')">
            <option value="raw">{{ t("actRaw") }}</option>
          </optgroup>
        </select>
      </label>

      <div class="ae-params">
        <div v-if="uses.level" class="field ae-level">
          <span class="row between"><span>{{ t("brightness") }}</span><span class="mono">{{ fmtNum(level) }} %</span></span>
          <div class="row">
            <input v-model.number="p.level" type="range" min="0" max="100" step="1" :style="{ '--track': levelTrack }" />
            <input v-model.number="p.level" class="num" type="number" min="0" max="100" step="1" />
          </div>
        </div>

        <label v-if="uses.scene" class="field ae-small">
          <span>{{ t("scene") }}</span>
          <select v-model.number="p.scene">
            <option v-for="n in 16" :key="n" :value="n - 1">{{ t("scene") }} {{ n - 1 }}</option>
          </select>
        </label>

        <div v-if="uses.kelvin" class="field ae-kelvin">
          <span class="row between"><span>{{ t("colorTemp") }}</span><span class="mono">{{ Math.round(kelvinVal) }} K</span></span>
          <div class="row">
            <span class="swatch" :style="{ background: kelvinToRgb(kelvinVal) }"></span>
            <input v-model.number="p.kelvin" type="range" min="2000" max="7000" step="50" :style="{ '--track': ctTrack }" />
            <input v-model.number="p.kelvin" class="num wide" type="number" min="1000" max="20000" step="50" />
          </div>
          <div class="row wrap presets">
            <button v-for="k in [2700, 3000, 4000, 5000, 6500]" :key="k" type="button" class="chip clickable" :class="{ primary: kelvinVal === k }" @click="p.kelvin = k">
              {{ k }} K
            </button>
          </div>
        </div>

        <div v-if="uses.rgb" class="field ae-rgb">
          <span>{{ t("color") }} (RGB)</span>
          <div class="row wrap">
            <input v-model="p.rgb" type="color" />
            <span class="mono small">{{ p.rgb }}</span>
            <button
              v-for="c in RGB_PRESETS"
              :key="c"
              type="button"
              class="swatch rgb-preset"
              :class="{ sel: p.rgb.toLowerCase() === c }"
              :style="{ background: c }"
              :title="c"
              @click="p.rgb = c"
            ></button>
          </div>
        </div>

        <label v-if="uses.fade" class="field ae-small">
          <span>{{ t("fadeTime") }}</span>
          <select v-model.number="p.fade">
            <option v-for="f in fadeOptions" :key="f" :value="f">{{ f === 0 ? t("fadeInstant") : `${fmtNum(f)} s` }}</option>
          </select>
        </label>

        <label v-if="uses.steps" class="field ae-small">
          <span>{{ t("dimSteps") }}</span>
          <input v-model.number="p.steps" type="number" min="1" max="5" step="1" />
        </label>

        <div v-if="kind === 'raw'" class="field ae-raw">
          <span>{{ t("rawJson") }}</span>
          <textarea v-model="p.raw" rows="4" spellcheck="false" :class="{ invalid: rawError }"></textarea>
          <span v-if="rawError" class="err-text small">{{ t("rawInvalid") }}</span>
          <span v-else class="hint">{{ t("rawHint") }}</span>
        </div>

        <div v-if="!uses.any && kind !== 'raw'" class="ae-noparams muted small">
          <Icon :path="kind === 'off' ? mdiLightbulbOutline : mdiLightbulbOn" :size="18" />
          {{ kind === "off" ? t("actOffHint") : kind === "on" ? t("actOnHint") : t("actLastHint") }}
        </div>
      </div>
    </div>

    <div v-if="(showSupport && support !== 'unknown' && support !== 'all') || (tryable && targets?.length)" class="row wrap ae-foot">
      <span v-if="showSupport && support === 'none'" class="chip err"><Icon :path="mdiAlertCircleOutline" :size="14" />{{ t("supportNone") }}</span>
      <span v-else-if="showSupport && support === 'some'" class="chip warn"><Icon :path="mdiAlertOutline" :size="14" />{{ t("supportSome") }}</span>
      <span class="grow"></span>
      <button
        v-if="tryable && targets?.length"
        type="button"
        class="btn flat sm"
        :disabled="!built || trying"
        :title="t('tryHint')"
        @click="tryIt"
      >
        <Icon :path="mdiPlayCircleOutline" :size="17" />{{ t("tryNow") }}
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from "vue";
import { mdiAlertCircleOutline, mdiAlertOutline, mdiLightbulbOn, mdiLightbulbOutline, mdiPlayCircleOutline } from "@mdi/js";
import Icon from "../Icon.vue";
import type { Target } from "../../lib/store";
import { FADE_TIMES, hexToRgb, kelvinToRgb, rgbToHex } from "../../lib/dali";
import { useAT } from "./i18n";
import { actionSupport, fmtNum, tryAction, type Features } from "./util";

type Kind =
  | "on"
  | "off"
  | "last"
  | "lastFade"
  | "dim"
  | "dimFade"
  | "dimUp"
  | "dimDown"
  | "scene"
  | "sceneFade"
  | "kelvin"
  | "kelvinFade"
  | "dimKelvin"
  | "rgb"
  | "dimRgb"
  | "raw";

const props = withDefaults(
  defineProps<{ modelValue: Features; targets?: Target[]; tryable?: boolean; showSupport?: boolean }>(),
  { targets: () => [], tryable: true, showSupport: true },
);
const emit = defineEmits<{ (e: "update:modelValue", v: Features): void }>();
const t = useAT();

const RGB_PRESETS = ["#ff0000", "#ff8000", "#ffff00", "#00ff00", "#00ffff", "#0000ff", "#ff00ff", "#ffffff"];

const kind = ref<Kind>("on");
const p = reactive({ level: 100, fade: 1, scene: 0, kelvin: 4000, rgb: "#ffffff", steps: 1, raw: "{}" });
const trying = ref(false);

const clamp = (v: any, lo: number, hi: number, dflt: number) => {
  const n = Number(v);
  return Number.isFinite(n) ? Math.min(hi, Math.max(lo, n)) : dflt;
};
const level = computed(() => clamp(p.level, 0, 100, 0));
const kelvinVal = computed(() => clamp(p.kelvin, 1000, 20000, 4000));
const fadeVal = computed(() => clamp(p.fade, 0, 3600, 0));

const uses = computed(() => {
  const k = kind.value;
  const u = {
    level: ["dim", "dimFade", "dimKelvin", "dimRgb"].includes(k),
    fade: ["dimFade", "lastFade", "sceneFade", "kelvinFade"].includes(k),
    scene: ["scene", "sceneFade"].includes(k),
    kelvin: ["kelvin", "kelvinFade", "dimKelvin"].includes(k),
    rgb: ["rgb", "dimRgb"].includes(k),
    steps: ["dimUp", "dimDown"].includes(k),
  };
  return { ...u, any: Object.values(u).some(Boolean) };
});

const fadeOptions = computed(() => {
  const set = new Set<number>(FADE_TIMES);
  if (Number.isFinite(Number(p.fade))) set.add(Number(p.fade));
  return [...set].sort((a, b) => a - b);
});

function rgbObj(hex: string) {
  const c = hexToRgb(/^#[0-9a-f]{6}$/i.test(hex) ? hex : "#ffffff");
  const r3 = (x: number) => Math.round(x * 1000) / 1000;
  return { r: r3(c.r), g: r3(c.g), b: r3(c.b) };
}

function build(): Features | null {
  switch (kind.value) {
    case "on":
      return { switchable: true };
    case "off":
      return { switchable: false };
    case "last":
      return { gotoLastActive: true };
    case "lastFade":
      return { gotoLastActiveWithFade: { fadeTime: fadeVal.value } };
    case "dim":
      return { dimmable: level.value };
    case "dimFade":
      return { dimmableWithFade: { dimValue: level.value, fadeTime: fadeVal.value } };
    case "dimUp":
      return { dimUp: Math.round(clamp(p.steps, 1, 5, 1)) };
    case "dimDown":
      return { dimDown: Math.round(clamp(p.steps, 1, 5, 1)) };
    case "scene":
      return { scene: Math.round(clamp(p.scene, 0, 15, 0)) };
    case "sceneFade":
      return { sceneWithFade: { scene: Math.round(clamp(p.scene, 0, 15, 0)), fadeTime: fadeVal.value } };
    case "kelvin":
      return { colorKelvin: Math.round(kelvinVal.value) };
    case "kelvinFade":
      return { colorKelvinWithFade: { color: Math.round(kelvinVal.value), fadeTime: fadeVal.value } };
    case "dimKelvin":
      return { dimmableKelvin: { dimmable: level.value, kelvin: Math.round(kelvinVal.value) } };
    case "rgb":
      return { colorRGB: rgbObj(p.rgb) };
    case "dimRgb":
      return { dimmableRGB: { ...rgbObj(p.rgb), dimmable: level.value } };
    case "raw":
      try {
        const o = JSON.parse(p.raw);
        return o && typeof o === "object" && !Array.isArray(o) ? o : null;
      } catch {
        return null;
      }
  }
  return null;
}

const built = computed(() => build());
const rawError = computed(() => kind.value === "raw" && built.value === null);
const support = computed(() => actionSupport(props.targets || [], built.value));

const isNum = (v: any) => typeof v === "number" && Number.isFinite(v);

/** Map an incoming ControlData object onto kind + parameters. */
function parse(v: Features) {
  const keys = Object.keys(v || {});
  const set = (k: Kind) => (kind.value = k);
  if (keys.length === 1) {
    const key = keys[0];
    const val = v[key];
    switch (key) {
      case "switchable":
        if (typeof val === "boolean") return set(val ? "on" : "off");
        break;
      case "gotoLastActive":
        return set("last");
      case "gotoLastActiveWithFade":
        if (isNum(val?.fadeTime)) {
          p.fade = val.fadeTime;
          return set("lastFade");
        }
        break;
      case "dimmable":
        if (isNum(val)) {
          p.level = val;
          return set("dim");
        }
        break;
      case "dimmableWithFade":
        if (isNum(val?.dimValue)) {
          p.level = val.dimValue;
          p.fade = isNum(val.fadeTime) ? val.fadeTime : 0;
          return set("dimFade");
        }
        break;
      case "dimUp":
      case "dimDown":
        if (isNum(val)) {
          p.steps = val;
          return set(key);
        }
        break;
      case "scene":
        if (isNum(val)) {
          p.scene = val;
          return set("scene");
        }
        break;
      case "sceneWithFade":
        if (isNum(val?.scene)) {
          p.scene = val.scene;
          p.fade = isNum(val.fadeTime) ? val.fadeTime : 0;
          return set("sceneFade");
        }
        break;
      case "colorKelvin":
        if (isNum(val)) {
          p.kelvin = val;
          return set("kelvin");
        }
        break;
      case "colorKelvinWithFade":
        if (isNum(val?.color)) {
          p.kelvin = val.color;
          p.fade = isNum(val.fadeTime) ? val.fadeTime : 0;
          return set("kelvinFade");
        }
        break;
      case "dimmableKelvin":
        if (isNum(val?.dimmable) && isNum(val?.kelvin)) {
          p.level = val.dimmable;
          p.kelvin = val.kelvin;
          return set("dimKelvin");
        }
        break;
      case "colorRGB":
        if (isNum(val?.r) && isNum(val?.g) && isNum(val?.b)) {
          p.rgb = rgbToHex(val.r, val.g, val.b);
          return set("rgb");
        }
        break;
      case "dimmableRGB":
        if (isNum(val?.r) && isNum(val?.g) && isNum(val?.b) && isNum(val?.dimmable)) {
          p.rgb = rgbToHex(val.r, val.g, val.b);
          p.level = val.dimmable;
          return set("dimRgb");
        }
        break;
    }
  }
  p.raw = JSON.stringify(v || {}, null, 2);
  set("raw");
}

function setKind(k: Kind) {
  if (k === "raw") p.raw = JSON.stringify(built.value ?? props.modelValue ?? {}, null, 2);
  kind.value = k;
}

watch(
  () => props.modelValue,
  (v) => {
    if (JSON.stringify(v ?? {}) === JSON.stringify(build())) return;
    parse(v ?? {});
  },
  { immediate: true, deep: true },
);

watch(
  [kind, p],
  () => {
    const f = build();
    if (f === null) return;
    if (JSON.stringify(f) === JSON.stringify(props.modelValue ?? {})) return;
    emit("update:modelValue", f);
  },
  { deep: true },
);

const levelTrack = computed(() => {
  const end = uses.value.kelvin ? kelvinToRgb(kelvinVal.value) : uses.value.rgb ? p.rgb : "#ffd54f";
  return `linear-gradient(90deg, #444, ${end})`;
});
const ctTrack = `linear-gradient(90deg, ${kelvinToRgb(2000)}, ${kelvinToRgb(4500)}, ${kelvinToRgb(7000)})`;

async function tryIt() {
  const f = built.value;
  if (!f || !props.targets?.length) return;
  trying.value = true;
  await tryAction(props.targets, f, t("tried"));
  trying.value = false;
}
</script>

<style scoped>
.ae { display: flex; flex-direction: column; gap: 8px; }
.ae-row { display: flex; flex-wrap: wrap; gap: 12px 16px; align-items: flex-start; }
.ae-kind { flex: 0 1 230px; min-width: 180px; }
.ae-params { flex: 1 1 300px; display: flex; flex-wrap: wrap; gap: 12px 16px; min-width: 0; }
.ae-level, .ae-kelvin { flex: 1 1 240px; }
.ae-rgb { flex: 1 1 240px; }
.ae-small { flex: 0 1 140px; min-width: 120px; }
.ae-raw { flex: 1 1 100%; }
.num { width: 76px !important; flex-shrink: 0; }
.num.wide { width: 90px !important; }
.presets { gap: 6px; margin-top: 2px; }
.presets .chip { border: 0; cursor: pointer; }
.rgb-preset { width: 24px; height: 24px; cursor: pointer; padding: 0; }
.rgb-preset.sel { outline: 2px solid var(--primary); outline-offset: 1px; }
.ae-noparams { display: flex; align-items: center; gap: 6px; padding-top: 24px; }
.ae-foot { gap: 6px; }
textarea.invalid { border-bottom-color: var(--error); }
.err-text { color: var(--error); }
@media (max-width: 700px) {
  .ae-kind { flex: 1 1 100%; }
  .ae-noparams { padding-top: 0; }
}
</style>
