<template>
  <div>
    <p class="tab-intro">{{ t("seqIntro") }}</p>

    <div v-if="auto.errors.sequences" class="banner err mb">
      <Icon :path="mdiAlertCircleOutline" />
      <div>{{ t("loadError") }}: {{ auto.errors.sequences }}</div>
    </div>

    <div v-if="auto.test?.active && !draft" class="banner warn mb">
      <Icon :path="mdiFlaskOutline" />
      <div class="grow">{{ t("testRunningBanner") }}</div>
      <button class="btn sm danger" :disabled="testBusy" @click="stopTest">
        <Icon :path="mdiStop" :size="16" />{{ t("stopTest") }}
      </button>
    </div>

    <div class="tab-toolbar">
      <span class="muted small grow">{{ countText }}</span>
      <button class="btn" @click="openNew"><Icon :path="mdiPlus" :size="18" />{{ t("newSequence") }}</button>
    </div>

    <div v-if="!auto.sequences.length" class="card">
      <Empty :icon="mdiPlaylistPlay" :text="t('seqEmpty')">
        <div class="faint small empty-hint">{{ t("seqEmptyHint") }}</div>
        <button class="btn" @click="openNew"><Icon :path="mdiPlus" :size="18" />{{ t("newSequence") }}</button>
      </Empty>
    </div>

    <div v-else class="grid cols-3">
      <ItemCard
        v-for="s in auto.sequences"
        :key="s.id"
        :title="s.name"
        :icon="s.active ? mdiPlay : mdiPlaylistPlay"
        :enabled="s.enabled"
        :active="s.active"
        :busy="!!busy[s.id]"
        duplicable
        @edit="openEdit(s)"
        @delete="remove(s)"
        @duplicate="duplicate(s)"
        @toggle="(v: boolean) => setEnabled(s, v)"
      >
        <template #sub>
          <span v-if="s.active" class="chip ok"><span class="dot ok pulse"></span>{{ t("running") }}</span>
          <span>{{ t("stepsCount", { n: s.steps?.length ?? 0 }) }}</span>
          <span>·</span>
          <span class="row sub-mode"><Icon v-if="s.loop" :path="mdiRepeat" :size="14" />{{ runModeText(s) }}</span>
          <span v-if="s.isMacro" class="chip" :title="t('macroHint')">{{ t("macro") }}</span>
        </template>
        <SequenceTimeline :steps="s.steps || []" :loop="s.loop" :repeat="s.repeat" :active="s.active" compact @select="(i: number) => openEdit(s, i)" />
        <div class="muted small ellipsis">
          <Icon :path="mdiTarget" :size="14" /> {{ targetsOf(s) }}
        </div>
        <template #actions>
          <button
            v-if="!s.active"
            class="btn sm"
            :disabled="!!busy[s.id] || !s.enabled || !s.steps?.length"
            :title="s.enabled ? t('startHint') : t('enableFirst')"
            @click="start(s)"
          >
            <Icon :path="mdiPlay" :size="16" />{{ t("start") }}
          </button>
          <button v-else class="btn sm danger" :disabled="!!busy[s.id]" @click="stop(s)">
            <Icon :path="mdiStop" :size="16" />{{ t("stop") }}
          </button>
        </template>
      </ItemCard>
    </div>

    <!-- ------------------------------------------------------------ editor -->
    <Modal
      :open="!!draft"
      wide
      :title="draft?.id != null ? t('editSequence') : t('newSequence')"
      :subtitle="draft?.id != null ? `ID ${draft.id}` : t('seqEditorSub')"
      :icon="mdiPlaylistPlay"
      @close="closeEditor"
    >
      <div v-if="draft" class="auto-editor">
        <div class="seq-head">
          <label class="field name-field">
            <span>{{ t("name") }}</span>
            <input v-model="draft.name" type="text" maxlength="64" :placeholder="t('seqNamePh')" />
          </label>
          <div class="field mode-field">
            <span>{{ t("runMode") }}</span>
            <div class="row wrap">
              <div class="btn-group">
                <button type="button" :class="{ active: draft.mode === 'once' }" @click="draft.mode = 'once'">{{ t("runOnce") }}</button>
                <button type="button" :class="{ active: draft.mode === 'repeat' }" @click="setRepeatMode">{{ t("runRepeat") }}</button>
                <button type="button" :class="{ active: draft.mode === 'loop' }" @click="draft.mode = 'loop'">{{ t("runLoop") }}</button>
              </div>
              <input v-if="draft.mode === 'repeat'" v-model.number="draft.repeat" type="number" min="1" max="10000" step="1" class="repeat-input" />
            </div>
            <span class="hint">{{ t(`runHint_${draft.mode}`, { n: draft.repeat ?? 1 }) }}</span>
          </div>
          <div class="field">
            <span>{{ t("enabled") }}</span>
            <div class="row toggle-row">
              <Toggle v-model="draft.enabled" />
              <span class="small muted">{{ draft.enabled ? t("seqEnabledHint") : t("seqDisabledHint") }}</span>
            </div>
          </div>
          <div v-if="state.expert && draft.id == null" class="field">
            <span>{{ t("macro") }}</span>
            <div class="row toggle-row">
              <Toggle v-model="draft.isMacro" />
              <span class="small muted">{{ t("macroHint") }}</span>
            </div>
          </div>
        </div>

        <div class="section-title">{{ t("timeline") }}</div>
        <SequenceTimeline :steps="draftSteps" :loop="draft.mode === 'loop'" :repeat="draft.mode === 'repeat' ? draft.repeat : null" :active="testActive" @select="focusStep" />

        <div class="section-title row">
          <span class="grow">{{ t("steps") }} ({{ draft.rows.length }})</span>
          <button v-if="draft.rows.length > 1" type="button" class="btn flat sm" @click="expandAll(!allOpen)">
            {{ allOpen ? t("collapseAll") : t("expandAll") }}
          </button>
        </div>

        <div class="steps">
          <div
            v-for="(row, i) in draft.rows"
            :key="row.k"
            :ref="(el) => setStepRef(row.k, el)"
            class="step"
            :class="{ off: !row.s.enabled, open: row.open, bad: !!rowIssue(row) }"
          >
            <div class="step-head" @click="row.open = !row.open">
              <span class="step-no" :style="{ background: actionColor(row.s.data.features) }">{{ i + 1 }}</span>
              <div class="grow step-sum">
                <div class="step-title">
                  {{ actionSummary(row.s.data.features, t) }}
                  <span class="muted">→ {{ targetsText(row.s.data.targets, t) }}</span>
                </div>
                <div class="small faint">
                  {{ row.s.enabled ? `t = ${fmtSec(starts[i])}` : t("stepDisabled") }} · {{ t("waitAfter") }} {{ fmtSec(Number(row.s.delay) || 0) }}
                </div>
              </div>
              <span v-if="rowIssue(row)" class="chip err" :title="rowIssue(row)"><Icon :path="mdiAlertCircleOutline" :size="14" /></span>
              <div class="row step-quick" @click.stop>
                <button type="button" class="btn icon sm hide-sm" :disabled="i === 0" :title="t('moveUp')" @click="move(i, -1)">
                  <Icon :path="mdiArrowUp" :size="18" />
                </button>
                <button type="button" class="btn icon sm hide-sm" :disabled="i === draft.rows.length - 1" :title="t('moveDown')" @click="move(i, 1)">
                  <Icon :path="mdiArrowDown" :size="18" />
                </button>
                <span :title="row.s.enabled ? t('stepEnabled') : t('stepDisabled')"><Toggle v-model="row.s.enabled" /></span>
              </div>
              <Icon :path="row.open ? mdiChevronUp : mdiChevronDown" :size="20" class="faint" />
            </div>

            <div v-if="row.open" class="step-body">
              <div class="field">
                <span>{{ t("targets") }}</span>
                <TargetPicker v-model="row.s.data.targets" />
              </div>
              <ActionEditor v-model="row.s.data.features" :targets="row.s.data.targets" />
              <div class="field">
                <span>{{ t("waitAfter") }}</span>
                <div class="row wrap">
                  <input v-model.number="row.s.delay" type="number" min="0" step="0.1" class="delay-input" />
                  <span class="muted">s</span>
                  <button
                    v-for="d in DELAY_PRESETS"
                    :key="d"
                    type="button"
                    class="chip clickable preset"
                    :class="{ primary: Number(row.s.delay) === d }"
                    @click="row.s.delay = d"
                  >
                    {{ fmtSec(d) }}
                  </button>
                </div>
                <span class="hint">{{ t("waitAfterHint") }}</span>
              </div>
              <div class="row wrap step-tools">
                <button type="button" class="btn flat sm" :disabled="i === 0" @click="move(i, -1)"><Icon :path="mdiArrowUp" :size="16" />{{ t("moveUp") }}</button>
                <button type="button" class="btn flat sm" :disabled="i === draft.rows.length - 1" @click="move(i, 1)">
                  <Icon :path="mdiArrowDown" :size="16" />{{ t("moveDown") }}
                </button>
                <button type="button" class="btn flat sm" @click="duplicateStep(i)"><Icon :path="mdiContentCopy" :size="16" />{{ t("duplicate") }}</button>
                <span class="grow"></span>
                <button type="button" class="btn danger flat sm" @click="removeStep(i)"><Icon :path="mdiDeleteOutline" :size="16" />{{ t("removeStep") }}</button>
              </div>
            </div>
          </div>

          <button type="button" class="add-row" @click="addStep"><Icon :path="mdiPlus" :size="18" />{{ t("addStep") }}</button>
        </div>

        <div class="test-panel" :class="{ running: testActive }">
          <span class="icon-bubble" :class="testActive ? 'ok' : 'off'"><Icon :path="mdiFlaskOutline" :size="20" /></span>
          <div class="grow">
            <div class="test-title">
              {{ t("testTitle") }}
              <span v-if="testActive" class="chip ok"><span class="dot ok pulse"></span>{{ t("running") }}</span>
            </div>
            <div class="muted small">{{ t("testHint") }}</div>
          </div>
          <button v-if="!testActive" type="button" class="btn outline sm" :disabled="testBusy || !canTest" :title="canTest ? '' : t('testNeedsSteps')" @click="startTest">
            <span v-if="testBusy" class="spinner"></span><Icon v-else :path="mdiPlay" :size="16" />{{ t("startTest") }}
          </button>
          <button v-else type="button" class="btn danger sm" :disabled="testBusy" @click="stopTest">
            <Icon :path="mdiStop" :size="16" />{{ t("stopTest") }}
          </button>
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
import { computed, nextTick, reactive, ref, type ComponentPublicInstance } from "vue";
import {
  mdiAlertCircleOutline,
  mdiArrowDown,
  mdiArrowUp,
  mdiChevronDown,
  mdiChevronUp,
  mdiContentCopy,
  mdiDeleteOutline,
  mdiFlaskOutline,
  mdiPlay,
  mdiPlaylistPlay,
  mdiPlus,
  mdiRepeat,
  mdiStop,
  mdiTarget,
} from "@mdi/js";
import Icon from "../Icon.vue";
import Modal from "../Modal.vue";
import Toggle from "../Toggle.vue";
import Empty from "../Empty.vue";
import TargetPicker from "../TargetPicker.vue";
import ActionEditor from "./ActionEditor.vue";
import ItemCard from "./ItemCard.vue";
import SequenceTimeline from "./SequenceTimeline.vue";
import { gw } from "../../lib/api";
import { confirmDialog, run, state, type Target } from "../../lib/store";
import { useAT } from "./i18n";
import { auto, load, loadTest, pollSoon } from "./data";
import {
  actionColor,
  actionSummary,
  clone,
  fmtSec,
  plainTargets,
  targetsText,
  type Features,
  type SequenceItem,
  type SequenceStep,
} from "./util";

