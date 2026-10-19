<template>
  <div class="mon">
    <!-- toolbar -->
    <section class="card tb">
      <div class="row wrap tb-row">
        <button class="btn sm" :class="{ gray: !paused }" @click="togglePause">
          <Icon :path="paused ? mdiPlay : mdiPause" :size="16" />{{ paused ? t("resume") : t("pause") }}
        </button>
        <button class="btn flat sm" :title="t('clearHint')" @click="clearView">
          <Icon :path="mdiNotificationClearAll" :size="16" />{{ t("clear") }}
        </button>
        <span class="chip rate" :class="{ ok: rate > 0 && !paused }" :title="t('rateHint')">
          <span class="dot" :class="{ ok: rate > 0, pulse: rate > 0 && !paused }"></span>
          <b class="mono">{{ rate.toFixed(1) }}</b>&nbsp;{{ t("fps") }}
        </span>
        <span class="grow"></span>
        <div class="btn-group" role="group">
          <button :class="{ active: newestFirst }" @click="newestFirst = true">{{ t("newestTop") }}</button>
          <button :class="{ active: !newestFirst }" @click="newestFirst = false">{{ t("chrono") }}</button>
        </div>
        <label v-if="!newestFirst" class="check" :title="t('followHint')">
          <Toggle v-model="follow" />{{ t("follow") }}
        </label>
      </div>

      <div class="filters">
        <div class="search-wrap">
          <Icon :path="mdiMagnify" :size="18" class="search-ico" />
          <input v-model="search" type="search" :placeholder="t('searchPh')" />
        </div>
        <input v-model="addr" class="addr" type="text" list="bus-mon-targets" :placeholder="t('addrPh')" :title="t('addrHint')" />
        <datalist id="bus-mon-targets">
          <option v-for="x in knownTargets" :key="x" :value="x" />
        </datalist>
        <select v-if="lineCount > 1" v-model="lineFilter" class="line-sel">
          <option :value="null">{{ t("allLines") }}</option>
          <option v-for="l in lineCount" :key="l" :value="l - 1">{{ t("line") }} {{ l - 1 }}</option>
        </select>
        <label class="check" :title="t('hidePollingHint')"><input v-model="hidePolling" type="checkbox" />{{ t("hidePolling") }}</label>
        <label class="check" :title="t('onlyExternalHint')"><input v-model="onlyExternal" type="checkbox" />{{ t("onlyExternal") }}</label>
      </div>

      <div class="row wrap kinds">
        <button
          v-for="k in KINDS"
          :key="k"
          class="chip kind-chip"
          :class="{ off: kinds.length > 0 && !kinds.includes(k) }"
          :style="kindStyle(k)"
          :title="kindHint(k)"
          @click="toggleKind(k)"
        >
          {{ kindLabel(k, lang) }}<span class="cnt">{{ counts[k] || 0 }}</span>
        </button>
        <button v-if="filtersActive" class="btn flat sm" @click="resetFilters">
          <Icon :path="mdiFilterRemove" :size="16" />{{ t("resetFilters") }}
        </button>
      </div>
    </section>

    <div class="mon-main" :class="{ split: showAside }">
      <section class="card list-card">
        <div v-if="paused" class="banner warn pause-banner">
          <Icon :path="mdiPause" :size="18" />
          <div class="grow">{{ t("pausedInfo", { n: missed }) }}</div>
          <button class="btn sm" @click="togglePause">{{ t("resume") }}</button>
        </div>

        <div v-if="!narrow" class="mon-grid mon-head">
          <span>{{ t("time") }}</span>
          <span :title="t('line')">{{ t("lineShort") }}</span>
          <span :title="t('srcHint')">{{ t("src") }}</span>
          <span>{{ t("kind") }}</span>
          <span>{{ t("target") }}</span>
          <span>Hex</span>
          <span>{{ t("decoded") }}</span>
        </div>

        <div ref="scroller" class="mon-scroll" tabindex="0" @scroll.passive="onScroll" @keydown="onKey">
          <Empty v-if="!rows.length" :icon="mdiTransitConnectionVariant" :text="emptyText">
            <button v-if="filtersActive" class="btn outline sm" @click="resetFilters">{{ t("resetFilters") }}</button>
          </Empty>
          <div v-else class="mon-spacer" :style="{ height: `${rows.length * rowH}px` }">
            <div class="mon-win" :style="{ transform: `translateY(${start * rowH}px)` }">
              <div
                v-for="f in visible"
                :key="keyOf(f)"
                class="mon-row"
                :class="{ sel: f === selected, 'mon-grid': !narrow, mob: narrow, ext: f.external && f.kind !== 'backward', ans: f.kind === 'backward', old: f.db, warnrow: !!f.warning }"
                :style="{ height: `${rowH}px` }"
                @click="select(f)"
              >
                <template v-if="!narrow">
                  <span class="mono c-time" :title="fmtMs(f.timestamp, true, lang)">{{ fmtMs(f.timestamp) }}</span>
                  <span class="mono c-line">{{ f.line }}</span>
                  <span><span class="src" :class="f.external ? 'ext' : 'gw'">{{ f.external ? "EXT" : "GW" }}</span></span>
                  <span><span class="kbadge" :style="kindStyle(f.kind)">{{ kindLabel(f.kind, lang) }}</span></span>
                  <span class="mono c-target">{{ f.target }}</span>
                  <span class="mono c-hex">{{ f.hex }}</span>
                  <span class="c-text" :title="f.warning ? `${f.text} – ${t('initAllWarn')}` : f.text">{{ f.text }}</span>
                </template>
                <template v-else>
                  <div class="mob-l1">
                    <span class="mono small">{{ fmtMs(f.timestamp) }}</span>
                    <span class="kbadge" :style="kindStyle(f.kind)">{{ kindLabel(f.kind, lang) }}</span>
                    <span class="mono small b">{{ f.target }}</span>
                    <span class="grow"></span>
                    <span class="src" :class="f.external ? 'ext' : 'gw'">{{ f.external ? "EXT" : "GW" }}</span>
                    <span class="mono small faint">{{ f.hex }}</span>
                  </div>
                  <div class="mob-l2 small" :title="f.warning ? t('initAllWarn') : undefined">{{ f.text }}</div>
                </template>
              </div>
            </div>
          </div>
        </div>

        <div class="mon-foot">
          <span class="small muted">{{ t("showing", { n: fmtInt(rows.length), total: fmtInt(combined.length) }) }}</span>
          <span v-if="pollHidden" class="small faint">· {{ t("pollHidden", { n: fmtInt(pollHidden) }) }}</span>
          <span v-if="older.length" class="small faint">· {{ t("olderCount", { n: fmtInt(older.length) }) }}</span>
          <span class="grow"></span>
          <button class="btn flat sm" :disabled="loadingOlder || noMoreOlder" :title="t('loadOlderHint')" @click="loadOlder">
            <span v-if="loadingOlder" class="spinner mini"></span>
            <Icon v-else :path="mdiHistory" :size="16" />
            {{ noMoreOlder ? t("noOlder") : t("loadOlder") }}
          </button>
          <div class="row csv" :title="t('csvHint')">
            <select v-model.number="csvHours" class="csv-sel">
              <option v-for="h in [1, 6, 24, 72, 168]" :key="h" :value="h">{{ h < 24 ? `${h} h` : `${h / 24} ${t("daysShort")}` }}</option>
            </select>
            <a class="btn outline sm" :href="downloadUrl(`monitor.csv?hours=${csvHours}`)" download>
              <Icon :path="mdiDownload" :size="16" />CSV
            </a>
          </div>
        </div>
      </section>

      <aside v-if="showAside && selected" class="card aside">
        <header class="aside-head">
          <div class="grow">
            <h3>{{ t("frameDetail") }}</h3>
            <div class="small muted mono">{{ fmtMs(selected.timestamp, true, lang) }}</div>
          </div>
          <button class="btn icon sm" :title="t('close')" @click="selected = null"><Icon :path="mdiClose" :size="18" /></button>
        </header>
        <div class="aside-body">
          <FrameDetail :frame="selected" :reply="selectedReply" @filter="applyAddr" @use="useFrame" @select="select" />
        </div>
      </aside>
    </div>

    <Modal
      :open="!!selected && !wide"
      :title="t('frameDetail')"
      :subtitle="selected ? fmtMs(selected.timestamp, true, lang) : ''"
      @close="selected = null"
    >
      <FrameDetail v-if="selected" :frame="selected" :reply="selectedReply" @filter="applyAddrAndClose" @use="useFrame" @select="select" />
    </Modal>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onActivated, onBeforeUnmount, onDeactivated, onMounted, ref, shallowRef, toRaw, watch } from "vue";
