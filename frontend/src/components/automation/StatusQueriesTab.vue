<template>
  <div>
    <p class="tab-intro">{{ t("sqIntro") }}</p>

    <div v-if="auto.errors.queries" class="banner err mb">
      <Icon :path="mdiAlertCircleOutline" />
      <div>{{ t("loadError") }}: {{ auto.errors.queries }}</div>
    </div>

    <div class="grid cols-2">
      <section v-for="l in lineKeys" :key="l" class="card sq">
        <header class="card-head">
          <span class="icon-bubble" :class="drafts[l] ? 'ok' : 'off'"><Icon :path="mdiRadar" :size="18" /></span>
          <div class="grow">
            <h3>{{ t("line") }} {{ l }}</h3>
            <div class="muted small">{{ t("sqDevices", { n: devicesOn(l) }) }}</div>
          </div>
          <span v-if="drafts[l]" class="chip ok">{{ t("sqActive") }}</span>
          <span v-else class="chip">{{ t("sqInactive") }}</span>
        </header>

        <div v-if="!drafts[l]" class="card-body">
          <p class="muted small sq-off">{{ t("sqOffText") }}</p>
          <button class="btn" :disabled="!!busy[l]" @click="enable(l)">
            <span v-if="busy[l]" class="spinner"></span><Icon v-else :path="mdiPlay" :size="18" />{{ t("sqEnable") }}
          </button>
        </div>

        <div v-else class="card-body">
          <div class="field">
            <span class="row between">
              <span>{{ t("sqDelay") }}</span>
              <span class="mono">{{ fmtSec(drafts[l].delayBetweenQueries) }}</span>
            </span>
            <div class="row">
              <input
                type="range"
                :min="logMin"
                :max="logMax"
                step="0.01"
                :value="Math.log10(Math.max(auto.bounds.min, Number(drafts[l].delayBetweenQueries) || auto.bounds.min))"
                @input="setFromSlider(l, +($event.target as HTMLInputElement).value)"
              />
              <input v-model.number="drafts[l].delayBetweenQueries" type="number" :min="auto.bounds.min" :max="auto.bounds.max" step="0.5" class="num" />
              <span class="muted">s</span>
            </div>
            <div class="row wrap presets">
              <button
                v-for="p in PRESETS"
                :key="p"
                type="button"
                class="chip clickable"
                :class="{ primary: Number(drafts[l].delayBetweenQueries) === p }"
                @click="drafts[l].delayBetweenQueries = p"
              >
                {{ fmtSec(p) }}
              </button>
            </div>
            <span class="hint">{{ t("sqDelayHint", { min: fmtSec(auto.bounds.min), max: fmtSec(auto.bounds.max) }) }}</span>
          </div>

          <div class="sq-toggles">
            <label class="row sq-toggle">
              <Toggle v-model="drafts[l].queryStatus" />
              <div class="grow">
                <div>{{ t("sqStatus") }} <span class="faint mono small">QUERY STATUS</span></div>
                <div class="small faint">{{ t("sqStatusHint") }}</div>
              </div>
            </label>
            <label class="row sq-toggle">
              <Toggle v-model="drafts[l].queryActualLevel" />
              <div class="grow">
                <div>{{ t("sqLevel") }} <span class="faint mono small">QUERY ACTUAL LEVEL</span></div>
                <div class="small faint">{{ t("sqLevelHint") }}</div>
              </div>
            </label>
          </div>

          <div v-if="!drafts[l].queryStatus && !drafts[l].queryActualLevel" class="banner warn small mt">
            <Icon :path="mdiAlertOutline" :size="18" />
            <div>{{ t("sqNoneSelected") }}</div>
          </div>

          <div class="load mt">
            <div class="row between load-head">
              <span class="small muted">{{ t("sqLoad") }}</span>
              <span class="chip" :class="est(l).cls">{{ est(l).label }}</span>
            </div>
            <div class="progress"><div :style="{ width: `${Math.min(100, est(l).busy * 100)}%`, background: est(l).color }"></div></div>
            <div class="load-stats">
              <div><b>{{ fmtNum(est(l).qps, 2) }}</b><span>{{ t("sqQps") }}</span></div>
              <div><b>{{ fmtNum(est(l).fps, 1) }}</b><span>{{ t("sqFps") }}</span></div>
              <div><b>{{ fmtNum(est(l).busy * 100, 1) }} %</b><span>{{ t("sqBusy") }}</span></div>
              <div><b>{{ est(l).refresh ? fmtSec(est(l).refresh) : "–" }}</b><span>{{ t("sqRefresh") }}</span></div>
            </div>
            <div class="small faint">{{ t("sqModel") }}</div>
          </div>

          <div v-if="validation(l)" class="small err-text mt">{{ validation(l) }}</div>
        </div>

        <footer v-if="drafts[l]" class="card-foot">
          <button class="btn flat danger" :disabled="!!busy[l]" @click="disable(l)">
            <Icon :path="mdiStopCircleOutline" :size="17" />{{ t("sqDisable") }}
          </button>
          <span class="grow"></span>
          <button v-if="dirty(l)" class="btn flat" :disabled="!!busy[l]" @click="reset(l)">{{ t("reset") }}</button>
          <button class="btn" :disabled="!!busy[l] || !dirty(l) || !!validation(l)" @click="save(l)">
            <span v-if="busy[l]" class="spinner"></span>{{ t("save") }}
          </button>
        </footer>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, watch } from "vue";
