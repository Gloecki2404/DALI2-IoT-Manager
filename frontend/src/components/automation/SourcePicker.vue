<template>
  <div class="sp">
    <div class="row wrap">
      <span v-for="(s, i) in modelValue" :key="i" class="chip src-chip">
        <Icon :path="iconFor(s.type)" :size="14" />{{ sourceLabel(s, t) }}
        <button type="button" class="x" :title="t('remove')" @click="remove(i)"><Icon :path="mdiClose" :size="14" /></button>
      </span>
      <span v-if="!modelValue.length" class="faint small">{{ t("noSources") }}</span>
    </div>
    <div class="row wrap mt add">
      <select v-model="kind" class="k-sel">
        <option value="device">{{ t("device") }}</option>
        <option value="group">{{ t("group") }}</option>
        <option value="broadcast">{{ t("broadcast") }}</option>
        <option value="d16gear">{{ t("srcRawGear") }}</option>
        <option value="d16group">{{ t("srcRawGroup") }}</option>
      </select>
      <select v-if="kind !== 'device' && lines > 1" v-model.number="line" class="l-sel">
        <option v-for="l in lines" :key="l" :value="l - 1">{{ t("line") }} {{ l - 1 }}</option>
      </select>
      <select v-if="kind === 'device'" v-model.number="sel" class="d-sel">
        <option :value="null" disabled>{{ t("choose") }}</option>
        <option v-for="d in devices" :key="d.id" :value="d.id">{{ d.name }} (L{{ d.line }} A{{ d.address }})</option>
      </select>
      <select v-else-if="kind === 'group' || kind === 'd16group'" v-model.number="sel" class="g-sel">
        <option :value="null" disabled>{{ t("choose") }}</option>
        <option v-for="g in 16" :key="g" :value="g - 1">{{ t("group") }} {{ g - 1 }}</option>
      </select>
      <input v-else-if="kind === 'd16gear'" v-model.number="sel" type="number" min="0" max="63" step="1" class="a-in" :placeholder="t('addressPh')" />
      <button type="button" class="btn outline sm" :disabled="!canAdd" @click="add">
        <Icon :path="mdiPlus" :size="16" />{{ t("add") }}
      </button>
    </div>
    <div v-if="kind === 'd16gear' || kind === 'd16group'" class="hint small faint mt-s">{{ t("srcRawHint") }}</div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { mdiClose, mdiLightbulb, mdiLightbulbGroup, mdiLightbulbMultiple, mdiPlus, mdiTransitConnectionVariant } from "@mdi/js";
import Icon from "../Icon.vue";
import { state } from "../../lib/store";
import { useAT } from "./i18n";
import { lineCount, sourceLabel, type SourceType, type TriggerSource } from "./util";

const props = defineProps<{ modelValue: TriggerSource[] }>();
const emit = defineEmits<{ (e: "update:modelValue", v: TriggerSource[]): void }>();
const t = useAT();

const kind = ref<SourceType>("device");
const sel = ref<number | null>(null);
const line = ref(0);
watch(kind, () => (sel.value = null));

const lines = computed(() => lineCount());
const devices = computed(() => Object.values(state.devices).sort((a, b) => a.line - b.line || a.address - b.address));

const canAdd = computed(() => {
  if (kind.value === "broadcast") return true;
  if (sel.value === null || (sel.value as any) === "") return false;
  const n = Number(sel.value);
  if (!Number.isInteger(n) || n < 0) return false;
  if (kind.value === "d16gear") return n <= 63;
  return true;
});

function build(): TriggerSource {
  const n = Number(sel.value);
  const l = lines.value > 1 ? line.value : 0;
  switch (kind.value) {
    case "device":
      return { type: "device", id: n };
    case "group":
      // Same encoding as TargetPicker: group + 16 · line.
      return { type: "group", id: l * 16 + n };
    case "broadcast":
      return { type: "broadcast", id: l };
    case "d16gear":
      return { type: "d16gear", address: n, line: l };
    case "d16group":
      return { type: "d16group", address: n, line: l };
  }
  return { type: "device", id: n };
}

const key = (s: TriggerSource) => `${s.type}:${s.id ?? ""}:${s.address ?? ""}:${s.line ?? ""}`;

function add() {
  if (!canAdd.value) return;
  const s = build();
  if (props.modelValue.some((x) => key(x) === key(s))) return;
  emit("update:modelValue", [...props.modelValue, s]);
  if (kind.value !== "broadcast") sel.value = null;
}
function remove(i: number) {
  const next = [...props.modelValue];
  next.splice(i, 1);
  emit("update:modelValue", next);
}

function iconFor(type: string) {
  if (type === "device") return mdiLightbulb;
  if (type === "group") return mdiLightbulbMultiple;
  if (type === "broadcast") return mdiLightbulbGroup;
  return mdiTransitConnectionVariant;
}
</script>

<style scoped>
.src-chip { background: color-mix(in srgb, var(--accent) 16%, transparent); color: color-mix(in srgb, var(--accent) 80%, var(--text)); }
.x { background: none; border: 0; padding: 0; margin-left: 2px; cursor: pointer; color: inherit; display: inline-flex; }
.k-sel { max-width: 190px; }
.l-sel { max-width: 110px; }
.d-sel { max-width: 280px; }
.g-sel { max-width: 140px; }
.a-in { max-width: 150px; }
.mt-s { margin-top: 6px; }
</style>
