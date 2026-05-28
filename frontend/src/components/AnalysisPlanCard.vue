<script setup>
import { useI18n } from "../i18n.js";
import { Lightbulb, ChevronDown, ChevronRight } from "lucide-vue-next";
import { ref } from "vue";

defineProps({
  plan: { type: Object, default: null },
});

const { t } = useI18n();
const expanded = ref(true);
</script>

<template>
  <div v-if="plan && plan.steps && plan.steps.length > 0" class="plan-card glass-panel">
    <h3 @click="expanded = !expanded" style="cursor:pointer">
      <Lightbulb :size="16" style="color:var(--accent-500)" />
      {{ t("chat.plan.title") }}
      <component :is="expanded ? ChevronDown : ChevronRight" :size="14" style="margin-left:auto" />
    </h3>
    <div v-if="expanded">
      <div
        v-for="step in plan.steps" :key="step.order"
        class="plan-step"
      >
        <div class="plan-step-num">{{ step.order }}</div>
        <div class="plan-step-info">
          <div class="plan-step-name">{{ step.plugin_name || step.description }}</div>
          <div class="plan-step-desc">{{ step.description }}</div>
        </div>
      </div>
      <div v-if="plan.estimated_runtime_minutes" style="font-size:11px;color:var(--text-muted);margin-top:8px">
        ~{{ plan.estimated_runtime_minutes }} min | GPU: {{ plan.gpu_recommended ? "recommended" : "not needed" }}
      </div>
    </div>
  </div>
</template>
