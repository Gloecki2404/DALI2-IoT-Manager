<template>
  <div class="page">
    <div class="page-head"><h1>{{ t("title") }}</h1></div>

    <div class="grid cols-2">
      <!-- ------------------------------------------------------ gateway -->
      <Card :title="t('gateway')" :icon="mdiRouterWireless">
        <div class="col gap-lg">
          <label class="field">
            <span>{{ t("gwName") }}</span>
            <div class="row">
              <input v-model="name" type="text" maxlength="64" />
              <button class="btn" :disabled="!name || name === state.info?.name" @click="saveName">{{ t("save") }}</button>
            </div>
          </label>
          <div class="kv">
            <span>Firmware</span><span>{{ state.info?.version }}</span>
            <span>{{ t("serial") }}</span><span class="mono">{{ state.info?.device?.serial }}</span>
            <span>UID</span><span class="mono small">{{ state.info?.uid }}</span>
            <span>Tier</span><span>{{ state.info?.tier }}</span>
          </div>
        </div>
        <template #footer>
          <a class="btn flat" :href="`http://${state.status?.gateway?.host}/`" target="_blank" rel="noopener">
            <Icon :path="mdiOpenInNew" :size="16" />{{ t("webUi") }}
          </a>
          <button class="btn danger outline" @click="reboot"><Icon :path="mdiRestart" :size="18" />{{ t("reboot") }}</button>
        </template>
      </Card>

      <!-- ------------------------------------------------------ settings -->
      <Card :title="t('protocol')" :icon="mdiTuneVariant">
        <div class="list">
          <div class="list-item">
            <div class="grow">
              <div class="title">{{ t("daliPing") }}</div>
              <div class="sub">{{ t("daliPingHelp") }}</div>
            </div>
            <Toggle :model-value="!!settings.dali_ping" @change="(v: boolean) => saveSetting('dali_ping', v)" />
          </div>
          <div class="list-item">
            <div class="grow">
              <div class="title">{{ t("logFile") }}</div>
              <div class="sub">{{ t("logFileHelp") }}</div>
            </div>
            <Toggle :model-value="!!settings.log_file_enabled" @change="(v: boolean) => saveSetting('log_file_enabled', v)" />
          </div>
        </div>
      </Card>

      <!-- ------------------------------------------------------ datetime -->
      <Card :title="t('datetime')" :icon="mdiClockOutline">
        <div class="col gap-lg">
          <div class="row between">
            <div>
              <div class="big mono">{{ dt.time || "–" }}</div>
              <div class="muted small">{{ dt.date }} · {{ dt.timezone }}</div>
            </div>
            <button class="btn icon" @click="loadDatetime"><Icon :path="mdiRefresh" /></button>
          </div>
          <div v-if="haTz && haTz !== dt.timezone" class="banner warn">
            <Icon :path="mdiAlert" :size="18" />
            <div class="grow">{{ t("tzMismatch", { gw: dt.timezone, ha: haTz }) }}</div>
            <button class="btn sm" @click="form.timezone = haTz">{{ t("takeHa") }}</button>
          </div>
          <label class="field">
            <span>{{ t("timezone") }}</span>
            <select v-model="form.timezone">
              <option v-for="z in timezones" :key="z" :value="z">{{ z }}</option>
            </select>
          </label>
          <div class="row">
            <Toggle v-model="form.automatic_time" />
            <span>{{ t("autoTime") }}</span>
          </div>
          <div v-if="!form.automatic_time" class="form-grid">
            <label class="field"><span>{{ t("date") }}</span><input v-model="form.date" type="date" /></label>
            <label class="field"><span>{{ t("time") }}</span><input v-model="form.time" type="time" step="1" /></label>
            <div class="field"><span>&nbsp;</span><button class="btn flat sm" @click="useBrowserTime">{{ t("nowBrowser") }}</button></div>
          </div>
        </div>
        <template #footer>
          <button class="btn" @click="saveDatetime">{{ t("save") }}</button>
        </template>
      </Card>

      <!-- ------------------------------------------------------ location -->
      <Card :title="t('location')" :subtitle="t('locationSub')" :icon="mdiMapMarker">
        <div class="form-grid">
          <label class="field"><span>{{ t("lat") }}</span><input v-model.number="loc.lat" type="number" step="0.0001" /></label>
          <label class="field"><span>{{ t("lon") }}</span><input v-model.number="loc.lon" type="number" step="0.0001" /></label>
        </div>
        <div class="row wrap mt">
          <button v-if="haLoc" class="btn outline sm" @click="Object.assign(loc, haLoc)"><Icon :path="mdiHomeAssistant" :size="16" />{{ t("takeHaLoc") }}</button>
          <button class="btn outline sm" @click="detectLocation"><Icon :path="mdiCrosshairsGps" :size="16" />{{ t("detect") }}</button>
          <a class="btn flat sm" :href="`https://www.openstreetmap.org/?mlat=${loc.lat}&mlon=${loc.lon}#map=15/${loc.lat}/${loc.lon}`" target="_blank" rel="noopener">
            <Icon :path="mdiMap" :size="16" />{{ t("showMap") }}
          </a>
        </div>
        <template #footer><button class="btn" @click="saveLocation">{{ t("save") }}</button></template>
      </Card>

      <!-- -------------------------------------------------------- backup -->
      <Card :title="t('backup')" :subtitle="t('backupSub')" :icon="mdiBackupRestore">
        <div class="section-title">{{ t("download") }}</div>
        <div class="row wrap">
          <a class="btn outline" :href="downloadUrl('gw/downloads/systemConfiguration')" download><Icon :path="mdiDownload" :size="18" />{{ t("sysConfig") }} (.lsc)</a>
          <a class="btn outline" :href="downloadUrl('gw/downloads/deviceNames')" download><Icon :path="mdiDownload" :size="18" />{{ t("deviceNames") }} (.csv)</a>
        </div>
        <div class="section-title">{{ t("restore") }}</div>
        <div class="col">
          <label class="upload">
            <Icon :path="mdiUpload" :size="18" />
            <span class="grow">{{ t("sysConfig") }} (.lsc)</span>
            <input type="file" accept=".lsc" @change="upload($event, '/upload/systemConfiguration', t('sysConfig'), true)" />
          </label>
          <label class="upload">
            <Icon :path="mdiUpload" :size="18" />
            <span class="grow">{{ t("deviceNames") }} (.csv)</span>
            <input type="file" accept=".csv" @change="upload($event, '/upload/deviceNames', t('deviceNames'), false)" />
          </label>
        </div>
        <div class="faint small mt">{{ t("restoreHint") }}</div>
      </Card>

      <!-- --------------------------------------------------------- addon -->
      <Card :title="t('addon')" :icon="mdiPuzzleOutline">
        <div class="kv">
          <span>{{ t("version") }}</span><span>{{ state.status?.version }}</span>
          <span>Gateway</span>
          <span class="row"><span class="dot" :class="state.status?.gateway?.connected ? 'ok' : 'err'"></span>{{ state.status?.gateway?.host }}</span>
          <span>{{ t("history") }}</span><span>{{ state.status?.history_days }} {{ t("days") }}</span>
          <span>{{ t("dbSize") }}</span><span>{{ ((state.status?.db_size || 0) / 1048576).toFixed(1) }} MB</span>
          <span>Home Assistant</span><span>{{ state.status?.ha?.version || (state.status?.dev_mode ? t("devMode") : "–") }}</span>
        </div>
        <div class="section-title">{{ t("changeGateway") }}</div>
        <div class="row">
          <input v-model="newHost" type="text" :placeholder="t('hostPlaceholder')" />
          <button class="btn" :disabled="!newHost" @click="setHost(newHost)">{{ t("connect") }}</button>
        </div>
        <div class="row wrap mt">
          <button class="btn outline sm" :disabled="discovering" @click="discover">
            <span v-if="discovering" class="spinner"></span><Icon v-else :path="mdiMagnify" :size="16" />{{ t("search") }}
          </button>
          <button class="btn outline sm" @click="announce"><Icon :path="mdiHomeImportOutline" :size="16" />{{ t("announce") }}</button>
        </div>
        <div v-for="f in found" :key="f.host" class="list-item clickable" @click="setHost(f.host)">
          <Icon :path="mdiRouterWireless" />
          <div class="grow"><div class="title">{{ f.name }}</div><div class="sub">{{ f.host }} · {{ f.version }}</div></div>
          <span class="chip primary">{{ t("connect") }}</span>
        </div>
        <div class="faint small mt">{{ t("addonHint") }}</div>
      </Card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from "vue";