import {
  mdiClose,
  mdiDownload,
  mdiFilterRemove,
  mdiHistory,
  mdiMagnify,
  mdiNotificationClearAll,
  mdiPause,
  mdiPlay,
  mdiTransitConnectionVariant,
} from "@mdi/js";
import Icon from "../Icon.vue";
import Empty from "../Empty.vue";
import Modal from "../Modal.vue";
import Toggle from "../Toggle.vue";
import FrameDetail from "./FrameDetail.vue";
import { api, downloadUrl } from "../../lib/api";
import { monitorPaused, onMonitor, state, toast } from "../../lib/store";
import { lang, useT } from "../../lib/i18n";
import { KINDS, KIND_META, answerTo, fmtMs, fromDbRow, kindKey, kindLabel, kindStyle, useFrameRate, type Frame } from "./frames";

const emit = defineEmits<{ (e: "use-frame", f: Frame): void }>();

const t = useT({
  de: {
    pause: "Pause",
    resume: "Fortsetzen",
    clear: "Leeren",
    clearHint: "Ansicht leeren – nur neue Frames anzeigen",
    fps: "Frames/s",
    rateHint: "Durchschnittliche Frame-Rate der letzten 10 Sekunden",
    newestTop: "Neueste oben",
    chrono: "Chronologisch",
    follow: "Mitlaufen",
    followHint: "Automatisch zum neuesten Frame scrollen",
    searchPh: "Text, Hex oder Befehl suchen…",
    addrPh: "Adresse (A5, G3, BC, D12)",
    addrHint: "Eine oder mehrere Adressen, durch Komma getrennt. Antworten auf Abfragen an diese Adresse werden mit angezeigt.",
    allLines: "Alle Linien",
    hidePolling: "Gateway-Polling ausblenden",
    hidePollingHint: "Blendet die zyklischen Statusabfragen des Gateways und deren Antworten aus",
    onlyExternal: "Nur externe Frames",
    onlyExternalHint: "Nur Frames anderer Busteilnehmer (Taster, Sensoren, andere Steuergeräte, Antworten)",
    resetFilters: "Filter zurücksetzen",
    initAllWarn: "Adressierung – hier werden Kurzadressen neu vergeben, Gerätenamen danach prüfen",
    pausedInfo: "Aufzeichnung pausiert – neue Frames werden nicht übernommen ({n} verworfen).",
    lineShort: "L",
    src: "Quelle",
    srcHint: "GW = vom Gateway gesendet, EXT = von einem anderen Busteilnehmer",
    kind: "Art",
    target: "Ziel",
    decoded: "Dekodiert",
    showing: "{n} von {total} Frames",
    pollHidden: "{n} Polling-Frames ausgeblendet",
    olderCount: "{n} ältere geladen",
    loadOlder: "Ältere laden",
    loadOlderHint: "Lädt 500 ältere Frames aus der Verlaufsdatenbank des Add-ons",
    noOlder: "Keine älteren Frames",
    olderLoaded: "{n} ältere Frames geladen",
    csvHint: "Monitor-Verlauf als CSV exportieren",
    daysShort: "T",
    frameDetail: "Frame-Details",
    emptyLive: "Noch keine Frames empfangen. Sobald auf dem DALI-Bus kommuniziert wird, erscheinen die Frames hier live.",
    emptyFiltered: "Keine Frames passen zu den aktuellen Filtern.",
    emptyPaused: "Aufzeichnung pausiert.",
  },
  en: {
    pause: "Pause",
    resume: "Resume",
    clear: "Clear",
    clearHint: "Clear the view – only show new frames",
    fps: "frames/s",
    rateHint: "Average frame rate over the last 10 seconds",
    newestTop: "Newest on top",
    chrono: "Chronological",
    follow: "Follow",
    followHint: "Automatically scroll to the newest frame",
    searchPh: "Search text, hex or command…",
    addrPh: "Address (A5, G3, BC, D12)",
    addrHint: "One or more addresses, comma separated. Answers to queries sent to these addresses are included.",
    allLines: "All lines",
    hidePolling: "Hide gateway polling",
    hidePollingHint: "Hides the gateway's cyclic status queries and their answers",
    onlyExternal: "External frames only",
    onlyExternalHint: "Only frames of other bus participants (buttons, sensors, other controllers, answers)",
    resetFilters: "Reset filters",
    initAllWarn: "Addressing – short addresses are being assigned, check device names afterwards",
    pausedInfo: "Recording paused – new frames are not captured ({n} dropped).",
    lineShort: "L",
    src: "Source",
    srcHint: "GW = sent by the gateway, EXT = sent by another bus participant",
    kind: "Kind",
    target: "Target",
    decoded: "Decoded",
    showing: "{n} of {total} frames",
    pollHidden: "{n} polling frames hidden",
    olderCount: "{n} older loaded",
    loadOlder: "Load older",
    loadOlderHint: "Loads 500 older frames from the add-on's history database",
    noOlder: "No older frames",
    olderLoaded: "{n} older frames loaded",
    csvHint: "Export the monitor history as CSV",
    daysShort: "d",
    frameDetail: "Frame details",
    emptyLive: "No frames received yet. As soon as there is communication on the DALI bus, frames appear here live.",
    emptyFiltered: "No frames match the current filters.",
    emptyPaused: "Recording paused.",
  },
});

