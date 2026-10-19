<template>
  <Modal :open="open" :title="title" :subtitle="subtitle" :icon="mdiTuneVariant" wide @close="$emit('close')">
    <div v-if="loading" class="center pad"><span class="spinner"></span></div>

    <!-- ------------------------------------------------------- instance -->
    <template v-else-if="instance !== null && data">
      <div class="section-title">{{ t("general") }}</div>
      <div class="form-grid">
        <label class="field toggle-field">
          <span>{{ t("enabled") }}</span>
          <Toggle v-model="form.enabled" />
        </label>
        <label class="field">
          <span>{{ t("scheme") }}</span>
          <select v-model.number="form.settings.event_scheme">
            <option v-for="(s, n) in SCHEMES" :key="s" :value="n">{{ t(`sch_${s}`) }}</option>
          </select>
        </label>
        <label class="field">
          <span>{{ t("priority") }}</span>
          <select v-model.number="form.settings.event_priority">
            <option v-for="p in [2, 3, 4, 5]" :key="p" :value="p">{{ t("prio", { n: p }) }}{{ p === 2 ? ` (${t("high")})` : p === 5 ? ` (${t("low")})` : "" }}</option>
          </select>
        </label>
        <label v-for="g in GROUP_KEYS" :key="g" class="field">
          <span>{{ t(g) }}</span>
          <select v-model.number="form.settings[g]">
            <option :value="255">{{ t("none") }}</option>
            <option v-for="n in 32" :key="n" :value="n - 1">{{ t("instGroup") }} {{ n - 1 }}</option>
          </select>
        </label>
      </div>

      <div class="section-title">{{ t("filter") }}</div>
      <div v-if="data.event_filter === null" class="muted small">{{ t("noFilter") }}</div>
      <div v-else-if="filterBits.length" class="checks">
        <label v-for="(name, bit) in filterBits" :key="name" class="check">
          <input type="checkbox" :checked="!!(form.event_filter & (1 << bit))" @change="toggleBit(bit)" />
          {{ t(`f_${name}`) }}
        </label>
      </div>
      <label v-else class="field">
        <span>{{ t("filterRaw") }}</span>
        <input v-model="filterHex" class="mono" @change="applyHex" />
      </label>

      <template v-if="timerFields.length">
        <div class="section-title">{{ t("timers") }}</div>
        <div class="form-grid">
          <label v-for="f in timerFields" :key="f.key" class="field">
            <span>{{ t(`t_${f.key}`) }}</span>
            <div class="row unit-row">
              <input type="number" :min="f.min * f.step" :max="f.max * f.step" :step="f.step" :value="display(f)" @change="setDisplay(f, ($event.target as HTMLInputElement).value)" />
              <span class="unit">{{ f.unit === "raw" ? "" : f.unit }}</span>
            </div>
            <span class="hint">
              {{ t("raw") }} {{ form.settings[f.key] ?? "–" }}
              <template v-if="f.key === 'double_timer' && form.settings[f.key] === 0"> · {{ t("off") }}</template>
              <template v-if="f.minKey && data.info[f.minKey] != null"> · {{ t("min") }} {{ fmt(data.info[f.minKey] * f.step, f.unit) }}</template>
              <template v-if="f.hint"> · {{ t(f.hint) }}</template>
            </span>
          </label>
        </div>
      </template>

      <details class="mt small">
        <summary class="muted">{{ t("info") }}</summary>
        <div class="kv mt">
          <span>{{ t("type") }}</span><span>{{ data.type ?? "–" }} ({{ data.kind }})</span>
          <span v-for="(v, k) in data.info" :key="k" class="contents">
            <span>{{ t(`i_${k}`) }}</span><span class="mono">{{ v ?? "–" }}</span>
          </span>
        </div>
      </details>
    </template>

    <!-- --------------------------------------------------------- device -->
    <template v-else-if="instance === null && device">
      <div class="section-title">{{ t("general") }}</div>
      <div class="form-grid">
        <label class="field toggle-field">
          <span>{{ t("powerCycle") }}</span>
          <Toggle v-model="dev.power_cycle_notification" />
          <span class="hint">{{ t("powerCycleHint") }}</span>
        </label>
        <div class="field">
          <span>{{ t("allInstances") }}</span>
          <div class="row">
            <button class="btn sm outline" :disabled="saving" @click="allInstances(true)">{{ t("enableAll") }}</button>
            <button class="btn sm outline" :disabled="saving" @click="allInstances(false)">{{ t("disableAll") }}</button>
          </div>
        </div>
      </div>

      <div class="section-title">{{ t("deviceGroups") }}</div>
      <div v-if="dev.device_groups === null" class="muted small">{{ t("groupsUnknown") }}</div>
      <div v-else class="group-grid">
        <button v-for="n in 32" :key="n" class="chip clickable group-chip" :class="{ primary: dev.device_groups.includes(n - 1) }" @click="toggleGroup(n - 1)">
          {{ n - 1 }}
        </button>
      </div>
      <div class="hint small muted mt-s">{{ t("deviceGroupsHint") }}</div>

      <div class="section-title">{{ t("address") }}</div>
      <div class="row wrap">
        <span>{{ t("currentAddress") }} <b class="mono">D{{ device.address }}</b></span>
        <select v-model.number="newAddress" class="addr-sel">
          <option v-for="n in 64" :key="n" :value="n - 1" :disabled="taken.has(n - 1) && n - 1 !== device.address">
            D{{ n - 1 }}{{ taken.has(n - 1) && n - 1 !== device.address ? ` (${t("taken")})` : "" }}
          </option>
        </select>
        <button class="btn sm outline" :disabled="saving || newAddress === device.address" @click="changeAddress">{{ t("changeAddress") }}</button>
      </div>
      <div class="hint small muted mt-s">{{ t("addressHint") }}</div>

      <div class="kv mt">
        <span>{{ t("operatingMode") }}</span>
        <span>{{ device.operating_mode ?? "–" }}{{ (device.operating_mode ?? 0) >= 128 ? ` (${t("manufacturerMode")})` : "" }}</span>
      </div>

      <template v-if="state.expert">
        <div class="section-title">{{ t("expert") }}</div>
        <button class="btn sm danger outline" :disabled="saving" @click="resetDevice">{{ t("reset") }}</button>
        <div class="hint small muted mt-s">{{ t("resetHint") }}</div>
      </template>
    </template>

    <template #footer>
      <span class="grow small muted">{{ changeCount ? t("pending", { n: changeCount }) : t("nvm") }}</span>
      <button v-if="instance !== null" class="btn flat" :disabled="loading || saving" @click="load">{{ t("reload") }}</button>
      <button class="btn" :disabled="!changeCount || saving" @click="save">
        <span v-if="saving" class="spinner mini light"></span>{{ t("apply") }}
      </button>
    </template>
  </Modal>
