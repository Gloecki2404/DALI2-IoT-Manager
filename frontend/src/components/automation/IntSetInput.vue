<template>
  <div class="isi" :class="{ disabled }">
    <div v-if="presets?.length" class="row wrap isi-presets">
      <button
        v-for="p in presets"
        :key="p.value"
        type="button"
        class="chip clickable"
        :class="{ primary: modelValue.includes(p.value) }"
        :disabled="disabled"
        @click="toggle(p.value)"
      >
        <span class="mono">{{ p.value }}</span> {{ p.label }}
      </button>
    </div>
    <div v-if="ranges.length" class="row wrap isi-chips">
      <span v-for="r in ranges" :key="r.from" class="chip primary">
        {{ r.from === r.to ? r.from : `${r.from}–${r.to}` }}
        <button type="button" class="x" :disabled="disabled" :title="t('remove')" @click="removeRange(r.from, r.to)"><Icon :path="mdiClose" :size="13" /></button>
      </span>
      <button v-if="modelValue.length > 1" type="button" class="btn flat sm" :disabled="disabled" @click="emit('update:modelValue', [])">{{ t("clear") }}</button>
    </div>
    <div class="row isi-add">
      <input
        v-model="text"
        type="text"
        inputmode="numeric"
        :placeholder="placeholder || t('intSetPh', { min, max })"
        :disabled="disabled"
        @keydown.enter.prevent="commit"
        @blur="commit"
      />
      <button type="button" class="btn outline sm" :disabled="disabled || !text.trim()" @click="commit">
        <Icon :path="mdiPlus" :size="16" />{{ t("add") }}
      </button>
    </div>
    <span v-if="error" class="isi-err small">{{ error }}</span>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import { mdiClose, mdiPlus } from "@mdi/js";
import Icon from "../Icon.vue";
import { useAT } from "./i18n";

const props = withDefaults(
  defineProps<{ modelValue: number[]; min?: number; max?: number; disabled?: boolean; placeholder?: string; presets?: { value: number; label: string }[] }>(),
  { min: 0, max: 63 },
);
const emit = defineEmits<{ (e: "update:modelValue", v: number[]): void }>();
const t = useAT();

const text = ref("");
const error = ref("");

const sorted = computed(() => [...new Set(props.modelValue)].sort((a, b) => a - b));
const ranges = computed(() => {
  const out: { from: number; to: number }[] = [];
  for (const v of sorted.value) {
    const last = out[out.length - 1];
    if (last && v === last.to + 1) last.to = v;
    else out.push({ from: v, to: v });
  }
  return out;
});

function toggle(v: number) {
  const set = new Set(props.modelValue);
  if (set.has(v)) set.delete(v);
  else set.add(v);
  emit("update:modelValue", [...set].sort((a, b) => a - b));
}

function removeRange(from: number, to: number) {
  emit(
    "update:modelValue",
    props.modelValue.filter((v) => v < from || v > to),
  );
}

function commit() {
  const s = text.value.trim();
  error.value = "";
  if (!s) return;
  const set = new Set(props.modelValue);
  for (const tok of s.split(/[,;\s]+/).filter(Boolean)) {
    const m = /^(\d+)(?:\s*[-–]\s*(\d+))?$/.exec(tok);
    if (!m) {
      error.value = t("intSetInvalid", { v: tok, min: props.min, max: props.max });
      return;
    }
    const a = +m[1];
    const b = m[2] !== undefined ? +m[2] : a;
    const lo = Math.min(a, b);
    const hi = Math.max(a, b);
    if (lo < props.min || hi > props.max) {
      error.value = t("intSetInvalid", { v: tok, min: props.min, max: props.max });
      return;
    }
    for (let v = lo; v <= hi; v++) set.add(v);
  }
  emit("update:modelValue", [...set].sort((x, y) => x - y));
  text.value = "";
}
</script>

<style scoped>
.isi { display: flex; flex-direction: column; gap: 8px; }
.isi.disabled { opacity: .5; }
.isi-presets { gap: 6px; }
.isi-presets .chip { border: 0; cursor: pointer; }
.isi-presets .chip:disabled { cursor: not-allowed; }
.isi-chips { gap: 4px; }
.isi-add input { max-width: 260px; }
.x { background: none; border: 0; padding: 0; margin-left: 2px; cursor: pointer; color: inherit; display: inline-flex; }
.isi-err { color: var(--error); }
</style>
