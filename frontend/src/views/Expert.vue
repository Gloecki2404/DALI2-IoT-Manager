<template>
  <div class="page">
    <div class="page-head"><h1>{{ t("title") }}</h1></div>

    <div v-if="!state.expert" class="banner warn">
      <Icon :path="mdiShieldAlertOutline" :size="18" />
      <div class="grow">{{ t("enableHint") }}</div>
      <button class="btn sm" @click="setExpert(true)">{{ t("enable") }}</button>
    </div>

    <template v-else>
      <div class="banner err mb">
        <Icon :path="mdiAlertOctagon" :size="18" />
        <div>{{ t("warning") }}</div>
      </div>

      <div class="grid cols-2">
        <!-- ---------------------------------------------------- network -->
        <Card :title="t('network')" :icon="mdiLan" icon-class="warn">
          <div v-if="netLoading" class="empty"><span class="spinner"></span></div>
          <div v-else-if="netError" class="banner info">
            <Icon :path="mdiInformationOutline" :size="18" /><div>{{ t("netUnavailable") }} <span class="faint small">({{ netError }})</span></div>
          </div>
          <template v-else>
            <div class="kv mb">
              <span>MAC</span><span class="mono">{{ net.mac_address }}</span>
              <span v-if="net.dhcp_lease">DHCP-Lease</span><span v-if="net.dhcp_lease" class="mono small">{{ net.dhcp_lease }}</span>
            </div>
            <div class="row mb"><Toggle v-model="netForm.dhcp" /><span>{{ t("dhcp") }}</span></div>
            <div class="form-grid">
              <label class="field"><span>{{ t("ip") }}</span><input v-model="netForm.ip_address" type="text" :disabled="netForm.dhcp" /></label>
              <label class="field"><span>{{ t("mask") }}</span><input v-model="netForm.subnet_mask" type="text" :disabled="netForm.dhcp" /></label>
              <label class="field"><span>{{ t("gatewayIp") }}</span><input v-model="netForm.gateway" type="text" :disabled="netForm.dhcp" /></label>
              <label class="field"><span>{{ t("dns") }}</span><input v-model="dnsText" type="text" :disabled="netForm.dhcp" /></label>
              <label class="field"><span>{{ t("fallback") }}</span><input v-model.number="netForm.static_fallback_retries" type="number" min="0" max="60" /><span class="hint">{{ t("fallbackHint") }}</span></label>
            </div>
          </template>
          <template v-if="!netError && !netLoading" #footer>
            <button class="btn danger" @click="saveNetwork">{{ t("applyNet") }}</button>
          </template>
        </Card>

        <!-- ---------------------------------------------------- firmware -->
        <Card :title="t('firmware')" :subtitle="`${t('current')}: ${state.info?.version || '–'}`" :icon="mdiChip" icon-class="warn">
          <p class="muted small" style="margin-top: 0">{{ t("firmwareHint") }}</p>
          <label class="upload">
            <Icon :path="mdiUpload" :size="18" /><span class="grow">{{ fwFile?.name || t("chooseFw") }}</span>
            <input type="file" accept=".lfu" @change="fwFile = ($event.target as HTMLInputElement).files?.[0] || null" />
          </label>
          <div v-if="fwProgress !== null" class="mt">
            <div class="progress"><div :style="{ width: `${fwProgress}%` }"></div></div>
            <div class="small muted mt">{{ fwStatus }}</div>
          </div>
          <template #footer>
            <button class="btn danger" :disabled="!fwFile || fwProgress !== null" @click="uploadFirmware">{{ t("installFw") }}</button>
          </template>
        </Card>

        <!-- ------------------------------------------------------ macros -->
        <Card :title="t('macros')" :icon="mdiScriptTextOutline">
          <p class="muted small" style="margin-top: 0">{{ t("macrosHint") }}</p>
          <div class="row wrap mb">
            <span v-for="m in state.info?.descriptor?.implementedMacros || []" :key="m" class="chip mono">{{ m }}</span>
          </div>
          <label class="upload">
            <Icon :path="mdiUpload" :size="18" /><span class="grow">{{ t("uploadMacro") }} (.xmf)</span>
            <input type="file" accept=".xmf" multiple @change="uploadMacro" />
          </label>
        </Card>

        <!-- ------------------------------------------------------- raw dali -->
        <Card :title="t('raw')" :icon="mdiConsole">
          <p class="muted small" style="margin-top: 0">{{ t("rawHint") }}</p>
          <RouterLink to="/bus" class="btn outline"><Icon :path="mdiConsole" :size="18" />{{ t("toCommands") }}</RouterLink>
        </Card>

        <!-- ------------------------------------------------------ cleanup -->
        <Card :title="t('cleanup')" :icon="mdiDeleteSweep" icon-class="err">
          <div class="list">
            <div class="list-item">
              <div class="grow"><div class="title">{{ t("delDevices") }}</div><div class="sub">{{ t("delDevicesHint") }}</div></div>
              <select v-if="lineCount > 1" v-model="delLine" style="width: 120px">
                <option :value="null">{{ t("allLines") }}</option>
                <option v-for="l in lineCount" :key="l" :value="l - 1">{{ t("line") }} {{ l - 1 }}</option>
              </select>
              <button class="btn danger outline sm" @click="deleteAll('devices')">{{ t("delete") }}</button>
            </div>
            <div class="list-item">
              <div class="grow"><div class="title">{{ t("delSensors") }}</div><div class="sub">{{ t("delDevicesHint") }}</div></div>
              <button class="btn danger outline sm" @click="deleteAll('sensors')">{{ t("delete") }}</button>
            </div>
            <div class="list-item">
              <div class="grow"><div class="title">{{ t("delZones") }}</div></div>
              <button class="btn danger outline sm" @click="deleteAll('zones')">{{ t("delete") }}</button>
            </div>
            <div class="list-item">
              <div class="grow"><div class="title">{{ t("delHistory") }}</div><div class="sub">{{ t("delHistoryHint") }}</div></div>
              <button class="btn danger outline sm" @click="clearHistory">{{ t("delete") }}</button>
            </div>
          </div>
        </Card>

        <!-- -------------------------------------------------------- reset -->
        <Card :title="t('reset')" :icon="mdiAlertOctagon" icon-class="err">
          <p style="margin-top: 0">{{ t("resetHint") }}</p>
          <ul class="muted small">
            <li>{{ t("reset1") }}</li>
            <li>{{ t("reset2") }}</li>
            <li>{{ t("reset3") }}</li>
          </ul>
          <template #footer>
            <button class="btn danger" @click="factoryReset"><Icon :path="mdiAlertOctagon" :size="18" />{{ t("resetBtn") }}</button>
          </template>
        </Card>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import {
  mdiAlertOctagon,
  mdiChip,
  mdiConsole,
  mdiDeleteSweep,
  mdiInformationOutline,
  mdiLan,
  mdiScriptTextOutline,
  mdiShieldAlertOutline,
  mdiUpload,
} from "@mdi/js";
import Card from "../components/Card.vue";
import Icon from "../components/Icon.vue";
import Toggle from "../components/Toggle.vue";
import { api, gw } from "../lib/api";
import { confirmDialog, run, setExpert, state, toast } from "../lib/store";
import { useT } from "../lib/i18n";