const t = useAT();
const DELAY_PRESETS = [0, 0.5, 1, 2, 5, 10, 30, 60];

interface StepRow {
  k: number;
  open: boolean;
  s: SequenceStep;
}
interface Draft {
  id: number | null;
  name: string;
  enabled: boolean;
  mode: "once" | "repeat" | "loop";
  repeat: number | null;
  isMacro: boolean;
  rows: StepRow[];
}

const busy = reactive<Record<number, boolean>>({});
const draft = ref<Draft | null>(null);
const saving = ref(false);
const testBusy = ref(false);
let snapshot = "";
let rowKey = 0;

const countText = computed(() => {
  const n = auto.sequences.length;
  const running = auto.sequences.filter((s) => s.active).length;
  return running ? t("seqCountRunning", { n, r: running }) : t("seqCount", { n });
});

function runModeText(s: SequenceItem) {
  if (s.loop) return t("runLoop");
  if (s.repeat && s.repeat > 0) return t("repeatN", { n: s.repeat });
  return t("runOnce");
}

function targetsOf(s: SequenceItem) {
  const seen = new Map<string, Target>();
  for (const st of s.steps || []) for (const tg of st.data?.targets || []) seen.set(`${tg.type}:${tg.id}`, tg);
  return targetsText([...seen.values()], t, 4);
}

