<template>
  <div>
    <p class="tab-intro">{{ t("schedIntro") }}</p>

    <div v-if="auto.errors.schedules" class="banner err mb">
      <Icon :path="mdiAlertCircleOutline" />
      <div>{{ t("loadError") }}: {{ auto.errors.schedules }}</div>
    </div>

    <div v-if="clockWarn" class="banner warn mb">
      <Icon :path="mdiClockAlertOutline" />
      <div>{{ clockWarn }}</div>
    </div>

    <div class="tab-toolbar">
      <div class="grow clock-info small muted">
        <span v-if="gwTime" class="row"><Icon :path="mdiClockOutline" :size="15" />{{ t("gatewayTime") }}: <b>{{ gwTime }}</b> ({{ gwTz }})</span>
        <span v-if="sunToday" class="row">
          <Icon :path="mdiWeatherSunsetUp" :size="15" />{{ fmtDateTime(sunToday.sunrise) }}
          <Icon :path="mdiWeatherSunsetDown" :size="15" />{{ fmtDateTime(sunToday.sunset) }}
        </span>
      </div>
      <button class="btn" @click="openNew"><Icon :path="mdiPlus" :size="18" />{{ t("newSchedule") }}</button>
    </div>

    <div v-if="!auto.schedules.length" class="card">
      <Empty :icon="mdiCalendarClock" :text="t('schedEmpty')">
        <div class="faint small empty-hint">{{ t("schedEmptyHint") }}</div>
        <button class="btn" @click="openNew"><Icon :path="mdiPlus" :size="18" />{{ t("newSchedule") }}</button>
      </Empty>
    </div>

    <div v-else class="grid cols-3">
      <ItemCard
        v-for="s in sorted"
        :key="s.id"
        :title="s.name"
        :icon="modeIcon(s.recallMode)"
        :enabled="s.enabled"
        :busy="!!busy[s.id]"
        duplicable
        @edit="openEdit(s)"
        @delete="remove(s)"
        @duplicate="duplicate(s)"
        @toggle="(v: boolean) => setEnabled(s, v)"
      >
        <template #sub>{{ weekdaysText(s.activeWeekdays) }}</template>
        <div class="when">
          <span class="when-main">{{ s.recallMode === "timeOfDay" ? fmtClock(s.recallTime) : whenText(s.recallMode, s.recallTime) }}</span>
          <span v-if="s.recallMode !== 'timeOfDay' && todayAt(s.recallMode, s.recallTime)" class="chip" :title="t('todayApprox')">
            {{ t("today") }} ≈ {{ fmtDateTime(todayAt(s.recallMode, s.recallTime)) }}
          </span>
        </div>
        <div class="wd-dots">
          <span v-for="(d, i) in WEEKDAYS" :key="d" class="wd-dot" :class="{ on: s.activeWeekdays?.[d] !== false }">{{ wdShort(i) }}</span>
        </div>
        <div class="small action-line">
          <span class="swatch" :style="{ background: actionColor(s.action?.data) }"></span>
          <b>{{ actionSummary(s.action?.data, t) }}</b>
          <span class="muted">→ {{ targetsText(s.targets, t) }}</span>
        </div>
        <div v-if="restrictions(s).length" class="row wrap">
          <span v-for="r in restrictions(s)" :key="r" class="chip">{{ r }}</span>
        </div>
      </ItemCard>
    </div>

    <!-- ------------------------------------------------------------ editor -->
    <Modal
      :open="!!draft"
      wide
      :title="draft?.id != null ? t('editSchedule') : t('newSchedule')"
      :subtitle="draft?.id != null ? `ID ${draft.id}` : t('schedEditorSub')"
      :icon="mdiCalendarClock"
      @close="closeEditor"
    >
      <div v-if="draft" class="auto-editor">
        <div class="banner info summary-banner">
          <Icon :path="modeIcon(draftMode)" />
          <div><b>{{ draftSummary }}</b></div>
        </div>

        <div class="form-grid mt">
          <label class="field">
            <span>{{ t("name") }}</span>
            <input v-model="draft.name" type="text" maxlength="64" :placeholder="t('schedNamePh')" />
          </label>
          <div class="field">
            <span>{{ t("enabled") }}</span>
            <div class="row toggle-row"><Toggle v-model="draft.enabled" /><span class="small muted">{{ draft.enabled ? t("schedEnabledHint") : t("schedDisabledHint") }}</span></div>
          </div>
        </div>

        <div class="section-title">{{ t("when") }}</div>
        <div class="row wrap gap-lg">
          <div class="btn-group">
            <button type="button" :class="{ active: draft.base === 'time' }" @click="draft.base = 'time'">
              <Icon :path="mdiClockOutline" :size="16" /> {{ t("modeTime") }}
            </button>
            <button type="button" :class="{ active: draft.base === 'sunrise' }" @click="draft.base = 'sunrise'">
              <Icon :path="mdiWeatherSunsetUp" :size="16" /> {{ t("sunrise") }}
            </button>
            <button type="button" :class="{ active: draft.base === 'sunset' }" @click="draft.base = 'sunset'">
              <Icon :path="mdiWeatherSunsetDown" :size="16" /> {{ t("sunset") }}
            </button>
          </div>
        </div>

        <div v-if="draft.base === 'time'" class="form-grid mt">
          <label class="field">
            <span>{{ t("timeOfDay") }}</span>
            <input v-model="timeStr" type="time" step="1" />
            <span class="hint">{{ t("timeOfDayHint", { tz: gwTz || "?" }) }}</span>
          </label>
        </div>
        <template v-else>
          <div class="row wrap mt sun-row">
            <label class="field off-field">
              <span>{{ t("offset") }}</span>
              <div class="row">
                <input v-model.number="draft.offset.hour" type="number" min="0" max="23" step="1" class="off-in" />
                <span class="muted">h</span>
                <input v-model.number="draft.offset.minute" type="number" min="0" max="59" step="1" class="off-in" />
                <span class="muted">min</span>
              </div>
            </label>
            <div class="field">
              <span>&nbsp;</span>
              <div class="btn-group">
                <button type="button" :class="{ active: draft.rel === 'before' }" @click="draft.rel = 'before'">{{ t("before") }}</button>
                <button type="button" :class="{ active: draft.rel === 'after' }" @click="draft.rel = 'after'">{{ t("after") }}</button>
              </div>
            </div>
            <div class="field grow">
              <span>&nbsp;</span>
              <div class="muted">
                {{ draft.base === "sunrise" ? t("sunrise") : t("sunset") }}
                <template v-if="todayAt(draftMode, draft.offset)">
                  · {{ t("today") }} ≈ <b>{{ fmtDateTime(todayAt(draftMode, draft.offset)) }}</b>
                </template>
              </div>
            </div>
          </div>
          <div class="banner info mt small">
            <Icon :path="mdiInformationOutline" :size="18" />
            <div>
              {{ t("sunHint") }}
              <template v-if="location"> {{ t("sunLocation", { lat: fmtNum(location.lat, 3), lon: fmtNum(location.lon, 3) }) }}</template>
              <template v-else> {{ t("sunNoLocation") }}</template>
            </div>
          </div>
        </template>

        <div class="section-title">{{ t("weekdays") }}</div>
        <div class="row wrap day-chips">
          <button
            v-for="(d, i) in WEEKDAYS"
            :key="d"
            type="button"
            class="chip clickable daychip"
            :class="{ primary: draft.weekdays[d] }"
            @click="draft.weekdays[d] = !draft.weekdays[d]"
          >
            {{ wdShort(i) }}
          </button>
          <span class="sep"></span>
          <button type="button" class="btn flat sm" @click="setWeekdays('all')">{{ t("daily") }}</button>
          <button type="button" class="btn flat sm" @click="setWeekdays('work')">{{ t("workdays") }}</button>
          <button type="button" class="btn flat sm" @click="setWeekdays('weekend')">{{ t("weekend") }}</button>
        </div>

        <div class="section-title">{{ t("months") }}</div>
        <div class="row wrap day-chips">
          <button
            v-for="(m, i) in MONTHS"
            :key="m"
            type="button"
            class="chip clickable daychip"
            :class="{ primary: draft.months[m] }"
            @click="draft.months[m] = !draft.months[m]"
          >
            {{ monthShort(i) }}
          </button>
          <span class="sep"></span>
          <button type="button" class="btn flat sm" @click="setMonths(true)">{{ t("all") }}</button>
        </div>

        <details class="adv" :open="draft.useDays || draft.usePeriod">
          <summary>{{ t("advancedRestrictions") }}</summary>
          <div class="adv-body">
            <label class="row adv-toggle">
              <Toggle v-model="draft.useDays" />
              <span>{{ t("useDays") }}</span>
            </label>
            <div v-if="draft.useDays" class="month-days">
              <button
                v-for="n in 31"
                :key="n"
                type="button"
                class="md"
                :class="{ on: draft.days.includes(n) }"
                @click="toggleDay(n)"
              >
                {{ n }}
              </button>
            </div>
            <label class="row adv-toggle mt">
              <Toggle v-model="draft.usePeriod" />
              <span>{{ t("usePeriod") }}</span>
            </label>
            <div v-if="draft.usePeriod" class="row wrap period">
              <span class="muted">{{ t("from") }}</span>
              <select v-model.number="draft.period.startDay" class="p-day"><option v-for="n in 31" :key="n" :value="n">{{ n }}.</option></select>
              <select v-model.number="draft.period.startMonth" class="p-month"><option v-for="(m, i) in MONTHS" :key="m" :value="i + 1">{{ monthLong(i) }}</option></select>
              <span class="muted">{{ t("to") }}</span>
              <select v-model.number="draft.period.endDay" class="p-day"><option v-for="n in 31" :key="n" :value="n">{{ n }}.</option></select>
              <select v-model.number="draft.period.endMonth" class="p-month"><option v-for="(m, i) in MONTHS" :key="m" :value="i + 1">{{ monthLong(i) }}</option></select>
            </div>
            <div class="hint small faint mt">{{ t("restrictHint") }}</div>
          </div>
        </details>

        <div class="section-title">{{ t("targets") }}</div>
        <TargetPicker v-model="draft.targets" />

        <div class="section-title">{{ t("action") }}</div>
        <ActionEditor v-model="draft.features" :targets="draft.targets" />
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
  mdiCalendarClock,
  mdiClockAlertOutline,
  mdiClockOutline,
  mdiInformationOutline,
  mdiPlus,
  mdiWeatherSunsetDown,
  mdiWeatherSunsetUp,
} from "@mdi/js";
import Icon from "../Icon.vue";
import Modal from "../Modal.vue";
import Toggle from "../Toggle.vue";
import Empty from "../Empty.vue";
import TargetPicker from "../TargetPicker.vue";
import ActionEditor from "./ActionEditor.vue";
import ItemCard from "./ItemCard.vue";
import { gw } from "../../lib/api";
import { confirmDialog, run, type Target } from "../../lib/store";
import { useAT } from "./i18n";
import { auto, getLocation, load } from "./data";
import {
  MONTHS,
  WEEKDAYS,
  actionColor,
  actionSummary,
  clone,
  fmtClock,
  fmtDateTime,
  fmtNum,
  fmtOffset,
  isRestrictiveDays,
  isRestrictivePeriod,
  pad2,
  plainTargets,
  sunTimes,
  targetsText,
  type ActivePeriod,
  type Features,
  type RecallMode,
  type SchedTime,
  type SchedulerItem,
} from "./util";

