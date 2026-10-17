<template>
  <div class="scan">
    <div class="grid scan-grid">
      <!-- current / last scan -->
      <Card :title="running ? t('running') : t('lastScan')" :icon="mdiRadar" :icon-class="statusMeta.cls" :subtitle="scan?.id ? `ID ${scan.id}` : ''">
        <template #actions>
          <button class="btn icon sm" :title="t('refresh')" :disabled="loading" @click="load()">
            <span v-if="loading" class="spinner mini"></span>
            <Icon v-else :path="mdiRefresh" :size="18" />
          </button>
        </template>

        <div v-if="!scan && loading" class="center pad"><span class="spinner"></span></div>
        <div v-else-if="!scan" class="muted">{{ error || t("noScan") }}</div>
        <template v-else>
          <div class="overall">
            <div class="ring" :style="{ '--p': progress, '--c': ringColor }">
              <div class="ring-inner">
                <div class="ring-val">{{ Math.round(progress) }}<small>%</small></div>
              </div>
            </div>
            <div class="grow col">
              <div class="row wrap">
                <span class="chip" :class="statusMeta.chip">
                  <span v-if="running" class="spinner mini"></span>
                  {{ statusMeta.label }}
                </span>
                <span v-if="running && elapsed" class="small muted">{{ t("elapsed", { t: elapsed }) }}</span>
              </div>
              <div class="kpis">
                <div>
                  <div class="kpi-val">{{ scan.found ?? 0 }}</div>
                  <div class="small muted">{{ t("foundGear") }}</div>
                </div>
                <div>
                  <div class="kpi-val">{{ scan.foundSensors ?? 0 }}</div>
                  <div class="small muted">{{ t("foundSensors") }}</div>
                </div>
              </div>
            </div>
          </div>

          <div v-if="scan.status === 'bus error'" class="banner err mt">
            <Icon :path="mdiAlertCircle" :size="18" />
            <div>{{ t("busErrorHint") }}</div>
          </div>
          <div v-else-if="scan.status === 'done' && !running" class="banner info mt">
            <Icon :path="mdiCheckCircle" :size="18" />
            <div>
              {{ t("doneHint", { n: scan.found ?? 0, s: scan.foundSensors ?? 0 }) }}
              <RouterLink to="/devices">{{ t("toDevices") }}</RouterLink>
              ·
              <RouterLink to="/sensors">{{ t("toSensors") }}</RouterLink>
            </div>
          </div>

          <div class="section-title">{{ t("perLine") }}</div>
          <div v-if="!lines.length" class="muted small">{{ t("noLineData") }}</div>
          <div v-for="l in lines" :key="l.line" class="line-row">
            <div class="row between">
              <div class="row">
                <b>{{ t("line") }} {{ l.line }}</b>
                <span class="chip" :class="lineMeta(l.scanState).chip">{{ lineMeta(l.scanState).label }}</span>
              </div>
              <span class="mono small">{{ Math.round(l.progress ?? 0) }} %</span>
            </div>
            <div class="progress mt-s" :class="{ anim: isLineRunning(l.scanState) }">
              <div :style="{ width: `${Math.max(0, Math.min(100, l.progress ?? 0))}%`, background: lineMeta(l.scanState).color }"></div>
            </div>
            <div class="row wrap small muted line-stats">
              <span>{{ t("foundGear") }}: <b class="txt">{{ l.found ?? 0 }}</b></span>
              <span>{{ t("foundSensors") }}: <b class="txt">{{ l.foundSensors ?? 0 }}</b></span>
              <span :title="t('scannedHint')">{{ t("scanned") }}: <b class="txt">{{ l.scanned ?? 0 }}</b></span>
              <span :title="t('addressedHint')">{{ t("addressed") }}: <b class="txt">{{ l.addressed ?? 0 }}</b></span>
            </div>
          </div>
        </template>

        <template v-if="running" #footer>
          <button class="btn danger outline" :disabled="busy" @click="cancel">
            <Icon :path="mdiStop" :size="18" />{{ t("cancelScan") }}
          </button>
        </template>
      </Card>

      <!-- start a new scan -->
      <Card :title="t('newScan')" :icon="mdiMagnifyScan" :subtitle="t('newScanSub')">
        <div class="modes" role="radiogroup">
          <label v-for="m in modes" :key="m.id" class="mode" :class="{ active: mode === m.id, danger: m.id === 'new' }">
            <input v-model="mode" type="radio" name="scan-mode" :value="m.id" :disabled="running" />
            <span class="icon-bubble" :class="m.cls"><Icon :path="m.icon" :size="20" /></span>
            <span class="mode-body">
              <span class="row wrap mode-title">
                <b>{{ m.title }}</b>
                <span class="chip" :class="m.chipCls">{{ m.tag }}</span>
              </span>
              <span class="small muted">{{ m.desc }}</span>
            </span>
          </label>
        </div>

        <div class="section-title">{{ t("lines") }}</div>
        <div class="row wrap">
          <button
            v-for="l in lineIds"
            :key="l"
            class="chip clickable line-chip"
            :class="{ primary: selLines.includes(l) }"
            :disabled="running"
            @click="toggleLine(l)"
          >
            <Icon :path="selLines.includes(l) ? mdiCheckboxMarked : mdiCheckboxBlankOutline" :size="16" />
            {{ t("line") }} {{ l }}
            <span class="faint">· {{ devicesOn(l) }} {{ t("devicesShort") }}</span>
          </button>
        </div>

        <div v-if="mode === 'new'" class="banner err mt">
          <Icon :path="mdiAlertOctagon" :size="18" />
          <div>{{ t("newWarn") }}</div>
        </div>
        <div v-else class="banner info mt small">
          <Icon :path="mdiInformationOutline" :size="18" />
          <div>{{ t("generalHint") }}</div>
        </div>

        <template #footer>
          <button class="btn" :class="{ danger: mode === 'new' }" :disabled="running || busy || !selLines.length || !online" @click="startScan">
            <span v-if="busy" class="spinner mini light"></span>
            <Icon v-else :path="mdiPlayCircle" :size="18" />
            {{ t("startScan") }}
          </button>
        </template>
      </Card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onActivated, onBeforeUnmount, onDeactivated, onMounted, ref, watch } from "vue";