// ------------------------------------------------------------ preferences
const PREF_KEY = "lunatone.busmonitor";
function loadPrefs(): Record<string, any> {
  try {
    return JSON.parse(localStorage.getItem(PREF_KEY) || "{}") || {};
  } catch {
    return {};
  }
}
const prefs = loadPrefs();
const newestFirst = ref<boolean>(prefs.newestFirst ?? true);
const hidePolling = ref<boolean>(prefs.hidePolling ?? false);
const onlyExternal = ref<boolean>(false);
const csvHours = ref<number>(prefs.csvHours ?? 1);
const follow = ref(true);
watch([newestFirst, hidePolling, csvHours], () => {
  try {
    localStorage.setItem(PREF_KEY, JSON.stringify({ newestFirst: newestFirst.value, hidePolling: hidePolling.value, csvHours: csvHours.value }));
  } catch {
    /* storage unavailable */
  }
});

const search = ref("");
const addr = ref("");
const lineFilter = ref<number | null>(null);
const kinds = ref<string[]>([]);
const lineCount = computed(() => Number(state.info?.descriptor?.lines) || Object.keys(state.info?.lines || {}).length || 1);

function toggleKind(k: string) {
  const i = kinds.value.indexOf(k);
  kinds.value = i >= 0 ? kinds.value.filter((x) => x !== k) : [...kinds.value, k];
}
function kindHint(k: string) {
  const m = KIND_META[k];
  return lang.value === "de" ? m.hintDe : m.hintEn;
}
const filtersActive = computed(
  () => !!(kinds.value.length || search.value.trim() || addr.value.trim() || hidePolling.value || onlyExternal.value || lineFilter.value !== null),
);
function resetFilters() {
  kinds.value = [];
  search.value = "";
  addr.value = "";
  hidePolling.value = false;
  onlyExternal.value = false;
  lineFilter.value = null;
}

