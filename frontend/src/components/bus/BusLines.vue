<template>
  <div class="lines">
    <div class="row wrap head-row">
      <span class="small muted">
        {{ updatedAt ? t("updated", { t: fmtTime(updatedAt / 1000, lang, false) }) : t("loading") }} · {{ t("autoRefresh") }}
      </span>
      <span class="grow"></span>
      <button class="btn outline sm" :disabled="loading" @click="load()">
        <span v-if="loading" class="spinner mini"></span>
        <Icon v-else :path="mdiRefresh" :size="16" />{{ t("refresh") }}
      </button>
    </div>

    <div class="grid line-grid">
      <Card
        v-for="l in lineIds"
        :key="l"
        :title="`${t('line')} ${l}`"
        :subtitle="meta(l).label"
        :icon="meta(l).icon"
        :icon-class="meta(l).cls"
      >
        <template #actions>
          <span class="chip" :class="meta(l).chip">{{ meta(l).short }}</span>
        </template>

        <div v-if="errors[l]" class="banner err small">
          <Icon :path="mdiAlertCircle" :size="18" />
          <div>{{ t("readError") }}: {{ errors[l] }}</div>
        </div>
        <div v-else class="banner small" :class="meta(l).banner">
          <Icon :path="meta(l).cls === 'ok' ? mdiCheckCircle : mdiInformationOutline" :size="18" />
          <div>{{ meta(l).explain }}</div>
        </div>

        <div class="stats">
          <div class="stat-box">
            <div class="sv">{{ lineDevices(l).length }}</div>
            <div class="sl">{{ t("gear") }}</div>
          </div>
          <div class="stat-box" :class="{ bad: unreachable(l) > 0 }">
            <div class="sv">{{ unreachable(l) }}</div>
            <div class="sl">{{ t("unreachable") }}</div>
          </div>
          <div class="stat-box" :class="{ warn: failing(l) > 0 }">
            <div class="sv">{{ failing(l) }}</div>
            <div class="sl">{{ t("failures") }}</div>
          </div>
          <div class="stat-box">
            <div class="sv">{{ sensorsOn(l) }}</div>
            <div class="sl">{{ t("sensors") }}</div>
          </div>
          <div class="stat-box" :title="t('framesHint')">
            <div class="sv">{{ framesLastMin[l] ?? 0 }}</div>
            <div class="sl">{{ t("framesMin") }}</div>
          </div>
        </div>

        <div class="section-title">{{ t("flags") }}</div>
        <div class="flags">
          <div v-for="f in flagList(l)" :key="f.key" class="flag" :class="{ on: f.value }" :title="f.desc">
            <span class="dot" :class="f.value ? f.sev : 'ok'"></span>
            <div class="grow">
              <div class="small flag-label">{{ f.label }}</div>
              <div v-if="f.value" class="faint small">{{ f.desc }}</div>
            </div>
            <span class="small mono" :class="f.value ? 'b' : 'faint'">{{ f.value === undefined ? "–" : f.value ? t("yes") : t("no") }}</span>
          </div>
        </div>

        <div class="section-title row between">
          <span>{{ t("addressMap") }}</span>
          <span class="faint small norm">{{ t("used", { n: lineDevices(l).length }) }}</span>
        </div>
        <div class="amap">
          <div v-for="a in 64" :key="a" class="cell" :class="cellClass(l, a - 1)" :title="cellTitle(l, a - 1)">
            {{ a - 1 }}
          </div>
        </div>
        <div class="row wrap legend small muted">
          <span><i class="lg ok"></i>{{ t("lgOk") }}</span>
          <span><i class="lg lit"></i>{{ t("lgOn") }}</span>
          <span><i class="lg warn"></i>{{ t("lgFail") }}</span>
          <span><i class="lg err"></i>{{ t("lgUnreach") }}</span>
          <span><i class="lg"></i>{{ t("lgFree") }}</span>
        </div>

        <template v-if="lineInfo(l)?.device?.serial">
          <div class="section-title">{{ t("lineDevice") }}</div>
          <div class="kv small">
            <span>{{ t("devType") }}</span>
            <span>{{ lineInfo(l).device.deviceType }} – {{ DALI_TYPES[lineInfo(l).device.deviceType]?.[lang] ?? "?" }}</span>
            <span>{{ t("serial") }}</span><span class="mono">{{ lineInfo(l).device.serial }}</span>
            <span>GTIN</span><span class="mono">{{ lineInfo(l).device.gtin }}</span>
            <span>{{ t("article") }}</span><span class="mono">{{ lineInfo(l).device.articleNumber }}</span>
            <span>{{ t("production") }}</span>
            <span>{{ t("week") }} {{ lineInfo(l).device.productionWeek }} / {{ lineInfo(l).device.productionYear }}</span>
          </div>
        </template>
      </Card>
    </div>

    <Card :title="t('iface')" :icon="mdiRouterNetwork" :subtitle="state.info?.version ? `Firmware ${state.info.version}` : ''" class="mt">
      <div class="kv small iface">
        <span>{{ t("lineCount") }}</span><span>{{ desc.lines ?? "–" }}</span>
        <span>{{ t("protocol") }}</span><span>{{ desc.protocolVersionMajor ?? "–" }}.{{ desc.protocolVersionMinor ?? "–" }}</span>
        <span>{{ t("buffer") }}</span><span>{{ desc.bufferSize ?? "–" }} {{ t("frames") }}</span>
        <span>{{ t("maxFrame") }}</span><span>{{ desc.maxYnFrameSize ?? "–" }}</span>
        <span>{{ t("tick") }}</span><span>{{ desc.tickResolution ?? "–" }}</span>
        <span>{{ t("psu") }}</span><span>{{ desc.powerSupplyImplemented === undefined ? "–" : desc.powerSupplyImplemented ? t("yes") : t("no") }}</span>
        <span>{{ t("macros") }}</span><span>{{ (desc.implementedMacros || []).length }}</span>
      </div>
    </Card>
  </div>