import {
  mdiAlertCircle,
  mdiAlertOctagon,
  mdiCheckCircle,
  mdiCheckboxBlankOutline,
  mdiCheckboxMarked,
  mdiEyeOutline,
  mdiInformationOutline,
  mdiMagnifyScan,
  mdiNewBox,
  mdiPlayCircle,
  mdiRadar,
  mdiRefresh,
  mdiStop,
  mdiTarget,
} from "@mdi/js";
import Card from "../Card.vue";
import Icon from "../Icon.vue";
import { gw } from "../../lib/api";
import { confirmDialog, gatewayOnline, run, state } from "../../lib/store";
import { useT } from "../../lib/i18n";

const t = useT({
  de: {
    running: "Scan läuft",
    lastScan: "Letzter Scan",
    noScan: "Es wurde noch kein Scan durchgeführt.",
    elapsed: "seit {t}",
    foundGear: "Betriebsgeräte",
    foundSensors: "Steuergeräte / Sensoren",
    perLine: "Fortschritt je Linie",
    noLineData: "Keine Liniendaten vorhanden.",
    scanned: "Gescannt",
    scannedHint: "Anzahl der geprüften Adressen",
    addressed: "Adressiert",
    addressedHint: "Anzahl der bearbeiteten Adressen (Betriebsgeräte und Steuergeräte)",
    cancelScan: "Scan abbrechen",
    cancelled: "Scan abgebrochen",
    newScan: "Neuen Scan starten",
    newScanSub: "Sucht DALI-Geräte auf den gewählten Linien",
    lines: "Linien",
    devicesShort: "Geräte",
    startScan: "Scan starten",
    started: "Scan gestartet",
    modeNormal: "Normaler Scan",
    modeNormalTag: "empfohlen",
    modeNormalDesc: "Findet neue und unadressierte Geräte und vergibt freie Kurzadressen. Bestehende Adressen, Gruppen und Szenen bleiben erhalten.",
    modeNew: "Neuinstallation",
    modeNewTag: "destruktiv",
    modeNewDesc: "Löscht ALLE Kurzadressen und adressiert sämtliche Geräte neu. Nur bei einer komplett neuen Anlage verwenden.",
    modeRead: "Ohne Adressierung",
    modeReadTag: "nur lesen",
    modeReadDesc: "Liest nur die bereits adressierten Geräte ein. Es werden keine Adressen verändert – ideal zum Abgleich.",
    newWarn: "Achtung: Bei einer Neuinstallation erhalten alle Geräte neue Kurzadressen. Gruppen, Szenen, Zonen und Automationen, die sich auf Adressen beziehen, müssen anschließend neu eingerichtet werden.",
    generalHint: "Während des Scans ist der Bus stark ausgelastet – Schaltbefehle können verzögert ausgeführt werden. Ein Scan dauert je nach Anzahl der Geräte einige Minuten.",
    confirmTitle: "Scan starten?",
    confirmNormal: "Der Bus wird nach neuen Geräten durchsucht ({lines}). Bestehende Adressen bleiben erhalten.",
    confirmRead: "Die adressierten Geräte werden eingelesen ({lines}). Es werden keine Adressen verändert.",
    confirmNewTitle: "Neuinstallation – alle Adressen neu vergeben?",
    confirmNew: "ALLE Geräte auf {lines} verlieren ihre Kurzadresse und werden neu adressiert. Gruppen, Szenen und Automationen können danach nicht mehr stimmen.\n\nDieser Vorgang kann nicht rückgängig gemacht werden.",
    confirmWord: "NEUINSTALLATION",
    confirmStart: "Scan starten",
    confirmCancelTitle: "Scan abbrechen?",
    confirmCancel: "Der laufende Scan wird abgebrochen. Bereits gefundene Geräte bleiben erhalten.",
    busErrorHint: "Busfehler: Die Linie hat keine oder zu geringe Busspannung. Busversorgung und Verkabelung prüfen (Tab „Linien“).",
    doneHint: "Scan abgeschlossen: {n} Betriebsgeräte und {s} Steuergeräte gefunden.",
    toDevices: "Zu den Geräten",
    toSensors: "Zu den Sensoren",
    st_not_started: "Nicht gestartet",
    st_cancelled: "Abgebrochen",
    st_done: "Abgeschlossen",
    st_addressing: "Adressierung läuft",
    st_in_progress: "Suche läuft",
    st_bus_error: "Busfehler",
    ls_idle: "Bereit",
    ls_cancelled: "Abgebrochen",
    ls_scanning: "Suche",
    ls_addressing: "Adressierung",
    ls_done: "Fertig",
    ls_skipped: "Übersprungen",
    ls_error: "Fehler",
  },
  en: {
    running: "Scan running",
    lastScan: "Last scan",
    noScan: "No scan has been performed yet.",
    elapsed: "for {t}",
    foundGear: "Control gear",
    foundSensors: "Control devices / sensors",
    perLine: "Progress per line",
    noLineData: "No line data available.",
    scanned: "Scanned",
    scannedHint: "Number of addresses checked",
    addressed: "Addressed",
    addressedHint: "Number of addresses processed (control gear and control devices)",
    cancelScan: "Cancel scan",
    cancelled: "Scan cancelled",
    newScan: "Start a new scan",
    newScanSub: "Searches DALI devices on the selected lines",
    lines: "Lines",
    devicesShort: "devices",
    startScan: "Start scan",
    started: "Scan started",
    modeNormal: "Normal scan",
    modeNormalTag: "recommended",
    modeNormalDesc: "Finds new and unaddressed devices and assigns free short addresses. Existing addresses, groups and scenes are kept.",
    modeNew: "New installation",
    modeNewTag: "destructive",
    modeNewDesc: "Deletes ALL short addresses and re-addresses every device. Only use this for a completely new installation.",
    modeRead: "Without addressing",
    modeReadTag: "read only",
    modeReadDesc: "Only reads the devices that already have an address. No addresses are changed – ideal for reconciling.",
    newWarn: "Warning: with a new installation every device gets a new short address. Groups, scenes, zones and automations referring to addresses must be set up again afterwards.",
    generalHint: "While scanning, the bus is heavily loaded – switching commands may be delayed. Depending on the number of devices a scan takes a few minutes.",
    confirmTitle: "Start scan?",
    confirmNormal: "The bus will be searched for new devices ({lines}). Existing addresses are kept.",
    confirmRead: "The addressed devices will be read ({lines}). No addresses are changed.",
    confirmNewTitle: "New installation – re-address everything?",
    confirmNew: "ALL devices on {lines} lose their short address and are addressed again. Groups, scenes and automations may no longer match afterwards.\n\nThis cannot be undone.",
    confirmWord: "NEW INSTALLATION",
    confirmStart: "Start scan",
    confirmCancelTitle: "Cancel scan?",
    confirmCancel: "The running scan will be cancelled. Devices found so far are kept.",
    busErrorHint: "Bus error: the line has no or too little bus voltage. Check the bus power supply and wiring (tab “Lines”).",
    doneHint: "Scan finished: {n} control gear and {s} control devices found.",
    toDevices: "Go to devices",
    toSensors: "Go to sensors",
    st_not_started: "Not started",
    st_cancelled: "Cancelled",
    st_done: "Finished",
    st_addressing: "Addressing",
    st_in_progress: "Searching",
    st_bus_error: "Bus error",
    ls_idle: "Idle",
    ls_cancelled: "Cancelled",
    ls_scanning: "Searching",
    ls_addressing: "Addressing",
    ls_done: "Done",
    ls_skipped: "Skipped",
    ls_error: "Error",
  },
});

