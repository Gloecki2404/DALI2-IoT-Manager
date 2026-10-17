<template>
  <div>
    <p class="tab-intro">{{ t("circIntro") }}</p>

    <div v-if="auto.errors.circadians" class="banner err mb">
      <Icon :path="mdiAlertCircleOutline" />
      <div>{{ t("loadError") }}: {{ auto.errors.circadians }}</div>
    </div>

    <div class="tab-toolbar">
      <span class="muted small grow">{{ t("circCount", { n: auto.circadians.length }) }}</span>
      <button class="btn" @click="openNew"><Icon :path="mdiPlus" :size="18" />{{ t("newCircadian") }}</button>
    </div>

    <div v-if="!auto.circadians.length" class="card">
      <Empty :icon="mdiThemeLightDark" :text="t('circEmpty')">
        <div class="faint small empty-hint">{{ t("circEmptyHint") }}</div>
        <button class="btn" @click="openNew"><Icon :path="mdiPlus" :size="18" />{{ t("newCircadian") }}</button>
      </Empty>
    </div>

    <div v-else class="grid cols-3">
      <ItemCard
        v-for="c in auto.circadians"
        :key="c.id"
        :title="c.name"
        :icon="mdiThemeLightDark"
        :enabled="c.enabled"
        :busy="!!busy[c.id]"
        duplicable
        @edit="openEdit(c)"
        @delete="remove(c)"
        @duplicate="duplicate(c)"
        @toggle="(v: boolean) => setEnabled(c, v)"
      >
        <template #sub>{{ targetsText(c.targets, t) }}</template>
        <CurveStrip :steps="c.longest?.steps || []" :label="`${c.longest?.day ?? 21}.${c.longest?.month ?? 6}.`" :icon="mdiWeatherSunny" />
        <CurveStrip :steps="c.shortest?.steps || []" :label="`${c.shortest?.day ?? 21}.${c.shortest?.month ?? 12}.`" :icon="mdiSnowflake" scale />
        <div class="small muted">{{ t("circNow", { v: nowText(c) }) }}</div>
        <template #actions>
          <button class="btn flat sm" :disabled="!!busy[c.id]" :title="t('gwStartHint')" @click="startStop(c, 'start')">
            <Icon :path="mdiPlay" :size="16" />{{ t("start") }}
          </button>
          <button class="btn flat sm" :disabled="!!busy[c.id]" :title="t('gwStopHint')" @click="startStop(c, 'stop')">
            <Icon :path="mdiStop" :size="16" />{{ t("stop") }}
          </button>
        </template>
      </ItemCard>
    </div>

    <Modal
      :open="!!draft"
      wide
      :title="draft?.id != null ? t('editCircadian') : t('newCircadian')"
      :subtitle="draft?.id != null ? `ID ${draft.id}` : t('circEditorSub')"
      :icon="mdiThemeLightDark"
      @close="closeEditor"
    >
      <div v-if="draft" class="auto-editor">
        <div class="form-grid">
          <label class="field">
            <span>{{ t("name") }}</span>
            <input v-model="draft.name" type="text" maxlength="64" :placeholder="t('circNamePh')" />
          </label>
          <div class="field">
            <span>{{ t("enabled") }}</span>
            <div class="row toggle-row"><Toggle v-model="draft.enabled" /><span class="small muted">{{ draft.enabled ? t("circEnabledHint") : t("circDisabledHint") }}</span></div>
          </div>
        </div>

        <div class="section-title">{{ t("targets") }}</div>
        <TargetPicker v-model="draft.targets" />
        <div v-if="kelvinUnsupported" class="chip warn mt"><Icon :path="mdiAlertOutline" :size="14" />{{ t("circNoKelvin") }}</div>

        <div class="section-title">{{ t("curves") }}</div>
        <div class="banner info small mb">
          <Icon :path="mdiInformationOutline" :size="18" />
          <div>{{ t("curveHowto") }}</div>
        </div>
        <CurveEditor :longest="draft.longest" :shortest="draft.shortest" />
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
import { computed, onMounted, reactive, ref } from "vue";
import {
  mdiAlertCircleOutline,
  mdiAlertOutline,
  mdiInformationOutline,
  mdiPlay,
  mdiPlus,
  mdiSnowflake,
  mdiStop,
  mdiThemeLightDark,
  mdiWeatherSunny,
} from "@mdi/js";
import Icon from "../Icon.vue";
import Modal from "../Modal.vue";
import Toggle from "../Toggle.vue";
import Empty from "../Empty.vue";
import TargetPicker from "../TargetPicker.vue";
import ItemCard from "./ItemCard.vue";
import CurveStrip from "./CurveStrip.vue";
import CurveEditor from "./CurveEditor.vue";
import { gw } from "../../lib/api";
import { confirmDialog, run, type Target } from "../../lib/store";
import { useAT } from "./i18n";
import { auto, getLocation, load } from "./data";
import {
  actionSupport,
  clone,
  curveValue,
  plainTargets,
  targetsText,
  type CircadianCurve,
  type CircadianItem,
  type CircadianStep,
} from "./util";