const t = useT({
  de: {
    title: "Expertenbereich",
    enableHint: "Diese Funktionen können die Anlage unbrauchbar machen. Aktiviere den Expertenmodus, um sie anzuzeigen.",
    enable: "Expertenmodus aktivieren",
    warning: "Achtung: Änderungen in diesem Bereich können die Erreichbarkeit des Gateways oder die komplette DALI-Konfiguration betreffen. Erstelle vorher eine Sicherung (System → Sicherung).",
    network: "Netzwerk",
    netUnavailable: "Die Netzwerkeinstellungen sind bei diesem Gerät nicht über die API verfügbar (z. B. WLAN-Variante).",
    dhcp: "Adresse per DHCP beziehen",
    ip: "IP-Adresse",
    mask: "Subnetzmaske",
    gatewayIp: "Standard-Gateway",
    dns: "DNS-Server (kommagetrennt)",
    fallback: "DHCP-Wiederholungen vor Fallback",
    fallbackHint: "Danach wird 169.254.0.1/16 verwendet (je Versuch 10 s)",
    applyNet: "Netzwerk übernehmen",
    confirmNet: "Netzwerkeinstellungen ändern? Bei falschen Werten ist das Gateway nicht mehr erreichbar und muss ggf. vor Ort zurückgesetzt werden.",
    netSaved: "Netzwerkeinstellungen gesendet – ggf. neue Adresse im Add-on eintragen",
    firmware: "Firmware-Update",
    current: "Installiert",
    firmwareHint: "Firmware-Dateien (.lfu) gibt es bei Lunatone. Während des Updates nicht die Stromversorgung trennen. Das Gateway startet danach neu.",
    chooseFw: "Firmware-Datei wählen (.lfu)",
    installFw: "Firmware installieren",
    confirmFw: "Firmware „{file}“ installieren? Das Gateway ist während des Updates einige Minuten nicht erreichbar.",
    fwUploading: "Übertrage… {p} %",
    fwInstalling: "Übertragen – das Gateway installiert und startet neu. Das kann einige Minuten dauern.",
    fwFailed: "Update fehlgeschlagen: {e}",
    macros: "DALI-Makros",
    macrosHint: "Vom Gateway unterstützte Makro-Nummern:",
    uploadMacro: "Makro-Datei hochladen",
    macroOk: "Makro hochgeladen",
    raw: "Rohe DALI-Befehle",
    rawHint: "16- und 24-Bit-Frames direkt auf den Bus senden, mit Adress- und Befehlsassistent.",
    toCommands: "Zu DALI-Bus → Befehle",
    cleanup: "Daten löschen",
    delDevices: "Alle Geräte aus dem Gateway löschen",
    delDevicesHint: "Die Betriebsgeräte behalten ihre Adressen – ein Scan findet sie wieder.",
    delSensors: "Alle DALI-Sensoren löschen",
    delZones: "Alle Zonen löschen",
    delHistory: "Add-on-Verlauf löschen",
    delHistoryHint: "Busmonitor, Statistiken, Ereignisse und Messwerte im Add-on",
    allLines: "Alle Linien",
    confirmDel: "Wirklich alle {what} löschen?",
    reset: "Werksreset",
    resetHint: "Setzt das Gateway auf Werkseinstellungen zurück:",
    reset1: "Löscht alle Automationen, Zonen und bekannten DALI-Geräte",
    reset2: "Setzt die Konfiguration des Gateways zurück",
    reset3: "Startet das Gateway automatisch neu",
    resetBtn: "Auf Werkseinstellungen zurücksetzen",
    confirmReset: "Das Gateway wird vollständig zurückgesetzt. Dieser Schritt kann nicht rückgängig gemacht werden.",
    resetDone: "Werksreset ausgelöst – das Gateway startet neu",
    wordNet: "NETZWERK",
    wordDel: "LÖSCHEN",
  },
  en: {
    title: "Expert area",
    enableHint: "These functions can break the installation. Enable expert mode to show them.",
    enable: "Enable expert mode",
    warning: "Caution: changes here can affect the reachability of the gateway or the complete DALI configuration. Create a backup first (System → Backup).",
    network: "Network",
    netUnavailable: "Network settings are not available through the API on this device (e.g. WLAN variant).",
    dhcp: "Obtain address via DHCP",
    ip: "IP address",
    mask: "Subnet mask",
    gatewayIp: "Default gateway",
    dns: "DNS servers (comma separated)",
    fallback: "DHCP retries before fallback",
    fallbackHint: "Then 169.254.0.1/16 is used (10 s per attempt)",
    applyNet: "Apply network",
    confirmNet: "Change network settings? With wrong values the gateway becomes unreachable and may need a local reset.",
    netSaved: "Network settings sent – update the address in the add-on if needed",
    firmware: "Firmware update",
    current: "Installed",
    firmwareHint: "Firmware files (.lfu) are provided by Lunatone. Do not disconnect power during the update. The gateway reboots afterwards.",
    chooseFw: "Choose firmware file (.lfu)",
    installFw: "Install firmware",
    confirmFw: "Install firmware “{file}”? The gateway is unreachable for a few minutes during the update.",
    fwUploading: "Uploading… {p} %",
    fwInstalling: "Uploaded – the gateway installs and reboots. This can take a few minutes.",
    fwFailed: "Update failed: {e}",
    macros: "DALI macros",
    macrosHint: "Macro numbers supported by the gateway:",
    uploadMacro: "Upload macro file",
    macroOk: "Macro uploaded",
    raw: "Raw DALI commands",
    rawHint: "Send 16 and 24 bit frames directly on the bus, with address and command assistant.",
    toCommands: "Go to DALI bus → Commands",
    cleanup: "Delete data",
    delDevices: "Delete all devices from the gateway",
    delDevicesHint: "Control gear keeps its addresses – a scan finds them again.",
    delSensors: "Delete all DALI sensors",
    delZones: "Delete all zones",
    delHistory: "Delete add-on history",
    delHistoryHint: "Bus monitor, statistics, events and measurements in the add-on",
    allLines: "All lines",
    confirmDel: "Really delete all {what}?",
    reset: "Factory reset",
    resetHint: "Resets the gateway to factory settings:",
    reset1: "Deletes all automations, zones and known DALI devices",
    reset2: "Resets the gateway configuration",
    reset3: "Reboots the gateway automatically",
    resetBtn: "Reset to factory settings",
    confirmReset: "The gateway will be completely reset. This cannot be undone.",
    resetDone: "Factory reset triggered – the gateway reboots",
    wordNet: "NETWORK",
    wordDel: "DELETE",
  },
});