const rest = ref<any>(null);
const restAt = ref(0);
const liveAt = ref(0);
const loading = ref(false);
const busy = ref(false);
const error = ref("");
const online = computed(() => gatewayOnline());

watch(
  () => state.scan,
  () => (liveAt.value = Date.now()),
  { deep: true },
);

/** Live websocket updates (state.scan) win when they are newer than the last REST poll. */
const scan = computed<any>(() => {
  const live = state.scan && Object.keys(state.scan).length ? state.scan : null;
  if (!live) return rest.value;
  if (!rest.value) return live;
  if (live.id && rest.value.id && live.id !== rest.value.id) return liveAt.value >= restAt.value ? live : rest.value;
  return liveAt.value >= restAt.value ? { ...rest.value, ...live } : rest.value;
});

const RUNNING = ["in progress", "addressing"];
const LINE_RUNNING = ["scanning", "addressing"];
const isLineRunning = (s: string) => LINE_RUNNING.includes(s);
const lines = computed<any[]>(() => (Array.isArray(scan.value?.lines) ? [...scan.value.lines].sort((a, b) => a.line - b.line) : []));
const running = computed(() => RUNNING.includes(scan.value?.status) || lines.value.some((l) => isLineRunning(l.scanState)));
const progress = computed(() => Math.max(0, Math.min(100, Number(scan.value?.progress) || 0)));

