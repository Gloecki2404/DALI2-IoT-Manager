<template>
  <div class="toasts">
    <TransitionGroup name="toast">
      <div v-for="t in toasts" :key="t.id" class="toast" :class="t.kind">
        <Icon :path="t.kind === 'error' ? mdiAlertCircle : t.kind === 'success' ? mdiCheckCircle : mdiInformation" :size="18" />
        <span>{{ t.text }}</span>
      </div>
    </TransitionGroup>
  </div>
</template>
<script setup lang="ts">
import { mdiAlertCircle, mdiCheckCircle, mdiInformation } from "@mdi/js";
import Icon from "./Icon.vue";
import { toasts } from "../lib/store";
</script>
<style scoped>
.toasts { position: fixed; bottom: 20px; left: 50%; transform: translateX(-50%); z-index: 200; display: flex; flex-direction: column; gap: 8px; align-items: center; pointer-events: none; width: min(560px, calc(100vw - 24px)); }
.toast { display: flex; gap: 10px; align-items: center; background: #323232; color: #fff; padding: 11px 16px; border-radius: 10px; box-shadow: 0 4px 16px rgba(0,0,0,.3); font-size: 13.5px; pointer-events: auto; max-width: 100%; }
.toast.error { background: #b3261e; }
.toast.success { background: #1e7a44; }
.toast-enter-active, .toast-leave-active { transition: all .2s; }
.toast-enter-from, .toast-leave-to { opacity: 0; transform: translateY(10px); }
@media (max-width: 700px) { .toasts { bottom: 80px; } }
</style>