</template>

<script setup lang="ts">
// All standard settings of a DALI-2 control device (IEC 62386-103) and its
// instances (301 push button, 303 occupancy, 304 light) – the same set DALI
// Cockpit offers. Values are raw DALI numbers; timers are shown in ms/s.
import { computed, reactive, ref, watch } from "vue";
import { mdiTuneVariant } from "@mdi/js";
import Modal from "./Modal.vue";
import Toggle from "./Toggle.vue";
import { api } from "../lib/api";
import { confirmDialog, run, state } from "../lib/store";
import { useT } from "../lib/i18n";

const props = defineProps<{ open: boolean; device: any | null; instance: number | null; devices: any[] }>();
const emit = defineEmits<{ (e: "close"): void; (e: "updated", device: any): void; (e: "reload"): void }>();

interface Field {
  key: string;
  unit: "ms" | "s" | "%" | "raw";
  step: number; // display units per raw step
  min: number;
  max: number;
  minKey?: string;
  hint?: string;
}
const TIMER_FIELDS: Record<number, Field[]> = {
  1: [
    { key: "short_timer", unit: "ms", step: 20, min: 0, max: 255, minKey: "short_timer_min" },
    { key: "double_timer", unit: "ms", step: 20, min: 0, max: 100, minKey: "double_timer_min", hint: "doubleHint" },
    { key: "repeat_timer", unit: "ms", step: 20, min: 0, max: 255 },
    { key: "stuck_timer", unit: "s", step: 1, min: 0, max: 255 },
  ],
  3: [
    { key: "hold_timer", unit: "s", step: 10, min: 1, max: 255, hint: "holdHint" },
    { key: "report_timer", unit: "s", step: 1, min: 0, max: 255, hint: "reportHint" },
    { key: "deadtime_timer", unit: "s", step: 0.05, min: 0, max: 255, hint: "deadtimeHint" },
  ],
  4: [
    { key: "report_timer", unit: "s", step: 1, min: 0, max: 255, hint: "reportHint" },
    { key: "deadtime_timer", unit: "s", step: 0.05, min: 0, max: 255, hint: "deadtimeHint" },
    { key: "hysteresis", unit: "%", step: 1, min: 0, max: 25, hint: "hysteresisHint" },
    { key: "hysteresis_min", unit: "raw", step: 1, min: 0, max: 255, hint: "hysteresisMinHint" },
  ],
};
// event filter bits per instance type (IEC 62386-301/303/304)
const FILTERS: Record<number, string[]> = {
  1: ["released", "pressed", "short", "double", "long_start", "long_repeat", "long_stop", "free_stuck"],
  3: ["occupied", "vacant", "repeat", "movement", "no_movement"],
  4: ["illuminance"],
};
const SCHEMES = ["instance", "device", "device_instance", "device_group", "instance_group"];
const GROUP_KEYS = ["primary_group", "group_1", "group_2"];