const t = useAT();

interface Draft {
  id: number | null;
  name: string;
  enabled: boolean;
  targets: Target[];
  longest: CircadianCurve;
  shortest: CircadianCurve;
}

const busy = reactive<Record<number, boolean>>({});
const draft = ref<Draft | null>(null);
const saving = ref(false);
const southern = ref(false);
let snapshot = "";

onMounted(async () => {
  const loc = await getLocation();
  southern.value = !!loc && loc.lat < 0;
});

function nowText(c: CircadianItem) {
  // Rough preview: value of the curve closest to today's date (no seasonal blending).
  const now = new Date();
  const h = now.getHours();
  const month = now.getMonth() + 1;
  const summerFirst = !southern.value;
  const nearSummer = month >= 4 && month <= 9 ? summerFirst : !summerFirst;
  const steps = (nearSummer ? c.longest?.steps : c.shortest?.steps) || [];
  const lvl = curveValue(steps, h, "dimmable");
  const k = curveValue(steps, h, "colorKelvin");
  const parts: string[] = [];
  if (lvl !== null) parts.push(`${Math.round(lvl)} %`);
  if (k !== null) parts.push(`${Math.round(k / 10) * 10} K`);
  return parts.join(" · ") || "–";
}

// ------------------------------------------------------------------ list actions
async function setEnabled(c: CircadianItem, v: boolean) {
  busy[c.id] = true;
  await run(() => gw.put(`/automations/circadian/${c.id}`, { enabled: v }), v ? t("enabledToast", { name: c.name }) : t("disabledToast", { name: c.name }));
  await load("circadians");
  busy[c.id] = false;
}

async function startStop(c: CircadianItem, what: "start" | "stop") {
  busy[c.id] = true;
  await run(
    () => gw.post(`/automations/circadian/${c.id}/${what}`),
    what === "start" ? t("gwStarted", { name: c.name }) : t("gwStopped", { name: c.name }),
  );
  await load("circadians");
  busy[c.id] = false;
}

async function remove(c: CircadianItem) {
  const ok = await confirmDialog({
    title: t("deleteCircTitle"),
    message: t("deleteMsg", { name: c.name || `#${c.id}` }),
    danger: true,
    confirmText: t("delete"),
  });
  if (!ok) return;
  await run(() => gw.del(`/automations/circadian/${c.id}`), t("deleted"));
  await load("circadians");
}

// ------------------------------------------------------------------ editor
function normCurve(c: CircadianCurve | undefined, day: number, month: number): CircadianCurve {
  return {
    day: c?.day || day,
    month: c?.month || month,
    steps: (c?.steps || [])
      .map((s) => ({
        hour: s.hour,
        dimmable: typeof s.dimmable === "number" ? s.dimmable : 100,
        enableDimmable: s.enableDimmable !== false && typeof s.dimmable === "number",
        colorKelvin: typeof s.colorKelvin === "number" ? s.colorKelvin : 4000,
        enableKelvin: s.enableKelvin !== false && typeof s.colorKelvin === "number",
      }))
      .sort((a, b) => a.hour - b.hour),
  };
}

function defaults() {
  // Longest day = summer solstice (21.6. north / 21.12. south of the equator).
  return southern.value
    ? { longest: { day: 21, month: 12 }, shortest: { day: 21, month: 6 } }
    : { longest: { day: 21, month: 6 }, shortest: { day: 21, month: 12 } };
}

function openDraft(d: Draft, fresh = false) {
  draft.value = d;
  snapshot = fresh ? "" : JSON.stringify(d);
}