// ------------------------------------------------------------------ list actions
async function setEnabled(s: SequenceItem, v: boolean) {
  busy[s.id] = true;
  await run(() => gw.put(`/automations/sequence/${s.id}`, { enabled: v }), v ? t("enabledToast", { name: s.name }) : t("disabledToast", { name: s.name }));
  await load("sequences");
  busy[s.id] = false;
}

async function start(s: SequenceItem) {
  busy[s.id] = true;
  await run(() => gw.post(`/automations/sequence/${s.id}/start`), t("seqStarted", { name: s.name }));
  pollSoon();
  await load("sequences");
  busy[s.id] = false;
}

async function stop(s: SequenceItem) {
  busy[s.id] = true;
  await run(() => gw.post(`/automations/sequence/${s.id}/stop`), t("seqStopped", { name: s.name }));
  await load("sequences");
  busy[s.id] = false;
}

async function remove(s: SequenceItem) {
  const ok = await confirmDialog({
    title: t("deleteSeqTitle"),
    message: t("deleteMsg", { name: s.name || `#${s.id}` }),
    danger: true,
    confirmText: t("delete"),
  });
  if (!ok) return;
  await run(() => gw.del(`/automations/sequence/${s.id}`), t("deleted"));
  await load("sequences");
}

// ------------------------------------------------------------------ editor
function toRows(steps: SequenceStep[], openIndex: number | null): StepRow[] {
  return (steps || []).map((s, i) => ({
    k: ++rowKey,
    open: openIndex === i,
    s: {
      enabled: s.enabled !== false,
      type: "features",
      data: { targets: clone(s.data?.targets || []), features: clone(s.data?.features || {}) },
      delay: Number(s.delay) || 0,
    },
  }));
}