const lineCount = computed(() => Number(state.info?.descriptor?.lines ?? 1));

// ------------------------------------------------------------ network
const net = reactive<any>({});
const netForm = reactive<any>({ dhcp: true, ip_address: "", subnet_mask: "", gateway: "", nameservers: [], static_fallback_retries: 0 });
const netError = ref("");
const netLoading = ref(true);
const dnsText = computed({
  get: () => (netForm.nameservers || []).join(", "),
  set: (v: string) => (netForm.nameservers = v.split(",").map((s) => s.trim()).filter(Boolean)),
});
async function loadNetwork() {
  netLoading.value = true;
  try {
    const r = await gw.get("/ethernet");
    Object.assign(net, r);
    Object.assign(netForm, r.settings || {});
    netError.value = "";
  } catch (e: any) {
    netError.value = e.message;
  }
  netLoading.value = false;
}
async function saveNetwork() {
  if (!(await confirmDialog({ title: t("network"), message: t("confirmNet"), danger: true, typeToConfirm: t("wordNet"), confirmText: t("applyNet") }))) return;
  await run(() => gw.post("/ethernet", { ...netForm }), t("netSaved"));
}

// ----------------------------------------------------------- firmware
const fwFile = ref<File | null>(null);
const fwProgress = ref<number | null>(null);
const fwStatus = ref("");
async function uploadFirmware() {
  const file = fwFile.value;
  if (!file) return;
  if (!(await confirmDialog({ title: t("firmware"), message: t("confirmFw", { file: file.name }), danger: true, typeToConfirm: "UPDATE", confirmText: t("installFw") }))) return;
  const fd = new FormData();
  fd.append("file", file, file.name);
  fwProgress.value = 0;
  const xhr = new XMLHttpRequest();
  xhr.open("POST", "api/gw/firmware/upload");
  xhr.setRequestHeader("X-Expert-Confirm", "yes");
  xhr.upload.onprogress = (e) => {
    if (e.lengthComputable) {
      fwProgress.value = Math.round((e.loaded / e.total) * 100);
      fwStatus.value = t("fwUploading", { p: fwProgress.value });
    }
  };
  xhr.onload = () => {
    if (xhr.status < 400) {
      fwProgress.value = 100;
      fwStatus.value = t("fwInstalling");
    } else {
      fwStatus.value = t("fwFailed", { e: `${xhr.status} ${xhr.responseText.slice(0, 200)}` });
      setTimeout(() => (fwProgress.value = null), 8000);
    }
  };
  xhr.onerror = () => {
    fwStatus.value = t("fwFailed", { e: "network" });
    setTimeout(() => (fwProgress.value = null), 8000);
  };
  xhr.send(fd);
}

