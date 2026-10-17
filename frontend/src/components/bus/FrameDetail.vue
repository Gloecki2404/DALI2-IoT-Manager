<template>
  <div class="fd">
    <div class="row wrap fd-chips">
      <span class="kbadge" :style="kindStyle(frame.kind)" :title="kindHint">{{ kindLabel(frame.kind, lang) }}</span>
      <span class="chip" :class="frame.external ? 'primary' : ''">
        <Icon :path="frame.external ? mdiAccessPoint : mdiRouterNetwork" :size="14" />
        {{ frame.external ? t("external") : t("gateway") }}
      </span>
      <span class="chip">{{ t("line") }} {{ frame.line }}</span>
      <span class="chip">{{ frame.bits }} Bit</span>
      <span v-if="frame.db" class="chip" :title="t('fromDb')">DB #{{ frame.id }}</span>
    </div>

    <div class="fd-text mono">{{ frame.text || "–" }}</div>

    <div class="kv">
      <span>{{ t("time") }}</span><span class="mono">{{ fmtMs(frame.timestamp, true, lang) }}</span>
      <span>{{ t("target") }}</span><span class="mono">{{ frame.target || "–" }}</span>
      <span>Hex</span><span class="mono">{{ frame.hex || bytesHex(frame.data || []) }}</span>
      <span>{{ t("decimal") }}</span><span class="mono">{{ (frame.data || []).join(" · ") }}</span>
      <template v-if="answerQuery">
        <span>{{ t("answerTo") }}</span><span class="mono">{{ answerQuery }}</span>
      </template>
      <template v-if="frame.query">
        <span>{{ t("pollFlag") }}</span><span>{{ t("pollHint") }}</span>
      </template>
    </div>

    <div class="section-title">{{ t("bits") }}</div>
    <div class="bytes">
      <div v-for="(b, bi) in frame.data" :key="bi" class="byte">
        <div class="byte-head small muted">
          Byte {{ bi + 1 }} · <span class="mono">0x{{ hex2(b) }}</span> · <span class="mono">{{ b }}</span>
        </div>
        <div class="bit-row">
          <span
            v-for="k in 8"
            :key="k"
            class="bit mono"
            :style="bitStyle(bitIndex(bi, k))"
            :title="fieldOf(bitIndex(bi, k))?.label"
          >
            {{ (b >> (8 - k)) & 1 }}
            <small>{{ bitIndex(bi, k) }}</small>
          </span>
        </div>
      </div>
    </div>
    <div class="legend">
      <div v-for="(fl, i) in fields" :key="i" class="legend-item">
        <span class="sw" :style="{ background: fl.color }"></span>
        <span class="mono faint small range">{{ fl.hi === fl.lo ? fl.hi : `${fl.hi}–${fl.lo}` }}</span>
        <span class="small lab">{{ fl.label }}</span>
        <span class="small mono val">{{ fl.value }}</span>
      </div>
    </div>

    <template v-if="isQuery && reply !== undefined">
      <div class="section-title">{{ t("reply") }}</div>
      <div v-if="reply" class="banner info small clickable-banner" @click="$emit('select', reply)">
        <Icon :path="mdiReply" :size="18" />
        <div>
          <b class="mono">{{ reply.data?.[0] }} · 0x{{ hex2(reply.data?.[0] ?? 0) }} · 0b{{ bin8(reply.data?.[0] ?? 0) }}</b>
          <span class="faint"> ({{ Math.round(((reply.timestamp || 0) - (frame.timestamp || 0)) * 1000) }} ms)</span>
        </div>
      </div>
      <div v-else class="banner warn small">
        <Icon :path="mdiAlertOutline" :size="18" />
        <div>{{ t("noAnswer") }}</div>
      </div>
    </template>

    <template v-if="explain">
      <div class="section-title">{{ t("interpretation") }}</div>
      <div class="banner info small">
        <Icon :path="mdiLightbulbOnOutline" :size="18" />
        <div>{{ explain.summary }}</div>
      </div>
      <div v-if="explain.bits" class="status-bits">
        <div v-for="b in explain.bits" :key="b.bit" class="sbit" :class="{ on: b.set, [b.severity]: b.set && b.severity }">
          <span class="mono small">{{ b.bit }}</span>
          <span class="dot" :class="b.set ? (b.severity === 'err' ? 'err' : b.severity === 'warn' ? 'warn' : 'ok') : ''"></span>
          <span class="small">{{ b.label }}</span>
        </div>
      </div>
    </template>

    <template v-if="eventInfo">
      <div class="section-title">{{ t("event") }}</div>
      <div class="kv">
        <span>{{ t("scheme") }}</span><span>{{ eventInfo.scheme }}</span>
        <template v-if="eventInfo.short_address != null">
          <span>{{ t("shortAddress") }}</span><span class="mono">D{{ eventInfo.short_address }}</span>
        </template>
        <template v-if="eventInfo.device_group != null">
          <span>{{ t("deviceGroup") }}</span><span class="mono">DG{{ eventInfo.device_group }}</span>
        </template>
        <template v-if="eventInfo.instance_group != null">
          <span>{{ t("instanceGroup") }}</span><span class="mono">IG{{ eventInfo.instance_group }}</span>
        </template>
        <template v-if="eventInfo.instance_type != null">
          <span>{{ t("instanceType") }}</span><span>{{ eventInfo.instance_type }} – {{ INSTANCE_TYPES[eventInfo.instance_type]?.[lang] ?? "?" }}</span>
        </template>
        <template v-if="eventInfo.instance_number != null">
          <span>{{ t("instanceNumber") }}</span><span>{{ eventInfo.instance_number }}</span>
        </template>
        <template v-if="eventInfo.event_type">
          <span>{{ t("eventType") }}</span><span><b>{{ EVENT_TYPES[eventInfo.event_type]?.[lang] ?? eventInfo.event_type }}</b></span>
        </template>
        <span>{{ t("eventInfo") }}</span><span class="mono">{{ eventInfo.info }} (0b{{ eventInfo.info.toString(2).padStart(10, "0") }})</span>
        <template v-if="eventInfo.source_key">
          <span>{{ t("sourceKey") }}</span><span class="mono">{{ eventInfo.source_key }}</span>
        </template>
        <template v-if="eventInfo.attributes && Object.keys(eventInfo.attributes).length">
          <span>{{ t("attributes") }}</span><span class="mono small">{{ JSON.stringify(eventInfo.attributes) }}</span>
        </template>
      </div>
    </template>

    <div v-if="note" class="banner warn small mt">
      <Icon :path="mdiAlertOutline" :size="18" />
      <div>{{ note }}</div>
    </div>

    <div class="row wrap mt fd-actions">
      <button v-if="filterTarget" class="btn outline sm" @click="$emit('filter', filterTarget)">
        <Icon :path="mdiFilterVariant" :size="16" />{{ t("filterAddr", { a: filterTarget }) }}
      </button>
      <button class="btn flat sm" @click="copy"><Icon :path="mdiContentCopy" :size="16" />{{ t("copyHex") }}</button>
      <button v-if="canUse" class="btn flat sm" @click="$emit('use', frame)">
        <Icon :path="mdiConsoleLine" :size="16" />{{ t("useInCommands") }}
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import {
  mdiAccessPoint,
  mdiAlertOutline,
  mdiConsoleLine,
  mdiContentCopy,
  mdiFilterVariant,
  mdiLightbulbOnOutline,
  mdiReply,
  mdiRouterNetwork,
} from "@mdi/js";
import Icon from "../Icon.vue";
import { lang, useT } from "../../lib/i18n";
import { state, toast } from "../../lib/store";
import {
  EVENT_TYPES,
  INSTANCE_TYPES,
  KIND_META,
  answerTo,
  bin8,
  bytesHex,
  decodeEvent,
  explainAnswer,
  fmtMs,
  frameFields,
  hex2,
  kindKey,
  kindLabel,
  kindStyle,
  type Frame,
} from "./frames";