const t = useAT();

interface Draft {
  id: number | null;
  name: string;
  enabled: boolean;
  targets: Target[];
  features: Features;
  base: "time" | "sunrise" | "sunset";
  rel: "before" | "after";
  time: SchedTime;
  offset: SchedTime;
  weekdays: Record<string, boolean>;
  months: Record<string, boolean>;
  useDays: boolean;
  days: number[];
  usePeriod: boolean;
  period: ActivePeriod;
  hadDays: boolean;
  hadPeriod: boolean;
}

const busy = reactive<Record<number, boolean>>({});
const draft = ref<Draft | null>(null);
const saving = ref(false);
let snapshot = "";

// ------------------------------------------------------------------ gateway clock / location
const location = ref<{ lat: number; lon: number } | null>(null);
const gwTime = ref("");
const gwTz = ref("");
const gwOffsetMin = ref<number | null>(null);

onMounted(async () => {
  location.value = await getLocation();
  try {
    const dt = await gw.get("/datetime");
    gwTz.value = dt?.timezone || "";
    const m = /^(\d{1,2}):(\d{2})(?::(\d{2}))?/.exec(String(dt?.time || ""));
    if (m) {
      gwTime.value = `${pad2(+m[1])}:${m[2]}`;
      const now = new Date();
      const gwMin = +m[1] * 60 + +m[2];
      const localMin = now.getHours() * 60 + now.getMinutes();
      let diff = (gwMin - localMin) % 1440;
      if (diff > 720) diff -= 1440;
      if (diff < -720) diff += 1440;
      gwOffsetMin.value = diff;
    }
  } catch {
    /* not available */
  }
});