// ------------------------------------------------------------- macros
async function uploadMacro(ev: Event) {
  const input = ev.target as HTMLInputElement;
  const files = Array.from(input.files || []);
  input.value = "";
  if (!files.length) return;
  const fd = new FormData();
  for (const f of files) fd.append("files", f, f.name);
  await run(() => api("POST", "gw/upload/daliMacro", fd), t("macroOk"));
}

// ------------------------------------------------------------ cleanup
const delLine = ref<number | null>(null);
async function deleteAll(what: "devices" | "sensors" | "zones") {
  const label = { devices: t("devices"), sensors: "DALI-Sensoren", zones: t("zones") }[what];
  if (!(await confirmDialog({ title: t("delete"), message: t("confirmDel", { what: label }), danger: true, typeToConfirm: t("wordDel"), confirmText: t("delete") }))) return;
  const q = what !== "zones" && delLine.value !== null ? `?line=${delLine.value}` : "";
  await run(() => gw.del(`/${what}${q}`), t("saved"));
}
async function clearHistory() {
  if (!(await confirmDialog({ title: t("delHistory"), message: t("delHistoryHint"), danger: true, confirmText: t("delete") }))) return;
  await run(() => api("DELETE", "history?what=all"), t("saved"));
}
async function factoryReset() {
  if (!(await confirmDialog({ title: t("reset"), message: t("confirmReset"), danger: true, typeToConfirm: "RESET", confirmText: t("resetBtn") }))) return;
  const ok = await run(() => gw.del("/reset", { "X-Expert-Confirm": "yes" }));
  if (ok !== undefined) toast(t("resetDone"), "success", 8000);
}

onMounted(() => {
  if (state.expert) loadNetwork();
});
</script>

<style scoped>
.upload { display: flex; align-items: center; gap: 10px; padding: 10px 12px; border: 1px dashed var(--divider); border-radius: 10px; cursor: pointer; color: var(--text2); }
.upload:hover { border-color: var(--primary); color: var(--primary); }
.upload input { display: none; }
</style>