// ------------------------------------------------------------ live data
const paused = computed(() => monitorPaused.value);
const missed = ref(0);
const rate = useFrameRate(10);

function togglePause() {
  monitorPaused.value = !monitorPaused.value;
  if (!monitorPaused.value) missed.value = 0;
}

// throttled refresh: the store pushes into a plain reactive array; we read it raw at most 5×/s
const tick = ref(0);
let active = true;
let pending = 0;
function bump() {
  if (!active || pending) return;
  pending = window.setTimeout(() => {
    pending = 0;
    tick.value++;
  }, 200);
}
const offMonitor = onMonitor(() => {
  if (monitorPaused.value) missed.value++;
  else bump();
});
watch(() => state.monitor.length, bump);
onActivated(() => {
  active = true;
  tick.value++;
});
onDeactivated(() => {
  active = false;
});

const clearMark = ref<number | null>(null);
const older = shallowRef<Frame[]>([]);

const live = computed<Frame[]>(() => {
  void tick.value;
  const raw = toRaw(state.monitor) as Frame[];
  const mark = clearMark.value;
  if (mark == null) return raw.slice();
  let i = raw.length;
  while (i > 0 && (raw[i - 1].timestamp || 0) > mark) i--;
  return raw.slice(i);
});
const combined = computed<Frame[]>(() => (older.value.length ? older.value.concat(live.value) : live.value));