function newStep(targets: Target[] = [], features: Features = { dimmable: 100 }, delay = 1): StepRow {
  return { k: ++rowKey, open: true, s: { enabled: true, type: "features", data: { targets: clone(targets), features: clone(features) }, delay } };
}

function serialize(d: Draft) {
  return JSON.stringify({ ...d, rows: d.rows.map((r) => r.s) });
}

function openDraft(d: Draft) {
  draft.value = d;
  snapshot = serialize(d);
}

function openNew() {
  openDraft({
    id: null,
    name: t("seqDefaultName", { n: auto.sequences.length + 1 }),
    enabled: true,
    mode: "once",
    repeat: null,
    isMacro: false,
    rows: [newStep()],
  });
}

function openEdit(s: SequenceItem, focus: number | null = null) {
  openDraft({
    id: s.id,
    name: s.name || "",
    enabled: s.enabled !== false,
    mode: s.loop ? "loop" : s.repeat && s.repeat > 0 ? "repeat" : "once",
    repeat: s.repeat ?? null,
    isMacro: !!s.isMacro,
    rows: toRows(s.steps, focus ?? (s.steps?.length === 1 ? 0 : null)),
  });
  if (focus !== null) nextTick(() => scrollToRow(draft.value?.rows[focus]?.k));
}

function duplicate(s: SequenceItem) {
  openDraft({
    id: null,
    name: t("copyOf", { name: s.name || `#${s.id}` }),
    enabled: s.enabled !== false,
    mode: s.loop ? "loop" : s.repeat && s.repeat > 0 ? "repeat" : "once",
    repeat: s.repeat ?? null,
    isMacro: !!s.isMacro,
    rows: toRows(s.steps, null),
  });
  snapshot = "";
}