const clockWarn = computed(() => {
  if (gwOffsetMin.value === null || Math.abs(gwOffsetMin.value) <= 3) return "";
  const local = new Date().toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });
  return t("clockWarn", { gw: gwTime.value, tz: gwTz.value || "?", local });
});

const sunToday = computed(() => {
  if (!location.value) return null;
  const d = new Date();
  d.setHours(12, 0, 0, 0);
  return sunTimes(d, location.value.lat, location.value.lon);
});

function todayAt(mode: RecallMode, time: Partial<SchedTime> | undefined): Date | null {
  if (mode === "timeOfDay" || !sunToday.value) return null;
  const base = mode.endsWith("Sunrise") ? sunToday.value.sunrise : sunToday.value.sunset;
  if (!base) return null;
  const off = ((time?.hour || 0) * 3600 + (time?.minute || 0) * 60 + (time?.second || 0)) * 1000;
  return new Date(base.getTime() + (mode.startsWith("before") ? -off : off));
}

// ------------------------------------------------------------------ text helpers
const wdShort = (i: number) => t(`wd${i}`);
const monthShort = (i: number) => t(`mo${i}`);
const monthLong = (i: number) => t(`month${i}`);

function modeIcon(mode: RecallMode) {
  if (mode === "timeOfDay") return mdiClockOutline;
  return mode.endsWith("Sunrise") ? mdiWeatherSunsetUp : mdiWeatherSunsetDown;
}