</template>

<script setup lang="ts">
import { computed, onActivated, onBeforeUnmount, onDeactivated, onMounted, reactive, ref, toRaw, watch } from "vue";
import {
  mdiAlertCircle,
  mdiCheckCircle,
  mdiFlashTriangle,
  mdiHelpCircleOutline,
  mdiInformationOutline,
  mdiPowerPlug,
  mdiPowerPlugOff,
  mdiRefresh,
  mdiRouterNetwork,
} from "@mdi/js";
import Card from "../Card.vue";
import Icon from "../Icon.vue";
import { gw } from "../../lib/api";
import { state } from "../../lib/store";
import { lang, useT } from "../../lib/i18n";
import { DALI_TYPES, fmtTime } from "../../lib/dali";

const t = useT({
  de: {
    updated: "Stand {t}",
    autoRefresh: "aktualisiert alle 15 s",
    readError: "Status konnte nicht gelesen werden",
    st_ok: "Busspannung vorhanden",
    st_ok_short: "OK",
    st_ok_explain: "Die Linie ist versorgt und arbeitet normal.",
    st_lowPower: "Busspannung zu niedrig",
    st_lowPower_short: "Niedrige Spannung",
    st_lowPower_explain: "Die Busspannung ist zu gering. Busnetzteil, Leitungslänge/-querschnitt und die Anzahl der Teilnehmer prüfen (max. 250 mA Busstrom, ≤ 2 V Spannungsabfall).",
    st_noPower: "Keine Busspannung",
    st_noPower_short: "Keine Spannung",
    st_noPower_explain: "Auf der Linie liegt keine Busspannung an. Ist ein Busnetzteil vorhanden und eingeschaltet? Kurzschluss oder Verpolung der DALI-Leitung prüfen.",
    st_notReachable: "Linie nicht erreichbar",
    st_notReachable_short: "Nicht erreichbar",
    st_notReachable_explain: "Die Linien-Schnittstelle des Gateways antwortet nicht. Gateway neu starten; bleibt der Fehler bestehen, den Hersteller-Support kontaktieren.",
    st_unknown: "Status unbekannt",
    st_unknown_short: "–",
    st_unknown_explain: "Der Linienstatus wurde noch nicht gelesen.",
    gear: "Geräte",
    unreachable: "Nicht erreichbar",
    failures: "Mit Fehler",
    sensors: "Sensoren",
    framesMin: "Frames/min",
    framesHint: "Empfangene Frames auf dieser Linie in der letzten Minute (Live-Monitor)",
    flags: "Linienzustand",
    f_busVoltageDown: "Busspannung ausgefallen",
    f_busVoltageDown_d: "Die Busspannung ist zusammengebrochen – alle Geräte gehen in den System-Failure-Level.",
    f_initializeMode: "Initialisierungsmodus",
    f_initializeMode_d: "Geräte sind im Initialisierungsmodus (Adressierung läuft, endet automatisch nach 15 min).",
    f_quiescentMode: "Ruhemodus (Quiescent)",
    f_quiescentMode_d: "Eingabegeräte senden keine Ereignisse (z. B. während einer Adressierung).",
    f_sendBlockedInitialize: "Senden gesperrt: Initialisierung",
    f_sendBlockedInitialize_d: "Das Gateway hält Befehle zurück, solange eine Initialisierung läuft.",
    f_sendBlockedQuiescent: "Senden gesperrt: Ruhemodus",
    f_sendBlockedQuiescent_d: "Das Gateway hält Befehle zurück, solange der Ruhemodus aktiv ist.",
    f_sendBlockedMacroRunning: "Senden gesperrt: Makro läuft",
    f_sendBlockedMacroRunning_d: "Ein Gateway-Makro (z. B. Scan) belegt die Linie.",
    f_sendBufferFull: "Sendepuffer voll",
    f_sendBufferFull_d: "Es werden mehr Befehle erzeugt als der Bus übertragen kann – Automationen/Polling reduzieren.",
    addressMap: "Adressbelegung (Kurzadressen 0–63)",
    used: "{n} von 64 belegt",
    lgOk: "Gerät",
    lgOn: "Gerät (an)",
    lgFail: "Fehler",
    lgUnreach: "Nicht erreichbar",
    lgFree: "Frei",
    lineDevice: "Linien-Hardware",
    devType: "Gerätetyp",
    serial: "Seriennummer",
    article: "Artikelnummer",
    production: "Produktion",
    week: "KW",
    iface: "Gateway-Schnittstelle",
    lineCount: "Anzahl Linien",
    protocol: "Protokollversion",
    buffer: "Sendepuffer",
    frames: "Frames",
    maxFrame: "Max. Framegröße",
    tick: "Zeitauflösung (Ticks)",
    psu: "Integrierte Busversorgung",
    macros: "Implementierte Makros",
  },
  en: {
    updated: "As of {t}",
    autoRefresh: "refreshes every 15 s",
    readError: "Could not read the status",
    st_ok: "Bus voltage present",
    st_ok_short: "OK",
    st_ok_explain: "The line is powered and works normally.",
    st_lowPower: "Bus voltage too low",
    st_lowPower_short: "Low voltage",
    st_lowPower_explain: "The bus voltage is too low. Check the bus power supply, cable length/cross-section and the number of participants (max. 250 mA bus current, ≤ 2 V voltage drop).",
    st_noPower: "No bus voltage",
    st_noPower_short: "No power",
    st_noPower_explain: "There is no bus voltage on the line. Is a bus power supply present and switched on? Check the DALI cable for a short circuit.",
    st_notReachable: "Line not reachable",
    st_notReachable_short: "Not reachable",
    st_notReachable_explain: "The gateway's line interface does not respond. Restart the gateway; if the problem persists, contact the manufacturer's support.",
    st_unknown: "Status unknown",
    st_unknown_short: "–",
    st_unknown_explain: "The line status has not been read yet.",
    gear: "Devices",
    unreachable: "Unreachable",
    failures: "With failure",
    sensors: "Sensors",
    framesMin: "frames/min",
    framesHint: "Frames received on this line during the last minute (live monitor)",
    flags: "Line state",
    f_busVoltageDown: "Bus voltage down",
    f_busVoltageDown_d: "The bus voltage collapsed – all devices go to their system failure level.",
    f_initializeMode: "Initialise mode",
    f_initializeMode_d: "Devices are in initialise mode (addressing in progress, ends automatically after 15 min).",
    f_quiescentMode: "Quiescent mode",
    f_quiescentMode_d: "Input devices do not send events (e.g. during addressing).",
    f_sendBlockedInitialize: "Sending blocked: initialise",
    f_sendBlockedInitialize_d: "The gateway holds back commands while an initialisation runs.",
    f_sendBlockedQuiescent: "Sending blocked: quiescent",
    f_sendBlockedQuiescent_d: "The gateway holds back commands while quiescent mode is active.",
    f_sendBlockedMacroRunning: "Sending blocked: macro running",
    f_sendBlockedMacroRunning_d: "A gateway macro (e.g. a scan) occupies the line.",
    f_sendBufferFull: "Send buffer full",
    f_sendBufferFull_d: "More commands are generated than the bus can transmit – reduce automations/polling.",
    addressMap: "Address map (short addresses 0–63)",
    used: "{n} of 64 used",
    lgOk: "Device",
    lgOn: "Device (on)",
    lgFail: "Failure",
    lgUnreach: "Unreachable",
    lgFree: "Free",
    lineDevice: "Line hardware",
    devType: "Device type",
    serial: "Serial number",
    article: "Article number",
    production: "Production",
    week: "week",
    iface: "Gateway interface",
    lineCount: "Number of lines",
    protocol: "Protocol version",
    buffer: "Send buffer",
    frames: "frames",
    maxFrame: "Max. frame size",
    tick: "Tick resolution",
    psu: "Integrated bus power supply",
    macros: "Implemented macros",
  },
});

