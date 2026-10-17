<template>
  <div>
    <p class="tab-intro">{{ t("trigIntro") }}</p>

    <div v-if="auto.errors.triggers" class="banner err mb">
      <Icon :path="mdiAlertCircleOutline" />
      <div>{{ t("loadError") }}: {{ auto.errors.triggers }}</div>
    </div>

    <div class="tab-toolbar">
      <span class="muted small grow">{{ t("trigCount", { n: auto.triggers.length }) }}</span>
      <button class="btn" @click="openNew"><Icon :path="mdiPlus" :size="18" />{{ t("newTrigger") }}</button>
    </div>

    <div v-if="!auto.triggers.length" class="card">
      <Empty :icon="mdiCallSplit" :text="t('trigEmpty')">
        <div class="faint small empty-hint">{{ t("trigEmptyHint") }}</div>
        <button class="btn" @click="openNew"><Icon :path="mdiPlus" :size="18" />{{ t("newTrigger") }}</button>
      </Empty>
    </div>

    <div v-else class="grid cols-3">
      <ItemCard
        v-for="a in auto.triggers"
        :key="a.id"
        :title="a.name"
        :icon="mdiCallSplit"
        :enabled="a.enabled"
        :busy="!!busy[a.id]"
        duplicable
        @edit="openEdit(a)"
        @delete="remove(a)"
        @duplicate="duplicate(a)"
        @toggle="(v: boolean) => setEnabled(a, v)"
      >
        <template #sub>{{ t("trigSub", { s: a.sources?.length ?? 0, t: a.targets?.length ?? 0 }) }}</template>
        <div class="flow">
          <div class="flow-col">
            <span v-for="(s, i) in a.sources || []" :key="i" class="chip src">{{ sourceLabel(s, t) }}</span>
            <span v-if="!a.sources?.length" class="faint small">{{ t("noSources") }}</span>
          </div>
          <Icon :path="mdiArrowRightBold" :size="20" class="flow-arrow" />
          <div class="flow-col">
            <span v-for="(tg, i) in a.targets || []" :key="i" class="chip primary">{{ targetLabel(tg, state.devices, state.zones, t) }}</span>
            <span v-if="!a.targets?.length" class="faint small">{{ t("noTargetsShort") }}</span>
          </div>
        </div>
        <span v-if="overlaps(a.sources, a.targets)" class="chip warn"><Icon :path="mdiAlertOutline" :size="14" />{{ t("trigLoopShort") }}</span>
        <template #actions>
          <button class="btn flat sm" :disabled="!!busy[a.id]" :title="t('gwStartHint')" @click="startStop(a, 'start')">
            <Icon :path="mdiPlay" :size="16" />{{ t("start") }}
          </button>
          <button class="btn flat sm" :disabled="!!busy[a.id]" :title="t('gwStopHint')" @click="startStop(a, 'stop')">
            <Icon :path="mdiStop" :size="16" />{{ t("stop") }}
          </button>
        </template>
      </ItemCard>
    </div>

    <Modal
      :open="!!draft"
      wide
      :title="draft?.id != null ? t('editTrigger') : t('newTrigger')"
      :subtitle="draft?.id != null ? `ID ${draft.id}` : t('trigEditorSub')"
      :icon="mdiCallSplit"
      @close="closeEditor"
    >
      <div v-if="draft" class="auto-editor">
        <div class="banner info small mb">
          <Icon :path="mdiInformationOutline" :size="18" />
          <div>{{ t("trigHowto") }}</div>
        </div>
        <div class="form-grid">
          <label class="field">
            <span>{{ t("name") }}</span>
            <input v-model="draft.name" type="text" maxlength="64" :placeholder="t('trigNamePh')" />
          </label>
          <div class="field">
            <span>{{ t("enabled") }}</span>
            <div class="row toggle-row"><Toggle v-model="draft.enabled" /><span class="small muted">{{ draft.enabled ? t("trigEnabledHint") : t("trigDisabledHint") }}</span></div>
          </div>
        </div>

        <div class="flow-edit">
          <div class="fe-box">
            <div class="section-title fe-title"><Icon :path="mdiRadar" :size="16" />{{ t("sources") }}</div>
            <div class="hint small faint mb-s">{{ t("sourcesHint") }}</div>
            <SourcePicker v-model="draft.sources" />
          </div>
          <div class="fe-arrow"><Icon :path="mdiArrowRightBold" :size="26" /></div>
          <div class="fe-box">
            <div class="section-title fe-title"><Icon :path="mdiTarget" :size="16" />{{ t("targets") }}</div>
            <div class="hint small faint mb-s">{{ t("trigTargetsHint") }}</div>
            <TargetPicker v-model="draft.targets" />
          </div>
        </div>

        <div v-if="overlaps(draft.sources, draft.targets)" class="banner warn mt small">
          <Icon :path="mdiAlertOutline" :size="18" />
          <div>{{ t("trigLoopWarn") }}</div>
        </div>
      </div>

      <template #footer>
        <span v-if="issues.length" class="footer-issue small" :title="issues.join('\n')">
          <Icon :path="mdiAlertCircleOutline" :size="16" />{{ issues[0] }}<template v-if="issues.length > 1"> (+{{ issues.length - 1 }})</template>
        </span>
        <button class="btn flat" @click="closeEditor">{{ t("cancel") }}</button>
        <button class="btn" :disabled="saving || !!issues.length" @click="save">
          <span v-if="saving" class="spinner"></span>{{ draft?.id != null ? t("save") : t("create") }}
        </button>
      </template>
    </Modal>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from "vue";