const statusMeta = computed(() => {
  const s = scan.value?.status || "not started";
  const key = `st_${s.replace(/\s+/g, "_")}`;
  const map: Record<string, { chip: string; cls: string }> = {
    done: { chip: "ok", cls: "ok" },
    cancelled: { chip: "warn", cls: "warn" },
    "bus error": { chip: "err", cls: "err" },
    "in progress": { chip: "primary", cls: "" },
    addressing: { chip: "primary", cls: "" },
    "not started": { chip: "", cls: "off" },
  };
  return { label: t(key), ...(map[s] || { chip: "", cls: "off" }) };
});
const ringColor = computed(() =>
  scan.value?.status === "done" ? "var(--success)" : scan.value?.status === "bus error" ? "var(--error)" : scan.value?.status === "cancelled" ? "var(--warning)" : "var(--primary)",
);

function lineMeta(s: string) {
  const map: Record<string, { chip: string; color: string }> = {
    done: { chip: "ok", color: "var(--success)" },
    scanning: { chip: "primary", color: "var(--primary)" },
    addressing: { chip: "primary", color: "var(--accent)" },
    cancelled: { chip: "warn", color: "var(--warning)" },
    error: { chip: "err", color: "var(--error)" },
    skipped: { chip: "", color: "var(--text3)" },
    idle: { chip: "", color: "var(--text3)" },
  };
  return { label: t(`ls_${s || "idle"}`), ...(map[s] || map.idle) };
}

