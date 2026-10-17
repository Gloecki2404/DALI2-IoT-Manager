<template>
  <div>
    <p class="tab-intro">{{ t("evtIntro") }}</p>

    <div v-if="auto.errors.events" class="banner err mb">
      <Icon :path="mdiAlertCircleOutline" />
      <div>{{ t("loadError") }}: {{ auto.errors.events }}</div>
    </div>

    <div v-if="lines < 2" class="banner warn mb">
      <Icon :path="mdiInformationOutline" />
      <div>{{ t("evtSingleLine", { n: lines }) }}</div>
    </div>

    <div class="tab-toolbar">
      <span class="muted small grow">{{ t("evtCount", { n: auto.events.length }) }}</span>
      <button class="btn" :disabled="lines < 2" :title="lines < 2 ? t('evtNeedLines') : ''" @click="openNew">
        <Icon :path="mdiPlus" :size="18" />{{ t("newEvt") }}
      </button>
    </div>

    <div v-if="!auto.events.length" class="card">
      <Empty :icon="mdiSwapHorizontalBold" :text="t('evtEmpty')">
        <div class="faint small empty-hint">{{ t("evtEmptyHint") }}</div>
        <button class="btn" :disabled="lines < 2" @click="openNew"><Icon :path="mdiPlus" :size="18" />{{ t("newEvt") }}</button>
      </Empty>
    </div>

    <div v-else class="grid cols-3">
      <ItemCard
        v-for="e in auto.events"
        :key="e.id"
        :title="e.name"
        :icon="mdiSwapHorizontalBold"
        :enabled="e.enabled"
        :busy="!!busy[e.id]"
        duplicable
        @edit="openEdit(e)"
        @delete="remove(e)"
        @duplicate="duplicate(e)"
        @toggle="(v: boolean) => setEnabled(e, v)"
      >
        <template #sub>
          {{ t("line") }} {{ e.source_line ?? 0 }} → {{ (e.target_lines || []).map((l) => `${t("line")} ${l}`).join(", ") || "–" }}
        </template>
        <div class="row wrap">
          <template v-if="activeFilterKeys(e.filters).length">
            <span v-for="k in activeFilterKeys(e.filters)" :key="k" class="chip">
              {{ t(`flt_${k}`) }}: {{ compact(e.filters[k]) }}
            </span>
          </template>
          <span v-else class="chip ok">{{ t("evtAll") }}</span>
        </div>
      </ItemCard>
    </div>

    <Modal
      :open="!!draft"
      wide
      :title="draft?.id != null ? t('editEvt') : t('newEvt')"
      :subtitle="draft?.id != null ? `ID ${draft.id}` : t('evtEditorSub')"
      :icon="mdiSwapHorizontalBold"
      @close="closeEditor"
    >
      <div v-if="draft" class="auto-editor">
        <div class="form-grid">
          <label class="field">
            <span>{{ t("name") }}</span>
            <input v-model="draft.name" type="text" maxlength="64" :placeholder="t('evtNamePh')" />
          </label>
          <div class="field">
            <span>{{ t("enabled") }}</span>
            <div class="row toggle-row"><Toggle v-model="draft.enabled" /><span class="small muted">{{ draft.enabled ? t("evtEnabledHint") : t("evtDisabledHint") }}</span></div>
          </div>
        </div>

        <div class="section-title">{{ t("evtLines") }}</div>
        <div class="row wrap lines-row">
          <label class="field src-line">
            <span>{{ t("sourceLine") }}</span>
            <select v-model.number="draft.source_line" @change="dropSourceFromTargets">
              <option v-for="l in lineOptions" :key="l" :value="l">{{ t("line") }} {{ l }}</option>
            </select>
          </label>
          <Icon :path="mdiArrowRightBold" :size="22" class="faint arrow" />
          <div class="field grow">
            <span>{{ t("targetLines") }}</span>
            <div class="row wrap">
              <button
                v-for="l in lineOptions.filter((x) => x !== draft!.source_line)"
                :key="l"
                type="button"
                class="chip clickable line-chip"
                :class="{ primary: draft.target_lines.includes(l) }"
                @click="toggleTarget(l)"
              >
                {{ t("line") }} {{ l }}
              </button>
            </div>
          </div>
        </div>

        <div class="section-title">{{ t("filters") }}</div>
        <div class="banner info small mb">
          <Icon :path="mdiFilterOutline" :size="18" />
          <div>
            {{ t("filterHowto") }}
            <div class="combos">
              <span class="muted">{{ t("filterCombos") }}:</span>
              <span v-for="c in COMBOS" :key="c.join('+')" class="chip" :class="{ primary: comboActive(c) }">
                {{ c.map((k) => t(`flt_${k}`)).join(" + ") }}
              </span>
            </div>
          </div>
        </div>

        <div class="filters">
          <div v-for="k in FILTER_KEYS" :key="k" class="flt" :class="{ on: draft.use[k], blocked: !canUse(k) && !draft.use[k] }">
            <label class="row flt-head">
              <Toggle :model-value="draft.use[k]" :disabled="!draft.use[k] && !canUse(k)" @change="(v: boolean) => (draft!.use[k] = v)" />
              <div class="grow">
                <div class="flt-title">{{ t(`flt_${k}`) }} <span class="faint small mono">{{ RANGES[k][0] }}–{{ RANGES[k][1] }}</span></div>
                <div class="small faint">{{ !draft.use[k] && !canUse(k) ? t("filterBlocked") : t(`flt_${k}_hint`) }}</div>
              </div>
            </label>
            <IntSetInput
              v-if="draft.use[k]"
              v-model="draft.filters[k]"
              :min="RANGES[k][0]"
              :max="RANGES[k][1]"
              :presets="k === 'instanceType' ? instancePresets : undefined"
            />
          </div>
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
  mdiArrowRightBold,
  mdiFilterOutline,
  mdiInformationOutline,
  mdiPlus,
  mdiSwapHorizontalBold,
} from "@mdi/js";
import Icon from "../Icon.vue";
import Modal from "../Modal.vue";
import Toggle from "../Toggle.vue";
import Empty from "../Empty.vue";
import ItemCard from "./ItemCard.vue";
import IntSetInput from "./IntSetInput.vue";
import { gw } from "../../lib/api";
import { confirmDialog, run } from "../../lib/store";
import { useAT } from "./i18n";
import { auto, load } from "./data";
import { lineCount, type EventTriggerItem } from "./util";

