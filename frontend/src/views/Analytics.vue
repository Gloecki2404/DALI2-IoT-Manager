<template>
  <div class="page">
    <div class="page-head">
      <h1>{{ t("title") }}</h1>
      <div v-if="tab !== 'health'" class="btn-group range" role="group" :aria-label="t('range')">
        <button v-for="r in RANGES" :key="r.h" :class="{ active: hours === r.h }" @click="hours = r.h">{{ r[lang] }}</button>
      </div>
      <span v-else class="small muted">{{ t("healthNow") }}</span>
      <button class="btn icon" :title="t('refresh')" @click="refresh++"><Icon :path="mdiRefresh" /></button>
    </div>

    <Tabs v-model="tab" :tabs="tabs" />

    <KeepAlive>
      <HealthTab v-if="tab === 'health'" :hours="hours" :refresh="refresh" />
      <BusLoadTab v-else-if="tab === 'bus'" :hours="hours" :refresh="refresh" />
      <QualityTab v-else-if="tab === 'quality'" :hours="hours" :refresh="refresh" />
      <UsageTab v-else-if="tab === 'usage'" :hours="hours" :refresh="refresh" />
      <EnergyTab v-else-if="tab === 'energy'" :hours="hours" :refresh="refresh" />
      <EventsTab v-else-if="tab === 'events'" :hours="hours" :refresh="refresh" />
    </KeepAlive>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { mdiCableData, mdiChartBar, mdiHeartPulse, mdiLightbulbOnOutline, mdiLightningBolt, mdiRefresh, mdiTimelineClockOutline } from "@mdi/js";
import Tabs from "../components/Tabs.vue";
import Icon from "../components/Icon.vue";
import HealthTab from "../components/analytics/HealthTab.vue";
import BusLoadTab from "../components/analytics/BusLoadTab.vue";
import QualityTab from "../components/analytics/QualityTab.vue";
import UsageTab from "../components/analytics/UsageTab.vue";
import EnergyTab from "../components/analytics/EnergyTab.vue";
import EventsTab from "../components/analytics/EventsTab.vue";
import { useInterval } from "../components/analytics/util";
import { state } from "../lib/store";
import { lang, useT } from "../lib/i18n";

const t = useT({
  de: {
    title: "Analysen",
    range: "Zeitraum",
    healthNow: "Aktueller Zustand",
    health: "Gesundheit",
    bus: "Buslast",
    quality: "Kommunikation",
    usage: "Nutzung",
    energy: "Energie & Diagnose",
    events: "Ereignisse",
  },
  en: {
    title: "Analytics",
    range: "Time range",
    healthNow: "Current state",
    health: "Health",
    bus: "Bus load",
    quality: "Communication",
    usage: "Usage",
    energy: "Energy & diagnostics",
    events: "Events",
  },
});

const RANGES = [
  { h: 1, de: "1 h", en: "1 h" },
  { h: 6, de: "6 h", en: "6 h" },
  { h: 24, de: "24 h", en: "24 h" },
  { h: 168, de: "7 T", en: "7 d" },
  { h: 720, de: "30 T", en: "30 d" },
];

const RANGE_KEY = "lunatone.analytics.hours";
function initialHours(): number {
  try {
    const v = Number(localStorage.getItem(RANGE_KEY));
    if (RANGES.some((r) => r.h === v)) return v;
  } catch {
    /* storage unavailable */
  }
  return 24;
}
const hours = ref(initialHours());
watch(hours, (h) => {
  try {
    localStorage.setItem(RANGE_KEY, String(h));
  } catch {
    /* ignore */
  }
});

const refresh = ref(0);
// silent auto refresh of the visible tab
useInterval(() => refresh.value++, 60000);

const route = useRoute();
const router = useRouter();
const TAB_IDS = ["health", "bus", "quality", "usage", "energy", "events"];
const tab = computed<string>({
  get: () => (TAB_IDS.includes(String(route.query.tab)) ? String(route.query.tab) : "health"),
  set: (v) => {
    router.replace({ query: { ...route.query, tab: v === "health" ? undefined : v } });
  },
});

const problems = computed(
  () => Object.values(state.devices).filter((d) => !d.available || d.status?.lampFailure || d.status?.controlGearFailure).length,
);

const tabs = computed(() => [
  { id: "health", label: t("health"), icon: mdiHeartPulse, badge: problems.value || undefined },
  { id: "bus", label: t("bus"), icon: mdiChartBar },
  { id: "quality", label: t("quality"), icon: mdiCableData },
  { id: "usage", label: t("usage"), icon: mdiLightbulbOnOutline },
  { id: "energy", label: t("energy"), icon: mdiLightningBolt },
  { id: "events", label: t("events"), icon: mdiTimelineClockOutline },
]);
</script>

<style scoped>
.range button { min-width: 44px; }
@media (max-width: 700px) {
  .page-head h1 { min-width: 0; }
  .range { order: 3; width: 100%; display: flex; }
  .range button { flex: 1; min-width: 0; padding: 0 6px; }
}
</style>
