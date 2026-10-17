<template>
  <Modal
    :open="!!req"
    :title="req?.title || ''"
    :icon="req?.danger ? mdiAlertOctagon : mdiHelpCircleOutline"
    :icon-class="req?.danger ? 'err' : ''"
    persistent
    top
    @close="done(false)"
  >
    <p style="white-space: pre-line; margin-top: 0">{{ req?.message }}</p>
    <div v-if="req?.typeToConfirm" class="field">
      <span>{{ t("typeHint", { word: req.typeToConfirm }) }}</span>
      <input v-model="typed" type="text" autocomplete="off" />
    </div>
    <template #footer>
      <button class="btn flat" @click="done(false)">{{ t("cancel") }}</button>
      <button
        class="btn"
        :class="{ danger: req?.danger }"
        :disabled="!!req?.typeToConfirm && typed !== req.typeToConfirm"
        @click="done(true)"
      >
        {{ req?.confirmText || t("confirm") }}
      </button>
    </template>
  </Modal>
</template>
<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { mdiAlertOctagon, mdiHelpCircleOutline } from "@mdi/js";
import Modal from "./Modal.vue";
import { confirmState } from "../lib/store";
import { useT } from "../lib/i18n";

const t = useT({
  de: { typeHint: "Zur Bestätigung „{word}“ eingeben" },
  en: { typeHint: "Type “{word}” to confirm" },
});
const req = computed(() => confirmState.current);
const typed = ref("");
watch(req, () => (typed.value = ""));
function done(v: boolean) {
  const r = confirmState.current;
  confirmState.current = null;
  r?.resolve(v);
}
</script>