function clearView() {
  const raw = toRaw(state.monitor);
  clearMark.value = raw.length ? raw[raw.length - 1].timestamp || Date.now() / 1000 : Date.now() / 1000;
  older.value = [];
  noMoreOlder.value = false;
  selected.value = null;
  tick.value++;
}

// ------------------------------------------------------------ filtering
function parseAddrs(s: string): Set<string> | null {
  const parts = s
    .split(/[,;\s]+/)
    .map((x) => x.trim().toUpperCase())
    .filter(Boolean)
    .map((x) => (/^\d+$/.test(x) ? `A${x}` : x));
  return parts.length ? new Set(parts) : null;
}
function matchAddr(f: Frame, set: Set<string>) {
  const tg = (f.target || "").toUpperCase();
  if (tg && set.has(tg)) return true;
  if (f.kind === "backward") {
    const q = answerTo(f);
    if (q) return set.has(q.split(/[:\s]/)[0].trim().toUpperCase());
  }
  return false;
}
const isPoll = (f: Frame) => !f.external && (f.query || f.kind === "query");

const filterResult = computed(() => {
  const src = combined.value;
  const q = search.value.trim().toLowerCase();
  const addrs = parseAddrs(addr.value);
  const kindSet = kinds.value.length ? new Set(kinds.value) : null;
  const line = lineFilter.value;
  const pendingPoll = new Map<number, boolean>();
  const out: Frame[] = [];
  let pollHidden = 0;
  for (const f of src) {
    let poll = false;
    if (f.kind === "backward") {
      if (pendingPoll.get(f.line)) {
        poll = true;
        pendingPoll.set(f.line, false);
      }
    } else if (f.kind !== "event") {
      poll = isPoll(f);
      pendingPoll.set(f.line, poll);
    }
    if (hidePolling.value && poll) {
      pollHidden++;
      continue;
    }
    if (onlyExternal.value && !f.external) continue;
    if (line !== null && f.line !== line) continue;
    if (kindSet && !kindSet.has(kindKey(f.kind))) continue;
    if (addrs && !matchAddr(f, addrs)) continue;
    if (q && !`${f.text} ${f.hex} ${f.target}`.toLowerCase().includes(q)) continue;
    out.push(f);
  }
  if (newestFirst.value) out.reverse();
  return { rows: out, pollHidden };
});
const rows = computed(() => filterResult.value.rows);
const pollHidden = computed(() => filterResult.value.pollHidden);

const counts = computed(() => {
  const c: Record<string, number> = {};
  for (const f of combined.value) {
    const k = kindKey(f.kind);
    c[k] = (c[k] || 0) + 1;
  }
  return c;
});

const knownTargets = computed(() => {
  const set = new Set<string>();
  for (const d of Object.values(state.devices)) set.add(`A${d.address}`);
  for (let g = 0; g < 16; g++) set.add(`G${g}`);
  set.add("BC");
  const raw = combined.value;
  for (let i = Math.max(0, raw.length - 3000); i < raw.length; i++) if (raw[i].target) set.add(raw[i].target);
  return [...set].sort((a, b) => a.replace(/\d+/, "").localeCompare(b.replace(/\d+/, "")) || (parseInt(a.replace(/\D/g, "")) || 0) - (parseInt(b.replace(/\D/g, "")) || 0));
});

