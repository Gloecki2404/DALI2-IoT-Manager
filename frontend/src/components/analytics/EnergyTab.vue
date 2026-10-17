<template>
  <div class="energy">
    <!-- no capable devices -->
    <div v-if="!capable.length" class="card">
      <Empty :icon="mdiLightningBolt" :text="t('noneTitle')">
        <div class="explain small muted">
          <p>{{ t("noneText") }}</p>
          <ul>
            <li><b>IEC 62386-252</b> – {{ t("p252") }}</li>
            <li><b>IEC 62386-253</b> – {{ t("p253") }}</li>
          </ul>
          <p>{{ t("noneHint") }}</p>
        </div>
      </Empty>
    </div>

    <template v-else>
      <div class="row wrap head-row">
        <label class="field dev-field">
          <span>{{ t("device") }}</span>
          <select v-model.number="deviceId">
            <option v-for="d in capable" :key="d.id" :value="d.id">{{ d.name }} (L{{ d.line }} · A{{ d.address }})</option>
          </select>
        </label>
        <div v-if="sources.length > 1" class="btn-group src-group">
          <button v-for="s in sources" :key="s" :class="{ active: source === s }" @click="source = s">{{ t(`src_${s}`) }}</button>
        </div>
        <span class="grow"></span>
        <span v-if="loading" class="spinner"></span>
        <button class="btn outline sm" :disabled="sampling" :title="t('sampleHint')" @click="sampleNow">
          <span v-if="sampling" class="spinner mini"></span>
          <Icon v-else :path="mdiRefresh" :size="16" />{{ t("sample") }}
        </button>
      </div>

      <div v-if="error" class="banner err">
        <Icon :path="mdiAlertCircle" :size="18" /><div>{{ error }}</div>
      </div>
      <Empty v-else-if="!loading && !rows.length" class="card" :icon="mdiTimerSand" :text="t('noSamples')" />

      <!-- energy -->
      <template v-else-if="rows.length && source === 'energy'">
        <div class="grid cols-4 kpis">
          <StatCard :icon="mdiFlash" :label="t('power')" :value="unit(latest.activePowerWatt, 'W', 1)" :sub="t('latest', { t: fmtDateTime(latest.ts, lang) })" />
          <StatCard :icon="mdiLightningBolt" :label="t('consumed')" :value="unit(consumedWh / 1000, 'kWh', 3)" :sub="t('inRange')" />
          <StatCard :icon="mdiGauge" :label="t('avgPower')" :value="unit(avgPower, 'W', 1)" :sub="t('fromCounter')" kind="off" />
          <StatCard :icon="mdiCounter" :label="t('counter')" :value="unit((latest.activeEnergyWattHours ?? 0) / 1000, 'kWh', 2)" :sub="t('counterSub')" kind="off" />
        </div>
        <div class="grid cols-2 mt-lg">
          <Card :title="t('energyChart')" :icon="mdiLightningBolt" :subtitle="t('energyChartSub')">
            <LineChart :datasets="energyDatasets" :height="240" y-unit="Wh" />
          </Card>
          <Card :title="t('powerChart')" :icon="mdiFlash" :subtitle="t('powerChartSub')">
            <LineChart :datasets="powerDatasets" :height="240" />
          </Card>
        </div>
      </template>

      <!-- diagnostics -->
      <template v-else-if="rows.length && source === 'diagnostics'">
        <div class="grid cols-4 kpis">
          <StatCard :icon="mdiClockOutline" :label="t('gearHours')" :value="hoursOf(latest.controlGearOperatingTimeSeconds)" :sub="t('gearStarts', { n: fmtNum(latest.controlGearStartCounter, lang) })" />
          <StatCard :icon="mdiLightbulbOnOutline" :label="t('lightHours')" :value="hoursOf(latest.lightSourceOnTimeSeconds)" :sub="t('lightStarts', { n: fmtNum(latest.lightSourceStartCounter, lang) })" />
          <StatCard :icon="mdiThermometer" :label="t('gearTemp')" :value="unit(latest.controlGearTemperatureCelsius, '°C', 0)" :sub="t('lightTemp', { v: unit(latest.lightSourceTemperatureCelsius, '°C', 0) })" :kind="tempKind(latest.controlGearTemperatureCelsius)" />
          <StatCard :icon="mdiSineWave" :label="t('supply')" :value="unit(latest.controlGearExternalSupplyVoltageVoltRms, 'V', 0)" :sub="supplySub" kind="off" />
        </div>

        <Card :title="t('lifetime')" :icon="mdiBatteryHeartVariant" class="mt-lg">
          <div class="life">
            <div class="life-row">
              <div class="row between small">
                <span>{{ t("lifeHours") }}</span>
                <span class="mono">{{ lifeText }}</span>
              </div>
              <div class="progress big"><div :style="{ width: `${Math.min(100, lifePct ?? 0)}%`, background: lifeColor(lifePct) }"></div></div>
            </div>
            <div class="life-row">
              <div class="row between small">
                <span>{{ t("lifeStarts") }}</span>
                <span class="mono">{{ startsText }}</span>
              </div>
              <div class="progress big"><div :style="{ width: `${Math.min(100, startsPct ?? 0)}%`, background: lifeColor(startsPct) }"></div></div>
            </div>
            <div class="small muted">{{ lifeHint }}</div>
          </div>
        </Card>

        <div class="grid cols-2 mt-lg">
          <Card :title="t('tempChart')" :icon="mdiThermometer">
            <LineChart :datasets="tempDatasets" :height="220" y-unit="°C" />
          </Card>
          <Card :title="t('voltChart')" :icon="mdiSineWave">
            <LineChart :datasets="voltDatasets" :height="220" y-unit="V" />
          </Card>
          <Card :title="t('countChart')" :icon="mdiCounter">
            <LineChart :datasets="countDatasets" :height="220" y2 />
          </Card>
          <Card :title="t('flags')" :icon="mdiAlertOutline" :subtitle="t('flagsSub')" flush>
            <div class="list">
              <div v-for="f in flagRows" :key="f.key" class="list-item flag">
                <span class="dot" :class="f.active ? 'err' : 'ok'"></span>
                <span class="grow small">{{ f.label }}</span>
                <span v-if="f.counter !== null" class="small mono muted" :title="t('counterHint')">{{ f.counter }}×</span>
                <span class="chip" :class="f.active ? 'err' : 'ok'">{{ f.active ? t("active") : t("inactive") }}</span>
              </div>
              <div v-if="!flagRows.length" class="list-item small muted">{{ t("noFlags") }}</div>
            </div>
          </Card>
        </div>
      </template>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import {
  mdiAlertCircle,
  mdiAlertOutline,
  mdiBatteryHeartVariant,
  mdiClockOutline,
  mdiCounter,
  mdiFlash,
  mdiGauge,
  mdiLightbulbOnOutline,
  mdiLightningBolt,
  mdiRefresh,
  mdiSineWave,
  mdiThermometer,
  mdiTimerSand,
} from "@mdi/js";
import Card from "../Card.vue";
import Icon from "../Icon.vue";
import Empty from "../Empty.vue";
import StatCard from "../StatCard.vue";
import LineChart from "../LineChart.vue";
import { api } from "../../lib/api";
import { run, state } from "../../lib/store";
import { lang, useT } from "../../lib/i18n";
import { DIAG_FLAGS, PALETTE, alpha, fmtDateTime, fmtNum, themeColors } from "./util";

