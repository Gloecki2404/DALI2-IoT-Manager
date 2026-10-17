<template>
  <div class="health">
    <div v-if="loading && !data" class="center pad"><span class="spinner"></span></div>
    <div v-else-if="error && !data" class="banner err">
      <Icon :path="mdiAlertCircle" :size="18" /><div>{{ error }}</div>
    </div>
    <Empty v-else-if="data && !data.total" :icon="mdiHeartPulse" :text="t('noDevices')" />
    <template v-else-if="data">
      <div class="summary">
        <div class="card score-card">
          <svg viewBox="0 0 120 120" class="gauge" role="img" :aria-label="`${t('score')} ${avgScore}`">
            <circle cx="60" cy="60" r="50" class="g-track" />
            <circle
              cx="60"
              cy="60"
              r="50"
              class="g-val"
              :style="{ stroke: scoreColor(avgScore), strokeDasharray: `${(avgScore / 100) * 314.16} 314.16` }"
            />
            <text x="60" y="58" text-anchor="middle" class="g-num">{{ avgScore }}</text>
            <text x="60" y="78" text-anchor="middle" class="g-lab">/ 100</text>
          </svg>
          <div class="score-text">
            <div class="score-title">{{ verdict.title }}</div>
            <div class="small muted">{{ verdict.text }}</div>
            <div class="small faint mt-s">{{ t("okShare", { ok: data.ok, total: data.total }) }}</div>
          </div>
        </div>
        <div class="grid stat-grid">
          <StatCard :icon="mdiCheckCircle" :label="t('stOk')" :value="counts.ok" :sub="pctOf(counts.ok)" kind="ok" />
          <StatCard :icon="mdiAlert" :label="t('stWarn')" :value="counts.warn" :sub="pctOf(counts.warn)" :kind="counts.warn ? 'warn' : 'off'" />
          <StatCard :icon="mdiAlertCircle" :label="t('stErr')" :value="counts.err" :sub="pctOf(counts.err)" :kind="counts.err ? 'err' : 'off'" />
          <StatCard :icon="mdiLanDisconnect" :label="t('stUnreach')" :value="counts.unreach" :sub="pctOf(counts.unreach)" :kind="counts.unreach ? 'err' : 'off'" />
        </div>
      </div>

      <Card v-if="actions.length" :title="t('actions')" :icon="mdiWrench" icon-class="warn" class="mt-lg">
        <div class="list">
          <div v-for="a in actions" :key="a.code" class="list-item action">
            <span class="icon-bubble" :class="levelCls(a.level)"><Icon :path="issueIcon(a.code)" :size="20" /></span>
            <div class="grow">
              <div class="title">{{ t("affected", { n: a.devices.length }) }} – {{ issueText({ code: a.code, level: a.level }) }}</div>
              <div class="sub">{{ issueRec(a.code) }}</div>
              <div class="row wrap dev-chips">
                <span v-for="d in a.devices" :key="d.device_id" class="chip">{{ d.name || `#${d.device_id}` }} · A{{ d.address }}</span>
              </div>
            </div>
          </div>
        </div>
      </Card>
      <div v-else class="banner info mt-lg">
        <Icon :path="mdiCheckCircle" :size="18" />
        <div>{{ t("allGood") }}</div>
      </div>

      <Card :title="t('perDevice')" :icon="mdiHeartPulse" :subtitle="t('perDeviceSub')" class="mt-lg" flush>
        <template #actions>
          <div class="btn-group">
            <button :class="{ active: !onlyProblems }" @click="onlyProblems = false">{{ t("all") }}</button>
            <button :class="{ active: onlyProblems }" @click="onlyProblems = true">{{ t("problems") }}</button>
          </div>
        </template>
        <Empty v-if="!shown.length" :icon="mdiCheckCircle" :text="t('noProblems')" />
        <div v-else class="list">
          <div v-for="d in shown" :key="d.device_id" class="list-item dev">
            <span class="score" :style="{ color: scoreColor(d.score), background: `color-mix(in srgb, ${scoreColor(d.score)} 14%, transparent)` }">{{ d.score }}</span>
            <div class="grow minw">
              <div class="row wrap">
                <span class="title">{{ d.name || `#${d.device_id}` }}</span>
                <span class="faint small mono">L{{ d.line }} · A{{ d.address }}</span>
              </div>
              <div v-if="d.issues.length" class="row wrap issues">
                <span v-for="(i, k) in d.issues" :key="k" class="chip" :class="levelChip(i.level)">
                  <Icon :path="issueIcon(i.code)" :size="14" />{{ issueText(i) }}
                </span>
              </div>
              <div v-else class="small muted">{{ t("noIssues") }}</div>
              <ul v-if="recsOf(d).length" class="recs small muted">
                <li v-for="r in recsOf(d)" :key="r">{{ r }}</li>
              </ul>
            </div>
            <div class="ratio" :title="t('ratioHint')">
              <div class="small faint">{{ t("answers") }}</div>
              <div class="mono" :class="{ bad: d.answer_ratio !== null && d.answer_ratio < 98 }">{{ d.answer_ratio === null ? "–" : fmtPct(d.answer_ratio, lang) }}</div>
            </div>
          </div>
        </div>
      </Card>
      <p class="small faint">{{ t("footnote") }}</p>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import {
  mdiAlert,
  mdiAlertCircle,
  mdiBatteryHeartVariant,
  mdiCableData,
  mdiCheckCircle,
  mdiChip,
  mdiHeartPulse,
  mdiInformationOutline,
  mdiLanDisconnect,
  mdiLightbulbAlert,
  mdiPowerPlugOff,
  mdiRestart,
  mdiTarget,
  mdiThermometer,
  mdiWrench,
} from "@mdi/js";
import Card from "../Card.vue";
import Icon from "../Icon.vue";
import Empty from "../Empty.vue";
import StatCard from "../StatCard.vue";
import { api } from "../../lib/api";
import { lang, useT } from "../../lib/i18n";
import { DIAG_FLAGS, fmtPct, themeColors } from "./util";

