<template>
  <div class="page">
    <div class="page-head">
      <div class="grow">
        <h1>{{ state.info?.name || "DALI-2 IoT" }}</h1>
        <div class="row wrap mt-sm">
          <span class="chip primary">{{ state.info?.version }}</span>
          <span v-if="state.info?.tier" class="chip">Tier: {{ state.info.tier }}</span>
          <span class="chip"><span class="dot" :class="online ? 'ok pulse' : 'err'"></span>{{ state.status?.gateway?.host }}</span>
          <span v-if="state.info?.emergencyLight" class="chip warn">{{ t("emergency") }}</span>
        </div>
      </div>
    </div>

    <div class="grid cols-4">
      <StatCard :icon="mdiLightbulbGroup" :label="t('devices')" :value="devices.length" :sub="t('onLines', { n: lineCount })" to="/devices" />
      <StatCard :icon="mdiLightbulbOn" :label="t('lightsOn')" :value="onCount" :sub="t('ofTotal', { n: devices.length })" kind="warn" to="/devices?filter=on" />
      <StatCard :icon="problems ? mdiAlertCircle : mdiCheckCircle" :label="t('problems')" :value="problems" :kind="problems ? 'err' : 'ok'"
                :sub="problems ? t('problemsSub', { u: unavailable, f: failures }) : t('allOk')" to="/devices?filter=problem" />
      <StatCard :icon="mdiPulse" :label="t('busActivity')" :value="`${rate.toFixed(1)}/s`" :sub="t('loadApprox', { p: loadPct.toFixed(1) })" kind="off" to="/bus" />
    </div>

    <div class="grid cols-2 mt-lg">
      <Card :title="t('quick')" :icon="mdiGestureTapButton">
        <div v-if="broadcastZone" class="quick-row">
          <div class="grow">
            <div class="title">{{ t("allLights") }}</div>
            <div class="muted small">{{ t("broadcastSub") }}</div>
          </div>
          <button class="btn gray sm" @click="ctl('zone', broadcastZone.id, { switchable: false })">{{ t("off") }}</button>
          <button class="btn sm" @click="ctl('zone', broadcastZone.id, { dimmable: 100 })">100 %</button>
        </div>
        <div v-for="z in groupZones" :key="z.id" class="quick-row">
          <span class="icon-bubble" :class="isOn(z.features) ? 'warn' : 'off'" style="width: 34px; height: 34px">
            <Icon :path="isOn(z.features) ? mdiLightbulbMultiple : mdiLightbulbMultipleOutline" :size="18" />
          </span>
          <div class="grow">
            <div class="title">{{ zoneName(z) }}</div>
            <div class="muted small">{{ members(z) }}</div>
          </div>
          <input v-if="'dimmable' in z.features" class="mini-range" type="range" min="0" max="100" :value="level(z.features)"
                 @change="ctl('zone', z.id, { dimmable: +($event.target as HTMLInputElement).value })" />
          <Toggle :model-value="isOn(z.features)" @change="(v: boolean) => ctl('zone', z.id, v ? { gotoLastActive: true } : { switchable: false })" />
        </div>
        <Empty v-if="!groupZones.length && !broadcastZone" :text="t('noGroups')" />
        <div class="row mt">
          <RouterLink to="/groups" class="btn flat sm">{{ t("manageGroups") }}</RouterLink>
        </div>
      </Card>

      <Card :title="t('events')" :icon="mdiTimelineAlertOutline">
        <template #actions><RouterLink to="/analytics" class="btn flat sm">{{ t("allEvents") }}</RouterLink></template>
        <div v-if="!recentEvents.length" class="muted small">{{ t("noEvents") }}</div>
        <div v-else class="list">
          <div v-for="(e, i) in recentEvents" :key="i" class="ev">
            <Icon :path="e.level === 'error' ? mdiAlertCircle : e.level === 'warning' ? mdiAlert : mdiInformationOutline" :size="18"
                  :class="['ev-icon', e.level]" />
            <div class="grow">
              <div>{{ e.message }}</div>
              <div class="faint small">{{ fmtTime(e.ts, lang) }}</div>
            </div>
          </div>
        </div>
      </Card>

      <Card :title="t('lines')" :icon="mdiTransitConnectionVariant">
        <div v-for="(l, idx) in lineInfos" :key="idx" class="quick-row">
          <span class="icon-bubble" :class="l.lineStatus === 'ok' ? 'ok' : 'err'" style="width: 34px; height: 34px">
            <Icon :path="mdiTransitConnectionVariant" :size="18" />
          </span>
          <div class="grow">
            <div class="title">{{ t("line") }} {{ idx }}</div>
            <div class="muted small">{{ lineText(l.lineStatus) }} · {{ t("devOnLine", { n: devices.filter((d) => d.line === Number(idx)).length }) }}</div>
          </div>
          <span v-if="l.sendBufferFull" class="chip warn">{{ t("bufferFull") }}</span>
          <span v-if="l.sendBlockedInitialize" class="chip warn">Initialize</span>
          <span v-if="l.sendBlockedQuiescent" class="chip warn">Quiescent</span>
          <span v-if="l.sendBlockedMacroRunning" class="chip">Macro</span>
        </div>
        <div class="mini-chart mt">
          <div class="muted small mb">{{ t("liveFrames") }}</div>
          <div class="bars">
            <div v-for="(v, i) in history" :key="i" class="bar" :style="{ height: `${Math.min(100, (v / maxHist) * 100)}%` }"></div>
          </div>
        </div>
      </Card>

      <Card :title="t('gateway')" :icon="mdiRouterWireless">
        <div class="kv">
          <span>{{ t("model") }}</span><span>DALI-2 IoT ({{ dev.articleNumber }})</span>
          <span>{{ t("serial") }}</span><span class="mono">{{ dev.serial }}</span>
          <span>GTIN</span><span class="mono">{{ dev.gtin }}</span>
          <span>{{ t("production") }}</span><span>KW {{ dev.productionWeek }} / {{ dev.productionYear }}</span>
          <span>PCB</span><span>{{ dev.pcb }}</span>
          <span>Firmware</span><span>{{ state.info?.version }}</span>
          <span>DALI</span><span>{{ t("protocol") }} {{ desc.protocolVersionMajor }}.{{ desc.protocolVersionMinor }} · {{ desc.lines }} {{ desc.lines === 1 ? t("line") : t("linesWord") }}</span>
          <span>Node-RED</span><span>{{ state.info?.nodeRed ? t("yes") : t("no") }}</span>
          <span>{{ t("startup") }}</span><span>{{ state.info?.startupMode }}</span>
        </div>
        <div v-if="errorsList.length" class="banner err mt">
          <Icon :path="mdiAlertCircle" :size="18" />
          <div><div v-for="(v, k) in state.info.errors" :key="k"><b>{{ k }}</b>: {{ v }}</div></div>
        </div>
      </Card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from "vue";