const props = defineProps<{ hours: number; refresh: number }>();

const t = useT({
  de: {
    noneTitle: "Keine Geräte mit Energie- oder Diagnosedaten",
    noneText: "Energiemessung und Wartungsdaten liefern nur DALI-2-Betriebsgeräte, die die entsprechenden Erweiterungen unterstützen (häufig als „D4i“ gekennzeichnet):",
    p252: "Energiemessung (Gerätetyp 51): Wirkenergie, Wirk- und Scheinleistung.",
    p253: "Diagnose & Wartung (Gerätetyp 52): Betriebsstunden, Schaltzyklen, Temperaturen, Spannungen und Fehlerzähler.",
    noneHint: "In dieser Installation meldet derzeit kein Gerät diese Gerätetypen. Sobald ein solches Gerät gefunden wird, werden die Werte automatisch alle 15 Minuten erfasst.",
    device: "Gerät",
    src_energy: "Energie",
    src_diagnostics: "Diagnose",
    sample: "Jetzt messen",
    sampleHint: "Liest Energie- und Diagnosedaten aller fähigen Geräte sofort aus",
    sampled: "Messwerte aktualisiert",
    noSamples: "Für diesen Zeitraum liegen noch keine Messwerte vor. Werte werden alle 15 Minuten erfasst – oder jetzt mit „Jetzt messen“.",
    power: "Aktuelle Leistung",
    latest: "Stand {t}",
    consumed: "Verbrauch",
    inRange: "im gewählten Zeitraum",
    avgPower: "Ø Leistung",
    fromCounter: "aus dem Energiezähler",
    counter: "Zählerstand",
    counterSub: "Wirkenergie gesamt",
    energyChart: "Energiezähler",
    energyChartSub: "Wirkenergie (Wh)",
    energyDs: "Wirkenergie",
    energyLoadDs: "Wirkenergie Lastseite",
    powerChart: "Leistung",
    powerChartSub: "Wirkleistung (W) und Scheinleistung (VA)",
    powerDs: "Wirkleistung (W)",
    apparentDs: "Scheinleistung (VA)",
    powerLoadDs: "Wirkleistung Lastseite (W)",
    gearHours: "Betriebszeit Gerät",
    gearStarts: "{n} Starts",
    lightHours: "Leuchtdauer",
    lightStarts: "{n} Einschaltungen",
    gearTemp: "Temperatur Gerät",
    lightTemp: "Leuchtmittel: {v}",
    supply: "Netzspannung",
    lifetime: "Lebensdauer",
    lifeHours: "Leuchtdauer vs. Bemessungslebensdauer",
    lifeStarts: "Einschaltungen vs. Bemessungswert",
    lifeOk: "Das Leuchtmittel ist noch weit vom Ende der Bemessungslebensdauer entfernt.",
    lifeWarn: "Über 80 % der Bemessungslebensdauer erreicht – Austausch einplanen.",
    lifeUnknown: "Das Gerät meldet keine Bemessungslebensdauer.",
    tempChart: "Temperaturen",
    voltChart: "Spannungen",
    countChart: "Zähler",
    tGear: "Betriebsgerät",
    tLight: "Leuchtmittel",
    tRef: "Referenz intern",
    vSupply: "Netz (V rms)",
    vLight: "Leuchtmittel (V)",
    cGearStarts: "Starts Betriebsgerät",
    cLightStarts: "Einschaltungen Leuchtmittel",
    cHours: "Leuchtstunden (rechts)",
    flags: "Fehlerstatus",
    flagsSub: "Letzte Messung, mit Fehlerzählern",
    counterHint: "Anzahl bisheriger Ereignisse",
    active: "aktiv",
    inactive: "OK",
    noFlags: "Keine Fehlerinformationen gemeldet.",
    hoursUnit: "h",
  },
  en: {
    noneTitle: "No devices with energy or diagnostic data",
    noneText: "Energy metering and maintenance data are only provided by DALI-2 control gear supporting the corresponding extensions (often labelled “D4i”):",
    p252: "Energy reporting (device type 51): active energy, active and apparent power.",
    p253: "Diagnostics & maintenance (device type 52): operating hours, switching cycles, temperatures, voltages and failure counters.",
    noneHint: "No device in this installation currently reports these device types. As soon as such a device is found, values are recorded automatically every 15 minutes.",
    device: "Device",
    src_energy: "Energy",
    src_diagnostics: "Diagnostics",
    sample: "Sample now",
    sampleHint: "Reads energy and diagnostic data of all capable devices right now",
    sampled: "Measurements updated",
    noSamples: "No measurements for this period yet. Values are recorded every 15 minutes – or right now with “Sample now”.",
    power: "Current power",
    latest: "As of {t}",
    consumed: "Consumption",
    inRange: "in the selected period",
    avgPower: "Avg power",
    fromCounter: "from the energy counter",
    counter: "Meter reading",
    counterSub: "total active energy",
    energyChart: "Energy counter",
    energyChartSub: "Active energy (Wh)",
    energyDs: "Active energy",
    energyLoadDs: "Active energy load side",
    powerChart: "Power",
    powerChartSub: "Active power (W) and apparent power (VA)",
    powerDs: "Active power (W)",
    apparentDs: "Apparent power (VA)",
    powerLoadDs: "Active power load side (W)",
    gearHours: "Gear operating time",
    gearStarts: "{n} starts",
    lightHours: "Light source on time",
    lightStarts: "{n} switch-ons",
    gearTemp: "Gear temperature",
    lightTemp: "Light source: {v}",
    supply: "Supply voltage",
    lifetime: "Lifetime",
    lifeHours: "On time vs. rated median useful life",
    lifeStarts: "Switch-ons vs. rated value",
    lifeOk: "The light source is still far from the end of its rated life.",
    lifeWarn: "More than 80 % of the rated life reached – plan a replacement.",
    lifeUnknown: "The device does not report a rated life.",
    tempChart: "Temperatures",
    voltChart: "Voltages",
    countChart: "Counters",
    tGear: "Control gear",
    tLight: "Light source",
    tRef: "Internal reference",
    vSupply: "Supply (V rms)",
    vLight: "Light source (V)",
    cGearStarts: "Gear starts",
    cLightStarts: "Light source switch-ons",
    cHours: "Light hours (right)",
    flags: "Failure status",
    flagsSub: "Latest sample, with failure counters",
    counterHint: "Number of events so far",
    active: "active",
    inactive: "OK",
    noFlags: "No failure information reported.",
    hoursUnit: "h",
  },
});

