<template>
  <Modal :open="!!device" :title="device?.name || ''" :subtitle="subtitle" :icon="mdiLightbulb" :icon-class="iconClass" wide @close="$emit('close')">
    <template v-if="device">
      <Tabs v-model="tab" :tabs="tabs" />

      <!-- ------------------------------------------------------ control -->
      <div v-if="tab === 'control'" class="grid cols-2">
        <Card :title="t('control')">
          <LightControl :features="device.features" target="device" :target-id="device.id" />
        </Card>
        <Card :title="t('statusFlags')">
          <div class="flags">
            <div v-for="f in flags" :key="f.key" class="flag" :class="{ active: f.active, bad: f.bad && f.active }">
              <Icon :path="f.active ? (f.bad ? mdiAlertCircle : mdiCheckCircle) : mdiCircleOutline" :size="18" />
              <div>
                <div class="title">{{ f.label }}</div>
                <div class="faint small">{{ f.help }}</div>
              </div>
            </div>
          </div>
          <div class="faint small mt">Raw status: <span class="mono">{{ device.status?.raw }} (0b{{ (device.status?.raw ?? 0).toString(2).padStart(8, "0") }})</span></div>
        </Card>
      </div>

      <!-- ------------------------------------------------------ settings -->
      <div v-else-if="tab === 'settings'" class="col gap-lg">
        <Card :title="t('general')">
          <div class="form-grid">
            <label class="field"><span>{{ t("name") }}</span><input v-model="form.name" type="text" /></label>
            <label class="field">
              <span>{{ t("fadeTime") }}</span>
              <select v-model.number="form.fadeTime">
                <option v-for="(s, i) in FADE_TIMES" :key="i" :value="s">{{ i === 0 ? t("noFade") : `${s} s` }}</option>
              </select>
            </label>
            <label class="field">
              <span>{{ t("fadeRate") }}</span>
              <select v-model.number="form.fadeRate">
                <option v-for="r in FADE_RATES" :key="r" :value="r">{{ r }} {{ t("stepsPerSec") }}</option>
              </select>
            </label>
          </div>
          <div class="section-title">{{ t("groups") }}</div>
          <div class="group-grid">
            <label v-for="g in 16" :key="g" class="group-chip" :class="{ on: form.groups.includes(g - 1) }">
              <input v-model="form.groups" type="checkbox" :value="g - 1" />{{ g - 1 }}
            </label>
          </div>
          <template #footer>
            <button class="btn" :disabled="saving" @click="saveGeneral">{{ t("save") }}</button>
          </template>
        </Card>

        <Card :title="t('daliParams')" :subtitle="t('daliParamsSub')">
          <template #actions>
            <button class="btn flat sm" :disabled="reading" @click="readParams">
              <span v-if="reading" class="spinner"></span><Icon v-else :path="mdiRefresh" :size="16" />{{ t("readDevice") }}
            </button>
          </template>
          <div v-if="!params" class="muted small">{{ t("paramsHint") }}</div>
          <div v-else class="form-grid">
            <div v-for="p in paramDefs" :key="p.key" class="field">
              <span>{{ p.label }}</span>
              <div class="row">
                <input v-if="p.editable && state.expert" v-model.number="edit[p.key]" type="number" min="0" :max="p.max ?? 254" />
                <div v-else class="mono param">{{ fmtParam(p.key, params[p.key]) }}</div>
                <button v-if="p.editable && state.expert" class="btn icon sm" :title="t('save')" @click="writeParam(p)"><Icon :path="mdiContentSave" :size="16" /></button>
              </div>
              <span v-if="p.editable && state.expert" class="hint">{{ fmtParam(p.key, edit[p.key]) }}</span>
            </div>
          </div>
          <div v-if="params && !state.expert" class="faint small mt">{{ t("expertToEdit") }}</div>
        </Card>

        <Card :title="t('maintenance')">
          <div class="row wrap">
            <button class="btn outline" @click="identify"><Icon :path="mdiLightbulbAlert" :size="18" />{{ t("identify") }}</button>
            <button class="btn danger outline" @click="remove"><Icon :path="mdiDelete" :size="18" />{{ t("removeDevice") }}</button>
          </div>
          <div class="faint small mt">{{ t("identifyHint") }}</div>
        </Card>
      </div>

      <!-- -------------------------------------------------------- scenes -->
      <div v-else-if="tab === 'scenes'">
        <div class="row between mb wrap">
          <div class="muted small">{{ t("scenesHint") }}</div>
          <button class="btn flat sm" :disabled="scenesLoading" @click="loadScenes(true)">
            <span v-if="scenesLoading" class="spinner"></span><Icon v-else :path="mdiRefresh" :size="16" />{{ t("readFromDevice") }}
          </button>
        </div>
        <div class="table-wrap card">
          <table class="table">
            <thead>
              <tr><th>{{ t("scene") }}</th><th>{{ t("brightness") }}</th><th v-if="hasColorTemp(device.features)">{{ t("colorTemp") }}</th><th>{{ t("color") }}</th><th class="right">{{ t("actions") }}</th></tr>
            </thead>
            <tbody>
              <tr v-for="n in 16" :key="n">
                <td><b>{{ n - 1 }}</b></td>
                <td>
                  <span v-if="scene(n - 1)?.dimmable != null">{{ Math.round(scene(n - 1).dimmable) }} %</span>
                  <span v-else class="faint">{{ t("notSet") }}</span>
                </td>
                <td v-if="hasColorTemp(device.features)">
                  <span v-if="scene(n - 1)?.colorKelvin" class="row"><span class="swatch" :style="{ background: kelvinToRgb(scene(n - 1).colorKelvin) }"></span>{{ scene(n - 1).colorKelvin }} K</span>
                  <span v-else class="faint">–</span>
                </td>
                <td>
                  <span v-if="scene(n - 1)?.colorRGB?.r != null" class="swatch" :style="{ background: rgbToHex(scene(n - 1).colorRGB.r, scene(n - 1).colorRGB.g, scene(n - 1).colorRGB.b) }"></span>
                  <span v-else class="faint">–</span>
                </td>
                <td class="right nowrap">
                  <button class="btn flat sm" @click="ctl({ scene: n - 1 })"><Icon :path="mdiPlay" :size="16" />{{ t("recall") }}</button>
                  <button class="btn flat sm" @click="saveScene(n - 1)"><Icon :path="mdiContentSave" :size="16" />{{ t("storeCurrent") }}</button>
                  <button v-if="state.expert && scene(n - 1)?.dimmable != null" class="btn icon sm" :title="t('removeScene')" @click="removeScene(n - 1)"><Icon :path="mdiDelete" :size="16" /></button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- ---------------------------------------------------------- info -->
      <div v-else-if="tab === 'info'" class="grid cols-2">
        <Card :title="t('identity')">
          <div class="kv">
            <span>{{ t("line") }}</span><span>{{ device.line }}</span>
            <span>{{ t("shortAddress") }}</span><span>{{ device.address }}</span>
            <span>{{ t("gatewayId") }}</span><span>{{ device.id }}</span>
            <span>{{ t("groups") }}</span><span>{{ device.groups?.length ? device.groups.join(", ") : t("none") }}</span>
            <span>{{ t("available") }}</span><span>{{ device.available ? t("yes") : t("no") }}</span>
          </div>
          <div class="section-title">{{ t("daliTypes") }}</div>
          <div class="row wrap">
            <span v-for="dt in device.daliTypes" :key="dt" class="chip primary">DT{{ dt }} · {{ DALI_TYPES[dt]?.[lang] || "?" }}</span>
          </div>
          <div class="section-title">{{ t("features") }}</div>
          <div class="row wrap">
            <span v-for="f in Object.keys(device.features)" :key="f" class="chip">{{ f }}</span>
          </div>
        </Card>
        <Card v-if="device.daliTypes.includes(51) || device.daliTypes.includes(52)" :title="t('measure')">
          <template #actions>
            <button class="btn flat sm" @click="loadExtras"><Icon :path="mdiRefresh" :size="16" />{{ t("readDevice") }}</button>
          </template>
          <div v-if="extras.error" class="banner warn">{{ extras.error }}</div>
          <div v-if="extras.energy" class="kv">
            <template v-for="(v, k) in extras.energy" :key="k"><span>{{ k }}</span><span class="mono">{{ v }}</span></template>
          </div>
          <div v-if="extras.diag" class="kv mt">
            <template v-for="(v, k) in extras.diag" :key="k"><span>{{ k }}</span><span class="mono">{{ v }}</span></template>
          </div>
        </Card>
        <Card :title="t('raw')">
          <pre class="mono raw">{{ JSON.stringify(device, null, 2) }}</pre>
        </Card>
      </div>
    </template>
  </Modal>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from "vue";