const props = defineProps<{
  frame: Frame;
  /** answer to a query frame: Frame, null = no answer, undefined = unknown */
  reply?: Frame | null;
}>();
defineEmits<{ (e: "filter", target: string): void; (e: "use", f: Frame): void; (e: "select", f: Frame): void }>();

const t = useT({
  de: {
    external: "Extern",
    gateway: "Gateway",
    fromDb: "Aus der Verlaufsdatenbank geladen",
    target: "Ziel",
    decimal: "Dezimal",
    answerTo: "Antwort auf",
    pollFlag: "Abfrage-Flag",
    pollHint: "Vom Gateway gesendete Abfrage – eine Antwort wird erwartet",
    bits: "Bit-Aufschlüsselung",
    interpretation: "Interpretation",
    event: "Ereignis",
    scheme: "Adress-Schema",
    shortAddress: "Kurzadresse",
    deviceGroup: "Gerätegruppe",
    instanceGroup: "Instanzgruppe",
    instanceType: "Instanztyp",
    instanceNumber: "Instanznummer",
    eventType: "Ereignistyp",
    eventInfo: "Ereignisinfo",
    sourceKey: "Quellschlüssel",
    attributes: "Attribute",
    filterAddr: "Nur {a} anzeigen",
    copyHex: "Hex kopieren",
    copied: "In die Zwischenablage kopiert",
    useInCommands: "Im Befehls-Tab öffnen",
    configNote: "Konfigurationsbefehl: Wird nur ausgeführt, wenn er innerhalb von 100 ms zweimal gesendet wird (IEC 62386-102).",
    reply: "Antwort",
    noAnswer: "Keine Antwort erhalten – bei JA/NEIN-Abfragen bedeutet das „NEIN“, sonst ist das Gerät nicht erreichbar.",
  },
  en: {
    external: "External",
    gateway: "Gateway",
    fromDb: "Loaded from the history database",
    target: "Target",
    decimal: "Decimal",
    answerTo: "Answer to",
    pollFlag: "Query flag",
    pollHint: "Query sent by the gateway – an answer is expected",
    bits: "Bit breakdown",
    interpretation: "Interpretation",
    event: "Event",
    scheme: "Address scheme",
    shortAddress: "Short address",
    deviceGroup: "Device group",
    instanceGroup: "Instance group",
    instanceType: "Instance type",
    instanceNumber: "Instance number",
    eventType: "Event type",
    eventInfo: "Event info",
    sourceKey: "Source key",
    attributes: "Attributes",
    filterAddr: "Show only {a}",
    copyHex: "Copy hex",
    copied: "Copied to clipboard",
    useInCommands: "Open in commands tab",
    configNote: "Configuration command: only executed when sent twice within 100 ms (IEC 62386-102).",
    reply: "Answer",
    noAnswer: "No answer received – for yes/no queries this means “NO”, otherwise the device is not reachable.",
  },
});