const DT_ENERGY = 51;
const DT_DIAG = 52;
const capable = computed(() =>
  Object.values(state.devices)
    .filter((d) => (d.daliTypes || []).some((x) => x === DT_ENERGY || x === DT_DIAG))
    .sort((a, b) => a.line - b.line || a.address - b.address),
);
const deviceId = ref<number | null>(null);
watch(
  capable,
  (list) => {
    if (!list.some((d) => d.id === deviceId.value)) deviceId.value = list[0]?.id ?? null;
  },
  { immediate: true },
);
const device = computed(() => (deviceId.value !== null ? state.devices[deviceId.value] : null));
const sources = computed(() => {
  const types = device.value?.daliTypes || [];
  const out: ("energy" | "diagnostics")[] = [];
  if (types.includes(DT_ENERGY)) out.push("energy");
  if (types.includes(DT_DIAG)) out.push("diagnostics");
  return out;
});
const source = ref<"energy" | "diagnostics">("energy");
watch(
  sources,
  (s) => {
    if (s.length && !s.includes(source.value)) source.value = s[0];
  },
  { immediate: true },
);

const rows = ref<any[]>([]);
const loading = ref(false);
const error = ref("");
const sampling = ref(false);

async function load() {
  if (deviceId.value === null) {
    rows.value = [];
    return;
  }
  loading.value = true;
  try {
    rows.value = (await api<any[]>("GET", `analytics/measurements/${deviceId.value}?source=${source.value}&hours=${props.hours}`)) || [];
    error.value = "";
  } catch (e: any) {
    error.value = e?.message || String(e);
  } finally {
    loading.value = false;
  }
}
watch(() => [deviceId.value, source.value, props.hours, props.refresh], load, { immediate: true });