// elapsed time while running
const runningSince = ref<number | null>(null);
const now = ref(Date.now());
watch(
  running,
  (r) => {
    runningSince.value = r ? runningSince.value ?? Date.now() : null;
  },
  { immediate: true },
);
const elapsed = computed(() => {
  if (!runningSince.value) return "";
  const s = Math.max(0, Math.round((now.value - runningSince.value) / 1000));
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")} min`;
});

async function load(silent = false) {
  if (!silent) loading.value = true;
  try {
    rest.value = await gw.get("/dali/scan");
    restAt.value = Date.now();
    error.value = "";
  } catch (e: any) {
    error.value = e?.message || String(e);
  } finally {
    loading.value = false;
  }
}

// poll every 2 s while a scan is running
let poll = 0;
let clock = 0;
let active = true;
function syncPolling() {
  const want = running.value && active;
  if (want && !poll) {
    poll = window.setInterval(() => load(true), 2000);
    clock = window.setInterval(() => (now.value = Date.now()), 1000);
  } else if (!want && poll) {
    clearInterval(poll);
    clearInterval(clock);
    poll = 0;
    clock = 0;
  }
}
watch(running, syncPolling);
let firstActivation = true;
onMounted(() => load().then(syncPolling));
onActivated(() => {
  active = true;
  // KeepAlive also fires this right after mount
  if (firstActivation) {
    firstActivation = false;
    return;
  }
  load(true).then(syncPolling);
});
onDeactivated(() => {
  active = false;
  syncPolling();
});
onBeforeUnmount(() => {
  clearInterval(poll);
  clearInterval(clock);
});

// ------------------------------------------------------------ start / cancel
type Mode = "normal" | "new" | "readonly";
const mode = ref<Mode>("normal");
const modes = computed(() => [
  { id: "normal" as Mode, icon: mdiTarget, cls: "", title: t("modeNormal"), tag: t("modeNormalTag"), chipCls: "ok", desc: t("modeNormalDesc") },
  { id: "readonly" as Mode, icon: mdiEyeOutline, cls: "off", title: t("modeRead"), tag: t("modeReadTag"), chipCls: "", desc: t("modeReadDesc") },
  { id: "new" as Mode, icon: mdiNewBox, cls: "err", title: t("modeNew"), tag: t("modeNewTag"), chipCls: "err", desc: t("modeNewDesc") },
]);

const lineIds = computed(() => {
  const n = Number(state.info?.descriptor?.lines) || Object.keys(state.info?.lines || {}).length || 1;
  return Array.from({ length: n }, (_, i) => i);
});
const selLines = ref<number[]>([]);
watch(
  lineIds,
  (ids) => {
    selLines.value = selLines.value.length ? selLines.value.filter((l) => ids.includes(l)) : [...ids];
    if (!selLines.value.length) selLines.value = [...ids];
  },
  { immediate: true },
);
function toggleLine(l: number) {
  selLines.value = selLines.value.includes(l) ? selLines.value.filter((x) => x !== l) : [...selLines.value, l].sort();
}
function devicesOn(l: number) {
  return Object.values(state.devices).filter((d) => (d.line ?? 0) === l).length;
}

