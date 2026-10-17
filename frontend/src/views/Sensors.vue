<template>
  <div class="page">
    <div class="page-head">
      <h1>{{ t("title") }}</h1>
      <button class="btn outline" :disabled="refreshing" @click="refreshAll">
        <span v-if="refreshing" class="spinner"></span><Icon v-else :path="mdiRefresh" :size="18" />{{ t("refreshAll") }}
      </button>
    </div>

    <div class="section-title">{{ t("gatewaySensors") }}</div>
    <div v-if="sensors.length" class="grid cols-3">
      <div v-for="s in sensors" :key="s.id" class="card sensor" @click="openSensor(s.id)">
        <div class="row">
          <span class="icon-bubble" :class="s.type === 'occupancy' && s.value ? 'warn' : ''"><Icon :path="iconFor(s.type)" :size="22" /></span>
          <div class="grow">
            <div class="title">{{ s.name || `${t("sensor")} ${s.id}` }}</div>
            <div class="muted small">{{ typeName(s.type) }} · {{ s.addressType === "dali" ? `DALI L${s.daliSensorAddress?.line} D${s.daliSensorAddress?.address} #${s.daliSensorAddress?.instanceNumber}` : t("internal") }}</div>
          </div>
          <div class="value">
            <template v-if="s.type === 'occupancy'">{{ s.value ? t("occupied") : t("vacant") }}</template>
            <template v-else>{{ fmtValue(s.value) }} <span class="muted small">{{ s.unit }}</span></template>
          </div>
        </div>
        <div class="faint small mt">{{ t("updated") }}: {{ s.timestamp ? new Date(s.timestamp).toLocaleString() : "–" }}</div>
      </div>
    </div>
    <Empty v-else :icon="mdiMotionSensorOff" :text="t('noSensors')" />

    <div class="section-title mt-lg">{{ t("inputs") }}</div>
    <div class="banner info mb">
      <Icon :path="mdiSchoolOutline" :size="18" />
      <div>{{ t("learnInfo") }}</div>
    </div>
    <div class="grid cols-2">
      <Card :title="t('learned')" :icon="mdiGestureTapButton" flush>
        <template #actions><button class="btn icon sm" @click="loadInputs"><Icon :path="mdiRefresh" :size="18" /></button></template>
        <div v-if="!inputs.length" class="empty small">{{ t("noInputs") }}</div>
        <div v-else class="list">
          <div v-for="i in inputs" :key="i.key" class="list-item">
            <span class="icon-bubble" :class="{ warn: recent(i) }"><Icon :path="iconForKind(i.kind)" :size="20" /></span>
            <div class="grow">
              <input v-if="editKey === i.key" v-model="editName" type="text" @keyup.enter="saveName(i)" @blur="saveName(i)" />
              <div v-else class="title" @click="startEdit(i)">{{ i.name || kindName(i.kind) }} <Icon :path="mdiPencil" :size="13" class="faint" /></div>
              <div class="sub">
                L{{ i.line }} · D{{ i.short_address }} · {{ i.instance_number !== null ? `#${i.instance_number}` : `T${i.instance_type}` }}
                · {{ t("events") }}: {{ i.count }} · {{ t("last") }}: {{ i.last_event }} ({{ fmtTime(i.last_seen, lang) }})
              </div>
            </div>
            <button class="btn icon sm" :title="t('delete')" @click="removeInput(i)"><Icon :path="mdiDelete" :size="18" /></button>
          </div>
        </div>
      </Card>
      <Card :title="t('liveEvents')" :icon="mdiFlashOutline" flush>
        <div v-if="!liveEvents.length" class="empty small">{{ t("noLive") }}</div>
        <div v-else class="list">
          <div v-for="(e, idx) in liveEvents" :key="idx" class="list-item">
            <span class="chip primary mono">{{ e.target }}</span>
            <div class="grow">
              <div class="title">{{ e.event?.event_type }}</div>
              <div class="sub">{{ kindName(e.event?.kind) }} · {{ e.hex }}</div>
            </div>
            <span class="faint small">{{ fmtTime(e.timestamp, lang, false) }}</span>
          </div>
        </div>
      </Card>
    </div>

    <div v-if="state.expert && sensors.some((s) => s.addressType === 'dali')" class="mt-lg">
      <button class="btn danger outline sm" @click="deleteAllDali"><Icon :path="mdiDeleteSweep" :size="16" />{{ t("deleteAllDali") }}</button>
    </div>

    <Modal :open="detailId !== null" :title="detail?.name || t('sensor')" :icon="iconFor(detail?.type || '')" wide @close="detailId = null">
      <div class="row between wrap mb">
        <div class="btn-group">
          <button v-for="h in [1, 6, 24, 168]" :key="h" :class="{ active: hours === h }" @click="hours = h">{{ h < 24 ? `${h} h` : `${h / 24} d` }}</button>
        </div>
        <div class="row">
          <button class="btn flat sm" @click="refreshOne"><Icon :path="mdiRefresh" :size="16" />{{ t("refresh") }}</button>
          <button class="btn danger flat sm" @click="deleteOne"><Icon :path="mdiDelete" :size="16" />{{ t("delete") }}</button>
        </div>
      </div>
      <LineChart v-if="series.length" :datasets="[{ label: detail?.name || '', data: series, borderColor: '#03a9f4', backgroundColor: 'rgba(3,169,244,.15)', fill: true }]"
                 :step="detail?.type === 'occupancy'" :y-unit="detail?.unit" />
      <Empty v-else :text="t('noHistory')" />
      <div v-if="detail" class="kv mt">
        <span>ID</span><span>{{ detail.id }}</span>
        <span>{{ t("type") }}</span><span>{{ typeName(detail.type) }}</span>
        <span>{{ t("value") }}</span><span>{{ detail.value }} {{ detail.unit }}</span>
        <span>{{ t("address") }}</span><span class="mono">{{ JSON.stringify(detail.daliSensorAddress || detail.addressType) }}</span>
      </div>
    </Modal>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import {
  mdiBrightness6,
  mdiDelete,
  mdiDeleteSweep,
  mdiFlashOutline,
  mdiGauge,
  mdiGestureTapButton,
  mdiLeaf,
  mdiMoleculeCo2,
  mdiMotionSensor,
  mdiMotionSensorOff,
  mdiPencil,
  mdiRefresh,
  mdiSchoolOutline,
  mdiThermometer,
  mdiWaterPercent,
  mdiAirFilter,
  mdiImport,
} from "@mdi/js";
import Card from "../components/Card.vue";
import Icon from "../components/Icon.vue";
import Empty from "../components/Empty.vue";
import Modal from "../components/Modal.vue";
import LineChart from "../components/LineChart.vue";
import { api, gw } from "../lib/api";
import { confirmDialog, run, state, type Sensor } from "../lib/store";
import { lang, useT } from "../lib/i18n";
import { fmtTime } from "../lib/dali";