import {
  mdiAlert,
  mdiAlertCircle,
  mdiCheckCircle,
  mdiGestureTapButton,
  mdiInformationOutline,
  mdiLightbulbGroup,
  mdiLightbulbMultiple,
  mdiLightbulbMultipleOutline,
  mdiLightbulbOn,
  mdiPulse,
  mdiRouterWireless,
  mdiTimelineAlertOutline,
  mdiTransitConnectionVariant,
} from "@mdi/js";
import Card from "../components/Card.vue";
import StatCard from "../components/StatCard.vue";
import Icon from "../components/Icon.vue";
import Toggle from "../components/Toggle.vue";
import Empty from "../components/Empty.vue";
import { api, gw } from "../lib/api";
import { onMonitor, run, state, type AddonEvent, type Zone } from "../lib/store";
import { lang, useT } from "../lib/i18n";
import { fmtTime, isOn, level } from "../lib/dali";

const t = useT({
  de: {
    emergency: "Notlicht",
    devices: "DALI-Geräte",
    onLines: "auf {n} Linie(n)",
    lightsOn: "Eingeschaltet",
    ofTotal: "von {n} Leuchten",
    problems: "Probleme",
    problemsSub: "{u} nicht erreichbar · {f} Fehler",
    allOk: "Alles in Ordnung",
    busActivity: "Busaktivität",
    loadApprox: "≈ {p} % Buslast",
    quick: "Schnellsteuerung",
    allLights: "Alle Leuchten",
    broadcastSub: "Broadcast an alle Geräte",
    noGroups: "Keine Gruppen mit Mitgliedern",
    manageGroups: "Gruppen verwalten",
    events: "Letzte Ereignisse",
    allEvents: "Alle",
    noEvents: "Keine Ereignisse in den letzten 24 Stunden.",
    lines: "DALI-Linien",
    devOnLine: "{n} Geräte",
    bufferFull: "Sendepuffer voll",
    liveFrames: "Frames pro Sekunde (letzte 2 Minuten)",
    gateway: "Gateway",
    model: "Modell",
    serial: "Seriennummer",
    production: "Produktion",
    protocol: "Protokoll",
    linesWord: "Linien",
    startup: "Startmodus",
    st_ok: "OK",
    st_lowPower: "Geringe Busspannung",
    st_noPower: "Keine Busspannung",
    st_notReachable: "Nicht erreichbar",
  },
  en: {
    emergency: "Emergency light",
    devices: "DALI devices",
    onLines: "on {n} line(s)",
    lightsOn: "Switched on",
    ofTotal: "of {n} lights",
    problems: "Problems",
    problemsSub: "{u} unreachable · {f} failures",
    allOk: "All good",
    busActivity: "Bus activity",
    loadApprox: "≈ {p} % bus load",
    quick: "Quick control",
    allLights: "All lights",
    broadcastSub: "Broadcast to all devices",
    noGroups: "No groups with members",
    manageGroups: "Manage groups",
    events: "Recent events",
    allEvents: "All",
    noEvents: "No events in the last 24 hours.",
    lines: "DALI lines",
    devOnLine: "{n} devices",
    bufferFull: "Send buffer full",
    liveFrames: "Frames per second (last 2 minutes)",
    gateway: "Gateway",
    model: "Model",
    serial: "Serial number",
    production: "Production",
    protocol: "Protocol",
    linesWord: "lines",
    startup: "Startup mode",
    st_ok: "OK",
    st_lowPower: "Low bus power",
    st_noPower: "No bus power",
    st_notReachable: "Not reachable",
  },
});

