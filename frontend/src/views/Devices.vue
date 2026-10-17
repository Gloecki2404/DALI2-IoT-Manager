<template>
  <div class="page">
    <div class="page-head">
      <h1>{{ t("title") }}</h1>
      <div class="btn-group">
        <button :class="{ active: view === 'tiles' }" @click="view = 'tiles'"><Icon :path="mdiViewGrid" :size="18" /></button>
        <button :class="{ active: view === 'table' }" @click="view = 'table'"><Icon :path="mdiViewList" :size="18" /></button>
      </div>
    </div>

    <div class="card toolbar">
      <div class="row wrap">
        <div class="search grow">
          <Icon :path="mdiMagnify" :size="18" class="search-icon" />
          <input v-model="q" type="search" :placeholder="t('search')" />
        </div>
        <select v-if="lines.length > 1" v-model="lineFilter" class="narrow">
          <option :value="null">{{ t("allLines") }}</option>
          <option v-for="l in lines" :key="l" :value="l">{{ t("line") }} {{ l }}</option>
        </select>
        <select v-model="groupFilter" class="narrow">
          <option :value="null">{{ t("allGroups") }}</option>
          <option v-for="g in usedGroups" :key="g" :value="g">{{ t("group") }} {{ g }}</option>
        </select>
      </div>
      <div class="row wrap mt">
        <button v-for="f in filters" :key="f.id" class="chip clickable" :class="{ primary: statusFilter === f.id }" @click="statusFilter = f.id">
          {{ f.label }} <b>{{ f.count }}</b>
        </button>
      </div>
    </div>

    <div v-if="!state.loaded" class="empty"><span class="spinner"></span></div>
    <Empty v-else-if="!list.length" :icon="mdiLightbulbQuestionOutline" :text="Object.keys(state.devices).length ? t('noMatch') : t('noDevices')">
      <RouterLink v-if="!Object.keys(state.devices).length" to="/bus" class="btn">{{ t("toScan") }}</RouterLink>
    </Empty>

    <div v-else-if="view === 'tiles'" class="grid tiles mt">
      <div v-for="d in list" :key="d.id" class="card tile" :class="{ on: isOn(d.features), bad: problem(d) }" @click="openId = d.id">
        <div class="row">
          <button class="bulb" :style="bulbStyle(d)" :disabled="!d.available" @click.stop="toggle(d)">
            <Icon :path="isOn(d.features) ? mdiLightbulbOn : mdiLightbulbOutline" :size="24" />
          </button>
          <div class="grow ellipsis">
            <div class="title ellipsis">{{ d.name }}</div>
            <div class="muted small">A{{ d.address }}<span v-if="lines.length > 1"> · L{{ d.line }}</span> · {{ typeLabel(d) }}</div>
          </div>
          <Toggle :model-value="isOn(d.features)" :disabled="!d.available" @change="toggle(d)" />
        </div>
        <div v-if="'dimmable' in d.features" class="row mt" @click.stop>
          <input type="range" min="0" max="100" :value="level(d.features)" :disabled="!d.available" @change="dim(d, +($event.target as HTMLInputElement).value)" />
          <span class="mono small pct">{{ Math.round(level(d.features)) }}%</span>
        </div>
        <div class="row wrap tile-foot">
          <span v-if="!d.available" class="chip err"><Icon :path="mdiLanDisconnect" :size="14" />{{ t("unavailable") }}</span>
          <span v-if="d.status?.lampFailure" class="chip err"><Icon :path="mdiLightbulbAlert" :size="14" />{{ t("lampFailure") }}</span>
          <span v-if="d.status?.controlGearFailure" class="chip err">{{ t("gearFailure") }}</span>
          <span v-if="hasColorTemp(d.features) && kelvinOf(d)" class="chip"><span class="swatch" :style="{ background: kelvinToRgb(kelvinOf(d)!) }"></span>{{ kelvinOf(d) }} K</span>
          <span v-for="g in d.groups" :key="g" class="chip primary">G{{ g }}</span>
        </div>
      </div>
    </div>

    <div v-else class="card mt table-wrap">
      <table class="table">
        <thead>
          <tr>
            <th></th><th>{{ t("name") }}</th><th>{{ t("line") }}</th><th>{{ t("address") }}</th><th>{{ t("type") }}</th>
            <th>{{ t("groups") }}</th><th>{{ t("brightness") }}</th><th>{{ t("status") }}</th><th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="d in list" :key="d.id" class="clickable" @click="openId = d.id">
            <td><span class="dot" :class="problem(d) ? 'err' : isOn(d.features) ? 'ok' : ''"></span></td>
            <td><b>{{ d.name }}</b></td>
            <td>{{ d.line }}</td>
            <td class="mono">A{{ d.address }}</td>
            <td class="small">{{ d.daliTypes.map((x) => "DT" + x).join(", ") }}</td>
            <td class="small">{{ d.groups.join(", ") || "–" }}</td>
            <td>{{ isOn(d.features) ? Math.round(level(d.features)) + " %" : t("off") }}</td>
            <td>
              <span v-if="!d.available" class="chip err">{{ t("unavailable") }}</span>
              <span v-else-if="d.status?.lampFailure" class="chip err">{{ t("lampFailure") }}</span>
              <span v-else-if="d.status?.controlGearFailure" class="chip err">{{ t("gearFailure") }}</span>
              <span v-else class="chip ok">OK</span>
            </td>
            <td @click.stop><Toggle :model-value="isOn(d.features)" :disabled="!d.available" @change="toggle(d)" /></td>
          </tr>
        </tbody>
      </table>
    </div>

    <DeviceDetail :device-id="openId" @close="openId = null" />
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useRoute } from "vue-router";
import {
  mdiLanDisconnect,
  mdiLightbulbAlert,
  mdiLightbulbOn,
  mdiLightbulbOutline,
  mdiLightbulbQuestionOutline,
  mdiMagnify,
  mdiViewGrid,
  mdiViewList,
} from "@mdi/js";
import Icon from "../components/Icon.vue";
import Toggle from "../components/Toggle.vue";
import Empty from "../components/Empty.vue";
import DeviceDetail from "../components/DeviceDetail.vue";
import { gw } from "../lib/api";
import { run, sentKelvin, state, type Device } from "../lib/store";
import { lang, useT } from "../lib/i18n";
import { DALI_TYPES, hasColorTemp, isOn, kelvin, kelvinToRgb, level } from "../lib/dali";

