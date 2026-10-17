<template>
  <div class="page">
    <div class="page-head">
      <h1>{{ t("title") }}</h1>
      <span class="chip" :class="online ? 'ok' : 'err'">
        <span class="dot" :class="online ? 'ok pulse' : 'err'"></span>
        {{ online ? t("gwOnline") : t("gwOffline") }}
      </span>
    </div>

    <Tabs v-model="tab" :tabs="tabs" />

    <KeepAlive>
      <BusMonitor v-if="tab === 'monitor'" @use-frame="useFrame" />
      <BusScan v-else-if="tab === 'scan'" />
      <BusLines v-else-if="tab === 'lines'" />
      <BusCommands v-else-if="tab === 'commands' && state.expert" />
      <div v-else-if="tab === 'commands'" class="card">
        <Empty :icon="mdiLock" :text="t('expertOnly')">
          <p class="small muted hint">{{ t("expertHint") }}</p>
          <button class="btn" @click="setExpert(true)">
            <Icon :path="mdiShieldAlertOutline" :size="18" />{{ t("enableExpert") }}
          </button>
        </Empty>
      </div>
    </KeepAlive>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { useRoute, useRouter } from "vue-router";
import { mdiConsoleLine, mdiLan, mdiLock, mdiMagnifyScan, mdiShieldAlertOutline, mdiTransitConnectionVariant } from "@mdi/js";
import Tabs from "../components/Tabs.vue";
import Empty from "../components/Empty.vue";
import Icon from "../components/Icon.vue";
import BusMonitor from "../components/bus/BusMonitor.vue";
import BusScan from "../components/bus/BusScan.vue";
import BusLines from "../components/bus/BusLines.vue";
import BusCommands from "../components/bus/BusCommands.vue";
import { commandDraft, type Frame } from "../components/bus/frames";
import { gatewayOnline, setExpert, state } from "../lib/store";
import { useT } from "../lib/i18n";

const t = useT({
  de: {
    title: "DALI-Bus",
    gwOnline: "Gateway verbunden",
    gwOffline: "Gateway getrennt",
    monitor: "Busmonitor",
    scan: "Scan",
    lines: "Linien",
    commands: "Befehle",
    expertOnly: "Das direkte Senden von DALI-Befehlen ist nur im Expertenmodus verfügbar.",
    expertHint: "Rohe DALI-Frames können Geräte dauerhaft umkonfigurieren (Adressen, Gruppen, Szenen). Aktiviere den Expertenmodus nur, wenn du weißt, was du tust.",
    enableExpert: "Expertenmodus aktivieren",
  },
  en: {
    title: "DALI bus",
    gwOnline: "Gateway connected",
    gwOffline: "Gateway disconnected",
    monitor: "Bus monitor",
    scan: "Scan",
    lines: "Lines",
    commands: "Commands",
    expertOnly: "Sending raw DALI commands is only available in expert mode.",
    expertHint: "Raw DALI frames can permanently reconfigure devices (addresses, groups, scenes). Only enable expert mode if you know what you are doing.",
    enableExpert: "Enable expert mode",
  },
});

const route = useRoute();
const router = useRouter();
const TAB_IDS = ["monitor", "scan", "lines", "commands"];
const tab = computed<string>({
  get: () => (TAB_IDS.includes(String(route.query.tab)) ? String(route.query.tab) : "monitor"),
  set: (v) => {
    router.replace({ query: { ...route.query, tab: v === "monitor" ? undefined : v } });
  },
});

const online = computed(() => gatewayOnline());
const scanRunning = computed(() => ["in progress", "addressing"].includes(state.scan?.status));
const lineIssues = computed(() => Object.values<any>(state.info?.lines || {}).filter((l) => l?.lineStatus && l.lineStatus !== "ok").length);

const tabs = computed(() => [
  { id: "monitor", label: t("monitor"), icon: mdiTransitConnectionVariant },
  { id: "scan", label: t("scan"), icon: mdiMagnifyScan, badge: scanRunning.value ? `${Math.round(state.scan?.progress || 0)} %` : undefined },
  { id: "lines", label: t("lines"), icon: mdiLan, badge: lineIssues.value || undefined },
  { id: "commands", label: t("commands"), icon: state.expert ? mdiConsoleLine : mdiLock },
]);

function useFrame(f: Frame) {
  commandDraft.value = { line: f.line, frames: [[...(f.data || [])]] };
  tab.value = "commands";
}
</script>

<style scoped>
.hint { max-width: 520px; margin: 0; }
</style>