function whenText(mode: RecallMode, time: Partial<SchedTime> | undefined): string {
  if (mode === "timeOfDay") return fmtClock(time);
  const ev = mode.endsWith("Sunrise") ? t("sunriseEv") : t("sunsetEv");
  const off = fmtOffset(time);
  if (!off) return t("atSunEvent", { ev });
  return mode.startsWith("before") ? t("beforeSun", { off, ev }) : t("afterSun", { off, ev });
}

/** Compress consecutive flags into ranges ("Mo–Fr", "Sa, So"). */
function runs(flags: boolean[], label: (i: number) => string): string {
  const parts: string[] = [];
  let i = 0;
  while (i < flags.length) {
    if (!flags[i]) {
      i++;
      continue;
    }
    let j = i;
    while (j + 1 < flags.length && flags[j + 1]) j++;
    const len = j - i + 1;
    if (len >= 3) parts.push(`${label(i)}–${label(j)}`);
    else for (let k = i; k <= j; k++) parts.push(label(k));
    i = j + 1;
  }
  return parts.join(", ");
}

function weekdaysText(w: Record<string, boolean> | null | undefined): string {
  const flags = WEEKDAYS.map((d) => w?.[d] !== false);
  const n = flags.filter(Boolean).length;
  if (n === 7) return t("daily");
  if (n === 0) return t("noWeekdays");
  if (n === 2 && flags[5] && flags[6]) return t("weekend");
  return runs(flags, wdShort);
}