const t = useT({
  de: {
    title: "Geräte",
    allLines: "Alle Linien",
    allGroups: "Alle Gruppen",
    fAll: "Alle",
    fOn: "Ein",
    fOff: "Aus",
    fProblem: "Probleme",
    noDevices: "Noch keine DALI-Geräte gefunden.",
    noMatch: "Keine Geräte passen zum Filter.",
    toScan: "DALI-Scan starten",
    lampFailure: "Lampenfehler",
    gearFailure: "Gerätefehler",
  },
  en: {
    title: "Devices",
    allLines: "All lines",
    allGroups: "All groups",
    fAll: "All",
    fOn: "On",
    fOff: "Off",
    fProblem: "Problems",
    noDevices: "No DALI devices found yet.",
    noMatch: "No devices match the filter.",
    toScan: "Start DALI scan",
    lampFailure: "Lamp failure",
    gearFailure: "Gear failure",
  },
});

const route = useRoute();
const q = ref("");
function stored(key: string, def: string): string {
  try {
    return localStorage.getItem(key) || def;
  } catch {
    return def;
  }
}
const view = ref<"tiles" | "table">(stored("lunatone.devview", "tiles") as any);
watch(view, (v) => {
  try {
    localStorage.setItem("lunatone.devview", v);
  } catch {
    /* ignore */
  }
});
const statusFilter = ref<string>((route.query.filter as string) || "all");
const lineFilter = ref<number | null>(null);
const groupFilter = ref<number | null>(null);
const openId = ref<number | null>(route.query.id ? Number(route.query.id) : null);