function openNew() {
  const def = defaults();
  const pt = (hour: number, d: number, k: number): CircadianStep => ({ hour, dimmable: d, enableDimmable: true, colorKelvin: k, enableKelvin: true });
  openDraft({
    id: null,
    name: t("circDefaultName", { n: auto.circadians.length + 1 }),
    enabled: true,
    targets: [],
    longest: { ...def.longest, steps: [pt(5, 10, 2700), pt(7, 60, 3500), pt(9, 90, 4500), pt(12, 100, 6000), pt(15, 100, 5500), pt(18, 80, 4000), pt(20, 50, 3000), pt(22, 20, 2700)] },
    shortest: { ...def.shortest, steps: [pt(7, 10, 2700), pt(9, 60, 3500), pt(12, 100, 5000), pt(14, 90, 4500), pt(16, 70, 3500), pt(18, 40, 2700), pt(21, 15, 2700)] },
  });
}

function fromItem(c: CircadianItem, asCopy: boolean): Draft {
  const def = defaults();
  return {
    id: asCopy ? null : c.id,
    name: asCopy ? t("copyOf", { name: c.name || `#${c.id}` }) : c.name || "",
    enabled: c.enabled !== false,
    targets: clone(c.targets || []),
    longest: normCurve(c.longest, def.longest.day, def.longest.month),
    shortest: normCurve(c.shortest, def.shortest.day, def.shortest.month),
  };
}
const openEdit = (c: CircadianItem) => openDraft(fromItem(c, false));
const duplicate = (c: CircadianItem) => openDraft(fromItem(c, true), true);

const kelvinUnsupported = computed(() => {
  const d = draft.value;
  if (!d || !d.targets.length) return false;
  const usesKelvin = [...d.longest.steps, ...d.shortest.steps].some((s) => s.enableKelvin);
  return usesKelvin && actionSupport(d.targets, { colorKelvin: 4000 }) === "none";
});

const DAYS_IN_MONTH = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
const issues = computed(() => {
  const d = draft.value;
  if (!d) return [];
  const out: string[] = [];
  if (!d.name.trim()) out.push(t("issueName"));
  if (!d.targets.length) out.push(t("issueNoTargets"));
  for (const [key, c] of [
    ["curveLongest", d.longest],
    ["curveShortest", d.shortest],
  ] as const) {
    const name = t(key);
    if (!c.steps.length) out.push(t("issueCurveEmpty", { curve: name }));
    if (!(c.day >= 1 && c.day <= DAYS_IN_MONTH[c.month - 1])) out.push(t("issueCurveDate", { curve: name }));
    for (const s of c.steps) {
      const lvl = Number(s.dimmable);
      const k = Number(s.colorKelvin);
      if (s.enableDimmable && !(Number.isFinite(lvl) && lvl >= 0 && lvl <= 100)) out.push(t("issueCurveValue", { curve: name, h: s.hour }));
      else if (s.enableKelvin && !(Number.isFinite(k) && k >= 1000 && k <= 20000)) out.push(t("issueCurveValue", { curve: name, h: s.hour }));
    }
  }
  return out;
});

function curveBody(c: CircadianCurve): CircadianCurve {
  return {
    day: c.day,
    month: c.month,
    steps: [...c.steps]
      .sort((a, b) => a.hour - b.hour)
      .map((s) => ({
        hour: s.hour,
        dimmable: Number(s.dimmable) || 0,
        enableDimmable: !!s.enableDimmable,
        colorKelvin: Number(s.colorKelvin) || 4000,
        enableKelvin: !!s.enableKelvin,
      })),
  };
}

async function save() {
  const d = draft.value;
  if (!d || issues.value.length) return;
  saving.value = true;
  // "enabled" is always sent explicitly: the update model defaults it to true.
  const body = {
    name: d.name.trim(),
    enabled: d.enabled,
    targets: plainTargets(d.targets),
    longest: curveBody(d.longest),
    shortest: curveBody(d.shortest),
  };
  const res =
    d.id == null
      ? await run(() => gw.post("/automations/circadian", body), t("createdToast", { name: body.name }))
      : await run(() => gw.put(`/automations/circadian/${d.id}`, body), t("savedToast", { name: body.name }));
  saving.value = false;
  if (res === undefined) return;
  draft.value = null;
  await load("circadians");
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
.footer-issue { color: var(--error); display: inline-flex; align-items: center; gap: 4px; margin-right: auto; max-width: 100%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
</style>