function setRepeatMode() {
  if (!draft.value) return;
  draft.value.mode = "repeat";
  if (!draft.value.repeat || draft.value.repeat < 1) draft.value.repeat = 3;
}

const draftSteps = computed<SequenceStep[]>(() => draft.value?.rows.map((r) => r.s) ?? []);
const starts = computed(() => {
  let acc = 0;
  return draftSteps.value.map((s) => {
    const at = acc;
    if (s.enabled) acc += Math.max(0, Number(s.delay) || 0);
    return at;
  });
});
const allOpen = computed(() => !!draft.value?.rows.length && draft.value.rows.every((r) => r.open));
function expandAll(v: boolean) {
  draft.value?.rows.forEach((r) => (r.open = v));
}

const stepEls = new Map<number, HTMLElement>();
function setStepRef(k: number, el: Element | ComponentPublicInstance | null) {
  if (el instanceof HTMLElement) stepEls.set(k, el);
  else stepEls.delete(k);
}
function scrollToRow(k: number | undefined) {
  if (k === undefined) return;
  stepEls.get(k)?.scrollIntoView({ block: "nearest", behavior: "smooth" });
}
function focusStep(i: number) {
  const row = draft.value?.rows[i];
  if (!row) return;
  row.open = true;
  nextTick(() => scrollToRow(row.k));
}

function move(i: number, dir: number) {
  const rows = draft.value?.rows;
  if (!rows) return;
  const j = i + dir;
  if (j < 0 || j >= rows.length) return;
  const [r] = rows.splice(i, 1);
  rows.splice(j, 0, r);
}
function duplicateStep(i: number) {
  const rows = draft.value?.rows;
  if (!rows) return;
  const src = rows[i].s;
  const copy = newStep(src.data.targets, src.data.features, src.delay);
  copy.s.enabled = src.enabled;
  rows.splice(i + 1, 0, copy);
  nextTick(() => scrollToRow(copy.k));
}
function removeStep(i: number) {
  draft.value?.rows.splice(i, 1);
}
function addStep() {
  const rows = draft.value?.rows;
  if (!rows) return;
  const last = rows[rows.length - 1];
  rows.forEach((r) => (r.open = false));
  const row = newStep(last?.s.data.targets ?? [], { dimmable: 100 }, last ? Number(last.s.delay) || 1 : 1);
  rows.push(row);
  nextTick(() => scrollToRow(row.k));
}

function rowIssue(r: StepRow): string {
  if (!r.s.enabled) return "";
  if (!r.s.data.targets?.length) return t("issueNoTargets");
  if (!Object.keys(r.s.data.features || {}).length) return t("issueNoAction");
  const d = Number(r.s.delay);
  if (!Number.isFinite(d) || d < 0) return t("issueDelay");
  return "";
}

const issues = computed(() => {
  const d = draft.value;
  if (!d) return [];
  const out: string[] = [];
  if (!d.name.trim()) out.push(t("issueName"));
  if (d.mode === "repeat" && !(Number(d.repeat) >= 1)) out.push(t("issueRepeat"));
  d.rows.forEach((r, i) => {
    const m = rowIssue(r);
    if (m) out.push(`${t("step")} ${i + 1}: ${m}`);
  });
  return out;
});

function buildSteps(): SequenceStep[] {
  return (draft.value?.rows ?? []).map((r) => ({
    enabled: r.s.enabled,
    type: "features",
    data: { targets: plainTargets(r.s.data.targets), features: r.s.data.features },
    delay: Math.max(0, Number(r.s.delay) || 0),
  }));
}
function runFields() {
  const d = draft.value!;
  return {
    loop: d.mode === "loop",
    repeat: d.mode === "repeat" ? Math.max(1, Math.round(Number(d.repeat) || 1)) : null,
  };
}