const fields = computed(() => frameFields(props.frame, lang.value));
const totalBits = computed(() => (props.frame.data?.length || 0) * 8);
const kindHint = computed(() => {
  const m = KIND_META[kindKey(props.frame.kind)];
  return lang.value === "de" ? m.hintDe : m.hintEn;
});

function bitIndex(byteIdx: number, k: number) {
  return totalBits.value - 1 - (byteIdx * 8 + (k - 1));
}
function fieldOf(bit: number) {
  return fields.value.find((f) => bit <= f.hi && bit >= f.lo);
}
function bitStyle(bit: number) {
  const f = fieldOf(bit);
  if (!f) return {};
  return { background: `color-mix(in srgb, ${f.color} 20%, transparent)`, borderColor: `color-mix(in srgb, ${f.color} 55%, transparent)` };
}

const answerQuery = computed(() => (props.frame.kind === "backward" ? answerTo(props.frame) : undefined));
const isQuery = computed(() => props.frame.kind === "query" || (props.frame.kind === "special" && /COMPARE|VERIFY|QUERY/.test(props.frame.text || "")));
const explain = computed(() => {
  if (props.frame.kind === "backward" && props.frame.data?.length) return explainAnswer(answerQuery.value, props.frame.data[0], lang.value);
  if (isQuery.value && props.reply?.data?.length) return explainAnswer(props.frame.text, props.reply.data[0], lang.value);
  return null;
});

