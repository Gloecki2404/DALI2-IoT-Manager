<template>
  <div class="empty">
    <Icon :path="icon || mdiInformationOutline" :size="44" />
    <div>{{ text }}</div>
    <slot />
  </div>
</template>
<script setup lang="ts">
import { mdiInformationOutline } from "@mdi/js";
import Icon from "./Icon.vue";
defineProps<{ text: string; icon?: string }>();
</script>