const lineIds = computed(() => {
  const n = Number(state.info?.descriptor?.lines) || Object.keys(state.info?.lines || {}).length || 1;
  return Array.from({ length: n }, (_, i) => i);
});
const desc = computed<any>(() => state.info?.descriptor || {});
const lineInfo = (l: number) => state.info?.lines?.[String(l)] ?? state.info?.lines?.[l];

const status = reactive<Record<number, any>>({});
const errors = reactive<Record<number, string>>({});
const loading = ref(false);
const updatedAt = ref(0);

async function load() {
  loading.value = true;
  await Promise.all(
    lineIds.value.map(async (l) => {
      try {
        status[l] = await gw.get(`/dali/readStatus/${l}`);
        delete errors[l];
      } catch (e: any) {
        errors[l] = e?.message || String(e);
      }
    }),
  );
  updatedAt.value = Date.now();
  loading.value = false;
}

function lineStatus(l: number): string {
  return status[l]?.lineStatus || lineInfo(l)?.lineStatus || "unknown";
}

function meta(l: number) {
  const s = lineStatus(l);
  const cls = s === "ok" ? "ok" : s === "lowPower" ? "warn" : s === "unknown" ? "off" : "err";
  const icon = s === "ok" ? mdiPowerPlug : s === "lowPower" ? mdiFlashTriangle : s === "unknown" ? mdiHelpCircleOutline : mdiPowerPlugOff;
  return {
    cls,
    icon,
    chip: cls === "off" ? "" : cls,
    banner: cls === "ok" ? "info" : cls === "off" ? "info" : cls,
    label: t(`st_${s}`),
    short: t(`st_${s}_short`),
    explain: t(`st_${s}_explain`),
  };
}