function monthsText(m: Record<string, boolean> | null | undefined): string {
  const flags = MONTHS.map((x) => m?.[x] !== false);
  const n = flags.filter(Boolean).length;
  if (n === 12) return "";
  if (n === 0) return t("noMonths");
  return runs(flags, monthShort);
}

function periodText(p: ActivePeriod) {
  return `${p.startDay}.${p.startMonth}. – ${p.endDay}.${p.endMonth}.`;
}

function restrictions(s: SchedulerItem): string[] {
  const out: string[] = [];
  const mt = monthsText(s.activeMonths);
  if (mt) out.push(mt);
  if (isRestrictiveDays(s.activeDays?.days)) out.push(t("onDays", { days: compactDays(s.activeDays!.days) }));
  if (isRestrictivePeriod(s.activePeriod)) out.push(periodText(s.activePeriod!));
  return out;
}

function compactDays(days: number[]): string {
  const flags = Array.from({ length: 31 }, (_, i) => days.includes(i + 1));
  return runs(flags, (i) => t("dayNum", { n: i + 1 }));
}

function summaryOf(mode: RecallMode, time: Partial<SchedTime>, weekdays: Record<string, boolean>, features: Features, targets: Target[]) {
  return t("schedSummary", {
    days: weekdaysText(weekdays),
    when: whenText(mode, time),
    action: actionSummary(features, t),
    targets: targetsText(targets, t),
  });
}

const sorted = computed(() => {
  const key = (s: SchedulerItem) => {
    const tm = (s.recallTime?.hour || 0) * 3600 + (s.recallTime?.minute || 0) * 60 + (s.recallTime?.second || 0);
    if (s.recallMode === "timeOfDay") return tm;
    const d = todayAt(s.recallMode, s.recallTime);
    if (d) return d.getHours() * 3600 + d.getMinutes() * 60 + d.getSeconds();
    return s.recallMode.endsWith("Sunrise") ? 6 * 3600 : 19 * 3600;
  };
  return [...auto.schedules].sort((a, b) => key(a) - key(b));
});

// ------------------------------------------------------------------ list actions
async function setEnabled(s: SchedulerItem, v: boolean) {
  busy[s.id] = true;
  await run(() => gw.put(`/automations/scheduler/${s.id}`, { enabled: v }), v ? t("enabledToast", { name: s.name }) : t("disabledToast", { name: s.name }));
  await load("schedules");
  busy[s.id] = false;
}

async function remove(s: SchedulerItem) {
  const ok = await confirmDialog({
    title: t("deleteSchedTitle"),
    message: t("deleteMsg", { name: s.name || `#${s.id}` }),
    danger: true,
    confirmText: t("delete"),
  });
  if (!ok) return;
  await run(() => gw.del(`/automations/scheduler/${s.id}`), t("deleted"));
  await load("schedules");
}

// ------------------------------------------------------------------ editor
const allWeekdays = (v = true) => Object.fromEntries(WEEKDAYS.map((d) => [d, v]));
const allMonths = (v = true) => Object.fromEntries(MONTHS.map((m) => [m, v]));
const FULL_YEAR: ActivePeriod = { startMonth: 1, startDay: 1, endMonth: 12, endDay: 31 };