const props = defineProps<{ hours: number; refresh: number }>();

const t = useT({
  de: {
    noDevices: "Keine DALI-Geräte vorhanden.",
    score: "Gesundheitswert",
    okShare: "{ok} von {total} Geräten ohne Befund",
    v_good: "Anlage in gutem Zustand",
    v_good_t: "Alle Geräte antworten zuverlässig und melden keine Fehler.",
    v_ok: "Kleinere Auffälligkeiten",
    v_ok_t: "Einige Geräte melden Warnungen – siehe Handlungsempfehlungen.",
    v_bad: "Handlungsbedarf",
    v_bad_t: "Mindestens ein Gerät ist gestört oder nicht erreichbar.",
    stOk: "In Ordnung",
    stWarn: "Warnungen",
    stErr: "Fehler",
    stUnreach: "Nicht erreichbar",
    ofTotal: "{p} % der Geräte",
    actions: "Handlungsempfehlungen",
    affected: "{n}×",
    allGood: "Keine Auffälligkeiten – es sind keine Maßnahmen erforderlich.",
    perDevice: "Geräte im Detail",
    perDeviceSub: "Sortiert nach Gesundheitswert (schlechteste zuerst)",
    problems: "Nur mit Befund",
    noProblems: "Kein Gerät mit Befund.",
    noIssues: "Keine Befunde",
    answers: "Antwortquote",
    ratioHint: "Anteil beantworteter Statusabfragen heute",
    footnote: "Der Gesundheitswert startet bei 100 und verringert sich je Befund (Fehler −40, Warnung −15, Hinweis −3). Die Antwortquote bezieht sich auf den heutigen Tag.",
    i_unavailable: "Nicht erreichbar",
    i_lamp_failure: "Lampenfehler",
    i_gear_failure: "Betriebsgerätefehler",
    i_limit_error: "Grenzwertfehler",
    i_power_cycle: "Netzunterbrechung erkannt",
    i_unaddressed: "Keine Kurzadresse",
    i_reset_state: "Werkseinstellung (Reset-Zustand)",
    i_bad_communication: "Schlechte Kommunikation ({d})",
    i_diag: "Diagnose: {d}",
    i_end_of_life: "Lebensdauer zu {d} erreicht",
    r_unavailable: "Netzspannung (230 V), DALI-Anschluss und Verkabelung des Betriebsgeräts prüfen. Wurde das Gerät getauscht, einen Scan durchführen.",
    r_lamp_failure: "Leuchtmittel bzw. LED-Modul und die Lastverdrahtung prüfen; ggf. Leuchtmittel tauschen.",
    r_gear_failure: "Betriebsgerät (Treiber/EVG) prüfen; bei dauerhaftem Fehler austauschen.",
    r_limit_error: "Der angeforderte Dimmwert lag außerhalb von Min/Max-Level – Min/Max-Einstellungen prüfen.",
    r_power_cycle: "Das Gerät war kurz spannungslos. Tritt das häufig auf, Stromkreis und Schaltaktoren prüfen.",
    r_unaddressed: "Einen normalen Scan durchführen, damit das Gerät eine Kurzadresse erhält.",
    r_reset_state: "Das Gerät ist im Auslieferungszustand – Gruppen, Szenen und Parameter ggf. neu übertragen.",
    r_bad_communication: "Antwortquote unter 98 %: Busleitung (Länge, Querschnitt, Spannungsabfall), Busversorgung und Störquellen prüfen.",
    r_diag: "Diagnosedaten im Tab „Energie & Diagnose“ prüfen (Temperatur, Spannung, Fehlerzähler).",
    r_end_of_life: "Das Leuchtmittel nähert sich dem Ende der Bemessungslebensdauer – Austausch einplanen.",
  },
  en: {
    noDevices: "No DALI devices available.",
    score: "Health score",
    okShare: "{ok} of {total} devices without findings",
    v_good: "Installation in good shape",
    v_good_t: "All devices answer reliably and report no errors.",
    v_ok: "Minor findings",
    v_ok_t: "Some devices report warnings – see the recommendations.",
    v_bad: "Action required",
    v_bad_t: "At least one device is faulty or not reachable.",
    stOk: "OK",
    stWarn: "Warnings",
    stErr: "Errors",
    stUnreach: "Unreachable",
    ofTotal: "{p} % of devices",
    actions: "Recommended actions",
    affected: "{n}×",
    allGood: "No findings – no action required.",
    perDevice: "Devices in detail",
    perDeviceSub: "Sorted by health score (worst first)",
    problems: "With findings",
    noProblems: "No device with findings.",
    noIssues: "No findings",
    answers: "Answer ratio",
    ratioHint: "Share of status queries answered today",
    footnote: "The health score starts at 100 and is reduced per finding (error −40, warning −15, info −3). The answer ratio refers to the current day.",
    i_unavailable: "Unreachable",
    i_lamp_failure: "Lamp failure",
    i_gear_failure: "Control gear failure",
    i_limit_error: "Limit error",
    i_power_cycle: "Power cycle seen",
    i_unaddressed: "No short address",
    i_reset_state: "Factory settings (reset state)",
    i_bad_communication: "Poor communication ({d})",
    i_diag: "Diagnostics: {d}",
    i_end_of_life: "{d} of rated lifetime reached",
    r_unavailable: "Check the mains supply (230 V), the DALI connection and wiring of the control gear. If the device was replaced, run a scan.",
    r_lamp_failure: "Check the lamp or LED module and the load wiring; replace the light source if necessary.",
    r_gear_failure: "Check the control gear (driver/ballast); replace it if the failure persists.",
    r_limit_error: "The requested level was outside min/max level – check the min/max settings.",
    r_power_cycle: "The device briefly lost power. If this happens often, check the circuit and switching actuators.",
    r_unaddressed: "Run a normal scan so the device receives a short address.",
    r_reset_state: "The device is in factory state – re-apply groups, scenes and parameters if necessary.",
    r_bad_communication: "Answer ratio below 98 %: check the bus cable (length, cross-section, voltage drop), bus power supply and interference sources.",
    r_diag: "Check the diagnostic data in the “Energy & diagnostics” tab (temperature, voltage, failure counters).",
    r_end_of_life: "The light source approaches the end of its rated life – plan a replacement.",
  },
});

