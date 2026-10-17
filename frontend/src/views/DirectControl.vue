<template>
  <div class="page">
    <div class="page-head">
      <div class="grow">
        <h1>{{ t("title") }}</h1>
        <div class="muted small">{{ t("subtitle") }}</div>
      </div>
      <button class="btn" :disabled="scanning || !online" @click="scan">
        <span v-if="scanning" class="spinner"></span><Icon v-else :path="mdiMagnify" :size="18" />{{ scanning ? t("scanning") : t("scan") }}
      </button>
    </div>

    <!-- ------------------------------------------------------ fail-safe -->
    <div class="grid cols-3">
      <StatCard :icon="mdiGestureTapButton" :label="t('controlDevices')" :value="devices.length"
                :sub="data.scanned ? t('scannedAt', { t: fmtTime(data.scanned, lang) }) : t('notScanned')" kind="off" />
      <StatCard :icon="autarkCount === devices.length && devices.length ? mdiShieldCheck : mdiShieldAlert" :label="t('autark')"
                :value="`${autarkCount} / ${devices.length}`" :kind="!devices.length ? 'off' : autarkCount === devices.length ? 'ok' : 'warn'"
                :sub="t('autarkSub')" />
      <StatCard :icon="mdiPowerPlug" :label="t('busPower')" :value="busPowerText" :kind="data.bus_power_in_gateway ? 'warn' : 'ok'"
                :sub="data.bus_power_in_gateway ? t('busPowerGateway') : t('busPowerExternal')" />
    </div>

    <div class="banner info mt-lg">
      <Icon :path="mdiInformationOutline" :size="18" />
      <div>
        <b>{{ t("howTitle") }}</b> {{ t("how1") }}
        <ul class="how">
          <li><b>{{ t("modeApp") }}</b> – {{ t("modeAppText") }}</li>
          <li><b>{{ t("modeInst") }}</b> – {{ t("modeInstText") }}</li>
        </ul>
        {{ t("how2") }}
        <RouterLink to="/groups">{{ t("toGroups") }}</RouterLink>
      </div>
    </div>

    <div v-for="(missing, line) in data.unaddressed || {}" :key="line">
      <div v-if="missing" class="banner warn mt">
        <Icon :path="mdiAlert" :size="18" />
        <div class="grow">{{ t("unaddressed", { line }) }}</div>
        <RouterLink to="/bus?tab=scan" class="btn sm">{{ t("toScan") }}</RouterLink>
      </div>
    </div>

    <!-- ------------------------------------------------------- devices -->
    <div class="section-title mt-lg">{{ t("devicesTitle") }}</div>
    <div v-if="loading" class="empty"><span class="spinner"></span></div>
    <Empty v-else-if="!devices.length" :icon="mdiGestureTapButton" :text="data.scanned ? t('noneFound') : t('notScannedYet')">
      <div class="faint small" style="max-width: 520px">{{ t("noneHint") }}</div>
    </Empty>
    <div v-else class="grid cols-2">
      <Card v-for="d in devices" :key="d.key" :icon="mdiGestureTapButton" :icon-class="d.autark ? 'ok' : 'warn'"
            :title="title(d)" :subtitle="subtitle(d)">
        <template #actions>
          <button class="btn icon sm" :title="t('identify')" @click="act(d, 'identify')"><Icon :path="mdiBullhornOutline" :size="18" /></button>
          <button class="btn icon sm" :title="t('reread')" @click="reread(d)"><Icon :path="mdiRefresh" :size="18" /></button>
        </template>

        <div class="verdict" :class="d.autark ? 'ok' : 'warn'">
          <Icon :path="d.autark ? mdiShieldCheck : mdiShieldAlert" :size="20" />
          <div>
            <div class="title">{{ d.autark ? t("verdictOk") : d.app_controller_present ? t("verdictOff") : t("verdictNone") }}</div>
            <div class="small">{{ d.autark ? t("verdictOkText") : d.app_controller_present ? t("verdictOffText") : t("verdictNoneText") }}</div>
          </div>
        </div>

        <div class="list mt">
          <div class="list-item">
            <div class="grow">
              <div class="title">{{ t("appController") }}</div>
              <div class="sub">
                {{ !d.app_controller_present ? t("notPresent") : d.app_controller_always_active ? t("alwaysActive") : t("appControllerHint") }}
              </div>
            </div>
            <Toggle :key="`app-${d.key}-${rev[d.key] || 0}`" :model-value="d.app_controller_enabled" :disabled="!d.app_controller_present || d.app_controller_always_active || busy[d.key]"
                    @change="(v: boolean) => setApp(d, v)" />
          </div>
          <div v-for="i in d.instances" :key="i.number" class="list-item">
            <span class="chip">{{ t("input") }} {{ i.number + 1 }}</span>
            <div class="grow">
              <div class="title">{{ kindName(i.kind) }}</div>
              <div class="sub">{{ t("eventsToHa") }}<span v-if="i.event_scheme"> · {{ t("scheme") }}: {{ i.event_scheme }}</span>
                <span v-if="i.error" class="err-text"> · {{ t("error") }} {{ i.error }}</span></div>
            </div>
            <Toggle :key="`inst-${d.key}-${i.number}-${rev[d.key] || 0}`" :model-value="i.enabled" :disabled="busy[d.key]" @change="(v: boolean) => setInstance(d, i.number, v)" />
          </div>
        </div>

        <div class="row wrap mt">
          <span v-if="d.status_flags?.input_device_error" class="chip err">{{ t("inputError") }}</span>
          <span v-if="d.status_flags?.application_controller_error || d.app_controller_error" class="chip err">{{ t("appError") }}</span>
          <span v-if="d.status_flags?.quiescent_mode" class="chip warn">{{ t("quiescent") }}</span>
          <span v-if="d.status_flags?.power_cycle_seen" class="chip clickable" :title="t('resetPowerCycle')" @click="act(d, 'reset_power_cycle')">{{ t("powerCycle") }} ✕</span>
          <span v-if="d.status_flags?.reset_state" class="chip">{{ t("resetState") }}</span>
        </div>

        <details class="mt small">
          <summary class="muted">{{ t("details") }}</summary>
          <div class="kv mt">
            <span>GTIN</span><span class="mono">{{ d.gtin || "–" }}</span>
            <span>{{ t("serial") }}</span><span class="mono">{{ d.serial ?? "–" }}</span>
            <span>Firmware</span><span>{{ d.firmware || "–" }}</span>
            <span>Hardware</span><span>{{ d.hardware || "–" }}</span>
            <span>IEC 62386-103</span><span>{{ d.version_103 || d.dali_version || "–" }}</span>
            <span>{{ t("statusByte") }}</span><span class="mono">0b{{ (d.status || 0).toString(2).padStart(8, "0") }}</span>
          </div>
        </details>
      </Card>
    </div>

    <!-- ------------------------------------------------ direct commands -->
    <Card class="mt-lg" :title="t('observed')" :subtitle="t('observedSub')" :icon="mdiEarHearing" flush>
      <template #actions>
        <div class="btn-group">
          <button v-for="h in [1, 24, 168]" :key="h" :class="{ active: hours === h }" @click="hours = h">{{ h < 24 ? `${h} h` : `${h / 24} d` }}</button>
        </div>
      </template>
      <div v-if="!direct.commands.length && !direct.events.length" class="empty small">{{ t("noObserved") }}</div>
      <div v-else class="table-wrap">
        <table class="table">
          <thead><tr><th>{{ t("target") }}</th><th>{{ t("command") }}</th><th class="right">{{ t("count") }}</th><th>{{ t("last") }}</th></tr></thead>
          <tbody>
            <tr v-for="(c, idx) in direct.commands" :key="'c' + idx">
              <td><span class="chip primary mono">{{ c.target }}</span></td>
              <td class="mono small">{{ c.text }}</td>
              <td class="right">{{ c.count }}</td>
              <td class="small">{{ fmtTime(c.last, lang) }}</td>
            </tr>
            <tr v-for="(e, idx) in direct.events" :key="'e' + idx">
              <td><span class="chip warn mono">{{ e.target }}</span></td>
              <td class="small">{{ t("eventRow") }}</td>
              <td class="right">{{ e.count }}</td>
              <td class="small">{{ fmtTime(e.last, lang) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </Card>

    <Card class="mt-lg" :title="t('mappingTitle')" :icon="mdiSitemapOutline">
      <p class="muted small" style="margin-top: 0">{{ t("mappingText") }}</p>
      <ol class="small muted">
        <li>{{ t("mapping1") }}</li>
        <li>{{ t("mapping2") }}</li>
        <li>{{ t("mapping3") }}</li>
      </ol>
    </Card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from "vue";
import {
  mdiAlert,
  mdiBullhornOutline,
  mdiEarHearing,
  mdiGestureTapButton,
  mdiInformationOutline,
  mdiMagnify,
  mdiPowerPlug,
  mdiRefresh,
  mdiShieldAlert,
  mdiShieldCheck,
  mdiSitemapOutline,
} from "@mdi/js";
import Card from "../components/Card.vue";
import Empty from "../components/Empty.vue";
import Icon from "../components/Icon.vue";
import StatCard from "../components/StatCard.vue";
import Toggle from "../components/Toggle.vue";
import { api } from "../lib/api";
import { confirmDialog, run, state } from "../lib/store";
import { lang, useT } from "../lib/i18n";
import { fmtTime } from "../lib/dali";

const t = useT({
  de: {
    title: "Direktsteuerung",
    subtitle: "Taster und Melder, die Leuchten direkt über den DALI-Bus steuern – auch ohne Gateway und Home Assistant",
    scan: "Steuergeräte suchen",
    scanning: "Suche läuft…",
    controlDevices: "Steuergeräte (Taster/Melder)",
    scannedAt: "gesucht {t}",
    notScanned: "noch nicht gesucht",
    autark: "Ausfallsicher",
    autarkSub: "Application Controller aktiv",
    busPower: "Busversorgung",
    busPowerExternal: "eigenes DALI-Netzteil – Bus läuft ohne Gateway weiter",
    busPowerGateway: "kommt vom Gateway – fällt das Gateway aus, ist der ganze Bus stromlos",
    extern: "Extern",
    gateway: "Gateway",
    unknown: "unbekannt",
    howTitle: "So funktioniert die Ausfallsicherheit:",
    how1: "DALI-2-Taster und -Melder arbeiten in zwei Modi, die auch gleichzeitig aktiv sein können:",
    modeApp: "Application Controller (Direktmodus)",
    modeAppText: "das Gerät sendet selbst DALI-Befehle an Leuchten oder Gruppen. Funktioniert ohne Gateway und Home Assistant.",
    modeInst: "Instanzen (Ereignisse)",
    modeInstText: "das Gerät meldet nur „gedrückt / bewegt“. Die Reaktion übernimmt Home Assistant oder das Gateway – fällt das aus, bleibt das Licht dunkel.",
    how2: "Ziel und Funktion der Taster (z. B. Gruppe 1, Toggle + Dimmen) werden im Gerät gespeichert. Die Gruppen in den Leuchten verwaltest du hier:",
    toGroups: "Gruppen & Zonen",
    unaddressed: "Auf Linie {line} gibt es Steuergeräte ohne Kurzadresse. Diese müssen erst per DALI-Scan adressiert werden.",
    toScan: "Zum Scan",
    devicesTitle: "Gefundene Steuergeräte",
    noneFound: "Keine DALI-2-Steuergeräte am Bus gefunden.",
    notScannedYet: "Noch nicht gesucht – klicke auf „Steuergeräte suchen“.",
    noneHint: "Neu angeschlossene Taster/Melder zuerst unter DALI-Bus → Scan adressieren. Die Suche fragt alle 64 Steuergeräte-Adressen ab (nur Leseabfragen, dauert einige Sekunden).",
    identify: "Identifizieren (Summer/LED)",
    reread: "Neu einlesen",
    verdictOk: "Ausfallsicher",
    verdictOkText: "Das Gerät steuert Leuchten selbst – funktioniert auch, wenn Gateway oder Home Assistant ausfallen.",
    verdictOff: "Nicht ausfallsicher",
    verdictOffText: "Der Application Controller ist ausgeschaltet. Ohne Gateway/Home Assistant passiert beim Drücken nichts.",
    verdictNone: "Kein Direktmodus möglich",
    verdictNoneText: "Dieses Gerät hat keinen eingebauten Application Controller und kann nur Ereignisse melden.",
    appController: "Direktmodus (Application Controller)",
    appControllerHint: "Sendet die im Gerät hinterlegten Befehle direkt an die Leuchten",
    alwaysActive: "Bei diesem Gerät immer aktiv",
    notPresent: "Nicht vorhanden",
    input: "Eingang",
    eventsToHa: "Ereignisse an Gateway/Home Assistant",
    scheme: "Schema",
    inputError: "Eingangsfehler",
    appError: "Controller-Fehler",
    quiescent: "Ruhemodus",
    powerCycle: "Netzunterbrechung",
    resetPowerCycle: "Anzeige zurücksetzen",
    resetState: "Werkszustand",
    details: "Geräteinformationen",
    serial: "Seriennummer",
    statusByte: "Status",
    confirmAppOff: "Direktmodus von {name} ausschalten?\n\nDanach reagieren die Leuchten nur noch über Gateway bzw. Home Assistant auf diesen Taster – bei einem Ausfall bleibt das Licht dunkel.",
    confirmAppOn: "Direktmodus von {name} einschalten?\n\nDas Gerät sendet dann bei jedem Tastendruck die im Gerät gespeicherten Befehle direkt an die Leuchten. Prüfe die Zuordnung, falls das Gerät neu ist (Werkseinstellung bei Lunatone MC: Broadcast).",
    observed: "Mitgelesene Direktbefehle",
    observedSub: "Befehle auf dem Bus, die nicht vom Gateway stammen – also von Tastern/Meldern im Direktmodus",
    noObserved: "Im gewählten Zeitraum keine Direktbefehle oder Ereignisse gesehen. Drücke einen Taster, um zu prüfen, was er sendet.",
    target: "Ziel",
    command: "Befehl",
    count: "Anzahl",
    last: "Zuletzt",
    eventRow: "Ereignis (Instanz-Modus) – braucht Gateway/HA",
    mappingTitle: "Taster einer Leuchte oder Gruppe zuordnen",
    mappingText: "Welcher Eingang welche Gruppe mit welcher Funktion steuert, speichert jeder Hersteller in einem eigenen, nicht genormten Speicherbereich des Geräts. Diese Zuordnung stellst du deshalb mit dem Herstellerwerkzeug ein:",
    mapping1: "Lunatone: DALI Cockpit (Windows) – Schnittstelle „Network“ mit der IP dieses Gateways – oder die Lunatone NFC-App (MC NFC).",
    mapping2: "Im Gerät Ziel (Broadcast, Gruppe 0–15 oder Adresse), Tastenfunktion und Befehle festlegen und „In Gerät schreiben“.",
    mapping3: "Hier prüfen: Direktmodus aktiv (grün) und beim Drücken erscheint der Befehl unter „Mitgelesene Direktbefehle“.",
    k_push_button: "Taster",
    k_absolute_input: "Absolutwertgeber",
    k_occupancy_sensor: "Präsenzmelder",
    k_light_sensor: "Lichtsensor",
    k_colour_sensor: "Farbsensor",
    k_general_purpose_sensor: "Allzweck-Sensor",
    k_generic: "Eingang",
    k_unknown: "Eingang",
    saved: "Übernommen",
    deviceWord: "Steuergerät",
    inputs: "Eingänge",
  },
  en: {
    title: "Direct control",
    subtitle: "Push buttons and sensors that control lights directly on the DALI bus – even without gateway and Home Assistant",
    scan: "Search control devices",
    scanning: "Searching…",
    controlDevices: "Control devices (buttons/sensors)",
    scannedAt: "searched {t}",
    notScanned: "not searched yet",
    autark: "Fail-safe",
    autarkSub: "Application controller active",
    busPower: "Bus power",
    busPowerExternal: "separate DALI power supply – bus keeps working without the gateway",
    busPowerGateway: "provided by the gateway – if the gateway fails the whole bus is unpowered",
    extern: "External",
    gateway: "Gateway",
    unknown: "unknown",
    howTitle: "How fail-safe operation works:",
    how1: "DALI-2 buttons and sensors have two modes that can be active at the same time:",
    modeApp: "Application controller (direct mode)",
    modeAppText: "the device sends DALI commands to lights or groups itself. Works without gateway and Home Assistant.",
    modeInst: "Instances (events)",
    modeInstText: "the device only reports “pressed / motion”. Home Assistant or the gateway reacts – if they fail, the light stays off.",
    how2: "Target and function of the buttons (e.g. group 1, toggle + dim) are stored in the device. Manage the groups of your lights here:",
    toGroups: "Groups & zones",
    unaddressed: "Line {line} has control devices without a short address. Address them with a DALI scan first.",
    toScan: "Go to scan",
    devicesTitle: "Control devices found",
    noneFound: "No DALI-2 control devices found on the bus.",
    notScannedYet: "Not searched yet – click “Search control devices”.",
    noneHint: "Address newly connected buttons/sensors first under DALI bus → Scan. The search queries all 64 control device addresses (read-only, takes a few seconds).",
    identify: "Identify (buzzer/LED)",
    reread: "Read again",
    verdictOk: "Fail-safe",
    verdictOkText: "The device controls lights itself – keeps working if gateway or Home Assistant fail.",
    verdictOff: "Not fail-safe",
    verdictOffText: "The application controller is switched off. Without gateway/Home Assistant nothing happens on a button press.",
    verdictNone: "No direct mode possible",
    verdictNoneText: "This device has no integrated application controller and can only report events.",
    appController: "Direct mode (application controller)",
    appControllerHint: "Sends the commands stored in the device directly to the lights",
    alwaysActive: "Always active on this device",
    notPresent: "Not present",
    input: "Input",
    eventsToHa: "Events to gateway/Home Assistant",
    scheme: "Scheme",
    inputError: "Input error",
    appError: "Controller error",
    quiescent: "Quiescent mode",
    powerCycle: "Power cycle",
    resetPowerCycle: "Reset indicator",
    resetState: "Reset state",
    details: "Device information",
    serial: "Serial number",
    statusByte: "Status",
    confirmAppOff: "Switch off direct mode of {name}?\n\nThe lights will then only react to this button via gateway or Home Assistant – during an outage the light stays off.",
    confirmAppOn: "Switch on direct mode of {name}?\n\nThe device then sends the commands stored in it directly to the lights on every press. Check the mapping if the device is new (Lunatone MC factory default: broadcast).",
    observed: "Observed direct commands",
    observedSub: "Commands on the bus that were not sent by the gateway – i.e. from buttons/sensors in direct mode",
    noObserved: "No direct commands or events seen in this period. Press a button to check what it sends.",
    target: "Target",
    command: "Command",
    count: "Count",
    last: "Last",
    eventRow: "Event (instance mode) – needs gateway/HA",
    mappingTitle: "Assign a button to a light or group",
    mappingText: "Which input controls which group with which function is stored by every manufacturer in its own, non-standard memory area of the device. Set this mapping with the manufacturer tool:",
    mapping1: "Lunatone: DALI Cockpit (Windows) – interface “Network” with the IP of this gateway – or the Lunatone NFC app (MC NFC).",
    mapping2: "Set target (broadcast, group 0–15 or address), button function and commands in the device and “write to device”.",
    mapping3: "Check here: direct mode active (green), and pressing the button shows the command under “Observed direct commands”.",
    k_push_button: "Push button",
    k_absolute_input: "Absolute input",
    k_occupancy_sensor: "Occupancy sensor",
    k_light_sensor: "Light sensor",
    k_colour_sensor: "Colour sensor",
    k_general_purpose_sensor: "General purpose sensor",
    k_generic: "Input",
    k_unknown: "Input",
    saved: "Applied",
    deviceWord: "Control device",
    inputs: "inputs",
  },
});

interface Instance {
  number: number;
  type: number | null;
  kind: string;
  enabled: boolean;
  event_scheme: string | null;
  error: number | null;
}
interface ControlDevice {
  key: string;
  line: number;
  address: number;
  autark: boolean;
  app_controller_present: boolean;
  app_controller_always_active: boolean;
  app_controller_enabled: boolean;
  app_controller_error: number | null;
  status: number;
  status_flags: Record<string, boolean>;
  instances: Instance[];
  manufacturer: string | null;
  gtin: string | null;
  serial: number | null;
  firmware: string | null;
  hardware: string | null;
  version_103: string | null;
  dali_version: string | null;
}

const data = reactive<any>({ devices: [], scanned: null, unaddressed: {}, bus_power_in_gateway: null });
const loading = ref(true);
const scanning = ref(false);
const busy = reactive<Record<string, boolean>>({});
const rev = reactive<Record<string, number>>({}); // forces toggles to re-render after cancel/failure
const hours = ref(24);
const direct = reactive<{ commands: any[]; events: any[] }>({ commands: [], events: [] });

const online = computed(() => !!state.status?.gateway?.connected);
const devices = computed<ControlDevice[]>(() => data.devices || []);
const autarkCount = computed(() => devices.value.filter((d) => d.autark).length);
const busPowerText = computed(() =>
  data.bus_power_in_gateway === true ? t("gateway") : data.bus_power_in_gateway === false ? t("extern") : t("unknown"),
);

const kindName = (k: string) => t(`k_${k || "unknown"}`);
const title = (d: ControlDevice) => `${d.manufacturer ? `${d.manufacturer} ` : ""}${t("deviceWord")} D${d.address}`;
const subtitle = (d: ControlDevice) => {
  const kinds = [...new Set(d.instances.map((i) => kindName(i.kind)))].join(", ");
  return `${t("line")} ${d.line} · ${d.instances.length} ${t("inputs")}${kinds ? ` (${kinds})` : ""}`;
};

async function load() {
  const res = await run(() => api("GET", "controldevices"));
  if (res) Object.assign(data, res);
  loading.value = false;
}
async function loadDirect() {
  const res = await run(() => api("GET", `controldevices/direct?hours=${hours.value}`));
  if (res) Object.assign(direct, res);
}
watch(hours, loadDirect);

async function scan() {
  scanning.value = true;
  const res = await run(() => api("POST", "controldevices/scan", {}));
  if (res) Object.assign(data, res);
  scanning.value = false;
}

function replace(device: ControlDevice) {
  const list = [...devices.value.filter((d) => d.key !== device.key), device];
  data.devices = list.sort((a, b) => a.line - b.line || a.address - b.address);
}

async function act(d: ControlDevice, action: string, instance?: number) {
  busy[d.key] = true;
  const res = await run(() => api("POST", "controldevices/action", { line: d.line, address: d.address, action, instance }), action === "identify" ? undefined : t("saved"));
  if (res) replace(res);
  else rev[d.key] = (rev[d.key] || 0) + 1;
  busy[d.key] = false;
}
async function reread(d: ControlDevice) {
  // identify is harmless and returns a freshly read device
  await act(d, "identify");
}
async function setApp(d: ControlDevice, on: boolean) {
  const ok = await confirmDialog({
    title: t("appController"),
    message: t(on ? "confirmAppOn" : "confirmAppOff", { name: title(d) }),
    danger: !on,
    confirmText: t("saved"),
  });
  if (!ok) {
    rev[d.key] = (rev[d.key] || 0) + 1;
    return;
  }
  await act(d, on ? "enable_app" : "disable_app");
}
async function setInstance(d: ControlDevice, n: number, on: boolean) {
  await act(d, on ? "enable_instance" : "disable_instance", n);
}

onMounted(() => {
  load();
  loadDirect();
});
</script>

<style scoped>
.how { margin: 6px 0; padding-left: 18px; }
.verdict { display: flex; gap: 10px; align-items: flex-start; padding: 10px 12px; border-radius: 10px; }
.verdict .title { font-weight: 600; }
.verdict.ok { background: color-mix(in srgb, var(--success) 12%, transparent); color: var(--success); }
.verdict.warn { background: color-mix(in srgb, var(--warning) 16%, transparent); color: color-mix(in srgb, var(--warning) 75%, var(--text)); }
.verdict .small { color: var(--text2); }
.err-text { color: var(--error); }
details summary { cursor: pointer; }
</style>