const emptyText = computed(() => (combined.value.length ? t("emptyFiltered") : paused.value ? t("emptyPaused") : t("emptyLive")));

const fmtInt = (n: number) => n.toLocaleString(lang.value === "de" ? "de-DE" : "en-GB");

// ------------------------------------------------------------ virtual list
function useMedia(query: string) {
  const mq = window.matchMedia(query);
  const r = ref(mq.matches);
  const handler = (e: MediaQueryListEvent) => (r.value = e.matches);
  mq.addEventListener("change", handler);
  onBeforeUnmount(() => mq.removeEventListener("change", handler));
  return r;
}
const narrow = useMedia("(max-width: 700px)");
const wide = useMedia("(min-width: 1180px)");
const rowH = computed(() => (narrow.value ? 50 : 30));
const OVERSCAN = 12;

const scroller = ref<HTMLElement>();
const scrollTop = ref(0);
const viewH = ref(500);
const start = computed(() => Math.max(0, Math.floor(scrollTop.value / rowH.value) - OVERSCAN));
const end = computed(() => Math.min(rows.value.length, Math.ceil((scrollTop.value + viewH.value) / rowH.value) + OVERSCAN));
const visible = computed(() => rows.value.slice(start.value, end.value));

const keys = new WeakMap<object, number>();
let keySeq = 0;
function keyOf(f: Frame) {
  let k = keys.get(f);
  if (k === undefined) {
    k = ++keySeq;
    keys.set(f, k);
  }
  return k;
}

let lastSetTop = -1;
function setTop(v: number) {
  const el = scroller.value;
  if (!el) return;
  el.scrollTop = v;
  lastSetTop = el.scrollTop;
  scrollTop.value = el.scrollTop;
}
function onScroll() {
  const el = scroller.value;
  if (!el) return;
  scrollTop.value = el.scrollTop;
  if (!newestFirst.value) {
    const atBottom = el.scrollTop + el.clientHeight >= el.scrollHeight - rowH.value * 1.5;
    if (atBottom) follow.value = true;
    else if (Math.abs(el.scrollTop - lastSetTop) > 2) follow.value = false;
  }
}

let ro: ResizeObserver | null = null;
onMounted(() => {
  if (scroller.value) {
    viewH.value = scroller.value.clientHeight;
    ro = new ResizeObserver(() => {
      if (scroller.value) viewH.value = scroller.value.clientHeight;
    });
    ro.observe(scroller.value);
    if (!newestFirst.value) nextTick(() => setTop(scroller.value?.scrollHeight ?? 0));
  }
});
onBeforeUnmount(() => {
  offMonitor();
  clearTimeout(pending);
  ro?.disconnect();
});

// jump to the "live" end when the order changes (registered before the rows watcher → runs first)
let skipAnchor = false;
watch(newestFirst, async (nf) => {
  skipAnchor = true;
  await nextTick();
  if (nf) setTop(0);
  else {
    follow.value = true;
    setTop(scroller.value?.scrollHeight ?? 0);
  }
});

// keep the visible frame in place while new frames arrive (unless pinned to the live end)
watch(rows, async (nv, ov) => {
  if (skipAnchor) {
    skipAnchor = false;
    return;
  }
  const el = scroller.value;
  if (!el) return;
  const h = rowH.value;
  if (!newestFirst.value && follow.value) {
    await nextTick();
    setTop(el.scrollHeight);
    return;
  }
  if (newestFirst.value && el.scrollTop < h) return;
  if (!ov?.length) return;
  const idx = Math.min(ov.length - 1, Math.floor(el.scrollTop / h));
  const anchor = ov[idx];
  const offset = el.scrollTop - idx * h;
  const ni = nv.indexOf(anchor);
  if (ni < 0 || ni === idx) return;
  await nextTick();
  setTop(ni * h + offset);
});

// ------------------------------------------------------------ selection
const selected = shallowRef<Frame | null>(null);
const showAside = computed(() => wide.value && !!selected.value);