import {
  mdiAlertCircle,
  mdiCheckCircle,
  mdiCircleOutline,
  mdiContentSave,
  mdiDelete,
  mdiInformationOutline,
  mdiLightbulb,
  mdiLightbulbAlert,
  mdiPalette,
  mdiPlay,
  mdiRefresh,
  mdiTune,
  mdiTuneVariant,
} from "@mdi/js";
import Modal from "./Modal.vue";
import Tabs from "./Tabs.vue";
import Card from "./Card.vue";
import Icon from "./Icon.vue";
import LightControl from "./LightControl.vue";
import { gw } from "../lib/api";
import { confirmDialog, run, state, toast, type Device } from "../lib/store";
import { lang, useT } from "../lib/i18n";
import { DALI_TYPES, FADE_RATES, FADE_TIMES, hasColorTemp, kelvinToRgb, rgbToHex, status } from "../lib/dali";

const props = defineProps<{ deviceId: number | null }>();
const emit = defineEmits<{ (e: "close"): void }>();

const t = useT({
  de: {
    control: "Steuerung",
    settings: "Einstellungen",
    info: "Info",
    statusFlags: "Statusmeldungen",
    general: "Allgemein",
    noFade: "Keine (sofort)",
    stepsPerSec: "Schritte/s",
    daliParams: "DALI-Parameter",
    daliParamsSub: "Direkt aus dem Betriebsgerät gelesen",
    readDevice: "Vom Gerät lesen",
    paramsHint: "Klicke auf „Vom Gerät lesen“, um Min-/Max-Level, Einschaltverhalten usw. abzufragen.",
    expertToEdit: "Zum Ändern der Parameter den Expertenmodus aktivieren.",
    maintenance: "Wartung",
    identify: "Identifizieren (blinken)",
    identifyHint: "Identifizieren lässt die Leuchte für ca. 10 Sekunden blinken (DALI-2 IDENTIFY DEVICE).",
    removeDevice: "Aus Gateway entfernen",
    scenesHint: "Szenen werden im Betriebsgerät gespeichert und funktionieren auch ohne Gateway.",
    readFromDevice: "Neu vom Gerät lesen",
    notSet: "nicht gesetzt",
    recall: "Aufrufen",
    storeCurrent: "Aktuell speichern",
    removeScene: "Szene entfernen",
    identity: "Identität",
    shortAddress: "Kurzadresse",
    gatewayId: "Gateway-ID",
    daliTypes: "DALI-Gerätetypen",
    features: "Unterstützte Funktionen",
    measure: "Messwerte",
    raw: "Rohdaten",
    minLevel: "Min-Level",
    maxLevel: "Max-Level",
    physMin: "Physikalisches Minimum",
    powerOn: "Einschaltlevel (Netz ein)",
    sysFail: "Level bei Busausfall",
    version: "DALI-Version",
    lightSource: "Leuchtmitteltyp",
    opMode: "Betriebsmodus",
    lastLevel: "letzter Wert",
    noChange: "keine Änderung",
    lampFailure: "Lampenfehler",
    lampFailureHelp: "Leuchtmittel defekt oder nicht angeschlossen",
    gearFailure: "Betriebsgerätefehler",
    gearFailureHelp: "Das Betriebsgerät meldet einen Fehler",
    lampOn: "Lampe an",
    lampOnHelp: "Leuchtmittel ist eingeschaltet",
    limitError: "Grenzwertfehler",
    limitErrorHelp: "Gewünschter Wert lag außerhalb Min/Max",
    fadeRunning: "Fade läuft",
    fadeRunningHelp: "Gerade wird übergeblendet",
    resetState: "Reset-Zustand",
    resetStateHelp: "Gerät hat Werkseinstellungen",
    unaddressed: "Ohne Kurzadresse",
    unaddressedHelp: "Gerät hat keine Kurzadresse",
    powerCycle: "Netzunterbrechung",
    powerCycleHelp: "Seit letzter Abfrage war die Versorgung weg",
    confirmDelete: "Gerät „{name}“ aus dem Gateway entfernen? Das Betriebsgerät selbst bleibt unverändert und wird beim nächsten Scan wieder gefunden.",
    confirmRemoveScene: "Szene {n} aus dem Gerät löschen?",
    written: "Parameter geschrieben",
  },
  en: {
    control: "Control",
    settings: "Settings",
    info: "Info",
    statusFlags: "Status flags",
    general: "General",
    noFade: "None (instant)",
    stepsPerSec: "steps/s",
    daliParams: "DALI parameters",
    daliParamsSub: "Read directly from the control gear",
    readDevice: "Read from device",
    paramsHint: "Click “Read from device” to query min/max level, power-on behaviour etc.",
    expertToEdit: "Enable expert mode to change these parameters.",
    maintenance: "Maintenance",
    identify: "Identify (blink)",
    identifyHint: "Identify makes the light blink for about 10 seconds (DALI-2 IDENTIFY DEVICE).",
    removeDevice: "Remove from gateway",
    scenesHint: "Scenes are stored in the control gear and also work without the gateway.",
    readFromDevice: "Read from device",
    notSet: "not set",
    recall: "Recall",
    storeCurrent: "Store current",
    removeScene: "Remove scene",
    identity: "Identity",
    shortAddress: "Short address",
    gatewayId: "Gateway ID",
    daliTypes: "DALI device types",
    features: "Supported features",
    measure: "Measurements",
    raw: "Raw data",
    minLevel: "Min level",
    maxLevel: "Max level",
    physMin: "Physical minimum",
    powerOn: "Power-on level",
    sysFail: "System failure level",
    version: "DALI version",
    lightSource: "Light source type",
    opMode: "Operating mode",
    lastLevel: "last level",
    noChange: "no change",
    lampFailure: "Lamp failure",
    lampFailureHelp: "Light source broken or disconnected",
    gearFailure: "Control gear failure",
    gearFailureHelp: "The control gear reports a failure",
    lampOn: "Lamp on",
    lampOnHelp: "Light source is switched on",
    limitError: "Limit error",
    limitErrorHelp: "Requested level was outside min/max",
    fadeRunning: "Fade running",
    fadeRunningHelp: "A fade is in progress",
    resetState: "Reset state",
    resetStateHelp: "Device has factory settings",
    unaddressed: "No short address",
    unaddressedHelp: "Device has no short address",
    powerCycle: "Power cycle seen",
    powerCycleHelp: "Supply was interrupted since the last query",
    confirmDelete: "Remove “{name}” from the gateway? The control gear itself is not changed and will be found again by the next scan.",
    confirmRemoveScene: "Delete scene {n} from the device?",
    written: "Parameter written",
  },
});