import {
  mdiAlertCircleOutline,
  mdiAlertOutline,
  mdiArrowRightBold,
  mdiCallSplit,
  mdiInformationOutline,
  mdiPlay,
  mdiPlus,
  mdiRadar,
  mdiStop,
  mdiTarget,
} from "@mdi/js";
import Icon from "../Icon.vue";
import Modal from "../Modal.vue";
import Toggle from "../Toggle.vue";
import Empty from "../Empty.vue";
import TargetPicker from "../TargetPicker.vue";
import ItemCard from "./ItemCard.vue";
import SourcePicker from "./SourcePicker.vue";
import { gw } from "../../lib/api";
import { confirmDialog, run, state, type Target } from "../../lib/store";
import { targetLabel } from "../../lib/dali";
import { useAT } from "./i18n";
import { auto, load } from "./data";
import { clone, plainTargets, sourceLabel, type TriggerActionItem, type TriggerSource } from "./util";

const t = useAT();

interface Draft {
  id: number | null;
  name: string;
  enabled: boolean;
  sources: TriggerSource[];
  targets: Target[];
}

const busy = reactive<Record<number, boolean>>({});
const draft = ref<Draft | null>(null);
const saving = ref(false);
let snapshot = "";

/** True if a source is also a target (commands would be mirrored back onto themselves). */
function overlaps(sources: TriggerSource[] | undefined, targets: Target[] | undefined): boolean {
  if (!sources?.length || !targets?.length) return false;
  return sources.some((s) =>
    targets.some(
      (tg) =>
        (s.type === "device" && tg.type === "device" && tg.id === s.id) ||
        (s.type === "group" && tg.type === "group" && tg.id === s.id) ||
        (s.type === "broadcast" && tg.type === "broadcast" && (tg.id === null || tg.id === undefined || tg.id === s.id)),
    ),
  );
}

async function setEnabled(a: TriggerActionItem, v: boolean) {
  busy[a.id] = true;
  await run(() => gw.put(`/automations/triggerAction/${a.id}`, { enabled: v }), v ? t("enabledToast", { name: a.name }) : t("disabledToast", { name: a.name }));
  await load("triggers");
  busy[a.id] = false;
}

async function startStop(a: TriggerActionItem, what: "start" | "stop") {
  busy[a.id] = true;
  await run(
    () => gw.post(`/automations/triggerAction/${a.id}/${what}`),
    what === "start" ? t("gwStarted", { name: a.name }) : t("gwStopped", { name: a.name }),
  );
  await load("triggers");
  busy[a.id] = false;
}

