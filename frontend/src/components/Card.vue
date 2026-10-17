<template>
  <section class="card">
    <header v-if="title || $slots.actions || icon" class="card-head">
      <span v-if="icon" class="icon-bubble" :class="iconClass"><Icon :path="icon" :size="18" /></span>
      <div class="grow">
        <h3>{{ title }}</h3>
        <div v-if="subtitle" class="muted small">{{ subtitle }}</div>
      </div>
      <slot name="actions" />
    </header>
    <div class="card-body" :class="{ flush }"><slot /></div>
    <footer v-if="$slots.footer" class="card-foot"><slot name="footer" /></footer>
  </section>
</template>
<script setup lang="ts">
import Icon from "./Icon.vue";
defineProps<{ title?: string; subtitle?: string; icon?: string; iconClass?: string; flush?: boolean }>();
</script>
