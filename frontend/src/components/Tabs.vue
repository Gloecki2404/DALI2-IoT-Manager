<template>
  <nav class="tabs">
    <button v-for="t in tabs" :key="t.id" :class="{ active: modelValue === t.id }" @click="$emit('update:modelValue', t.id)">
      <Icon v-if="t.icon" :path="t.icon" :size="17" />{{ t.label }}
      <span v-if="t.badge" class="chip primary">{{ t.badge }}</span>
    </button>
  </nav>
</template>
<script setup lang="ts">
import Icon from "./Icon.vue";
defineProps<{ tabs: { id: string; label: string; icon?: string; badge?: string | number }[]; modelValue: string }>();
defineEmits<{ (e: "update:modelValue", v: string): void }>();
</script>