async function sampleNow() {
  sampling.value = true;
  await run(() => api("POST", "analytics/sample"), t("sampled"));
  sampling.value = false;
  await load();
}

const latest = computed<any>(() => rows.value[rows.value.length - 1] || {});
const first = computed<any>(() => rows.value[0] || {});
function unit(v: number | null | undefined, u: string, digits = 1) {
  return v === null || v === undefined || Number.isNaN(v) ? "–" : `${fmtNum(v, lang.value, digits)} ${u}`;
}
function hoursOf(sec: number | null | undefined) {
  return sec === null || sec === undefined ? "–" : `${fmtNum(sec / 3600, lang.value, 0)} ${t("hoursUnit")}`;
}

// ------------------------------------------------------------ energy
const consumedWh = computed(() => {
  const a = first.value.activeEnergyWattHours;
  const b = latest.value.activeEnergyWattHours;
  return typeof a === "number" && typeof b === "number" ? Math.max(0, b - a) : 0;
});
const avgPower = computed(() => {
  const dt = (latest.value.ts ?? 0) - (first.value.ts ?? 0);
  return dt > 60 ? (consumedWh.value * 3600) / dt : null;
});
const series = (key: string) => rows.value.filter((r) => typeof r[key] === "number").map((r) => ({ x: r.ts, y: r[key] }));
const line = (label: string, key: string, color: string, extra: Record<string, any> = {}) => ({
  label,
  data: series(key),
  borderColor: color,
  backgroundColor: alpha(color, 0.15),
  pointRadius: rows.value.length < 40 ? 2 : 0,
  ...extra,
});
const energyDatasets = computed(() =>
  [line(t("energyDs"), "activeEnergyWattHours", PALETTE[2], { fill: "origin" }), line(t("energyLoadDs"), "activeEnergyLoadsideWattHours", PALETTE[5])].filter((d) => d.data.length),
);
const powerDatasets = computed(() =>
  [
    line(t("powerDs"), "activePowerWatt", PALETTE[1], { fill: "origin" }),
    line(t("apparentDs"), "apparentPowerVoltAmpere", PALETTE[0], { borderDash: [5, 4] }),
    line(t("powerLoadDs"), "activePowerLoadsideWatt", PALETTE[5]),
  ].filter((d) => d.data.length),
);