import {
  mdiAlert,
  mdiBackupRestore,
  mdiClockOutline,
  mdiCrosshairsGps,
  mdiDownload,
  mdiHomeAssistant,
  mdiHomeImportOutline,
  mdiMagnify,
  mdiMap,
  mdiMapMarker,
  mdiOpenInNew,
  mdiPuzzleOutline,
  mdiRefresh,
  mdiRestart,
  mdiRouterWireless,
  mdiTuneVariant,
  mdiUpload,
} from "@mdi/js";
import Card from "../components/Card.vue";
import Icon from "../components/Icon.vue";
import Toggle from "../components/Toggle.vue";
import { api, downloadUrl, gw } from "../lib/api";
import { confirmDialog, run, state, toast } from "../lib/store";
import { useT } from "../lib/i18n";

const t = useT({
  de: {
    title: "System",
    gateway: "Gateway",
    gwName: "Name des Gateways",
    serial: "Seriennummer",
    webUi: "Weboberfläche des Geräts",
    reboot: "Neustart",
    confirmReboot: "Gateway jetzt neu starten? Die Beleuchtung bleibt im aktuellen Zustand, Automationen pausieren für ca. 1 Minute.",
    rebooting: "Gateway startet neu…",
    protocol: "Einstellungen",
    daliPing: "DALI-Ping",
    daliPingHelp: "Sendet regelmäßig einen PING auf den Bus (für DALI-2-Steuergeräte, die einen aktiven Controller erwarten).",
    logFile: "Logdatei schreiben",
    logFileHelp: "Nur zur Fehlersuche auf Anweisung des Supports. Verlangsamt das Gerät, schaltet sich nach 30 Tagen ab.",
    datetime: "Datum & Uhrzeit",
    tzMismatch: "Zeitzone des Gateways ({gw}) weicht von Home Assistant ({ha}) ab – Zeitpläne und Sonnenzeiten können falsch sein.",
    takeHa: "Übernehmen",
    timezone: "Zeitzone",
    autoTime: "Uhrzeit automatisch (NTP)",
    date: "Datum",
    time: "Uhrzeit",
    nowBrowser: "Aktuelle Zeit",
    location: "Standort",
    locationSub: "Wird für Sonnenaufgang/-untergang in Zeitplänen verwendet",
    lat: "Breitengrad",
    lon: "Längengrad",
    takeHaLoc: "Von Home Assistant",
    detect: "Automatisch ermitteln",
    showMap: "Karte",
    backup: "Sicherung & Wiederherstellung",
    backupSub: "Konfiguration des Gateways sichern oder einspielen",
    download: "Herunterladen",
    restore: "Wiederherstellen",
    sysConfig: "Systemkonfiguration",
    deviceNames: "Gerätenamen",
    restoreHint: "Die Systemkonfiguration enthält Geräte, Zonen, Automationen und Einstellungen. Nach dem Einspielen startet das Gateway neu.",
    confirmUpload: "{what} aus „{file}“ einspielen? Die aktuelle Konfiguration wird überschrieben.",
    uploaded: "{what} eingespielt",
    addon: "Add-on",
    version: "Version",
    history: "Verlauf",
    dbSize: "Datenbank",
    devMode: "Entwicklungsmodus",
    changeGateway: "Gateway wechseln",
    hostPlaceholder: "IP-Adresse oder Hostname",
    connect: "Verbinden",
    search: "Netzwerk durchsuchen",
    announce: "Integration in HA anbieten",
    announced: "Integration wurde in Home Assistant angeboten (Einstellungen → Geräte & Dienste)",
    notAnnounced: "Anbieten nicht möglich (nur unter Home Assistant OS)",
    addonHint: "Die feste Gateway-Adresse kann auch in der Add-on-Konfiguration hinterlegt werden.",
    noneFound: "Kein Gateway gefunden",
  },
  en: {
    title: "System",
    gateway: "Gateway",
    gwName: "Gateway name",
    serial: "Serial number",
    webUi: "Device web UI",
    reboot: "Reboot",
    confirmReboot: "Reboot the gateway now? Lights keep their state, automations pause for about 1 minute.",
    rebooting: "Gateway is rebooting…",
    protocol: "Settings",
    daliPing: "DALI ping",
    daliPingHelp: "Periodically sends a PING on the bus (for DALI-2 control devices expecting an active controller).",
    logFile: "Write log file",
    logFileHelp: "Only for troubleshooting when asked by support. Slows the device down, switches off after 30 days.",
    datetime: "Date & time",
    tzMismatch: "Gateway time zone ({gw}) differs from Home Assistant ({ha}) – schedules and sun times may be wrong.",
    takeHa: "Apply",
    timezone: "Time zone",
    autoTime: "Automatic time (NTP)",
    date: "Date",
    time: "Time",
    nowBrowser: "Current time",
    location: "Location",
    locationSub: "Used for sunrise/sunset in schedules",
    lat: "Latitude",
    lon: "Longitude",
    takeHaLoc: "From Home Assistant",
    detect: "Detect automatically",
    showMap: "Map",
    backup: "Backup & restore",
    backupSub: "Save or restore the gateway configuration",
    download: "Download",
    restore: "Restore",
    sysConfig: "System configuration",
    deviceNames: "Device names",
    restoreHint: "The system configuration contains devices, zones, automations and settings. The gateway reboots after restoring.",
    confirmUpload: "Restore {what} from “{file}”? The current configuration will be overwritten.",
    uploaded: "{what} restored",
    addon: "Add-on",
    version: "Version",
    history: "History",
    dbSize: "Database",
    devMode: "Development mode",
    changeGateway: "Change gateway",
    hostPlaceholder: "IP address or hostname",
    connect: "Connect",
    search: "Search network",
    announce: "Offer integration in HA",
    announced: "Integration offered in Home Assistant (Settings → Devices & services)",
    notAnnounced: "Not possible (only on Home Assistant OS)",
    addonHint: "A fixed gateway address can also be set in the add-on configuration.",
    noneFound: "No gateway found",
  },
});