const t = useAT();

type FKey = "shortAddress" | "deviceGroup" | "instanceType" | "instanceNumber";
const FILTER_KEYS: FKey[] = ["shortAddress", "deviceGroup", "instanceType", "instanceNumber"];
const RANGES: Record<FKey, [number, number]> = {
  shortAddress: [0, 63],
  deviceGroup: [0, 31],
  instanceType: [0, 31],
  instanceNumber: [0, 31],
};
// Combinations a DALI-2 event frame can carry (IEC 62386-103 event addressing schemes).
const COMBOS: FKey[][] = [
  ["shortAddress", "instanceType"],
  ["shortAddress", "instanceNumber"],
  ["deviceGroup", "instanceType"],
  ["instanceType", "instanceNumber"],
];

interface Draft {
  id: number | null;
  name: string;
  enabled: boolean;
  source_line: number;
  target_lines: number[];
  use: Record<FKey, boolean>;
  filters: Record<FKey, number[]>;
}

const busy = reactive<Record<number, boolean>>({});
const draft = ref<Draft | null>(null);
const saving = ref(false);
let snapshot = "";

const lines = computed(() => lineCount());
const lineOptions = computed(() => {
  const set = new Set<number>(Array.from({ length: lines.value }, (_, i) => i));
  if (draft.value) {
    set.add(draft.value.source_line);
    draft.value.target_lines.forEach((l) => set.add(l));
  }
  return [...set].sort((a, b) => a - b);
});

const instancePresets = computed(() =>
  [0, 1, 2, 3, 4, 5, 6].map((v) => ({ value: v, label: t(`inst${v}`) })),
);

function activeFilterKeys(f: Record<string, number[]> | undefined): string[] {
  return Object.keys(f || {}).filter((k) => Array.isArray(f![k]) && f![k].length);
}

function compact(values: number[]): string {
  const s = [...new Set(values)].sort((a, b) => a - b);
  const out: string[] = [];
  let i = 0;
  while (i < s.length) {
    let j = i;
    while (j + 1 < s.length && s[j + 1] === s[j] + 1) j++;
    out.push(j - i >= 2 ? `${s[i]}–${s[j]}` : s.slice(i, j + 1).join(", "));
    i = j + 1;
  }
  return out.join(", ");
}

function validSet(keys: FKey[]): boolean {
  if (keys.length <= 1) return true;
  if (keys.length > 2) return false;
  return COMBOS.some((c) => c.includes(keys[0]) && c.includes(keys[1]));
}
function usedKeys(d: Draft): FKey[] {
  return FILTER_KEYS.filter((k) => d.use[k]);
}
function canUse(k: FKey): boolean {
  const d = draft.value;
  if (!d) return false;
  return validSet([...usedKeys(d).filter((x) => x !== k), k]);
}
function comboActive(c: FKey[]): boolean {
  const d = draft.value;
  if (!d) return false;
  const used = usedKeys(d);
  return used.length === 2 && c.every((k) => used.includes(k));
}

// ------------------------------------------------------------------ list actions
async function setEnabled(e: EventTriggerItem, v: boolean) {
  busy[e.id] = true;
  await run(
    () => gw.post(`/automations/eventTriggerAction/${e.id}/${v ? "start" : "stop"}`),
    v ? t("enabledToast", { name: e.name }) : t("disabledToast", { name: e.name }),
  );
  await load("events");
  busy[e.id] = false;
}

