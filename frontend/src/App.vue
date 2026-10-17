<template>
  <div class="shell" :class="{ collapsed: navCollapsed }">
    <aside class="sidebar">
      <div class="brand">
        <img src="./assets/logo.svg" alt="" width="34" height="34" />
        <div class="brand-text">
          <div class="brand-title">{{ state.info?.name || "DALI-2 IoT" }}</div>
          <div class="brand-sub">
            <span class="dot" :class="online ? 'ok pulse' : 'err'"></span>
            {{ online ? t("connected") : state.wsConnected ? t("gatewayOffline") : t("reconnecting") }}
          </div>
        </div>
      </div>
      <nav>
        <RouterLink v-for="item in visibleNav" :key="item.to" :to="item.to" class="nav-item" :title="item.label">
          <Icon :path="item.icon" :size="21" />
          <span class="nav-label">{{ item.label }}</span>
          <span v-if="item.badge" class="chip err nav-badge">{{ item.badge }}</span>
        </RouterLink>
      </nav>
      <div class="sidebar-foot">
        <label class="row expert" :title="t('expertMode')">
          <Icon :path="mdiShieldAlertOutline" :size="19" />
          <span class="nav-label grow">{{ t("expertMode") }}</span>
          <Toggle :model-value="state.expert" @change="setExpert" />
        </label>
        <div class="row lang nav-label">
          <div class="btn-group">
            <button :class="{ active: lang === 'de' }" @click="setLang('de')">DE</button>
            <button :class="{ active: lang === 'en' }" @click="setLang('en')">EN</button>
          </div>
          <span class="faint small">v{{ state.status?.version }}</span>
        </div>
      </div>
    </aside>

    <main class="main">
      <div v-if="state.status && !state.status.gateway?.host" class="page">
        <SetupGateway />
      </div>
      <template v-else>
        <div v-if="state.status && !online" class="offline-banner">
          <Icon :path="mdiLanDisconnect" :size="18" />
          {{ t("gatewayOffline") }} ({{ state.status.gateway?.host }})
          <span v-if="state.status.gateway?.last_error" class="faint small">– {{ state.status.gateway.last_error }}</span>
        </div>
        <RouterView v-slot="{ Component }">
          <component :is="Component" />
        </RouterView>
      </template>
    </main>

    <nav class="bottom-nav">
      <RouterLink v-for="item in mobileNav" :key="item.to" :to="item.to" class="bn-item">
        <Icon :path="item.icon" :size="22" />
        <span>{{ item.short || item.label }}</span>
      </RouterLink>
      <button class="bn-item" @click="moreOpen = true">
        <Icon :path="mdiDotsHorizontal" :size="22" />
        <span>{{ t("more") }}</span>
      </button>
    </nav>

    <Modal :open="moreOpen" :title="t('more')" @close="moreOpen = false">
      <div class="list">
        <RouterLink v-for="item in visibleNav" :key="item.to" :to="item.to" class="list-item clickable" @click="moreOpen = false">
          <span class="icon-bubble"><Icon :path="item.icon" :size="20" /></span>
          <span class="title">{{ item.label }}</span>
        </RouterLink>
        <label class="list-item">
          <span class="icon-bubble warn"><Icon :path="mdiShieldAlertOutline" :size="20" /></span>
          <span class="title grow">{{ t("expertMode") }}</span>
          <Toggle :model-value="state.expert" @change="setExpert" />
        </label>
        <div class="list-item">
          <span class="icon-bubble off"><Icon :path="mdiTranslate" :size="20" /></span>
          <span class="title grow">Sprache / Language</span>
          <div class="btn-group">
            <button :class="{ active: lang === 'de' }" @click="setLang('de')">DE</button>
            <button :class="{ active: lang === 'en' }" @click="setLang('en')">EN</button>
          </div>
        </div>
      </div>
    </Modal>

    <ConfirmHost />
    <ToastHost />
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import {
  mdiChartBox,
  mdiCog,
  mdiDotsHorizontal,
  mdiLanDisconnect,
  mdiLightbulbGroup,
  mdiMotionSensor,
  mdiRobot,
  mdiShieldAlertOutline,
  mdiShieldCheckOutline,
  mdiTools,
  mdiTranslate,
  mdiTransitConnectionVariant,
  mdiViewDashboard,
  mdiVectorSquare,
} from "@mdi/js";
import Icon from "./components/Icon.vue";
import Toggle from "./components/Toggle.vue";
import Modal from "./components/Modal.vue";
import ConfirmHost from "./components/ConfirmHost.vue";
import ToastHost from "./components/ToastHost.vue";
import SetupGateway from "./views/SetupGateway.vue";
import { setExpert, state } from "./lib/store";
import { lang, setLang, useT } from "./lib/i18n";