// ---------------------------------------------------------------- name
const name = ref("");
watch(() => state.info?.name, (n) => (name.value = n || ""), { immediate: true });
async function saveName() {
  const res = await run(() => gw.put("/info", { name: name.value }), t("saved"));
  if (res) state.info = { ...state.info, ...res };
}
async function reboot() {
  if (!(await confirmDialog({ title: t("reboot"), message: t("confirmReboot"), danger: true, confirmText: t("reboot") }))) return;
  await run(() => gw.post("/reboot"), t("rebooting"));
}

// ------------------------------------------------------------ settings
const settings = reactive<Record<string, boolean>>({});
async function loadSettings() {
  const s = await run(() => gw.get("/settings"));
  if (s) Object.assign(settings, s);
}
async function saveSetting(key: string, value: boolean) {
  const res = await run(() => gw.put("/settings", { [key]: value }), t("saved"));
  if (res) Object.assign(settings, res);
  else await loadSettings();
}

// ------------------------------------------------------------ datetime
const dt = reactive<any>({});
const form = reactive({ timezone: "", automatic_time: true, date: "", time: "" });
const timezones = ref<string[]>([]);
const haTz = computed(() => state.status?.ha?.time_zone);
async function loadDatetime() {
  const d = await run(() => gw.get("/datetime"));
  if (d) {
    Object.assign(dt, d);
    form.timezone = d.timezone;
    form.automatic_time = d.automatic_time;
  }
}
function useBrowserTime() {
  const now = new Date();
  form.date = now.toISOString().slice(0, 10);
  form.time = now.toTimeString().slice(0, 8);
}
async function saveDatetime() {
  const body: Record<string, unknown> = { timezone: form.timezone, automatic_time: form.automatic_time };
  if (!form.automatic_time) {
    body.date = form.date;
    body.time = form.time;
  }
  const res = await run(() => gw.post("/datetime", body), t("saved"));
  if (res) Object.assign(dt, res);
}

