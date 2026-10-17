<template>
  <div class="page">
    <div class="page-head">
      <h1>{{ t("title") }}</h1>
    </div>
    <Tabs v-model="tab" :tabs="tabs" />

    <!-- ------------------------------------------------------------ groups -->
    <template v-if="tab === 'groups'">
      <div class="banner info mb">
        <Icon :path="mdiInformationOutline" :size="18" />
        <div>{{ t("groupsInfo") }}</div>
      </div>

      <div v-if="usedGroups.length" class="grid cols-3 mb">
        <Card v-for="g in usedGroups" :key="g" :title="`${t('group')} ${g}`" :subtitle="membersOf(g).map((d) => d.name).join(', ')" :icon="mdiLightbulbMultiple">
          <LightControl :features="groupFeatures(g)" target="group" :target-id="g" :show-scenes="true" />
        </Card>
      </div>

      <Card :title="t('matrix')" :subtitle="t('matrixSub')" flush>
        <template #actions>
          <span v-if="dirtyCount" class="chip warn">{{ t("unsaved", { n: dirtyCount }) }}</span>
          <button class="btn flat sm" :disabled="!dirtyCount" @click="resetMatrix">{{ t("cancel") }}</button>
          <button class="btn sm" :disabled="!dirtyCount || saving" @click="saveMatrix">
            <span v-if="saving" class="spinner"></span>{{ t("save") }}
          </button>
        </template>
        <div class="table-wrap">
          <table class="table matrix">
            <thead>
              <tr>
                <th class="sticky-col">{{ t("device") }}</th>
                <th v-for="g in 16" :key="g" class="center gcol" :class="{ used: usedGroups.includes(g - 1) }">{{ g - 1 }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="d in devices" :key="d.id">
                <td class="sticky-col">
                  <div class="title">{{ d.name }}</div>
                  <div class="faint small">A{{ d.address }}<span v-if="lineCount > 1"> · L{{ d.line }}</span></div>
                </td>
                <td v-for="g in 16" :key="g" class="center cell" :class="{ changed: isChanged(d.id, g - 1) }" @click="flip(d.id, g - 1)">
                  <span class="check" :class="{ on: matrix[d.id]?.includes(g - 1) }">
                    <Icon v-if="matrix[d.id]?.includes(g - 1)" :path="mdiCheck" :size="16" />
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </Card>
    </template>

    <!-- ------------------------------------------------------------- zones -->
    <template v-else>
      <div class="row between mb wrap">
        <div class="muted">{{ t("zonesInfo") }}</div>
        <button class="btn" @click="openZone(null)"><Icon :path="mdiPlus" :size="18" />{{ t("newZone") }}</button>
      </div>
      <div class="grid cols-3">
        <Card v-for="z in zoneList" :key="z.id" :title="zoneName(z)" :icon="z.targets[0]?.type === 'broadcast' ? mdiLightbulbGroup : mdiVectorSquare">
          <template #actions>
            <button class="btn icon sm" :title="t('edit')" @click="openZone(z)"><Icon :path="mdiPencil" :size="18" /></button>
            <button class="btn icon sm" :title="t('delete')" @click="deleteZone(z)"><Icon :path="mdiDelete" :size="18" /></button>
          </template>
          <div class="row wrap mb">
            <span v-for="(tg, i) in z.targets" :key="i" class="chip primary">{{ targetLabel(tg, state.devices, state.zones, t) }}</span>
          </div>
          <LightControl v-if="Object.keys(z.features || {}).length" :features="z.features" target="zone" :target-id="z.id" :show-scenes="false" />
          <div v-else class="faint small">{{ t("noFeatures") }}</div>
        </Card>
      </div>
      <Empty v-if="!zoneList.length" :icon="mdiVectorSquare" :text="t('noZones')" />
      <div v-if="state.expert && zoneList.length" class="mt-lg">
        <button class="btn danger outline sm" @click="deleteAllZones"><Icon :path="mdiDeleteSweep" :size="16" />{{ t("deleteAll") }}</button>
      </div>
    </template>

    <Modal :open="zoneEdit.open" :title="zoneEdit.id === null ? t('newZone') : t('editZone')" :icon="mdiVectorSquare" @close="zoneEdit.open = false">
      <div class="col gap-lg">
        <label class="field"><span>{{ t("name") }}</span><input v-model="zoneEdit.name" type="text" /></label>
        <div class="field">
          <span>{{ t("targets") }}</span>
          <TargetPicker v-model="zoneEdit.targets" :types="['device', 'group', 'broadcast']" />
        </div>
        <div class="faint small">{{ t("zoneHint") }}</div>
      </div>
      <template #footer>
        <button class="btn flat" @click="zoneEdit.open = false">{{ t("cancel") }}</button>
        <button class="btn" :disabled="!zoneEdit.targets.length" @click="saveZone">{{ t("save") }}</button>
      </template>
    </Modal>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from "vue";
import {
  mdiCheck,
  mdiDelete,
  mdiDeleteSweep,
  mdiInformationOutline,
  mdiLightbulbGroup,
  mdiLightbulbMultiple,
  mdiPencil,
  mdiPlus,
  mdiVectorSquare,
} from "@mdi/js";
import Card from "../components/Card.vue";
import Icon from "../components/Icon.vue";
import Tabs from "../components/Tabs.vue";
import Modal from "../components/Modal.vue";
import Empty from "../components/Empty.vue";
import LightControl from "../components/LightControl.vue";
import TargetPicker from "../components/TargetPicker.vue";
import { gw } from "../lib/api";
import { confirmDialog, run, state, type Target, type Zone } from "../lib/store";
import { useT } from "../lib/i18n";
import { targetLabel } from "../lib/dali";

const t = useT({
  de: {
    title: "Gruppen & Zonen",
    groupsTab: "DALI-Gruppen",
    zonesTab: "Zonen",
    groupsInfo: "DALI-Gruppen werden direkt in den Betriebsgeräten gespeichert (max. 16 pro Linie). Ein Gerät kann in mehreren Gruppen sein. Gruppenbefehle sind schnell und synchron.",
    matrix: "Gruppenzuordnung",
    matrixSub: "Klicke auf ein Feld, um ein Gerät einer Gruppe hinzuzufügen oder zu entfernen.",
    unsaved: "{n} Änderung(en)",
    zonesInfo: "Zonen sind virtuelle Zusammenfassungen im Gateway aus Geräten, Gruppen oder Broadcasts – auch linienübergreifend.",
    newZone: "Neue Zone",
    editZone: "Zone bearbeiten",
    noFeatures: "Keine steuerbaren Funktionen (Zone ohne Mitglieder)",
    noZones: "Noch keine Zonen vorhanden.",
    deleteAll: "Alle Zonen löschen",
    zoneHint: "Tipp: Gruppen-Ziele nutzen DALI-Gruppenbefehle (schnell, synchron). Einzelne Geräte werden nacheinander angesteuert.",
    confirmDeleteZone: "Zone „{name}“ löschen?",
    confirmDeleteAll: "Wirklich ALLE Zonen löschen? Die Standard-Zonen (Broadcast, Gruppen) werden vom Gateway neu angelegt.",
  },
  en: {
    title: "Groups & zones",
    groupsTab: "DALI groups",
    zonesTab: "Zones",
    groupsInfo: "DALI groups are stored inside the control gear (max. 16 per line). A device can be in several groups. Group commands are fast and synchronous.",
    matrix: "Group assignment",
    matrixSub: "Click a cell to add a device to a group or remove it.",
    unsaved: "{n} change(s)",
    zonesInfo: "Zones are virtual collections on the gateway made of devices, groups or broadcasts – even across lines.",
    newZone: "New zone",
    editZone: "Edit zone",
    noFeatures: "No controllable features (zone without members)",
    noZones: "No zones yet.",
    deleteAll: "Delete all zones",
    zoneHint: "Tip: group targets use DALI group commands (fast, synchronous). Individual devices are addressed one after another.",
    confirmDeleteZone: "Delete zone “{name}”?",
    confirmDeleteAll: "Really delete ALL zones? The default zones (broadcast, groups) are re-created by the gateway.",
  },
});

const tab = ref("groups");
const tabs = computed(() => [
  { id: "groups", label: t("groupsTab"), icon: mdiLightbulbMultiple },
  { id: "zones", label: t("zonesTab"), icon: mdiVectorSquare, badge: zoneList.value.length || undefined },
]);
const lineCount = computed(() => Number(state.info?.descriptor?.lines ?? 1));
const devices = computed(() => Object.values(state.devices).sort((a, b) => a.line - b.line || a.address - b.address));
const usedGroups = computed(() => [...new Set(devices.value.flatMap((d) => d.groups))].sort((a, b) => a - b));
const membersOf = (g: number) => devices.value.filter((d) => d.groups.includes(g));

function groupFeatures(g: number) {
  const zone = Object.values(state.zones).find((z) => z.targets.length === 1 && z.targets[0].type === "group" && z.targets[0].id === g);
  if (zone && Object.keys(zone.features || {}).length) return zone.features;
  return membersOf(g)[0]?.features || {};
}

// ---------------------------------------------------------------- matrix
const matrix = reactive<Record<number, number[]>>({});
function resetMatrix() {
  for (const d of devices.value) matrix[d.id] = [...d.groups];
}
watch(() => devices.value.map((d) => `${d.id}:${d.groups.join(",")}`).join("|"), resetMatrix, { immediate: true });
const isChanged = (id: number, g: number) => (state.devices[id]?.groups.includes(g) ?? false) !== (matrix[id]?.includes(g) ?? false);
const dirtyIds = computed(() => devices.value.filter((d) => [...Array(16).keys()].some((g) => isChanged(d.id, g))).map((d) => d.id));
const dirtyCount = computed(() => dirtyIds.value.length);
function flip(id: number, g: number) {
  const list = matrix[id] || (matrix[id] = []);
  const i = list.indexOf(g);
  if (i >= 0) list.splice(i, 1);
  else list.push(g);
}
const saving = ref(false);
async function saveMatrix() {
  saving.value = true;
  for (const id of dirtyIds.value) {
    const groups = [...matrix[id]].sort((a, b) => a - b);
    const res = await run(() => gw.put(`/device/${id}`, { groups }));
    if (res !== undefined && state.devices[id]) state.devices[id].groups = res?.groups ?? groups;
  }
  saving.value = false;
}

// ----------------------------------------------------------------- zones
const zoneList = computed(() => Object.values(state.zones).sort((a, b) => a.id - b.id));
function zoneName(z: Zone) {
  const m = /^group (\d+)$/.exec(z.name || "");
  if (m) return `${t("group")} ${m[1]}`;
  if (z.name === "broadcast") return t("broadcast");
  return z.name || `${t("zone")} ${z.id}`;
}
const zoneEdit = reactive({ open: false, id: null as number | null, name: "", targets: [] as Target[] });
function openZone(z: Zone | null) {
  zoneEdit.id = z?.id ?? null;
  zoneEdit.name = z?.name ?? "";
  zoneEdit.targets = z ? z.targets.map((x) => ({ ...x })) : [];
  zoneEdit.open = true;
}
async function reloadZones() {
  const res = await gw.get("/zones");
  state.zones = Object.fromEntries((res?.zones || []).map((z: Zone) => [z.id, z]));
}
async function saveZone() {
  const body = { name: zoneEdit.name, targets: zoneEdit.targets };
  const ok = await run(
    () => (zoneEdit.id === null ? gw.post("/zone", body) : gw.put(`/zone/${zoneEdit.id}`, body)),
    t("saved"),
  );
  if (ok !== undefined) {
    zoneEdit.open = false;
    await run(reloadZones);
  }
}
async function deleteZone(z: Zone) {
  if (!(await confirmDialog({ title: t("delete"), message: t("confirmDeleteZone", { name: zoneName(z) }), danger: true, confirmText: t("delete") }))) return;
  await run(() => gw.del(`/zone/${z.id}`), t("saved"));
  await run(reloadZones);
}
async function deleteAllZones() {
  if (!(await confirmDialog({ title: t("deleteAll"), message: t("confirmDeleteAll"), danger: true, confirmText: t("delete") }))) return;
  await run(() => gw.del("/zones"), t("saved"));
  await run(reloadZones);
}
</script>

<style scoped>
.matrix th, .matrix td { padding: 6px 4px; }
.matrix .sticky-col { position: sticky; left: 0; background: var(--card); z-index: 2; padding-left: 16px; min-width: 170px; }
.matrix .title { font-weight: 500; }
.gcol { width: 38px; color: var(--text3); }
.gcol.used { color: var(--primary); }
.cell { cursor: pointer; }
.cell.changed { background: color-mix(in srgb, var(--warning) 18%, transparent) !important; }
.check { width: 24px; height: 24px; border-radius: 6px; border: 2px solid var(--divider); display: inline-flex; align-items: center; justify-content: center; transition: all .12s; }
.check.on { background: var(--primary); border-color: var(--primary); color: #fff; }
.cell:hover .check { border-color: var(--primary); }
</style>