function fromItem(s: SchedulerItem | null, asCopy = false): Draft {
  const mode = s?.recallMode ?? "timeOfDay";
  const time = { hour: s?.recallTime?.hour ?? 7, minute: s?.recallTime?.minute ?? 0, second: s?.recallTime?.second ?? 0 };
  const isTime = mode === "timeOfDay";
  const days = s?.activeDays?.days ?? [];
  const restrictiveDays = isRestrictiveDays(days);
  const restrictivePeriod = isRestrictivePeriod(s?.activePeriod);
  return {
    id: s && !asCopy ? s.id : null,
    name: s ? (asCopy ? t("copyOf", { name: s.name || `#${s.id}` }) : s.name || "") : t("schedDefaultName", { n: auto.schedules.length + 1 }),
    enabled: s ? s.enabled !== false : true,
    targets: clone(s?.targets ?? []),
    features: clone(s?.action?.data ?? { dimmable: 80 }),
    base: isTime ? "time" : mode.endsWith("Sunrise") ? "sunrise" : "sunset",
    rel: mode.startsWith("after") ? "after" : "before",
    time: isTime ? time : { hour: 7, minute: 0, second: 0 },
    offset: isTime ? { hour: 0, minute: 30, second: 0 } : time,
    weekdays: { ...allWeekdays(true), ...(s?.activeWeekdays ?? {}) },
    months: { ...allMonths(true), ...(s?.activeMonths ?? {}) },
    useDays: restrictiveDays,
    days: restrictiveDays ? [...days].sort((a, b) => a - b) : [],
    usePeriod: restrictivePeriod,
    period: restrictivePeriod ? { ...(s!.activePeriod as ActivePeriod) } : { startMonth: 5, startDay: 1, endMonth: 9, endDay: 30 },
    hadDays: !asCopy && restrictiveDays,
    hadPeriod: !asCopy && restrictivePeriod,
  };
}

function openDraft(d: Draft, fresh = false) {
  draft.value = d;
  snapshot = fresh ? "" : JSON.stringify(d);
}
const openNew = () => openDraft(fromItem(null));
const openEdit = (s: SchedulerItem) => openDraft(fromItem(s));
const duplicate = (s: SchedulerItem) => openDraft(fromItem(s, true), true);

const draftMode = computed<RecallMode>(() => {
  const d = draft.value;
  if (!d || d.base === "time") return "timeOfDay";
  return `${d.rel}${d.base === "sunrise" ? "Sunrise" : "Sunset"}` as RecallMode;
});

const timeStr = computed({
  get: () => (draft.value ? `${pad2(draft.value.time.hour)}:${pad2(draft.value.time.minute)}:${pad2(draft.value.time.second)}` : ""),
  set: (v: string) => {
    const m = /^(\d{1,2}):(\d{2})(?::(\d{2}))?/.exec(v || "");
    if (!m || !draft.value) return;
    draft.value.time = { hour: +m[1], minute: +m[2], second: m[3] ? +m[3] : 0 };
  },
});

const draftSummary = computed(() => {
  const d = draft.value;
  if (!d) return "";
  return summaryOf(draftMode.value, d.base === "time" ? d.time : d.offset, d.weekdays, d.features, d.targets);
});

function setWeekdays(kind: "all" | "work" | "weekend") {
  if (!draft.value) return;
  WEEKDAYS.forEach((d, i) => (draft.value!.weekdays[d] = kind === "all" ? true : kind === "work" ? i < 5 : i >= 5));
}
function setMonths(v: boolean) {
  if (draft.value) draft.value.months = allMonths(v);
}
function toggleDay(n: number) {
  const d = draft.value;
  if (!d) return;
  const i = d.days.indexOf(n);
  if (i >= 0) d.days.splice(i, 1);
  else d.days = [...d.days, n].sort((a, b) => a - b);
}

const DAYS_IN_MONTH = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
const issues = computed(() => {
  const d = draft.value;
  if (!d) return [];
  const out: string[] = [];
  if (!d.name.trim()) out.push(t("issueName"));
  if (!d.targets.length) out.push(t("issueNoTargets"));
  if (!Object.keys(d.features || {}).length) out.push(t("issueNoAction"));
  if (!WEEKDAYS.some((w) => d.weekdays[w])) out.push(t("issueNoWeekdays"));
  if (!MONTHS.some((m) => d.months[m])) out.push(t("issueNoMonths"));
  if (d.useDays && !d.days.length) out.push(t("issueNoDays"));
  if (d.usePeriod) {
    const p = d.period;
    if (p.startDay > DAYS_IN_MONTH[p.startMonth - 1] || p.endDay > DAYS_IN_MONTH[p.endMonth - 1]) out.push(t("issuePeriod"));
  }
  const tm = d.base === "time" ? d.time : d.offset;
  const okNum = (v: any, max: number) => Number.isInteger(Number(v)) && Number(v) >= 0 && Number(v) <= max;
  if (!okNum(tm.hour, 23) || !okNum(tm.minute, 59) || !okNum(tm.second, 59)) out.push(t("issueTime"));
  return out;
});