// ------------------------------------------------------------ diagnostics
function tempKind(v: number | null | undefined) {
  if (typeof v !== "number") return "off";
  return v >= 85 ? "err" : v >= 70 ? "warn" : "ok";
}
const supplySub = computed(() => {
  const f = latest.value.controlGearExternalSupplyVoltageFrequencyHertz;
  const pf = latest.value.controlGearPowerFactor;
  return [typeof f === "number" ? `${f} Hz` : "", typeof pf === "number" ? `PF ${fmtNum(pf, lang.value, 2)}` : ""].filter(Boolean).join(" · ") || "–";
});
const lifePct = computed(() => {
  const life = latest.value.ratedMedianUsefulLifeOfLuminaireHours;
  const on = latest.value.lightSourceOnTimeSeconds;
  return life && typeof on === "number" ? (100 * on) / 3600 / life : null;
});
const startsPct = computed(() => {
  const rated = latest.value.ratedMedianUsefulLightSourceStarts;
  const starts = latest.value.lightSourceStartCounter;
  return rated && typeof starts === "number" ? (100 * starts) / rated : null;
});
const lifeText = computed(() => {
  const life = latest.value.ratedMedianUsefulLifeOfLuminaireHours;
  const on = latest.value.lightSourceOnTimeSeconds;
  if (!life) return hoursOf(on);
  return `${hoursOf(on)} / ${fmtNum(life, lang.value, 0)} ${t("hoursUnit")} (${fmtNum(lifePct.value, lang.value, 1)} %)`;
});
const startsText = computed(() => {
  const rated = latest.value.ratedMedianUsefulLightSourceStarts;
  const starts = latest.value.lightSourceStartCounter;
  if (!rated) return typeof starts === "number" ? fmtNum(starts, lang.value) : "–";
  return `${fmtNum(starts, lang.value)} / ${fmtNum(rated, lang.value)} (${fmtNum(startsPct.value, lang.value, 1)} %)`;
});
const lifeHint = computed(() => (lifePct.value === null ? t("lifeUnknown") : lifePct.value > 80 || (startsPct.value ?? 0) > 80 ? t("lifeWarn") : t("lifeOk")));
function lifeColor(p: number | null) {
  const c = themeColors();
  return p === null ? c.text3 : p > 90 ? c.error : p > 80 ? c.warning : c.success;
}
const tempDatasets = computed(() =>
  [
    line(t("tGear"), "controlGearTemperatureCelsius", PALETTE[1]),
    line(t("tLight"), "lightSourceTemperatureCelsius", PALETTE[3]),
    line(t("tRef"), "internalControlGearReferenceTemperatureCelsius", PALETTE[5], { borderDash: [5, 4] }),
  ].filter((d) => d.data.length),
);
const voltDatasets = computed(() =>
  [line(t("vSupply"), "controlGearExternalSupplyVoltageVoltRms", PALETTE[0]), line(t("vLight"), "lightSourceVoltageVolt", PALETTE[4])].filter((d) => d.data.length),
);
const countDatasets = computed(() => {
  const hours = rows.value.filter((r) => typeof r.lightSourceOnTimeSeconds === "number").map((r) => ({ x: r.ts, y: Math.round(r.lightSourceOnTimeSeconds / 360) / 10 }));
  return [
    line(t("cGearStarts"), "controlGearStartCounter", PALETTE[0]),
    line(t("cLightStarts"), "lightSourceStartCounter", PALETTE[2]),
    { label: t("cHours"), data: hours, borderColor: PALETTE[1], borderDash: [5, 4], yAxisID: "y2", pointRadius: 0 },
  ].filter((d) => d.data.length);
});
const flagRows = computed(() =>
  Object.entries(DIAG_FLAGS)
    .filter(([k]) => k in latest.value)
    .map(([k, meta]) => ({
      key: k,
      label: meta[lang.value],
      active: !!latest.value[k],
      counter: meta.counter && typeof latest.value[meta.counter] === "number" ? latest.value[meta.counter] : null,
    })),
);
</script>

<style scoped>
.explain { max-width: 620px; text-align: left; }
.explain ul { margin: 6px 0; padding-left: 18px; }
.explain li { margin: 4px 0; }
.head-row { margin-bottom: 12px; align-items: flex-end; gap: 10px; }
.dev-field { min-width: 240px; max-width: 420px; flex: 1 1 260px; }
.src-group { margin-bottom: 3px; }
.kpis :deep(.stat) { padding: 12px 14px; }
.kpis :deep(.stat .value) { font-size: 20px; }
.life { display: flex; flex-direction: column; gap: 14px; }
.life-row { display: flex; flex-direction: column; gap: 6px; }
.progress.big { height: 10px; border-radius: 5px; }
.progress.big > div { border-radius: 5px; }
.flag { min-height: 40px; padding: 6px 16px; }
.spinner.mini { width: 14px; height: 14px; }
</style>
