<template>
  <div class="setup">
    <div class="card setup-card">
      <img src="../assets/logo.svg" width="64" height="64" alt="" />
      <h1>{{ t("welcome") }}</h1>
      <p class="muted">{{ t("intro") }}</p>

      <button class="btn" :disabled="searching" @click="search">
        <span v-if="searching" class="spinner"></span><Icon v-else :path="mdiMagnify" :size="18" />
        {{ searching ? t("searching") : t("search") }}
      </button>

      <div v-if="found.length" class="list found">
        <div v-for="f in found" :key="f.host" class="list-item clickable" @click="connectTo(f.host)">
          <span class="icon-bubble"><Icon :path="mdiRouterWireless" /></span>
          <div class="grow">
            <div class="title">{{ f.name }}</div>
            <div class="sub">{{ f.host }} · {{ f.version }}</div>
          </div>
          <span class="chip primary">{{ t("connect") }}</span>
        </div>
      </div>
      <div v-else-if="searched" class="muted small">{{ t("nothing") }}</div>

      <div class="divider"></div>
      <div class="field">
        <span>{{ t("manual") }}</span>
        <div class="row">
          <input v-model="host" type="text" placeholder="192.168.0.236" @keyup.enter="connectTo(host)" />
          <button class="btn" :disabled="!host" @click="connectTo(host)">{{ t("connect") }}</button>
        </div>
      </div>
    </div>
  </div>
</template>
<script setup lang="ts">
import { ref } from "vue";
import { mdiMagnify, mdiRouterWireless } from "@mdi/js";
import Icon from "../components/Icon.vue";
import { api } from "../lib/api";
import { run } from "../lib/store";
import { useT } from "../lib/i18n";

const t = useT({
  de: {
    welcome: "Willkommen beim DALI-2 IoT Manager",
    intro: "Es ist noch kein Gateway verbunden. Suche im Netzwerk oder gib die Adresse des Lunatone DALI-2 IoT ein.",
    search: "Netzwerk durchsuchen",
    searching: "Suche läuft…",
    nothing: "Kein Gateway gefunden. Bitte die Adresse manuell eingeben.",
    manual: "Adresse manuell eingeben",
    connect: "Verbinden",
    connected: "Verbunden",
  },
  en: {
    welcome: "Welcome to the DALI-2 IoT Manager",
    intro: "No gateway is connected yet. Search the network or enter the address of the Lunatone DALI-2 IoT.",
    search: "Search network",
    searching: "Searching…",
    nothing: "No gateway found. Please enter the address manually.",
    manual: "Enter address manually",
    connect: "Connect",
    connected: "Connected",
  },
});
const host = ref("");
const found = ref<any[]>([]);
const searching = ref(false);
const searched = ref(false);
async function search() {
  searching.value = true;
  found.value = (await run(() => api("POST", "discover"))) || [];
  searching.value = false;
  searched.value = true;
}
async function connectTo(h: string) {
  if (!h) return;
  await run(() => api("POST", "gateway", { host: h.trim() }), t("connected"));
}
</script>
<style scoped>
.setup { display: flex; justify-content: center; padding-top: 6vh; }
.setup-card { max-width: 520px; width: 100%; padding: 28px; display: flex; flex-direction: column; gap: 14px; align-items: stretch; text-align: center; }
.setup-card img { align-self: center; }
.found { text-align: left; border: 1px solid var(--divider); border-radius: 12px; }
.field { text-align: left; }
</style>