const eventInfo = computed(() => {
  if (props.frame.kind !== "event") return null;
  if (props.frame.event) return props.frame.event;
  const ev = decodeEvent(props.frame.data || []);
  return ev;
});

const note = computed(() => {
  const d = props.frame.data || [];
  if (d.length === 2 && d[0] & 1 && props.frame.kind === "command" && d[1] >= 32 && d[1] <= 129) return t("configNote");
  return "";
});

const filterTarget = computed(() => {
  if (props.frame.target) return props.frame.target;
  const q = answerQuery.value;
  if (q && q.includes(":")) return q.split(":")[0].trim();
  return "";
});

const canUse = computed(() => state.expert && props.frame.kind !== "backward" && props.frame.kind !== "event" && [2, 3].includes(props.frame.data?.length || 0));

async function copy() {
  try {
    await navigator.clipboard.writeText(props.frame.hex || bytesHex(props.frame.data || []));
    toast(t("copied"), "success", 1800);
  } catch {
    /* clipboard not available (e.g. insecure context) */
  }
}
</script>

<style scoped>
.fd { display: flex; flex-direction: column; gap: 12px; }
.fd-chips { gap: 6px; }
.kbadge { display: inline-flex; align-items: center; height: 24px; padding: 0 9px; border-radius: 12px; font-size: 12px; font-weight: 600; }
.fd-text { font-size: 14px; padding: 10px 12px; background: var(--bg2); border-radius: 10px; word-break: break-word; }
.kv { font-size: 13px; }
.kv > span { min-width: 0; word-break: break-word; }
.section-title { margin: 6px 0 -2px; }
.bytes { display: flex; flex-wrap: wrap; gap: 10px; }
.byte { display: flex; flex-direction: column; gap: 4px; }
.bit-row { display: flex; gap: 3px; }
.bit {
  width: 26px; height: 34px; border-radius: 6px; border: 1px solid var(--divider);
  display: flex; flex-direction: column; align-items: center; justify-content: center; font-size: 14px; font-weight: 600; line-height: 1;
}
.bit small { font-size: 9px; font-weight: 400; color: var(--text3); margin-top: 3px; }
.legend { display: flex; flex-direction: column; gap: 4px; }
.legend-item { display: grid; grid-template-columns: 12px 42px minmax(90px, max-content) 1fr; gap: 8px; align-items: center; }
.legend-item .sw { width: 12px; height: 12px; border-radius: 3px; }
.legend-item .lab { color: var(--text2); }
.legend-item .val { word-break: break-word; }
.status-bits { display: grid; grid-template-columns: repeat(auto-fill, minmax(190px, 1fr)); gap: 4px 12px; }
.sbit { display: flex; align-items: center; gap: 8px; color: var(--text3); }
.sbit.on { color: var(--text); font-weight: 500; }
.sbit.err { color: var(--error); }
.fd-actions { gap: 6px; }
.clickable-banner { cursor: pointer; }
.clickable-banner:hover { filter: brightness(0.97); }
@media (max-width: 700px) {
  .bit { width: 22px; height: 30px; font-size: 13px; }
  .legend-item { grid-template-columns: 12px 36px 1fr; }
  .legend-item .val { grid-column: 2 / -1; }
}
</style>