async function remove(a: TriggerActionItem) {
  const ok = await confirmDialog({
    title: t("deleteTrigTitle"),
    message: t("deleteMsg", { name: a.name || `#${a.id}` }),
    danger: true,
    confirmText: t("delete"),
  });
  if (!ok) return;
  await run(() => gw.del(`/automations/triggerAction/${a.id}`), t("deleted"));
  await load("triggers");
}

function openDraft(d: Draft, fresh = false) {
  draft.value = d;
  snapshot = fresh ? "" : JSON.stringify(d);
}
function openNew() {
  openDraft({ id: null, name: t("trigDefaultName", { n: auto.triggers.length + 1 }), enabled: true, sources: [], targets: [] });
}
function fromItem(a: TriggerActionItem, asCopy: boolean): Draft {
  return {
    id: asCopy ? null : a.id,
    name: asCopy ? t("copyOf", { name: a.name || `#${a.id}` }) : a.name || "",
    enabled: a.enabled !== false,
    sources: clone(a.sources || []),
    targets: clone(a.targets || []),
  };
}
const openEdit = (a: TriggerActionItem) => openDraft(fromItem(a, false));
const duplicate = (a: TriggerActionItem) => openDraft(fromItem(a, true), true);

const issues = computed(() => {
  const d = draft.value;
  if (!d) return [];
  const out: string[] = [];
  if (!d.name.trim()) out.push(t("issueName"));
  if (!d.sources.length) out.push(t("issueNoSources"));
  if (!d.targets.length) out.push(t("issueNoTargets"));
  return out;
});

function plainSources(list: TriggerSource[]): TriggerSource[] {
  return list.map((s) =>
    s.type === "d16gear" || s.type === "d16group"
      ? { type: s.type, address: Number(s.address) || 0, line: Number(s.line) || 0 }
      : { type: s.type, id: Number(s.id) || 0 },
  );
}

async function save() {
  const d = draft.value;
  if (!d || issues.value.length) return;
  saving.value = true;
  const body = { name: d.name.trim(), enabled: d.enabled, sources: plainSources(d.sources), targets: plainTargets(d.targets) };
  const res =
    d.id == null
      ? await run(() => gw.post("/automations/triggerAction", body), t("createdToast", { name: body.name }))
      : await run(() => gw.put(`/automations/triggerAction/${d.id}`, body), t("savedToast", { name: body.name }));
  saving.value = false;
  if (res === undefined) return;
  draft.value = null;
  await load("triggers");
}

async function closeEditor() {
  if (draft.value && JSON.stringify(draft.value) !== snapshot) {
    const ok = await confirmDialog({ title: t("discardTitle"), message: t("discardMsg"), confirmText: t("discard"), danger: true });
    if (!ok) return;
  }
  draft.value = null;
}
</script>

<style scoped>
.flow { display: grid; grid-template-columns: 1fr auto 1fr; gap: 8px; align-items: center; }
.flow-col { display: flex; flex-wrap: wrap; gap: 4px; min-width: 0; }
.flow-col .chip { max-width: 100%; overflow: hidden; text-overflow: ellipsis; }
.flow-arrow { color: var(--text3); }
.chip.src { background: color-mix(in srgb, var(--accent) 16%, transparent); color: color-mix(in srgb, var(--accent) 80%, var(--text)); }
.toggle-row { min-height: 38px; }
.flow-edit { display: grid; grid-template-columns: 1fr auto 1fr; gap: 12px; align-items: start; margin-top: 8px; }
.fe-box { border: 1px solid var(--divider); border-radius: 12px; padding: 0 14px 14px; min-width: 0; }
.fe-title { display: flex; align-items: center; gap: 6px; margin-top: 12px; }
.fe-arrow { align-self: center; color: var(--primary); }
.mb-s { margin-bottom: 8px; }
.footer-issue { color: var(--error); display: inline-flex; align-items: center; gap: 4px; margin-right: auto; max-width: 100%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
@media (max-width: 760px) {
  .flow-edit { grid-template-columns: 1fr; }
  .fe-arrow { transform: rotate(90deg); justify-self: center; }
}
</style>