const device = computed<Device | null>(() => (props.deviceId != null ? state.devices[props.deviceId] ?? null : null));
const tab = ref("control");
const tabs = computed(() => [
  { id: "control", label: t("control"), icon: mdiTune },
  { id: "settings", label: t("settings"), icon: mdiTuneVariant },
  { id: "scenes", label: t("scenes"), icon: mdiPalette },
  { id: "info", label: t("info"), icon: mdiInformationOutline },
]);
const subtitle = computed(() => (device.value ? `${t("line")} ${device.value.line} · ${t("address")} ${device.value.address}` : ""));
const iconClass = computed(() => {
  const d = device.value;
  if (!d) return "";
  if (!d.available || d.status?.lampFailure || d.status?.controlGearFailure) return "err";
  return "";
});

const flags = computed(() => {
  const s: any = device.value?.status || {};
  return [
    { key: "lampFailure", label: t("lampFailure"), help: t("lampFailureHelp"), active: !!s.lampFailure, bad: true },
    { key: "controlGearFailure", label: t("gearFailure"), help: t("gearFailureHelp"), active: !!s.controlGearFailure, bad: true },
    { key: "lampOn", label: t("lampOn"), help: t("lampOnHelp"), active: !!s.lampOn, bad: false },
    { key: "limitError", label: t("limitError"), help: t("limitErrorHelp"), active: !!s.limitError, bad: true },
    { key: "fadeRunning", label: t("fadeRunning"), help: t("fadeRunningHelp"), active: !!s.fadeRunning, bad: false },
    { key: "resetState", label: t("resetState"), help: t("resetStateHelp"), active: !!s.resetState, bad: false },
    { key: "isUnaddressed", label: t("unaddressed"), help: t("unaddressedHelp"), active: !!s.isUnaddressed, bad: true },
    { key: "powerCycleSeen", label: t("powerCycle"), help: t("powerCycleHelp"), active: !!s.powerCycleSeen, bad: false },
  ];
});

