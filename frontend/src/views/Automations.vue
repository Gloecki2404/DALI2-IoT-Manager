<template>
  <div class="page automations">
    <div class="page-head">
      <span class="icon-bubble"><Icon :path="mdiRobot" :size="22" /></span>
      <div class="grow head-text">
        <h1>{{ t("title") }}</h1>
        <div class="muted small head-sub">
          <Icon :path="mdiShieldCheckOutline" :size="15" />
          <span>{{ t("subtitle") }}</span>
        </div>
      </div>
      <button class="btn flat" :disabled="refreshing" :title="t('refresh')" @click="refresh">
        <span v-if="refreshing" class="spinner"></span><Icon v-else :path="mdiRefresh" :size="18" />
        <span class="hide-xs">{{ t("refresh") }}</span>
      </button>
    </div>

    <Tabs v-model="tab" :tabs="tabs" />

    <div v-if="!auto.loaded" class="loading">
      <span class="spinner"></span>
      <span class="muted">{{ t("loading") }}</span>
    </div>
    <template v-else>
      <SequencesTab v-if="tab === 'sequences'" />
      <SchedulesTab v-else-if="tab === 'schedules'" />
      <CircadianTab v-else-if="tab === 'circadian'" />
      <TriggerActionsTab v-else-if="tab === 'triggers'" />
      <EventForwardingTab v-else-if="tab === 'events'" />
      <StatusQueriesTab v-else-if="tab === 'queries'" />
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import {
  mdiCalendarClock,
  mdiCallSplit,
  mdiPlaylistPlay,
  mdiRadar,
  mdiRefresh,
  mdiRobot,
  mdiShieldCheckOutline,
  mdiSwapHorizontalBold,
  mdiThemeLightDark,
} from "@mdi/js";
import Icon from "../components/Icon.vue";
import Tabs from "../components/Tabs.vue";
import SequencesTab from "../components/automation/SequencesTab.vue";
import SchedulesTab from "../components/automation/SchedulesTab.vue";
import CircadianTab from "../components/automation/CircadianTab.vue";
import TriggerActionsTab from "../components/automation/TriggerActionsTab.vue";
import EventForwardingTab from "../components/automation/EventForwardingTab.vue";
import StatusQueriesTab from "../components/automation/StatusQueriesTab.vue";
import { state } from "../lib/store";
import { useAT } from "../components/automation/i18n";
import { auto, loadAll, startPolling, stopPolling } from "../components/automation/data";

const t = useAT();
const route = useRoute();
const router = useRouter();

const TAB_IDS = ["sequences", "schedules", "circadian", "triggers", "events", "queries"];
const initial = String(route.query.tab || "");
const tab = ref(TAB_IDS.includes(initial) ? initial : "sequences");
watch(tab, (v) => {
  if (route.query.tab !== v) router.replace({ query: { ...route.query, tab: v } });
});
watch(
  () => route.query.tab,
  (v) => {
    if (typeof v === "string" && TAB_IDS.includes(v) && v !== tab.value) tab.value = v;
  },
);

const tabs = computed(() => {
  const running = auto.sequences.filter((s) => s.active).length;
  return [
    { id: "sequences", label: t("tabSequences"), icon: mdiPlaylistPlay, badge: running ? `▶ ${running}` : auto.sequences.length || "" },
    { id: "schedules", label: t("tabSchedules"), icon: mdiCalendarClock, badge: auto.schedules.length || "" },
    { id: "circadian", label: t("tabCircadian"), icon: mdiThemeLightDark, badge: auto.circadians.length || "" },
    { id: "triggers", label: t("tabTriggers"), icon: mdiCallSplit, badge: auto.triggers.length || "" },
    { id: "events", label: t("tabEvents"), icon: mdiSwapHorizontalBold, badge: auto.events.length || "" },
    { id: "queries", label: t("tabQueries"), icon: mdiRadar, badge: Object.keys(auto.queries).length || "" },
  ];
});

const refreshing = ref(false);
async function refresh() {
  refreshing.value = true;
  await loadAll();
  refreshing.value = false;
}

onMounted(() => {
  refresh();
  startPolling();
});
onBeforeUnmount(stopPolling);

// Reload once the gateway comes back online.
watch(
  () => !!state.status?.gateway?.connected,
  (online, before) => {
    if (online && before === false) refresh();
  },
);
</script>

<style scoped>
.head-text { min-width: 0; }
.head-sub { display: flex; gap: 6px; align-items: flex-start; margin-top: 2px; max-width: 820px; }
.head-sub svg { margin-top: 1px; color: var(--success); }
.loading { display: flex; align-items: center; gap: 10px; justify-content: center; padding: 48px 0; }
@media (max-width: 480px) {
  .hide-xs { display: none; }
}
</style>

<style>
/* Shared layout helpers for the automation tabs (namespaced; editors are teleported to <body>). */
.automations .tab-intro { color: var(--text2); margin: 0 0 14px; max-width: 920px; font-size: 13.5px; line-height: 1.5; }
.automations .tab-toolbar { display: flex; align-items: center; gap: 12px; margin-bottom: 14px; flex-wrap: wrap; }
.automations .empty-hint { max-width: 480px; margin-top: -4px; }
.automations button.chip, .auto-editor button.chip { border: 0; font-family: inherit; cursor: pointer; }
.automations button.chip:disabled, .auto-editor button.chip:disabled { cursor: not-allowed; opacity: .6; }
.auto-editor .section-title:first-child { margin-top: 0; }
.auto-editor .add-row {
  display: flex; align-items: center; justify-content: center; gap: 6px; width: 100%; height: 44px; margin-top: 2px;
  border: 1.5px dashed var(--divider); border-radius: 12px; background: transparent; color: var(--primary);
  font: inherit; font-weight: 500; cursor: pointer; transition: background .15s, border-color .15s;
}
.auto-editor .add-row:hover { background: var(--primary-soft); border-color: color-mix(in srgb, var(--primary) 40%, transparent); }
.auto-editor .add-row:disabled { opacity: .5; cursor: not-allowed; }
/* The editors are modals themselves – keep confirm dialogs (discard / delete) above them. */
</style>