const t = useT({
  de: {
    titleInstance: "Eingang {n} – Einstellungen",
    titleDevice: "Geräteeinstellungen",
    general: "Allgemein",
    enabled: "Ereignisse senden",
    scheme: "Ereignisschema",
    sch_instance: "Instanz (ohne Adresse)",
    sch_device: "Gerät + Typ",
    sch_device_instance: "Gerät + Instanz (empfohlen)",
    sch_device_group: "Gerätegruppe",
    sch_instance_group: "Instanzgruppe",
    priority: "Ereignispriorität",
    prio: "Priorität {n}",
    high: "hoch",
    low: "niedrig",
    primary_group: "Primäre Instanzgruppe",
    group_1: "Instanzgruppe 1",
    group_2: "Instanzgruppe 2",
    none: "Keine",
    instGroup: "Gruppe",
    filter: "Ereignisfilter – welche Ereignisse gesendet werden",
    noFilter: "Diese Instanz hat keinen Ereignisfilter.",
    filterRaw: "Filter (hex, 24 Bit)",
    f_released: "Losgelassen",
    f_pressed: "Gedrückt",
    f_short: "Kurz gedrückt",
    f_double: "Doppelt gedrückt",
    f_long_start: "Lang gedrückt (Start)",
    f_long_repeat: "Lang gedrückt (Wiederholung)",
    f_long_stop: "Lang gedrückt (Ende)",
    f_free_stuck: "Taster frei / klemmt",
    f_occupied: "Besetzt",
    f_vacant: "Unbesetzt",
    f_repeat: "Noch besetzt / unbesetzt (Wiederholung)",
    f_movement: "Bewegung",
    f_no_movement: "Keine Bewegung",
    f_illuminance: "Helligkeitswert",
    timers: "Zeiten",
    t_short_timer: "Kurzer Druck bis",
    t_double_timer: "Doppelklick-Fenster",
    t_repeat_timer: "Wiederholrate beim Halten",
    t_stuck_timer: "Klemmt nach",
    t_hold_timer: "Haltezeit (Nachlauf)",
    t_report_timer: "Reportzeit (Wiederholung)",
    t_deadtime_timer: "Totzeit",
    t_hysteresis: "Hysterese",
    t_hysteresis_min: "Hysterese-Minimum",
    raw: "Rohwert",
    off: "aus",
    min: "min.",
    doubleHint: "0 = Doppelklick aus",
    holdHint: "Schritte zu 10 s",
    reportHint: "Abstand der wiederholten Meldung",
    deadtimeHint: "Mindestabstand zwischen zwei Meldungen (50 ms)",
    hysteresisHint: "Meldung erst bei dieser Änderung",
    hysteresisMinHint: "kleinste Änderung in Rohwert-Schritten",
    info: "Weitere Werte (nur lesen)",
    type: "Instanztyp",
    i_resolution: "Auflösung (Bit)",
    i_instance_status: "Instanzstatus",
    i_instance_error: "Instanzfehler",
    i_short_timer_min: "Kurzer Druck min. (Rohwert)",
    i_double_timer_min: "Doppelklick min. (Rohwert)",
    i_catching: "Erfassung",
    powerCycle: "Power-Cycle-Meldung",
    powerCycleHint: "Meldet nach Netzwiederkehr ein Ereignis an den Bus",
    allInstances: "Alle Eingänge",
    enableAll: "Alle aktivieren",
    disableAll: "Alle deaktivieren",
    deviceGroups: "Gerätegruppen (Steuergeräte, 0–31)",
    deviceGroupsHint: "Gruppen für Steuergeräte – getrennt von den Leuchtengruppen 0–15.",
    groupsUnknown: "Gerätegruppen konnten nicht gelesen werden.",
    address: "Kurzadresse",
    currentAddress: "Aktuell",
    taken: "belegt",
    changeAddress: "Adresse ändern",
    addressHint: "Ändert nur dieses Gerät. Gateway-Sensoren, Automationen und Home-Assistant-Zuordnungen, die sich auf die alte Adresse beziehen, müssen danach angepasst werden.",
    confirmAddress: "Kurzadresse von D{old} auf D{new} ändern?\n\nGateway-Sensoren, Automationen und Zuordnungen in Home Assistant, die die alte Adresse verwenden, funktionieren danach nicht mehr.",
    operatingMode: "Betriebsart",
    manufacturerMode: "herstellerspezifisch",
    expert: "Experte",
    reset: "Auf Standardwerte zurücksetzen (RESET)",
    resetHint: "Setzt alle genormten Einstellungen zurück. Kurzadresse und Herstellerkonfiguration bleiben.",
    confirmReset: "Alle genormten Einstellungen von D{a} auf die Standardwerte zurücksetzen?",
    confirmWord: "RESET",
    pending: "{n} Änderung(en) nicht übernommen",
    nvm: "Wird nichtflüchtig im Gerät gespeichert",
    reload: "Neu lesen",
    apply: "Übernehmen",
    confirmTitle: "Einstellungen schreiben?",
    confirmText: "Folgende Werte werden ins Gerät geschrieben:\n\n{list}",
    saved: "Übernommen",
  },
  en: {
    titleInstance: "Input {n} – settings",
    titleDevice: "Device settings",
    general: "General",
    enabled: "Send events",
    scheme: "Event scheme",
    sch_instance: "Instance (no address)",
    sch_device: "Device + type",
    sch_device_instance: "Device + instance (recommended)",
    sch_device_group: "Device group",
    sch_instance_group: "Instance group",
    priority: "Event priority",
    prio: "Priority {n}",
    high: "high",
    low: "low",
    primary_group: "Primary instance group",
    group_1: "Instance group 1",
    group_2: "Instance group 2",
    none: "None",
    instGroup: "Group",
    filter: "Event filter – which events are sent",
    noFilter: "This instance has no event filter.",
    filterRaw: "Filter (hex, 24 bit)",
    f_released: "Released",
    f_pressed: "Pressed",
    f_short: "Short press",
    f_double: "Double press",
    f_long_start: "Long press (start)",
    f_long_repeat: "Long press (repeat)",
    f_long_stop: "Long press (stop)",
    f_free_stuck: "Button free / stuck",
    f_occupied: "Occupied",
    f_vacant: "Vacant",
    f_repeat: "Still occupied / vacant (repeat)",
    f_movement: "Movement",
    f_no_movement: "No movement",
    f_illuminance: "Illuminance value",
    timers: "Timers",
    t_short_timer: "Short press up to",
    t_double_timer: "Double press window",
    t_repeat_timer: "Repeat rate while held",
    t_stuck_timer: "Stuck after",
    t_hold_timer: "Hold time",
    t_report_timer: "Report time (repeat)",
    t_deadtime_timer: "Dead time",
    t_hysteresis: "Hysteresis",
    t_hysteresis_min: "Hysteresis minimum",
    raw: "Raw",
    off: "off",
    min: "min.",
    doubleHint: "0 = double press off",
    holdHint: "steps of 10 s",
    reportHint: "interval of the repeated report",
    deadtimeHint: "minimum gap between two reports (50 ms)",
    hysteresisHint: "report only after this change",
    hysteresisMinHint: "smallest change in raw steps",
    info: "More values (read only)",
    type: "Instance type",
    i_resolution: "Resolution (bits)",
    i_instance_status: "Instance status",
    i_instance_error: "Instance error",
    i_short_timer_min: "Short press min. (raw)",
    i_double_timer_min: "Double press min. (raw)",
    i_catching: "Catching",
    powerCycle: "Power cycle notification",
    powerCycleHint: "Sends an event to the bus after mains power returns",
    allInstances: "All inputs",
    enableAll: "Enable all",
    disableAll: "Disable all",
    deviceGroups: "Device groups (control devices, 0–31)",
    deviceGroupsHint: "Groups of control devices – separate from the light groups 0–15.",
    groupsUnknown: "Device groups could not be read.",
    address: "Short address",
    currentAddress: "Current",
    taken: "taken",
    changeAddress: "Change address",
    addressHint: "Changes only this device. Gateway sensors, automations and Home Assistant mappings referring to the old address must be adjusted afterwards.",
    confirmAddress: "Change the short address from D{old} to D{new}?\n\nGateway sensors, automations and Home Assistant mappings using the old address stop working.",
    operatingMode: "Operating mode",
    manufacturerMode: "manufacturer specific",
    expert: "Expert",
    reset: "Reset to default values (RESET)",
    resetHint: "Resets all standard settings. Short address and manufacturer configuration are kept.",
    confirmReset: "Reset all standard settings of D{a} to their default values?",
    confirmWord: "RESET",
    pending: "{n} change(s) not applied",
    nvm: "Stored non-volatile in the device",
    reload: "Read again",
    apply: "Apply",
    confirmTitle: "Write settings?",
    confirmText: "These values will be written to the device:\n\n{list}",
    saved: "Applied",
  },
});

