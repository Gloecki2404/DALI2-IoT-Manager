<template>
  <article class="card ic" :class="{ off: enabled === false, running: active }">
    <header class="ic-head">
      <span class="icon-bubble" :class="bubbleClass"><Icon :path="icon" :size="20" /></span>
      <button type="button" class="ic-title grow" @click="$emit('edit')">
        <span class="ic-name">{{ title || t("unnamed") }}</span>
        <span v-if="$slots.sub" class="ic-sub"><slot name="sub" /></span>
      </button>
      <span v-if="enabled !== undefined" class="ic-toggle" :title="enabled ? t('enabledHint') : t('disabledHint')">
        <Toggle :key="toggleKey" :model-value="enabled" :disabled="busy" @change="(v: boolean) => $emit('toggle', v)" />
      </span>
    </header>
    <div class="ic-body"><slot /></div>
    <footer class="ic-foot">
      <slot name="actions" />
      <span class="grow"></span>
      <button type="button" class="btn icon sm" :title="t('edit')" @click="$emit('edit')"><Icon :path="mdiPencilOutline" :size="18" /></button>
      <button v-if="duplicable" type="button" class="btn icon sm" :title="t('duplicate')" @click="$emit('duplicate')">
        <Icon :path="mdiContentCopy" :size="17" />
      </button>
      <button type="button" class="btn icon sm del" :title="t('delete')" @click="$emit('delete')"><Icon :path="mdiDeleteOutline" :size="18" /></button>
    </footer>
  </article>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { mdiContentCopy, mdiDeleteOutline, mdiPencilOutline } from "@mdi/js";
import Icon from "../Icon.vue";
import Toggle from "../Toggle.vue";
import { useAT } from "./i18n";

const props = defineProps<{
  title: string;
  icon: string;
  enabled?: boolean;
  active?: boolean;
  busy?: boolean;
  duplicable?: boolean;
}>();
defineEmits<{
  (e: "edit"): void;
  (e: "delete"): void;
  (e: "duplicate"): void;
  (e: "toggle", v: boolean): void;
}>();
const t = useAT();
const bubbleClass = computed(() => (props.active ? "ok" : props.enabled === false ? "off" : ""));
// Re-mount the toggle after a request finished so it always mirrors the real state (e.g. after an error).
const toggleKey = ref(0);
watch(
  () => props.busy,
  (b, old) => {
    if (old && !b) toggleKey.value++;
  },
);
</script>

<style scoped>
.ic { display: flex; flex-direction: column; transition: opacity .15s, box-shadow .15s; }
.ic.running { box-shadow: 0 0 0 2px color-mix(in srgb, var(--success) 55%, transparent), var(--shadow); }
.ic-head { display: flex; align-items: center; gap: 12px; padding: 14px 14px 6px 16px; }
.ic-title { display: flex; flex-direction: column; align-items: flex-start; min-width: 0; background: none; border: 0; padding: 0; color: inherit; text-align: left; cursor: pointer; font: inherit; }
.ic-name { font-weight: 500; font-size: 15px; max-width: 100%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.ic-sub { color: var(--text2); font-size: 12.5px; display: flex; gap: 6px; flex-wrap: wrap; align-items: center; }
.ic.off .ic-name, .ic.off .ic-body { opacity: .6; }
.ic-body { padding: 6px 16px 10px; flex: 1; display: flex; flex-direction: column; gap: 8px; min-width: 0; }
.ic-foot { display: flex; align-items: center; gap: 6px; padding: 8px 10px 8px 14px; border-top: 1px solid var(--divider); flex-wrap: wrap; }
.btn.icon.del:hover { color: var(--error); }
.ic-toggle { display: inline-flex; }
</style>