interface Issue {
  level: string;
  code: string;
  detail?: string;
}
interface HealthDevice {
  device_id: number;
  name: string;
  address: number;
  line: number;
  issues: Issue[];
  score: number;
  answer_ratio: number | null;
}

const data = ref<{ devices: HealthDevice[]; ok: number; total: number } | null>(null);
const loading = ref(false);
const error = ref("");
const onlyProblems = ref(false);

async function load() {
  loading.value = true;
  try {
    data.value = await api("GET", "analytics/health");
    error.value = "";
  } catch (e: any) {
    error.value = e?.message || String(e);
  } finally {
    loading.value = false;
  }
}
watch(() => props.refresh, load, { immediate: true });

const devices = computed(() => data.value?.devices ?? []);
const hasLevel = (d: HealthDevice, lv: string) => d.issues.some((i) => i.level === lv);
const counts = computed(() => {
  const c = { ok: 0, warn: 0, err: 0, unreach: 0 };
  for (const d of devices.value) {
    if (d.issues.some((i) => i.code === "unavailable")) c.unreach++;
    else if (hasLevel(d, "error")) c.err++;
    else if (hasLevel(d, "warning")) c.warn++;
    else c.ok++;
  }
  return c;
});
const avgScore = computed(() => (devices.value.length ? Math.round(devices.value.reduce((s, d) => s + d.score, 0) / devices.value.length) : 100));
const verdict = computed(() => {
  if (counts.value.err || counts.value.unreach) return { title: t("v_bad"), text: t("v_bad_t") };
  if (counts.value.warn) return { title: t("v_ok"), text: t("v_ok_t") };
  return { title: t("v_good"), text: t("v_good_t") };
});
function pctOf(n: number) {
  const total = devices.value.length || 1;
  return t("ofTotal", { p: Math.round((100 * n) / total) });
}