const loading = ref(false);
const saving = ref(false);
const data = ref<any>(null);
const form = reactive<{ enabled: boolean; event_filter: number; settings: Record<string, number> }>({ enabled: false, event_filter: 0, settings: {} });
const dev = reactive<{ power_cycle_notification: boolean; device_groups: number[] | null }>({ power_cycle_notification: false, device_groups: [] });
const newAddress = ref(0);
const filterHex = ref("");

const title = computed(() => (props.instance !== null ? t("titleInstance", { n: props.instance + 1 }) : t("titleDevice")));
const subtitle = computed(() => (props.device ? `${props.device.manufacturer ? `${props.device.manufacturer} · ` : ""}D${props.device.address} · ${t("general") === "General" ? "Line" : "Linie"} ${props.device.line}` : ""));
const timerFields = computed<Field[]>(() => TIMER_FIELDS[data.value?.type] || []);
const filterBits = computed<string[]>(() => FILTERS[data.value?.type] || []);
const taken = computed(() => new Set((props.devices || []).filter((d) => d.line === props.device?.line).map((d) => d.address)));

function fmt(v: number, unit: string) {
  return `${Math.round(v * 100) / 100}${unit === "raw" ? "" : ` ${unit}`}`;
}
function display(f: Field) {
  const raw = form.settings[f.key];
  return raw == null ? "" : Math.round(raw * f.step * 100) / 100;
}
function setDisplay(f: Field, value: string) {
  const raw = Math.round(Number(value) / f.step);
  if (Number.isFinite(raw)) form.settings[f.key] = Math.max(f.min, Math.min(f.max, raw));
}
function toggleBit(bit: number) {
  form.event_filter ^= 1 << bit;
}
function applyHex() {
  const v = parseInt(filterHex.value, 16);
  if (Number.isFinite(v)) form.event_filter = v & 0xffffff;
}
function toggleGroup(g: number) {
  if (!dev.device_groups) return;
  dev.device_groups = dev.device_groups.includes(g) ? dev.device_groups.filter((x) => x !== g) : [...dev.device_groups, g].sort((a, b) => a - b);
}