import { mdiAlertCircleOutline, mdiAlertOutline, mdiPlay, mdiRadar, mdiStopCircleOutline } from "@mdi/js";
import Icon from "../Icon.vue";
import Toggle from "../Toggle.vue";
import { gw } from "../../lib/api";
import { confirmDialog, run, state } from "../../lib/store";
import { useAT } from "./i18n";
import { auto, load } from "./data";
import { clone, fmtNum, fmtSec, lineCount, type LineConfig } from "./util";

const t = useAT();
const PRESETS = [0.5, 1, 2, 5, 10, 30, 60, 300];

// Timing model, measured with the bus monitor on a DALI-2 IoT gateway: for every device the enabled
// queries are sent back to back (≈ 55 ms per query incl. the answer), then the gateway waits
// "delayBetweenQueries" before it continues with the next device.
const SLOT_S = 0.055; // spacing of two queries to the same device
const BUSY_S = 0.025; // bus occupied per query: forward frame (16 bit ≈ 15.8 ms) + backward frame (8 bit ≈ 9.2 ms)

const drafts = reactive<Record<string, LineConfig>>({});
const busy = reactive<Record<string, boolean>>({});

const lineKeys = computed(() => {
  const set = new Set<string>(Array.from({ length: lineCount() }, (_, i) => String(i)));
  Object.keys(auto.queries).forEach((k) => set.add(k));
  return [...set].sort((a, b) => Number(a) - Number(b));
});

function sync(only?: string) {
  for (const l of lineKeys.value) {
    if (only !== undefined && l !== only) continue;
    const cfg = auto.queries[l];
    if (cfg) drafts[l] = clone(cfg);
    else delete drafts[l];
  }
}
onMounted(() => sync());
watch(
  () => auto.queries,
  () => {
    // keep unsaved edits, refresh untouched lines
    for (const l of lineKeys.value) if (!dirty(l)) sync(l);
  },
);

function dirty(l: string) {
  const a = auto.queries[l];
  const b = drafts[l];
  if (!a || !b) return false;
  return (
    Number(a.delayBetweenQueries) !== Number(b.delayBetweenQueries) ||
    !!a.queryStatus !== !!b.queryStatus ||
    !!a.queryActualLevel !== !!b.queryActualLevel
  );
}

function devicesOn(l: string) {
  const n = Number(l);
  return Object.values(state.devices).filter((d) => Number(d.line ?? 0) === n).length;
}

const logMin = computed(() => Math.log10(auto.bounds.min));
const logMax = computed(() => Math.log10(auto.bounds.max));