// ------------------------------------------------------------- settings
const form = reactive({ name: "", groups: [] as number[], fadeTime: 0, fadeRate: 44.7 });
const saving = ref(false);


async function saveGeneral() {
  const d = device.value;
  if (!d) return;
  saving.value = true;
  await run(async () => {
    if (form.name !== d.name || JSON.stringify([...form.groups].sort((a, b) => a - b)) !== JSON.stringify([...d.groups].sort((a, b) => a - b))) {
      const res = await gw.put(`/device/${d.id}`, { name: form.name, groups: [...form.groups].sort((a, b) => a - b) });
      if (res) Object.assign(d, { name: res.name ?? form.name, groups: res.groups ?? form.groups });
    }
    if (form.fadeTime !== status(d.features, "fadeTime")) await gw.control("device", d.id, { fadeTime: form.fadeTime });
    if (form.fadeRate !== status(d.features, "fadeRate")) await gw.control("device", d.id, { fadeRate: form.fadeRate });
  }, t("saved"));
  saving.value = false;
}

// ------------------------------------------------------ DALI parameters
interface ParamDef {
  key: string;
  label: string;
  query: number;
  editable?: boolean;
  setCmd?: number;
  max?: number;
}
const paramDefs = computed<ParamDef[]>(() => [
  { key: "min", label: t("minLevel"), query: 162, editable: true, setCmd: 43 },
  { key: "max", label: t("maxLevel"), query: 161, editable: true, setCmd: 42 },
  { key: "phys", label: t("physMin"), query: 154 },
  { key: "powerOn", label: t("powerOn"), query: 163, editable: true, setCmd: 45, max: 255 },
  { key: "sysFail", label: t("sysFail"), query: 164, editable: true, setCmd: 44, max: 255 },
  { key: "version", label: t("version"), query: 151 },
  { key: "lightSource", label: t("lightSource"), query: 159 },
  { key: "opMode", label: t("opMode"), query: 158 },
]);
const params = ref<Record<string, number | null> | null>(null);
const edit = reactive<Record<string, number>>({});
const reading = ref(false);
const addrByte = computed(() => ((device.value?.address ?? 0) << 1) | 1);