async function remove(e: EventTriggerItem) {
  const ok = await confirmDialog({
    title: t("deleteEvtTitle"),
    message: t("deleteMsg", { name: e.name || `#${e.id}` }),
    danger: true,
    confirmText: t("delete"),
  });
  if (!ok) return;
  await run(() => gw.del(`/automations/eventTriggerAction/${e.id}`), t("deleted"));
  await load("events");
}

// ------------------------------------------------------------------ editor
function emptyFilters(): Record<FKey, number[]> {
  return { shortAddress: [], deviceGroup: [], instanceType: [], instanceNumber: [] };
}

function fromItem(e: EventTriggerItem | null, asCopy = false): Draft {
  const filters = emptyFilters();
  const use = { shortAddress: false, deviceGroup: false, instanceType: false, instanceNumber: false };
  for (const k of FILTER_KEYS) {
    const v = e?.filters?.[k];
    if (Array.isArray(v) && v.length) {
      filters[k] = [...v];
      use[k] = true;
    }
  }
  const src = e?.source_line ?? 0;
  return {
    id: e && !asCopy ? e.id : null,
    name: e ? (asCopy ? t("copyOf", { name: e.name || `#${e.id}` }) : e.name || "") : t("evtDefaultName", { n: auto.events.length + 1 }),
    enabled: e ? e.enabled !== false : true,
    source_line: src,
    target_lines: e ? [...(e.target_lines || [])] : Array.from({ length: lines.value }, (_, i) => i).filter((l) => l !== src),
    use,
    filters,
  };
}

function openDraft(d: Draft, fresh = false) {
  draft.value = d;
  snapshot = fresh ? "" : JSON.stringify(d);
}
const openNew = () => openDraft(fromItem(null));
const openEdit = (e: EventTriggerItem) => openDraft(fromItem(e));
const duplicate = (e: EventTriggerItem) => openDraft(fromItem(e, true), true);

function toggleTarget(l: number) {
  const d = draft.value;
  if (!d) return;
  const i = d.target_lines.indexOf(l);
  if (i >= 0) d.target_lines.splice(i, 1);
  else d.target_lines = [...d.target_lines, l].sort((a, b) => a - b);
}
function dropSourceFromTargets() {
  const d = draft.value;
  if (d) d.target_lines = d.target_lines.filter((l) => l !== d.source_line);
}

const issues = computed(() => {
  const d = draft.value;
  if (!d) return [];
  const out: string[] = [];
  if (!d.name.trim()) out.push(t("issueName"));
  if (!d.target_lines.length) out.push(t("issueNoTargetLines"));
  if (d.target_lines.includes(d.source_line)) out.push(t("issueSourceIsTarget"));
  const used = usedKeys(d);
  if (!validSet(used)) out.push(t("issueFilterCombo"));
  for (const k of used) if (!d.filters[k].length) out.push(t("issueFilterEmpty", { f: t(`flt_${k}`) }));
  return out;
});

async function save() {
  const d = draft.value;
  if (!d || issues.value.length) return;
  saving.value = true;
  const filters: Record<string, number[]> = {};
  for (const k of usedKeys(d)) filters[k] = [...d.filters[k]].sort((a, b) => a - b);
  const body = { name: d.name.trim(), enabled: d.enabled, source_line: d.source_line, target_lines: [...d.target_lines], filters };
  const res =
    d.id == null
      ? await run(() => gw.post("/automations/eventTriggerAction", body), t("createdToast", { name: body.name }))
      : await run(() => gw.put(`/automations/eventTriggerAction/${d.id}`, body), t("savedToast", { name: body.name }));
  saving.value = false;
  if (res === undefined) return;
  draft.value = null;
  await load("events");
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
.toggle-row { min-height: 38px; }
.lines-row { gap: 12px 16px; align-items: flex-end; }
.src-line { width: 160px; }
.arrow { margin-bottom: 8px; }
.line-chip { border: 0; height: 30px; padding: 0 12px; border-radius: 15px; }
.combos { display: flex; flex-wrap: wrap; gap: 4px; align-items: center; margin-top: 8px; }
.filters { display: grid; grid-template-columns: repeat(auto-fill, minmax(330px, 1fr)); gap: 10px; }
.flt { border: 1px solid var(--divider); border-radius: 12px; padding: 10px 12px; display: flex; flex-direction: column; gap: 10px; }
.flt.on { border-color: color-mix(in srgb, var(--primary) 45%, var(--divider)); }
.flt.blocked { opacity: .55; }
.flt-head { gap: 12px; cursor: pointer; align-items: flex-start; }
.flt-title { font-weight: 500; }
.footer-issue { color: var(--error); display: inline-flex; align-items: center; gap: 4px; margin-right: auto; max-width: 100%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
@media (max-width: 700px) {
  .filters { grid-template-columns: 1fr; }
  .arrow { display: none; }
}
</style>
