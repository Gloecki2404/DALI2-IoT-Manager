<template>
  <svg :width="size" :height="size" viewBox="0 0 24 24" aria-hidden="true" class="mdi">
    <path :d="path" fill="currentColor" />
  </svg>
</template>
<script setup lang="ts">
withDefaults(defineProps<{ path: string; size?: number | string }>(), { size: 20 });
</script>
<style scoped>
.mdi { flex-shrink: 0; display: inline-block; vertical-align: middle; }
</style>
