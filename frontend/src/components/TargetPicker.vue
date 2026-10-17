<template>
  <div class="tp">
    <div class="row wrap">
      <span v-for="(tg, i) in modelValue" :key="i" class="chip primary">
        <Icon :path="iconFor(tg.type)" :size="14" />{{ targetLabel(tg, state.devices, state.zones, t) }}
        <button class="x" @click="remove(i)"><Icon :path="mdiClose" :size="14" /></button>
      </span>
      <span v-if="!modelValue.length" class="faint small">{{ t("noTargets") }}</span>
    </div>
    <div class="row wrap mt">
      <select v-model="kind" style="max-width: 150px">
        <option v-for="k in types" :key="k" :value="k">{{ t(k) }}</option>
      </select>
      <select v-if="kind === 'device'" v-model.number="sel" style="max-width: 260px">
        <option v-for="d in devices" :key="d.id" :value="d.id">{{ d.name }} (A{{ d.address }})</option>
      </select>
      <select v-else-if="kind === 'group'" v-model.number="sel" style="max-width: 160px">
        <option v-for="g in 16" :key="g" :value="g - 1">{{ t("group") }} {{ g - 1 }}</option>
      </select>
      <select v-if="lineCount > 1 && (kind === 'group' || kind === 'broadcast')" v-model="line" style="max-width: 150px">
        <option v-if="kind === 'broadcast'" :value="null">{{ t("allLines") }}</option>
        <option v-for="l in lineCount" :key="l" :value="l - 1">{{ t("line") }} {{ l - 1 }}</option>
      </select>
      <select v-if="kind === 'zone'" v-model.number="sel" style="max-width: 260px">
        <option v-for="z in zones" :key="z.id" :value="z.id">{{ z.name }}</option>
      </select>
      <button class="btn outline sm" :disabled="kind !== 'broadcast' && sel === null" @click="add">
        <Icon :path="mdiPlus" :size="16" />{{ t("add") }}
      </button>
    </div>
  </div>
</template>
<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { mdiClose, mdiLightbulb, mdiLightbulbGroup, mdiLightbulbMultiple, mdiPlus, mdiVectorSquare } from "@mdi/js";
import Icon from "./Icon.vue";
import { state, type Target } from "../lib/store";
import { targetLabel } from "../lib/dali";
import { useT } from "../lib/i18n";

const props = withDefaults(defineProps<{ modelValue: Target[]; types?: string[] }>(), {
  types: () => ["device", "group", "zone", "broadcast"],
});
const emit = defineEmits<{ (e: "update:modelValue", v: Target[]): void }>();
const t = useT({
  de: { noTargets: "Noch keine Ziele gewählt", allLines: "Alle Linien" },
  en: { noTargets: "No targets selected yet", allLines: "All lines" },
});
const lineCount = computed(() => Number(state.info?.descriptor?.lines ?? 1));
const line = ref<number | null>(0);
const kind = ref(props.types[0]);
const sel = ref<number | null>(null);
watch(kind, () => (sel.value = null));
const devices = computed(() => Object.values(state.devices).sort((a, b) => a.line - b.line || a.address - b.address));
const zones = computed(() => Object.values(state.zones));

function iconFor(type: string) {
  return type === "device" ? mdiLightbulb : type === "group" ? mdiLightbulbMultiple : type === "broadcast" ? mdiLightbulbGroup : mdiVectorSquare;
}
function add() {
  let id: number | null = sel.value;
  if (kind.value === "broadcast") id = lineCount.value > 1 ? line.value : null;
  else if (kind.value === "group" && lineCount.value > 1) id = (sel.value ?? 0) + 16 * (line.value ?? 0);
  const tg = { type: kind.value, id } as Target;
  if (props.modelValue.some((x) => x.type === tg.type && x.id === tg.id)) return;
  emit("update:modelValue", [...props.modelValue, tg]);
}
function remove(i: number) {
  const next = [...props.modelValue];
  next.splice(i, 1);
  emit("update:modelValue", next);
}
</script>
<style scoped>
.x { background: none; border: 0; padding: 0; margin-left: 2px; cursor: pointer; color: inherit; display: inline-flex; }
</style>
