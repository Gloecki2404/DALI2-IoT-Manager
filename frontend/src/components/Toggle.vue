<template>
  <label class="toggle" @click.stop>
    <input type="checkbox" :checked="modelValue" :disabled="disabled" @change="onChange" />
    <span class="track"></span><span class="thumb"></span>
  </label>
</template>
<script setup lang="ts">
defineProps<{ modelValue: boolean; disabled?: boolean }>();
const emit = defineEmits<{ (e: "update:modelValue", v: boolean): void; (e: "change", v: boolean): void }>();
function onChange(e: Event) {
  const v = (e.target as HTMLInputElement).checked;
  emit("update:modelValue", v);
  emit("change", v);
}
</script>