const all = computed(() => Object.values(state.devices).sort((a, b) => a.line - b.line || a.address - b.address));
const lines = computed(() => [...new Set(all.value.map((d) => d.line))].sort());
const usedGroups = computed(() => [...new Set(all.value.flatMap((d) => d.groups))].sort((a, b) => a - b));
const problem = (d: Device) => !d.available || d.status?.lampFailure || d.status?.controlGearFailure;

const filters = computed(() => [
  { id: "all", label: t("fAll"), count: all.value.length },
  { id: "on", label: t("fOn"), count: all.value.filter((d) => isOn(d.features)).length },
  { id: "off", label: t("fOff"), count: all.value.filter((d) => !isOn(d.features)).length },
  { id: "problem", label: t("fProblem"), count: all.value.filter(problem).length },
]);

const list = computed(() =>
  all.value.filter((d) => {
    if (q.value && !`${d.name} A${d.address} ${d.id}`.toLowerCase().includes(q.value.toLowerCase())) return false;
    if (lineFilter.value !== null && d.line !== lineFilter.value) return false;
    if (groupFilter.value !== null && !d.groups.includes(groupFilter.value)) return false;
    if (statusFilter.value === "on" && !isOn(d.features)) return false;
    if (statusFilter.value === "off" && isOn(d.features)) return false;
    if (statusFilter.value === "problem" && !problem(d)) return false;
    return true;
  }),
);

function typeLabel(d: Device) {
  const main = d.daliTypes.includes(8) ? 8 : d.daliTypes[0];
  return main !== undefined ? DALI_TYPES[main]?.[lang.value] ?? `DT${main}` : "DALI";
}
function kelvinOf(d: Device): number | null {
  const reported = kelvin(d.features);
  const s = sentKelvin.get(`device:${d.id}`);
  return s && s.reported === reported ? s.k : reported;
}
function bulbStyle(d: Device) {
  if (!isOn(d.features)) return {};
  const k = hasColorTemp(d.features) ? kelvinOf(d) : null;
  const col = k ? kelvinToRgb(k) : "#ffc107";
  return { color: col, background: `color-mix(in srgb, ${col} 22%, transparent)` };
}
async function toggle(d: Device) {
  const on = isOn(d.features);
  await run(() => gw.control("device", d.id, on ? { switchable: false } : "gotoLastActive" in d.features ? { gotoLastActive: true } : { switchable: true }));
}
async function dim(d: Device, v: number) {
  await run(() => gw.control("device", d.id, { dimmable: v }));
}
</script>

<style scoped>
.toolbar { padding: 12px 14px; }
.search { position: relative; min-width: 200px; }
.search input { padding-left: 34px; }
.search-icon { position: absolute; left: 10px; top: 10px; color: var(--text2); }
.narrow { max-width: 170px; }
.tile { padding: 14px; cursor: pointer; transition: box-shadow .15s, transform .12s; }
.tile:hover { transform: translateY(-1px); box-shadow: 0 4px 16px rgba(0, 0, 0, .08); }
.tile.bad { border-color: color-mix(in srgb, var(--error) 50%, transparent); }
.tile .title { font-weight: 500; font-size: 14.5px; }
.bulb { width: 44px; height: 44px; border-radius: 50%; border: 0; background: var(--bg2); color: var(--text2); display: flex; align-items: center; justify-content: center; cursor: pointer; flex-shrink: 0; transition: all .2s; }
.bulb:disabled { opacity: .5; cursor: not-allowed; }
.pct { width: 38px; text-align: right; }
.tile-foot { margin-top: 8px; gap: 6px; min-height: 24px; }
.ellipsis { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; min-width: 0; }
</style>