const online = computed(() => !!state.status?.gateway?.connected);
const devices = computed(() => Object.values(state.devices));
const onCount = computed(() => devices.value.filter((d) => isOn(d.features)).length);
const unavailable = computed(() => devices.value.filter((d) => !d.available).length);
const failures = computed(() => devices.value.filter((d) => d.status?.lampFailure || d.status?.controlGearFailure).length);
const problems = computed(() => devices.value.filter((d) => !d.available || d.status?.lampFailure || d.status?.controlGearFailure).length);
const lineCount = computed(() => state.info?.descriptor?.lines ?? 1);
const lineInfos = computed<Record<string, any>>(() => state.info?.lines || {});
const dev = computed(() => state.info?.device || {});
const desc = computed(() => state.info?.descriptor || {});
const errorsList = computed(() => Object.keys(state.info?.errors || {}));

const zones = computed(() => Object.values(state.zones));
const broadcastZone = computed(() => zones.value.find((z) => z.targets.length === 1 && z.targets[0].type === "broadcast" && Object.keys(z.features).length));
const groupZones = computed(() => zones.value.filter((z) => z !== broadcastZone.value && Object.keys(z.features || {}).length));

function zoneName(z: Zone) {
  const m = /^group (\d+)$/.exec(z.name || "");
  return m ? `${t("group")} ${m[1]}` : z.name;
}
function members(z: Zone) {
  const names: string[] = [];
  for (const tg of z.targets) {
    if (tg.type === "group") names.push(...devices.value.filter((d) => d.groups.includes(tg.id as number)).map((d) => d.name));
    else if (tg.type === "device") names.push(state.devices[tg.id as number]?.name ?? `#${tg.id}`);
    else if (tg.type === "broadcast") names.push(t("broadcast"));
  }
  return names.join(", ") || "–";
}
function lineText(s: string) {
  return t(`st_${s}`);
}
async function ctl(target: string, id: number, data: Record<string, unknown>) {
  await run(() => gw.control(target, id, data));
}

// live frame rate
const history = ref<number[]>(Array(60).fill(0));
let count = 0;
let bits = 0;
const rate = ref(0);
const loadPct = ref(0);
const maxHist = computed(() => Math.max(4, ...history.value));
let off: (() => boolean) | null = null;
let timer: number | undefined;
onMounted(() => {
  off = onMonitor((f) => {
    count++;
    bits += (f.bits || 0) + 3;
  });
  timer = window.setInterval(() => {
    const perSec = count / 2;
    history.value = [...history.value.slice(1), perSec];
    rate.value = rate.value * 0.6 + perSec * 0.4;
    loadPct.value = loadPct.value * 0.6 + ((bits / 2) / 1200) * 100 * 0.4;
    count = 0;
    bits = 0;
  }, 2000);
  loadEvents();
});
onUnmounted(() => {
  off?.();
  clearInterval(timer);
});

const fetched = ref<AddonEvent[]>([]);
async function loadEvents() {
  try {
    fetched.value = await api("GET", "events?hours=24&limit=20");
  } catch {
    /* ignore */
  }
}
const recentEvents = computed(() => {
  const seen = new Set<string>();
  return [...state.events, ...fetched.value]
    .filter((e) => {
      const k = `${e.ts}${e.message}`;
      if (seen.has(k)) return false;
      seen.add(k);
      return true;
    })
    .sort((a, b) => b.ts - a.ts)
    .slice(0, 8);
});
</script>

<style scoped>
.mt-sm { margin-top: 6px; }
.quick-row { display: flex; align-items: center; gap: 12px; padding: 8px 0; border-bottom: 1px solid var(--divider); }
.quick-row:last-of-type { border-bottom: 0; }
.quick-row .title { font-weight: 500; }
.mini-range { width: 110px; }
.ev { display: flex; gap: 10px; padding: 7px 0; border-bottom: 1px solid var(--divider); font-size: 13.5px; }
.ev:last-child { border-bottom: 0; }
.ev-icon { margin-top: 1px; color: var(--info); }
.ev-icon.error { color: var(--error); }
.ev-icon.warning { color: var(--warning); }
.bars { display: flex; align-items: flex-end; gap: 2px; height: 60px; }
.bar { flex: 1; background: var(--primary); opacity: .75; border-radius: 2px 2px 0 0; min-height: 1px; transition: height .3s; }
@media (max-width: 700px) { .mini-range { width: 70px; } }
</style>