const t = useT({
  de: {
    title: "Sensoren & Taster",
    refreshAll: "Alle Sensoren abfragen",
    gatewaySensors: "Sensoren (vom Gateway)",
    sensor: "Sensor",
    internal: "intern",
    occupied: "Belegt",
    vacant: "Frei",
    updated: "Aktualisiert",
    noSensors: "Keine Sensoren gefunden. DALI-2-Sensoren (Präsenz, Licht, Klima) werden beim DALI-Scan erkannt.",
    inputs: "DALI-2 Eingänge (Taster, Melder)",
    learnInfo: "Taster und Melder werden automatisch erkannt, sobald sie ein Ereignis auf den Bus senden – einfach jeden Taster einmal drücken. Danach stehen sie in Home Assistant als Ereignis-Entitäten und Geräte-Auslöser zur Verfügung.",
    learned: "Erkannte Eingänge",
    noInputs: "Noch keine Eingänge erkannt.",
    events: "Ereignisse",
    last: "zuletzt",
    liveEvents: "Live-Ereignisse vom Bus",
    noLive: "Warte auf Ereignisse… (Taster drücken oder Bewegung auslösen)",
    deleteAllDali: "Alle DALI-Sensoren aus dem Gateway löschen",
    confirmDeleteAll: "Alle DALI-Sensoren aus dem Gateway entfernen? Sie werden beim nächsten Scan wieder gefunden.",
    confirmDelete: "Sensor „{name}“ aus dem Gateway entfernen?",
    confirmDeleteInput: "Erkannten Eingang „{name}“ vergessen? Er wird beim nächsten Ereignis wieder erkannt.",
    noHistory: "Noch kein Verlauf aufgezeichnet.",
    k_push_button: "Taster",
    k_occupancy_sensor: "Präsenzmelder",
    k_light_sensor: "Lichtsensor",
    k_absolute_input: "Absolutwertgeber",
    k_general_purpose_sensor: "Allzweck-Sensor",
    k_unknown: "Eingang",
    s_temperature: "Temperatur",
    s_airHumidity: "Luftfeuchte",
    s_airPressure: "Luftdruck",
    s_eCO2: "eCO₂",
    s_VOC: "VOC",
    s_airQuality: "Luftqualität",
    s_light: "Helligkeit",
    s_occupancy: "Präsenz",
    s_unknown: "Unbekannt",
  },
  en: {
    title: "Sensors & buttons",
    refreshAll: "Query all sensors",
    gatewaySensors: "Sensors (from gateway)",
    sensor: "Sensor",
    internal: "internal",
    occupied: "Occupied",
    vacant: "Vacant",
    updated: "Updated",
    noSensors: "No sensors found. DALI-2 sensors (occupancy, light, climate) are detected by the DALI scan.",
    inputs: "DALI-2 inputs (buttons, detectors)",
    learnInfo: "Push buttons and detectors are detected automatically as soon as they send an event on the bus – just press every button once. They then appear in Home Assistant as event entities and device triggers.",
    learned: "Detected inputs",
    noInputs: "No inputs detected yet.",
    events: "Events",
    last: "last",
    liveEvents: "Live events from the bus",
    noLive: "Waiting for events… (press a button or trigger motion)",
    deleteAllDali: "Delete all DALI sensors from the gateway",
    confirmDeleteAll: "Remove all DALI sensors from the gateway? They will be found again by the next scan.",
    confirmDelete: "Remove sensor “{name}” from the gateway?",
    confirmDeleteInput: "Forget detected input “{name}”? It is re-detected with its next event.",
    noHistory: "No history recorded yet.",
    k_push_button: "Push button",
    k_occupancy_sensor: "Occupancy sensor",
    k_light_sensor: "Light sensor",
    k_absolute_input: "Absolute input",
    k_general_purpose_sensor: "General purpose sensor",
    k_unknown: "Input",
    s_temperature: "Temperature",
    s_airHumidity: "Humidity",
    s_airPressure: "Air pressure",
    s_eCO2: "eCO₂",
    s_VOC: "VOC",
    s_airQuality: "Air quality",
    s_light: "Illuminance",
    s_occupancy: "Occupancy",
    s_unknown: "Unknown",
  },
});