const t = useT({
  de: {
    overview: "Übersicht",
    lights: "Geräte",
    groups: "Gruppen & Zonen",
    groupsShort: "Gruppen",
    sensors: "Sensoren & Taster",
    sensorsShort: "Sensoren",
    automations: "Automationen",
    direct: "Direktsteuerung",
    bus: "DALI-Bus",
    analytics: "Analysen",
    system: "System",
    expert: "Experte",
    connected: "Verbunden",
    more: "Mehr",
  },
  en: {
    overview: "Overview",
    lights: "Devices",
    groups: "Groups & zones",
    groupsShort: "Groups",
    sensors: "Sensors & buttons",
    sensorsShort: "Sensors",
    automations: "Automations",
    direct: "Direct control",
    bus: "DALI bus",
    analytics: "Analytics",
    system: "System",
    expert: "Expert",
    connected: "Connected",
    more: "More",
  },
});

const navCollapsed = ref(false);
const moreOpen = ref(false);
const online = computed(() => !!state.status?.gateway?.connected);
const failures = computed(
  () =>
    Object.values(state.devices).filter((d) => !d.available || d.status?.lampFailure || d.status?.controlGearFailure).length,
);

const nav = computed(() => [
  { to: "/", label: t("overview"), icon: mdiViewDashboard },
  { to: "/devices", label: t("lights"), icon: mdiLightbulbGroup, badge: failures.value || "" },
  { to: "/groups", label: t("groups"), short: t("groupsShort"), icon: mdiVectorSquare },
  { to: "/sensors", label: t("sensors"), short: t("sensorsShort"), icon: mdiMotionSensor },
  { to: "/direct", label: t("direct"), icon: mdiShieldCheckOutline },
  { to: "/automations", label: t("automations"), icon: mdiRobot },
  { to: "/bus", label: t("bus"), icon: mdiTransitConnectionVariant },
  { to: "/analytics", label: t("analytics"), icon: mdiChartBox },
  { to: "/system", label: t("system"), icon: mdiCog },
  { to: "/expert", label: t("expert"), icon: mdiTools, expert: true },
]);
const visibleNav = computed(() => nav.value.filter((n) => !n.expert || state.expert));
const mobileNav = computed(() => nav.value.filter((n) => ["/", "/devices", "/bus", "/analytics"].includes(n.to)));
</script>

<style scoped>
.shell { display: flex; min-height: 100vh; }
.sidebar {
  width: var(--sidebar-w); flex-shrink: 0; background: var(--card); border-right: 1px solid var(--divider);
  display: flex; flex-direction: column; position: sticky; top: 0; height: 100vh;
}
.brand { display: flex; gap: 10px; align-items: center; padding: 16px 16px 14px; border-bottom: 1px solid var(--divider); }
.brand-title { font-weight: 600; font-size: 15px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 160px; }
.brand-sub { font-size: 12px; color: var(--text2); display: flex; align-items: center; gap: 6px; }
.sidebar nav { padding: 8px; display: flex; flex-direction: column; gap: 2px; overflow-y: auto; flex: 1; }
.nav-item { display: flex; align-items: center; gap: 14px; padding: 0 12px; height: 42px; border-radius: 10px; color: var(--text2); font-weight: 500; font-size: 14px; }
.nav-item:hover { background: var(--hover); color: var(--text); }
.nav-item.router-link-exact-active, .nav-item.router-link-active:not([href="#/"]) { background: var(--primary-soft); color: var(--primary); }
.nav-badge { margin-left: auto; height: 20px; padding: 0 7px; }
.sidebar-foot { border-top: 1px solid var(--divider); padding: 10px 14px 14px; display: flex; flex-direction: column; gap: 10px; }
.expert { color: var(--text2); gap: 12px; cursor: pointer; font-size: 13.5px; }
.lang { justify-content: space-between; }
.main { flex: 1; min-width: 0; }
.offline-banner { display: flex; gap: 8px; align-items: center; background: color-mix(in srgb, var(--error) 12%, var(--card)); color: var(--error); padding: 8px 20px; font-size: 13.5px; position: sticky; top: 0; z-index: 5; }
.bottom-nav { display: none; }
@media (max-width: 700px) {
  .sidebar { display: none; }
  .bottom-nav {
    display: flex; position: fixed; bottom: 0; left: 0; right: 0; background: var(--card); border-top: 1px solid var(--divider);
    z-index: 50; padding-bottom: env(safe-area-inset-bottom);
  }
  .bn-item { flex: 1; display: flex; flex-direction: column; align-items: center; gap: 2px; padding: 8px 0 6px; color: var(--text2); font-size: 11px; background: none; border: 0; cursor: pointer; }
  .bn-item.router-link-exact-active, .bn-item.router-link-active:not([href="#/"]) { color: var(--primary); }
}
</style>