function flagList(l: number) {
  const s = status[l] || {};
  const i = lineInfo(l) || {};
  const defs: [string, any, string][] = [
    ["busVoltageDown", s.busVoltageDown, "err"],
    ["initializeMode", s.initializeMode, "warn"],
    ["quiescentMode", s.quiescentMode, "warn"],
    ["sendBlockedInitialize", i.sendBlockedInitialize, "warn"],
    ["sendBlockedQuiescent", i.sendBlockedQuiescent, "warn"],
    ["sendBlockedMacroRunning", i.sendBlockedMacroRunning, "warn"],
    ["sendBufferFull", i.sendBufferFull, "err"],
  ];
  return defs.map(([key, value, sev]) => ({ key, value: value === undefined ? undefined : !!value, sev, label: t(`f_${key}`), desc: t(`f_${key}_d`) }));
}

const lineDevices = (l: number) => Object.values(state.devices).filter((d) => (d.line ?? 0) === l);
const unreachable = (l: number) => lineDevices(l).filter((d) => !d.available).length;
const failing = (l: number) => lineDevices(l).filter((d) => d.available && (d.status?.lampFailure || d.status?.controlGearFailure)).length;
const sensorsOn = (l: number) => Object.values(state.sensors).filter((s) => (s.daliSensorAddress?.line ?? 0) === l).length;

const byAddr = computed(() => {
  const m = new Map<string, any>();
  for (const d of Object.values(state.devices)) m.set(`${d.line ?? 0}:${d.address}`, d);
  return m;
});
function cellClass(l: number, a: number) {
  const d = byAddr.value.get(`${l}:${a}`);
  if (!d) return "free";
  if (!d.available) return "err";
  if (d.status?.lampFailure || d.status?.controlGearFailure) return "warn";
  const on = d.status?.lampOn || d.features?.switchable?.status === true;
  return on ? "ok lit" : "ok";
}
function cellTitle(l: number, a: number) {
  const d = byAddr.value.get(`${l}:${a}`);
  if (!d) return `A${a} – ${t("lgFree")}`;
  const st = !d.available ? t("unreachable") : d.status?.lampFailure || d.status?.controlGearFailure ? t("lgFail") : t("available");
  return `A${a} – ${d.name} (${st})`;
}