const LIGHT_SOURCES: Record<number, string> = { 0: "Fluorescent", 2: "HID", 3: "LV halogen", 4: "Incandescent", 6: "LED", 7: "OLED", 252: "Other", 253: "Unknown", 254: "None" };

function fmtParam(key: string, v: number | null | undefined): string {
  if (v === null || v === undefined) return "–";
  if (key === "version") return `${v >> 2}.${v & 3}`;
  if (key === "lightSource") return LIGHT_SOURCES[v] ?? String(v);
  if (key === "opMode") return v === 0 ? "Normal" : `0x${v.toString(16)}`;
  if ((key === "powerOn" || key === "sysFail") && v === 255) return t("lastLevel");
  if (["min", "max", "phys", "powerOn", "sysFail"].includes(key)) return `${v} (${((v * 100) / 254).toFixed(1)} %)`;
  return String(v);
}

async function readParams() {
  const d = device.value;
  if (!d) return;
  reading.value = true;
  await run(async () => {
    const frames = paramDefs.value.map((p) => ({ address: addrByte.value, command: p.query }));
    const answers: (number | null)[] = await gw.post(`/dali/sendDali16/${d.line}`, frames);
    const result: Record<string, number | null> = {};
    paramDefs.value.forEach((p, i) => {
      result[p.key] = answers?.[i] ?? null;
      if (p.editable) edit[p.key] = answers?.[i] ?? 0;
    });
    params.value = result;
  });
  reading.value = false;
}

async function writeParam(p: ParamDef) {
  const d = device.value;
  if (!d || p.setCmd === undefined) return;
  const v = Math.max(0, Math.min(p.max ?? 254, Math.round(edit[p.key])));
  const ok = await confirmDialog({ title: p.label, message: `${d.name}: ${fmtParam(p.key, params.value?.[p.key])} → ${fmtParam(p.key, v)}`, confirmText: t("save") });
  if (!ok) return;
  await run(async () => {
    // DTR0 = value, then the configuration command twice (IEC 62386-102 send-twice)
    await gw.post(`/dali/sendDali16/${d.line}`, [
      { address: 0xa3, command: v },
      { address: addrByte.value, command: p.setCmd },
      { address: addrByte.value, command: p.setCmd },
    ]);
    await readParams();
  }, t("written"));
}