function fillInstance(res: any) {
  data.value = res;
  form.enabled = res.enabled;
  form.event_filter = res.event_filter ?? 0;
  form.settings = { ...res.settings };
  filterHex.value = (res.event_filter ?? 0).toString(16).toUpperCase();
}
function fillDevice(source: any = props.device) {
  dev.power_cycle_notification = !!source?.power_cycle_notification;
  dev.device_groups = source?.device_groups ? [...source.device_groups] : null;
  newAddress.value = source?.address ?? 0;
}

async function load() {
  if (!props.device) return;
  if (props.instance === null) {
    // read fresh – groups/power cycle notification are not part of older scans
    loading.value = true;
    const fresh = await run(() => api("POST", "controldevices/read", { line: props.device.line, address: props.device.address }));
    loading.value = false;
    if (fresh) emit("updated", fresh);
    fillDevice(fresh || props.device);
    return;
  }
  loading.value = true;
  const res = await run(() => api("POST", "controldevices/instance", { line: props.device.line, address: props.device.address, instance: props.instance }));
  if (res) fillInstance(res);
  loading.value = false;
}
// separate sources: a getter returning a new array would fire on every device update
watch(
  [() => props.open, () => props.device?.key, () => props.instance],
  () => {
    data.value = null;
    if (props.open) load();
  },
  { immediate: true },
);