async function save() {
  const d = draft.value;
  if (!d || issues.value.length) return;
  saving.value = true;
  const body: Record<string, unknown> = { name: d.name.trim(), enabled: d.enabled, ...runFields(), steps: buildSteps() };
  let res: unknown;
  if (d.id == null) {
    body.isMacro = d.isMacro;
    res = await run(() => gw.post("/automations/sequence", body), t("createdToast", { name: body.name }));
  } else {
    res = await run(() => gw.put(`/automations/sequence/${d.id}`, body), t("savedToast", { name: body.name }));
  }
  saving.value = false;
  if (res === undefined) return;
  if (testActive.value) await stopTest(true);
  draft.value = null;
  await load("sequences");
}

async function closeEditor() {
  if (draft.value && serialize(draft.value) !== snapshot) {
    const ok = await confirmDialog({ title: t("discardTitle"), message: t("discardMsg"), confirmText: t("discard"), danger: true });
    if (!ok) return;
  }
  if (testActive.value) await stopTest(true);
  draft.value = null;
}

// ------------------------------------------------------------------ test run
const testActive = computed(() => !!auto.test?.active);
const canTest = computed(() => !!draft.value?.rows.some((r) => r.s.enabled && !rowIssue(r)));

async function startTest() {
  const d = draft.value;
  if (!d) return;
  testBusy.value = true;
  const steps = buildSteps().filter((s, i) => !rowIssue(d.rows[i]));
  await run(async () => {
    await gw.put("/automations/sequence/test", { name: d.name.trim() || "Test", enabled: true, ...runFields(), steps });
    await gw.put("/automations/sequence/test", { active: true });
  }, t("testStarted"));
  pollSoon();
  await loadTest();
  testBusy.value = false;
}

async function stopTest(silent = false) {
  testBusy.value = true;
  await run(() => gw.put("/automations/sequence/test", { active: false }), silent === true ? undefined : t("testStopped"));
  await loadTest();
  testBusy.value = false;
}

</script>

<style scoped>
.sub-mode { gap: 3px; }
.ellipsis { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.repeat-input { width: 90px !important; }
.seq-head { display: flex; flex-wrap: wrap; gap: 12px 20px; align-items: flex-start; }
.seq-head > .field { flex: 1 1 200px; }
.seq-head > .mode-field { flex: 0 1 auto; }
.seq-head > .name-field { flex: 2 1 220px; }
.toggle-row { min-height: 38px; }
.steps { display: flex; flex-direction: column; gap: 8px; }
.step { border: 1px solid var(--divider); border-radius: 12px; background: var(--card); transition: border-color .15s; }
.step.open { border-color: color-mix(in srgb, var(--primary) 40%, var(--divider)); }
.step.bad { border-color: color-mix(in srgb, var(--error) 50%, var(--divider)); }
.step.off .step-sum, .step.off .step-no { opacity: .5; }
.step-head { display: flex; align-items: center; gap: 10px; padding: 8px 10px 8px 12px; cursor: pointer; min-height: 52px; }
.step-no {
  width: 28px; height: 28px; border-radius: 50%; display: inline-flex; align-items: center; justify-content: center;
  font-weight: 600; font-size: 12.5px; color: #1f2328; flex-shrink: 0; box-shadow: inset 0 0 0 1px rgba(0, 0, 0, .08);
}
.step-sum { min-width: 0; }
.step-title { font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.step-quick { gap: 2px; }
.step-body { padding: 4px 14px 12px; border-top: 1px solid var(--divider); display: flex; flex-direction: column; gap: 14px; padding-top: 12px; }
.delay-input { width: 100px !important; }
.preset { border: 0; }
.step-tools { gap: 4px; border-top: 1px dashed var(--divider); padding-top: 8px; }
.test-panel {
  display: flex; align-items: center; gap: 12px; margin-top: 18px; padding: 12px 14px; border-radius: 12px;
  background: var(--bg2); flex-wrap: wrap;
}
.test-panel.running { background: color-mix(in srgb, var(--success) 12%, transparent); }
.test-title { font-weight: 500; display: flex; align-items: center; gap: 8px; }
.footer-issue { color: var(--error); display: inline-flex; align-items: center; gap: 4px; margin-right: auto; max-width: 100%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
@media (max-width: 700px) {
  .hide-sm { display: none; }
  .step-head { gap: 8px; padding: 8px; }
  .step-body { padding: 10px; }
}
</style>
