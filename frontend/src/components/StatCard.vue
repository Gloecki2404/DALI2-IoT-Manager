<template>
  <div class="card stat" :class="{ clickable: !!to }" @click="to && $router.push(to)">
    <span class="icon-bubble" :class="kind"><Icon :path="icon" :size="22" /></span>
    <div>
      <div class="value">{{ value }}</div>
      <div class="label">{{ label }}</div>
      <div v-if="sub" class="faint small">{{ sub }}</div>
    </div>
  </div>
</template>
<script setup lang="ts">
import Icon from "./Icon.vue";
defineProps<{ icon: string; label: string; value: string | number; sub?: string; kind?: string; to?: string }>();
</script>
<style scoped>
.clickable { cursor: pointer; transition: transform .12s; }
.clickable:hover { transform: translateY(-1px); }
</style>