const changes = computed<Record<string, any>>(() => {
  const out: Record<string, any> = {};
  if (props.instance !== null) {
    if (!data.value) return out;
    if (form.enabled !== data.value.enabled) out.enabled = form.enabled;
    if (data.value.event_filter !== null && form.event_filter !== data.value.event_filter) out.event_filter = form.event_filter;
    for (const [k, v] of Object.entries(form.settings)) if (v != null && v !== data.value.settings[k]) out[k] = v;
  } else if (props.device) {
    if (dev.power_cycle_notification !== !!props.device.power_cycle_notification) out.power_cycle_notification = dev.power_cycle_notification;
    const before = (props.device.device_groups || []).join(",");
    if (dev.device_groups && dev.device_groups.join(",") !== before) out.device_groups = dev.device_groups;
  }
  return out;
});
const changeCount = computed(() => Object.keys(changes.value).length);

function describe(key: string, value: any): string {
  if (key === "enabled") return `${t("enabled")}: ${value ? "✓" : "✗"}`;
  if (key === "event_filter") return `${t("filter").split(" –")[0]}: 0x${value.toString(16).toUpperCase()}`;
  if (key === "event_scheme") return `${t("scheme")}: ${t(`sch_${SCHEMES[value]}`)}`;
  if (key === "power_cycle_notification") return `${t("powerCycle")}: ${value ? "✓" : "✗"}`;
  if (key === "device_groups") return `${t("deviceGroups")}: ${value.join(", ") || "–"}`;
  const f = timerFields.value.find((x) => x.key === key);
  if (f) return `${t(`t_${key}`)}: ${fmt(value * f.step, f.unit)} (${t("raw")} ${value})`;
  if (GROUP_KEYS.includes(key)) return `${t(key)}: ${value === 255 ? t("none") : value}`;
  return `${t(key)}: ${value}`;
}

async function post(changesToSend: Record<string, any>, instance: number | null) {
  const d = props.device;
  return run(() => api("POST", "controldevices/configure", { line: d.line, address: d.address, instance, changes: changesToSend }), t("saved"));
}

async function save() {
  const list = Object.entries(changes.value).map(([k, v]) => `• ${describe(k, v)}`).join("\n");
  if (!(await confirmDialog({ title: t("confirmTitle"), message: t("confirmText", { list }), confirmText: t("apply") }))) return;
  saving.value = true;
  const res = await post(changes.value, props.instance);
  saving.value = false;
  if (!res) return;
  if (res.instance) fillInstance(res.instance);
  if (res.device) emit("updated", res.device);
}

async function allInstances(on: boolean) {
  saving.value = true;
  const res = await post({ all_instances: on }, null);
  saving.value = false;
  if (res?.device) emit("updated", res.device);
}

async function changeAddress() {
  const d = props.device;
  const ok = await confirmDialog({ title: t("address"), message: t("confirmAddress", { old: d.address, new: newAddress.value }), danger: true, confirmText: t("changeAddress") });
  if (!ok) return;
  saving.value = true;
  const res = await post({ short_address: newAddress.value }, null);
  saving.value = false;
  if (res?.device) {
    emit("reload");
    emit("close");
  }
}

async function resetDevice() {
  const d = props.device;
  const ok = await confirmDialog({ title: t("reset"), message: t("confirmReset", { a: d.address }), danger: true, typeToConfirm: t("confirmWord"), confirmText: t("reset") });
  if (!ok) return;
  saving.value = true;
  const res = await run(() => api("POST", "controldevices/action", { line: d.line, address: d.address, action: "reset" }), t("saved"));
  saving.value = false;
  if (res) emit("updated", res);
}


</script>

<style scoped>
.pad { padding: 40px 0; }
.form-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 12px 16px; }
.toggle-field { justify-content: flex-start; }
.checks { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 6px 16px; }
.check { display: flex; gap: 8px; align-items: center; font-size: 13.5px; cursor: pointer; }
.unit-row input { flex: 1; min-width: 0; }
.unit { color: var(--text2); font-size: 13px; min-width: 22px; }
.group-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(42px, 1fr)); gap: 6px; }
.group-chip { justify-content: center; }
.addr-sel { width: auto; }
.contents { display: contents; }
.mt-s { margin-top: 6px; }
</style>