const sensors = computed(() => Object.values(state.sensors).sort((a, b) => a.id - b.id));
const ICONS: Record<string, string> = {
  temperature: mdiThermometer,
  airHumidity: mdiWaterPercent,
  airPressure: mdiGauge,
  eCO2: mdiMoleculeCo2,
  VOC: mdiLeaf,
  airQuality: mdiAirFilter,
  light: mdiBrightness6,
  occupancy: mdiMotionSensor,
};
const iconFor = (type: string) => ICONS[type] || mdiGauge;
const iconForKind = (k: string) => (k === "push_button" ? mdiGestureTapButton : k === "occupancy_sensor" ? mdiMotionSensor : k === "light_sensor" ? mdiBrightness6 : mdiImport);
const typeName = (type: string) => t(`s_${type || "unknown"}`);
const kindName = (k: string) => t(`k_${k || "unknown"}`);
const fmtValue = (v: number) => (typeof v === "number" ? (Math.abs(v) >= 100 ? v.toFixed(0) : v.toFixed(1)) : "–");

const refreshing = ref(false);
async function refreshAll() {
  refreshing.value = true;
  const res = await run(() => gw.post("/sensors"), t("saved"));
  if (res?.sensors) for (const s of res.sensors) state.sensors[s.id] = s;
  refreshing.value = false;
}
async function deleteAllDali() {
  if (!(await confirmDialog({ title: t("deleteAllDali"), message: t("confirmDeleteAll"), danger: true, confirmText: t("delete") }))) return;
  await run(() => gw.del("/sensors"), t("saved"));
  const res = await run(() => gw.get("/sensors"));
  if (res) state.sensors = Object.fromEntries(res.sensors.map((s: Sensor) => [s.id, s]));
}

