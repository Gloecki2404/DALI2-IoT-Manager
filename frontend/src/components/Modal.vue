<template>
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="open" class="backdrop" :class="{ top }" @mousedown.self="!persistent && $emit('close')">
        <div class="dialog" :class="{ wide, full }" role="dialog">
          <header>
            <span v-if="icon" class="icon-bubble" :class="iconClass"><Icon :path="icon" :size="20" /></span>
            <div class="grow">
              <h2>{{ title }}</h2>
              <div v-if="subtitle" class="muted small">{{ subtitle }}</div>
            </div>
            <slot name="head" />
            <button class="btn icon" @click="$emit('close')"><Icon :path="mdiClose" /></button>
          </header>
          <div class="content"><slot /></div>
          <footer v-if="$slots.footer"><slot name="footer" /></footer>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>
<script setup lang="ts">
import { mdiClose } from "@mdi/js";
import Icon from "./Icon.vue";
defineProps<{
  open: boolean;
  title: string;
  subtitle?: string;
  icon?: string;
  iconClass?: string;
  wide?: boolean;
  full?: boolean;
  persistent?: boolean;
  top?: boolean; // stacks above other dialogs (confirmations)
}>();
defineEmits<{ (e: "close"): void }>();
</script>
<style scoped>
.backdrop.top { z-index: 150; }
.backdrop { position: fixed; inset: 0; background: rgba(0, 0, 0, 0.45); display: flex; align-items: center; justify-content: center; z-index: 100; padding: 16px; }
.dialog { background: var(--card); color: var(--text); border-radius: 18px; width: 100%; max-width: 520px; max-height: calc(100vh - 32px); display: flex; flex-direction: column; box-shadow: 0 12px 48px rgba(0, 0, 0, 0.3); }
.dialog.wide { max-width: 900px; }
.dialog.full { max-width: 1200px; height: calc(100vh - 32px); }
header { display: flex; align-items: center; gap: 12px; padding: 16px 16px 10px 20px; }
.content { padding: 6px 20px 18px; overflow: auto; flex: 1; }
footer { display: flex; gap: 8px; justify-content: flex-end; padding: 12px 20px; border-top: 1px solid var(--divider); flex-wrap: wrap; }
@media (max-width: 700px) {
  .backdrop { padding: 0; align-items: flex-end; }
  .dialog, .dialog.wide, .dialog.full { max-width: 100%; max-height: 94vh; height: auto; border-radius: 18px 18px 0 0; }
  .dialog.full { height: 94vh; }
}
.fade-enter-active, .fade-leave-active { transition: opacity .15s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