async function startScan() {
  const linesText = selLines.value.map((l) => `${t("line")} ${l}`).join(", ");
  const ok =
    mode.value === "new"
      ? await confirmDialog({
          title: t("confirmNewTitle"),
          message: t("confirmNew", { lines: linesText }),
          danger: true,
          typeToConfirm: t("confirmWord"),
          confirmText: t("confirmStart"),
        })
      : await confirmDialog({
          title: t("confirmTitle"),
          message: mode.value === "readonly" ? t("confirmRead", { lines: linesText }) : t("confirmNormal", { lines: linesText }),
          confirmText: t("confirmStart"),
        });
  if (!ok) return;
  busy.value = true;
  const res = await run(
    () =>
      gw.post("/dali/scan", {
        newInstallation: mode.value === "new",
        noAddressing: mode.value === "readonly",
        useLines: [...selLines.value],
      }),
    t("started"),
  );
  busy.value = false;
  if (res) {
    rest.value = res;
    restAt.value = Date.now();
    runningSince.value = Date.now();
  }
  await load(true);
  syncPolling();
}

async function cancel() {
  const ok = await confirmDialog({ title: t("confirmCancelTitle"), message: t("confirmCancel"), confirmText: t("cancelScan"), danger: true });
  if (!ok) return;
  busy.value = true;
  const res = await run(() => gw.post("/dali/scan/cancel"), t("cancelled"));
  busy.value = false;
  if (res) {
    rest.value = res;
    restAt.value = Date.now();
  }
  await load(true);
}
</script>

<style scoped>
.scan-grid { grid-template-columns: repeat(auto-fit, minmax(380px, 1fr)); align-items: start; }
.pad { padding: 30px 0; }
.overall { display: flex; gap: 18px; align-items: center; }
.ring {
  --p: 0; --c: var(--primary);
  width: 104px; height: 104px; border-radius: 50%; flex-shrink: 0;
  background: conic-gradient(var(--c) calc(var(--p) * 1%), var(--bg2) 0);
  display: flex; align-items: center; justify-content: center; transition: background .4s;
}
.ring-inner { width: 82px; height: 82px; border-radius: 50%; background: var(--card); display: flex; align-items: center; justify-content: center; }
.ring-val { font-size: 24px; font-weight: 500; }
.ring-val small { font-size: 13px; color: var(--text2); margin-left: 1px; }
.kpis { display: flex; gap: 28px; margin-top: 6px; }
.kpi-val { font-size: 22px; font-weight: 500; line-height: 1.1; }
.line-row { padding: 10px 0; border-bottom: 1px solid var(--divider); }
.line-row:last-child { border-bottom: 0; }
.mt-s { margin-top: 6px; }
.line-stats { gap: 4px 14px; margin-top: 6px; }
.txt { color: var(--text); font-weight: 500; }
.progress.anim > div { background-image: linear-gradient(45deg, rgba(255,255,255,.22) 25%, transparent 25%, transparent 50%, rgba(255,255,255,.22) 50%, rgba(255,255,255,.22) 75%, transparent 75%); background-size: 16px 16px; animation: stripes 1s linear infinite; }
@keyframes stripes { to { background-position: 16px 0; } }
.modes { display: flex; flex-direction: column; gap: 8px; }
.mode { position: relative; display: flex; gap: 12px; align-items: flex-start; padding: 12px; border-radius: 12px; border: 1px solid var(--divider); cursor: pointer; transition: border-color .15s, background .15s; }
.mode:focus-within { box-shadow: 0 0 0 2px var(--primary-soft); }
.mode:hover { background: var(--hover); }
.mode input { position: absolute; opacity: 0; pointer-events: none; }
.mode.active { border-color: var(--primary); background: var(--primary-soft); }
.mode.active.danger { border-color: var(--error); background: color-mix(in srgb, var(--error) 8%, transparent); }
.mode-body { display: flex; flex-direction: column; gap: 3px; min-width: 0; }
.mode-title { gap: 8px; }
.line-chip { border: 0; font-family: inherit; }
.line-chip:disabled { opacity: .5; cursor: not-allowed; }
.spinner.mini { width: 14px; height: 14px; }
.spinner.light { border-color: rgba(255,255,255,.35); border-top-color: #fff; }
@media (max-width: 700px) {
  .scan-grid { grid-template-columns: 1fr; }
  .overall { gap: 14px; }
  .ring { width: 88px; height: 88px; }
  .ring-inner { width: 70px; height: 70px; }
}
</style>