function scoreColor(s: number) {
  const c = themeColors();
  return s >= 90 ? c.success : s >= 60 ? c.warning : c.error;
}
function levelChip(l: string) {
  return l === "error" ? "err" : l === "warning" ? "warn" : "primary";
}
function levelCls(l: string) {
  return l === "error" ? "err" : l === "warning" ? "warn" : "";
}
function issueIcon(code: string) {
  return (
    {
      unavailable: mdiLanDisconnect,
      lamp_failure: mdiLightbulbAlert,
      gear_failure: mdiChip,
      limit_error: mdiTarget,
      power_cycle: mdiPowerPlugOff,
      unaddressed: mdiInformationOutline,
      reset_state: mdiRestart,
      bad_communication: mdiCableData,
      diag: mdiThermometer,
      end_of_life: mdiBatteryHeartVariant,
    }[code] || mdiAlert
  );
}
function issueText(i: Issue) {
  let d = i.detail ?? "";
  if (i.code === "diag" && d) d = DIAG_FLAGS[d]?.[lang.value] ?? d;
  const key = `i_${i.code}`;
  const s = t(key, { d });
  return s === key ? i.code : s;
}
function issueRec(code: string) {
  const key = `r_${code}`;
  const s = t(key);
  return s === key ? "" : s;
}
function recsOf(d: HealthDevice) {
  const seen = new Set<string>();
  return d.issues
    .filter((i) => i.level !== "info" || i.code === "power_cycle")
    .map((i) => issueRec(i.code))
    .filter((r) => r && !seen.has(r) && (seen.add(r), true));
}

const shown = computed(() => (onlyProblems.value ? devices.value.filter((d) => d.issues.length) : devices.value));

const LEVEL_ORDER: Record<string, number> = { error: 0, warning: 1, info: 2 };
const actions = computed(() => {
  const map = new Map<string, { code: string; level: string; devices: HealthDevice[] }>();
  for (const d of devices.value) {
    for (const i of d.issues) {
      if (i.level === "info" && i.code !== "power_cycle") continue;
      const e = map.get(i.code) || { code: i.code, level: i.level, devices: [] };
      if (!e.devices.includes(d)) e.devices.push(d);
      map.set(i.code, e);
    }
  }
  return [...map.values()].sort((a, b) => (LEVEL_ORDER[a.level] ?? 3) - (LEVEL_ORDER[b.level] ?? 3) || b.devices.length - a.devices.length);
});
</script>

<style scoped>
.pad { padding: 40px 0; }
.summary { display: grid; grid-template-columns: minmax(280px, 380px) 1fr; gap: 16px; align-items: stretch; }
.score-card { display: flex; align-items: center; gap: 18px; padding: 16px 20px; }
.gauge { width: 118px; height: 118px; flex-shrink: 0; }
.g-track { fill: none; stroke: var(--bg2); stroke-width: 11; }
.g-val { fill: none; stroke-width: 11; stroke-linecap: round; transform: rotate(-90deg); transform-origin: 60px 60px; transition: stroke-dasharray .6s; }
.g-num { font-size: 32px; font-weight: 500; fill: var(--text); font-family: var(--font); }
.g-lab { font-size: 12px; fill: var(--text3); font-family: var(--font); }
.score-title { font-size: 17px; font-weight: 500; margin-bottom: 4px; }
.mt-s { margin-top: 6px; }
.stat-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }
.stat-grid :deep(.stat) { padding: 12px 14px; }
.action { align-items: flex-start; }
.dev-chips { gap: 4px; margin-top: 6px; }
.dev { align-items: flex-start; }
.score { width: 42px; height: 42px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: 600; font-size: 15px; flex-shrink: 0; }
.minw { min-width: 0; }
.issues { gap: 4px; margin-top: 4px; }
.recs { margin: 6px 0 0; padding-left: 18px; }
.recs li { margin: 2px 0; }
.ratio { text-align: right; flex-shrink: 0; }
.ratio .bad { color: var(--error); font-weight: 600; }
@media (max-width: 900px) {
  .summary { grid-template-columns: 1fr; }
}
@media (max-width: 700px) {
  .score-card { gap: 12px; padding: 14px; }
  .gauge { width: 96px; height: 96px; }
  .stat-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .ratio .small { font-size: 10.5px; }
}
</style>