// frames per line in the last minute (from the live monitor buffer)
const framesLastMin = ref<Record<number, number>>({});
function countFrames() {
  const cut = Date.now() / 1000 - 60;
  const out: Record<number, number> = {};
  const raw = toRaw(state.monitor);
  for (let i = raw.length - 1; i >= 0; i--) {
    const f = raw[i];
    if ((f.timestamp || 0) < cut) break;
    out[f.line] = (out[f.line] || 0) + 1;
  }
  framesLastMin.value = out;
}

let timer = 0;
let frameTimer = 0;
function startTimers() {
  stopTimers();
  timer = window.setInterval(load, 15000);
  frameTimer = window.setInterval(countFrames, 5000);
}
function stopTimers() {
  clearInterval(timer);
  clearInterval(frameTimer);
}
let firstActivation = true;
onMounted(() => {
  load();
  countFrames();
  startTimers();
});
onActivated(() => {
  // KeepAlive also fires this right after mount
  if (firstActivation) {
    firstActivation = false;
    return;
  }
  load();
  countFrames();
  startTimers();
});
onDeactivated(stopTimers);
onBeforeUnmount(stopTimers);
watch(lineIds, () => load());
</script>

<style scoped>
.head-row { margin-bottom: 12px; }
.line-grid { grid-template-columns: repeat(auto-fit, minmax(380px, 1fr)); align-items: start; }
.stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(86px, 1fr)); gap: 8px; margin-top: 12px; }
.stat-box { background: var(--bg2); border-radius: 10px; padding: 8px 6px; text-align: center; min-width: 0; }
.stat-box .sv { font-size: 19px; font-weight: 500; line-height: 1.2; }
.stat-box .sl { font-size: 11px; color: var(--text2); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.stat-box.bad { background: color-mix(in srgb, var(--error) 12%, transparent); color: var(--error); }
.stat-box.warn { background: color-mix(in srgb, var(--warning) 14%, transparent); }
.flags { display: flex; flex-direction: column; }
.flag { display: flex; align-items: center; gap: 10px; padding: 6px 0; border-bottom: 1px solid color-mix(in srgb, var(--divider) 60%, transparent); }
.flag:last-child { border-bottom: 0; }
.flag-label { color: var(--text2); }
.flag.on .flag-label { color: var(--text); font-weight: 500; }
.b { font-weight: 600; }
.norm { text-transform: none; letter-spacing: 0; font-weight: 400; }
.amap { display: grid; grid-template-columns: repeat(16, 1fr); gap: 3px; }
.cell {
  aspect-ratio: 1; border-radius: 5px; background: var(--bg2); color: var(--text3);
  font-size: 10px; font-family: var(--mono); display: flex; align-items: center; justify-content: center; cursor: default; min-width: 0;
}
.cell.ok { background: color-mix(in srgb, var(--success) 22%, transparent); color: color-mix(in srgb, var(--success) 70%, var(--text)); font-weight: 600; }
.cell.ok.lit { background: color-mix(in srgb, #ffc107 55%, transparent); color: color-mix(in srgb, #8d6e00 80%, var(--text)); }
.cell.warn { background: color-mix(in srgb, var(--warning) 35%, transparent); color: var(--text); font-weight: 600; }
.cell.err { background: color-mix(in srgb, var(--error) 30%, transparent); color: var(--error); font-weight: 600; }
.legend { gap: 4px 14px; margin-top: 8px; }
.lg { display: inline-block; width: 10px; height: 10px; border-radius: 3px; background: var(--bg2); margin-right: 5px; vertical-align: -1px; }
.lg.ok { background: color-mix(in srgb, var(--success) 40%, transparent); }
.lg.lit { background: color-mix(in srgb, #ffc107 65%, transparent); }
.lg.warn { background: color-mix(in srgb, var(--warning) 50%, transparent); }
.lg.err { background: color-mix(in srgb, var(--error) 45%, transparent); }
.iface { grid-template-columns: max-content 1fr max-content 1fr; }
.spinner.mini { width: 14px; height: 14px; }
@media (max-width: 700px) {
  .line-grid { grid-template-columns: 1fr; }
  .stats { grid-template-columns: repeat(3, 1fr); }
  .stat-box .sl { white-space: normal; }
  .amap { grid-template-columns: repeat(8, 1fr); }
  .cell { font-size: 11px; }
  .iface { grid-template-columns: max-content 1fr; }
}
</style>