async function identify() {
  const d = device.value;
  if (!d) return;
  await run(() => gw.post(`/dali/sendDali16/${d.line}`, [{ address: addrByte.value, command: 37 }]), t("identify"));
}

async function remove() {
  const d = device.value;
  if (!d) return;
  if (!(await confirmDialog({ title: t("removeDevice"), message: t("confirmDelete", { name: d.name }), danger: true, confirmText: t("delete") }))) return;
  const ok = await run(() => gw.del(`/device/${d.id}`), t("saved"));
  if (ok !== undefined) {
    delete state.devices[d.id];
    emit("close");
  }
}

// --------------------------------------------------------------- scenes
const scenes = ref<Record<string, any> | null>(null);
const scenesLoading = ref(false);
watch(tab, (v) => v === "scenes" && !scenes.value && loadScenes(false));
async function loadScenes(refresh: boolean) {
  const d = device.value;
  if (!d) return;
  scenesLoading.value = true;
  const res = await run(() => (refresh ? gw.post(`/device/${d.id}/scenes`) : gw.get(`/device/${d.id}/scenes`)));
  if (res) scenes.value = res;
  scenesLoading.value = false;
}
function scene(n: number) {
  return scenes.value?.[String(n)];
}
async function ctl(data: Record<string, unknown>) {
  const d = device.value;
  if (d) await run(() => gw.control("device", d.id, data));
}
async function saveScene(n: number) {
  await ctl({ saveToScene: n });
  toast(`${t("scene")} ${n}: ${t("saved")}`, "success");
  setTimeout(() => loadScenes(true), 800);
}
async function removeScene(n: number) {
  const d = device.value;
  if (!d || !(await confirmDialog({ title: t("removeScene"), message: t("confirmRemoveScene", { n }), danger: true }))) return;
  await run(() =>
    gw.post(`/dali/sendDali16/${d.line}`, [
      { address: addrByte.value, command: 80 + n },
      { address: addrByte.value, command: 80 + n },
    ]),
  );
  setTimeout(() => loadScenes(true), 500);
}

// --------------------------------------------------------------- extras
const extras = reactive<{ energy: any; diag: any; error: string }>({ energy: null, diag: null, error: "" });
async function loadExtras() {
  const d = device.value;
  if (!d) return;
  extras.error = "";
  try {
    if (d.daliTypes.includes(51)) extras.energy = await gw.get(`/device/${d.id}/energyReporting`);
    if (d.daliTypes.includes(52)) extras.diag = await gw.get(`/device/${d.id}/diagnosticsMaintenance`);
  } catch (e: any) {
    extras.error = e.message;
  }
}

// reset everything when another device is opened (declared last: uses all refs above)
watch(
  () => props.deviceId,
  () => {
    tab.value = "control";
    params.value = null;
    scenes.value = null;
    extras.energy = extras.diag = null;
    extras.error = "";
    const d = device.value;
    if (!d) return;
    form.name = d.name;
    form.groups = [...(d.groups || [])];
    form.fadeTime = status(d.features, "fadeTime") ?? 0;
    form.fadeRate = status(d.features, "fadeRate") ?? 44.7;
  },
  { immediate: true },
);
</script>

<style scoped>
.flags { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.flag { display: flex; gap: 8px; align-items: flex-start; color: var(--text3); }
.flag .title { color: var(--text2); font-weight: 500; font-size: 13px; }
.flag.active { color: var(--success); }
.flag.active .title { color: var(--text); }
.flag.bad { color: var(--error); }
.group-grid { display: grid; grid-template-columns: repeat(8, 1fr); gap: 6px; }
.group-chip { display: flex; align-items: center; justify-content: center; gap: 4px; height: 34px; border-radius: 8px; background: var(--bg2); cursor: pointer; font-weight: 500; user-select: none; }
.group-chip input { display: none; }
.group-chip.on { background: var(--primary); color: #fff; }
.param { padding: 8px 0; }
.raw { max-height: 320px; overflow: auto; background: var(--bg2); padding: 10px; border-radius: 8px; margin: 0; font-size: 11.5px; }
@media (max-width: 700px) {
  .flags { grid-template-columns: 1fr; }
  .group-grid { grid-template-columns: repeat(4, 1fr); }
}
</style>