// ------------------------------------------------------------ location
const loc = reactive({ lat: 0, lon: 0 });
const haLoc = computed(() => (state.status?.ha?.latitude != null ? { lat: state.status.ha.latitude, lon: state.status.ha.longitude } : null));
async function loadLocation() {
  const l = await run(() => gw.get("/location"));
  if (l) Object.assign(loc, { lat: +l.lat.toFixed(5), lon: +l.lon.toFixed(5) });
}
async function detectLocation() {
  const l = await run(() => gw.post("/location/detect"));
  if (l) Object.assign(loc, { lat: +l.lat.toFixed(5), lon: +l.lon.toFixed(5) });
}
async function saveLocation() {
  await run(() => gw.post("/location", { lat: loc.lat, lon: loc.lon }), t("saved"));
}

// -------------------------------------------------------------- backup
async function upload(ev: Event, path: string, what: string, reboots: boolean) {
  const input = ev.target as HTMLInputElement;
  const file = input.files?.[0];
  input.value = "";
  if (!file) return;
  if (!(await confirmDialog({ title: t("restore"), message: t("confirmUpload", { what, file: file.name }), danger: reboots, confirmText: t("restore") }))) return;
  const fd = new FormData();
  fd.append("files", file, file.name);
  await run(() => api("POST", `gw${path}`, fd), t("uploaded", { what }));
}