function select(f: Frame) {
  selected.value = f;
}
function ensureVisible(i: number) {
  const el = scroller.value;
  if (!el) return;
  const h = rowH.value;
  if (i * h < el.scrollTop) setTop(i * h);
  else if ((i + 1) * h > el.scrollTop + el.clientHeight) setTop((i + 1) * h - el.clientHeight);
}
function onKey(e: KeyboardEvent) {
  const arr = rows.value;
  if (!arr.length) return;
  if (e.key === "ArrowDown" || e.key === "ArrowUp") {
    e.preventDefault();
    let i = selected.value ? arr.indexOf(selected.value) : -1;
    i = e.key === "ArrowDown" ? Math.min(arr.length - 1, i + 1) : Math.max(0, i - 1);
    selected.value = arr[i];
    ensureVisible(i);
  } else if (e.key === "Escape") {
    selected.value = null;
  }
}

/** The answer following a query on the same line (null = none, undefined = unknown/pending). */
const selectedReply = computed<Frame | null | undefined>(() => {
  const f = selected.value;
  if (!f || (f.kind !== "query" && f.kind !== "special")) return undefined;
  const arr = combined.value;
  const i = arr.indexOf(f);
  if (i < 0) return undefined;
  for (let j = i + 1; j < arr.length; j++) {
    const g = arr[j];
    if (g.line !== f.line) continue;
    return g.kind === "backward" ? g : null;
  }
  return undefined;
});

function applyAddr(target: string) {
  addr.value = target;
}
function applyAddrAndClose(target: string) {
  addr.value = target;
  selected.value = null;
}
function useFrame(f: Frame) {
  selected.value = null;
  emit("use-frame", f);
}

// ------------------------------------------------------------ older frames (DB)
const loadingOlder = ref(false);
const noMoreOlder = ref(false);

async function loadOlder() {
  loadingOlder.value = true;
  try {
    const first = combined.value[0];
    const cutoff = first?.timestamp ?? clearMark.value ?? Number.POSITIVE_INFINITY;
    let cursor = older.value.length && older.value[0].id ? older.value[0].id : Number.MAX_SAFE_INTEGER;
    let kept: Frame[] = [];
    // the newest DB rows overlap with the live buffer → page back until we reach older frames
    for (let iter = 0; iter < 20 && !kept.length; iter++) {
      const page = await api<any[]>("GET", `monitor?before=${cursor}&limit=500`);
      if (!page?.length) {
        noMoreOlder.value = true;
        break;
      }
      cursor = page[0].id;
      kept = page.filter((r) => (r.timestamp ?? 0) < cutoff).map(fromDbRow);
      if (page.length < 500 && !kept.length) {
        noMoreOlder.value = true;
        break;
      }
    }
    if (kept.length) {
      older.value = kept.concat(older.value);
      toast(t("olderLoaded", { n: kept.length }), "success", 2000);
    }
  } catch (e: any) {
    toast(e?.message || String(e), "error", 6000);
  } finally {
    loadingOlder.value = false;
  }
}
</script>

<style scoped>
.mon { display: flex; flex-direction: column; gap: 12px; }
.tb { padding: 12px 14px; display: flex; flex-direction: column; gap: 10px; overflow: visible; }
.tb-row { gap: 8px; }
.rate { gap: 6px; min-width: 112px; justify-content: center; }
.check { display: inline-flex; align-items: center; gap: 7px; font-size: 13px; color: var(--text2); cursor: pointer; white-space: nowrap; }
.filters { display: flex; flex-wrap: wrap; gap: 8px 14px; align-items: center; }
.search-wrap { position: relative; flex: 2 1 240px; min-width: 0; }
.search-wrap input { padding-left: 34px; }
.search-ico { position: absolute; left: 9px; top: 10px; color: var(--text3); pointer-events: none; }
.addr { flex: 1 1 150px; max-width: 240px; }
.line-sel { width: auto; min-width: 120px; flex: 0 0 auto; }
.kinds { gap: 6px; }
.kind-chip { border: 0; cursor: pointer; font-family: inherit; transition: opacity .15s, filter .15s; }
.kind-chip:hover { filter: brightness(0.95); }
.kind-chip.off { opacity: .35; filter: grayscale(.7); }
.kind-chip .cnt { font-weight: 400; opacity: .8; margin-left: 5px; font-family: var(--mono); font-size: 11px; }