// ---------------------------------------------------------- detail modal
const detailId = ref<number | null>(null);
const hours = ref(24);
const series = ref<{ x: number; y: number }[]>([]);
const detail = computed(() => (detailId.value !== null ? state.sensors[detailId.value] : null));
function openSensor(id: number) {
  detailId.value = id;
  loadSeries();
}
watch(hours, loadSeries);
async function loadSeries() {
  if (detailId.value === null) return;
  const rows = await run(() => api("GET", `analytics/sensor/${detailId.value}?hours=${hours.value}`));
  series.value = (rows || []).map((r: any) => ({ x: r.ts, y: r.value }));
}
async function refreshOne() {
  if (detailId.value === null) return;
  const s = await run(() => gw.post(`/sensors/${detailId.value}`));
  if (s) state.sensors[s.id] = s;
}
async function deleteOne() {
  const s = detail.value;
  if (!s || !(await confirmDialog({ title: t("delete"), message: t("confirmDelete", { name: s.name }), danger: true, confirmText: t("delete") }))) return;
  await run(() => gw.del(`/sensors/${s.id}`), t("saved"));
  delete state.sensors[s.id];
  detailId.value = null;
}

// ------------------------------------------------------------- inputs
const inputs = ref<any[]>([]);
async function loadInputs() {
  inputs.value = (await run(() => api("GET", "inputs"))) || [];
}
onMounted(loadInputs);
const liveEvents = computed(() => state.monitor.filter((f) => f.kind === "event" && f.event?.source_key).slice(-20).reverse());
watch(
  () => liveEvents.value.length,
  () => {
    const keys = new Set(inputs.value.map((i) => i.key));
    if (liveEvents.value.some((e) => !keys.has(e.event.source_key))) setTimeout(loadInputs, 1500);
  },
);
const recent = (i: any) => Date.now() / 1000 - i.last_seen < 10;
const editKey = ref<string | null>(null);
const editName = ref("");
function startEdit(i: any) {
  editKey.value = i.key;
  editName.value = i.name || "";
}
async function saveName(i: any) {
  if (editKey.value !== i.key) return;
  editKey.value = null;
  if ((i.name || "") === editName.value) return;
  await run(() => api("PUT", `inputs/${encodeURIComponent(i.key)}`, { name: editName.value }), t("saved"));
  i.name = editName.value;
}
async function removeInput(i: any) {
  if (!(await confirmDialog({ title: t("delete"), message: t("confirmDeleteInput", { name: i.name || i.key }), danger: true }))) return;
  await run(() => api("DELETE", `inputs/${encodeURIComponent(i.key)}`));
  await loadInputs();
}
</script>

<style scoped>
.sensor { padding: 14px 16px; cursor: pointer; transition: transform .12s; }
.sensor:hover { transform: translateY(-1px); }
.sensor .title { font-weight: 500; }
.sensor .value { font-size: 20px; font-weight: 500; white-space: nowrap; }
.title { cursor: pointer; }
</style>