// --------------------------------------------------------------- addon
const newHost = ref("");
const found = ref<any[]>([]);
const discovering = ref(false);
async function setHost(host: string) {
  await run(() => api("POST", "gateway", { host }), t("saved"));
  found.value = [];
}
async function discover() {
  discovering.value = true;
  found.value = (await run(() => api("POST", "discover"))) || [];
  if (!found.value.length) toast(t("noneFound"));
  discovering.value = false;
}
async function announce() {
  const r = await run(() => api("POST", "announce"));
  if (r) toast(r.ok ? t("announced") : t("notAnnounced"), r.ok ? "success" : "info", 6000);
}

onMounted(async () => {
  loadSettings();
  loadDatetime();
  loadLocation();
  const tz = await run(() => gw.get("/datetime/timezones"));
  timezones.value = tz?.timezones || [];
  if (!state.status?.ha?.version) {
    const s = await run(() => api("GET", "status"));
    if (s) state.status = s;
  }
});
</script>

<style scoped>
.big { font-size: 26px; font-weight: 500; }
.upload { display: flex; align-items: center; gap: 10px; padding: 10px 12px; border: 1px dashed var(--divider); border-radius: 10px; cursor: pointer; color: var(--text2); }
.upload:hover { border-color: var(--primary); color: var(--primary); }
.upload input { display: none; }
</style>