async function save() {
  const d = draft.value;
  if (!d || issues.value.length) return;
  saving.value = true;
  const tm = d.base === "time" ? d.time : d.offset;
  const body: Record<string, unknown> = {
    name: d.name.trim(),
    enabled: d.enabled,
    targets: plainTargets(d.targets),
    recallMode: draftMode.value,
    recallTime: { hour: Number(tm.hour) || 0, minute: Number(tm.minute) || 0, second: Number(tm.second) || 0 },
    action: { type: "features", data: d.features },
    activeWeekdays: { ...d.weekdays },
    activeMonths: { ...d.months },
  };
  // Optional restrictions: when switched off on an existing schedule, send the "no restriction" equivalent.
  if (d.useDays) body.activeDays = { days: [...d.days] };
  else if (d.hadDays) body.activeDays = { days: Array.from({ length: 31 }, (_, i) => i + 1) };
  if (d.usePeriod) body.activePeriod = { ...d.period };
  else if (d.hadPeriod) body.activePeriod = { ...FULL_YEAR };

  const res =
    d.id == null
      ? await run(() => gw.post("/automations/scheduler", body), t("createdToast", { name: body.name }))
      : await run(() => gw.put(`/automations/scheduler/${d.id}`, body), t("savedToast", { name: body.name }));
  saving.value = false;
  if (res === undefined) return;
  draft.value = null;
  await load("schedules");
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
.clock-info { display: flex; flex-wrap: wrap; gap: 4px 16px; align-items: center; }
.clock-info .row { gap: 4px; }
.when { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.when-main { font-size: 22px; font-weight: 500; line-height: 1.2; }
.wd-dots { display: flex; gap: 4px; }
.wd-dot { width: 26px; height: 22px; border-radius: 6px; font-size: 10.5px; display: inline-flex; align-items: center; justify-content: center; background: var(--bg2); color: var(--text3); font-weight: 500; }
.wd-dot.on { background: var(--primary-soft); color: var(--primary); }
.action-line { display: flex; align-items: center; gap: 6px; min-width: 0; }
.action-line .muted { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.toggle-row { min-height: 38px; }
.summary-banner { align-items: center; }
.day-chips { gap: 6px; }
.daychip { border: 0; min-width: 40px; justify-content: center; height: 30px; border-radius: 15px; }
.sep { width: 8px; }
.sun-row { gap: 12px 16px; align-items: flex-end; }
.off-in { width: 70px !important; }
.adv { margin-top: 16px; border: 1px solid var(--divider); border-radius: 12px; }
.adv summary { cursor: pointer; padding: 10px 14px; font-weight: 500; color: var(--text2); }
.adv-body { padding: 0 14px 14px; }
.adv-toggle { gap: 10px; cursor: pointer; }
.month-days { display: grid; grid-template-columns: repeat(auto-fill, minmax(38px, 1fr)); gap: 4px; margin-top: 10px; max-width: 420px; }
.md { height: 32px; border-radius: 8px; border: 1px solid var(--divider); background: transparent; color: var(--text2); cursor: pointer; font-size: 12.5px; }
.md.on { background: var(--primary); color: #fff; border-color: var(--primary); }
.period { margin-top: 10px; gap: 8px; }
.p-day { width: 76px !important; }
.p-month { width: 150px !important; }
.footer-issue { color: var(--error); display: inline-flex; align-items: center; gap: 4px; margin-right: auto; max-width: 100%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
</style>