function setFromSlider(l: string, v: number) {
  const raw = Math.pow(10, v);
  const nice = raw < 10 ? Math.round(raw * 2) / 2 : raw < 60 ? Math.round(raw) : raw < 600 ? Math.round(raw / 10) * 10 : Math.round(raw / 60) * 60;
  drafts[l].delayBetweenQueries = Math.min(auto.bounds.max, Math.max(auto.bounds.min, nice));
}

function validation(l: string): string {
  const d = drafts[l];
  if (!d) return "";
  const v = Number(d.delayBetweenQueries);
  if (!Number.isFinite(v) || v < auto.bounds.min || v > auto.bounds.max) return t("sqDelayRange", { min: auto.bounds.min, max: auto.bounds.max });
  return "";
}

function est(l: string) {
  const d = drafts[l];
  const n = (d?.queryStatus ? 1 : 0) + (d?.queryActualLevel ? 1 : 0);
  const devs = devicesOn(l);
  const delay = Math.max(auto.bounds.min, Number(d?.delayBetweenQueries) || auto.bounds.min);
  const perDevice = delay + n * SLOT_S;
  const qps = n && devs ? n / perDevice : 0;
  const fps = qps * 2;
  const busyFrac = qps * BUSY_S;
  const refresh = n && devs ? devs * perDevice : 0;
  const level = busyFrac < 0.1 ? "ok" : busyFrac < 0.25 ? "warn" : "err";
  return {
    qps,
    fps,
    busy: busyFrac,
    refresh,
    cls: level,
    color: level === "ok" ? "var(--success)" : level === "warn" ? "var(--warning)" : "var(--error)",
    label: !devs ? t("sqNoDevices") : level === "ok" ? t("sqLoadLow") : level === "warn" ? t("sqLoadMid") : t("sqLoadHigh"),
  };
}

async function enable(l: string) {
  busy[l] = true;
  const body: LineConfig = { delayBetweenQueries: Math.max(auto.bounds.min, 1), queryStatus: true, queryActualLevel: true };
  await run(() => gw.post(`/automations/statusQueries/${l}`, body), t("sqEnabledToast", { l }));
  await load("queries");
  sync(l);
  busy[l] = false;
}

async function save(l: string) {
  const d = drafts[l];
  if (!d || validation(l)) return;
  busy[l] = true;
  const body: LineConfig = {
    delayBetweenQueries: Number(d.delayBetweenQueries),
    queryStatus: !!d.queryStatus,
    queryActualLevel: !!d.queryActualLevel,
  };
  const res = await run(() => gw.put(`/automations/statusQueries/${l}`, body), t("sqSavedToast", { l }));
  await load("queries");
  if (res !== undefined) sync(l);
  busy[l] = false;
}

function reset(l: string) {
  sync(l);
}

async function disable(l: string) {
  const ok = await confirmDialog({
    title: t("sqDisableTitle", { l }),
    message: t("sqDisableMsg"),
    danger: true,
    confirmText: t("sqDisable"),
  });
  if (!ok) return;
  busy[l] = true;
  await run(() => gw.del(`/automations/statusQueries/${l}`), t("sqDisabledToast", { l }));
  await load("queries");
  sync(l);
  busy[l] = false;
}
</script>

<style scoped>
.sq { display: flex; flex-direction: column; }
.sq .card-body { flex: 1; display: flex; flex-direction: column; gap: 14px; }
.sq-off { margin: 0; }
.num { width: 90px !important; flex-shrink: 0; }
.presets { gap: 6px; margin-top: 2px; }
.presets .chip { border: 0; cursor: pointer; }
.sq-toggles { display: flex; flex-direction: column; gap: 10px; }
.sq-toggle { gap: 12px; align-items: flex-start; cursor: pointer; }
.load { display: flex; flex-direction: column; gap: 8px; background: var(--bg2); border-radius: 12px; padding: 12px; }
.load .progress { background: var(--card); }
.load-stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; }
.load-stats > div { display: flex; flex-direction: column; min-width: 0; }
.load-stats b { font-size: 16px; font-weight: 500; }
.load-stats span { font-size: 11.5px; color: var(--text2); }
.err-text { color: var(--error); }
@media (max-width: 700px) {
  .load-stats { grid-template-columns: repeat(2, 1fr); }
}
</style>