.mon-main { display: grid; grid-template-columns: minmax(0, 1fr); gap: 12px; align-items: start; }
.mon-main.split { grid-template-columns: minmax(0, 1fr) 390px; }
.list-card { display: flex; flex-direction: column; }
.pause-banner { margin: 10px 12px 0; align-items: center; }

.mon-grid { display: grid; grid-template-columns: 96px 22px 40px 76px 70px 70px minmax(0, 1fr); gap: 0 10px; align-items: center; padding: 0 14px; }
.mon-head { height: 36px; font-size: 12px; color: var(--text2); font-weight: 500; border-bottom: 1px solid var(--divider); }
.mon-scroll { height: clamp(320px, calc(100vh - 400px), 1400px); overflow-y: auto; overflow-x: hidden; position: relative; outline: none; }
.mon-scroll:focus-visible { box-shadow: inset 0 0 0 2px var(--primary-soft); }
.mon-spacer { position: relative; }
.mon-win { position: absolute; left: 0; right: 0; top: 0; will-change: transform; }
.mon-row { border-bottom: 1px solid color-mix(in srgb, var(--divider) 55%, transparent); cursor: pointer; font-size: 13px; white-space: nowrap; overflow: hidden; }
.mon-row:hover { background: var(--hover); }
.mon-row.sel { background: var(--primary-soft); box-shadow: inset 3px 0 0 var(--primary); }
.mon-row.ext { box-shadow: inset 3px 0 0 color-mix(in srgb, #ef6c00 70%, transparent); }
.mon-row.sel.ext { box-shadow: inset 3px 0 0 var(--primary); }
.mon-row.ans .c-text { color: var(--text2); }
.mon-row.old { opacity: .82; }
.mon-row.warnrow { box-shadow: inset 3px 0 0 var(--error); }
.mon-row.warnrow .c-text, .mon-row.warnrow .mob-l2 { color: var(--error); }
.mon-row > span { overflow: hidden; text-overflow: ellipsis; min-width: 0; }
.c-time { font-size: 12px; color: var(--text2); }
.c-line { color: var(--text3); font-size: 12px; }
.c-target { font-weight: 600; }
.c-hex { color: var(--text2); }
.kbadge { display: inline-flex; align-items: center; height: 20px; padding: 0 8px; border-radius: 10px; font-size: 11.5px; font-weight: 600; }
.src { display: inline-block; font-family: var(--mono); font-size: 10.5px; font-weight: 600; padding: 1px 5px; border-radius: 5px; background: var(--bg2); color: var(--text2); }
.src.ext { background: color-mix(in srgb, #ef6c00 15%, transparent); color: color-mix(in srgb, #ef6c00 75%, var(--text)); }

.mob { display: flex; flex-direction: column; justify-content: center; gap: 3px; padding: 0 12px; }
.mob-l1 { display: flex; align-items: center; gap: 8px; min-width: 0; }
.mob-l1 .b { font-weight: 600; }
.mob-l2 { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--text2); }

.mon-foot { display: flex; flex-wrap: wrap; align-items: center; gap: 6px 10px; padding: 8px 14px; border-top: 1px solid var(--divider); }
.csv { gap: 6px; }
.csv-sel { width: auto; height: 30px; padding: 4px 8px; font-size: 13px; }
.spinner.mini { width: 14px; height: 14px; }

.aside { position: sticky; top: 12px; max-height: calc(100vh - 24px); display: flex; flex-direction: column; }
.aside-head { display: flex; align-items: center; gap: 10px; padding: 14px 12px 8px 16px; border-bottom: 1px solid var(--divider); }
.aside-body { overflow: auto; padding: 12px 16px 16px; }

@media (max-width: 700px) {
  .tb { padding: 10px; }
  .addr { max-width: none; }
  .mon-scroll { height: clamp(300px, calc(100vh - 470px), 900px); }
  .rate { min-width: 0; }
}
</style>
