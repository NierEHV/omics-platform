<script setup>
import { ref, watch, nextTick, computed } from "vue";
import { useChatStore } from "../stores/chat.js";
import { useFilesStore } from "../stores/files.js";
import { useI18n } from "../i18n.js";
import { Send, Square, FlaskConical } from "lucide-vue-next";
import { marked } from "marked";
import AnalysisPlanCard from "./AnalysisPlanCard.vue";

const chat = useChatStore();
const filesStore = useFilesStore();
const { t } = useI18n();

const uploadedFiles = computed(() => {
  return filesStore.selectedFile ? [filesStore.selectedFile] : [];
});

const input = ref("");
const scrollEl = ref(null);
const textareaEl = ref(null);

marked.setOptions({ breaks: true });

function renderMarkdown(text) {
  if (!text) return "";
  return marked.parse(text);
}

const modality = ref("auto");
const modalities = ["auto", "scrna", "bulk", "spatial", "tcr", "metagenomics", "amplicon"];

function send() {
  const text = input.value.trim();
  if (!text && uploadedFiles.value.length === 0) return;
  chat.send(text, uploadedFiles.value, modality.value);
  input.value = "";
}

function onKeydown(e) {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    send();
  }
}

watch(() => chat.messages.length, async () => {
  await nextTick();
  if (scrollEl.value) {
    scrollEl.value.scrollTop = scrollEl.value.scrollHeight;
  }
});

function setExample(q) {
  input.value = q;
  send();
}
</script>

<template>
  <div class="chat-shell">
    <!-- Modality bar -->
    <div class="modality-bar">
      <button
        v-for="m in modalities" :key="m"
        class="modality-chip"
        :class="{ active: modality === m }"
        @click="modality = m"
      >
        {{ t(`chat.modality.${m}`) }}
      </button>
    </div>

    <!-- Messages -->
    <div ref="scrollEl" class="chat-scroll">
      <!-- Empty state -->
      <div v-if="chat.messages.length === 0" class="chat-empty-state">
        <div class="chat-empty-icon">
          <FlaskConical :size="28" />
        </div>
        <div>
          <h4>{{ t("chat.emptyTitle") }}</h4>
          <p>{{ t("chat.emptyDesc") }}</p>
        </div>
        <div class="example-questions">
          <button
            v-for="(q, i) in t('chat.examples')"
            :key="i"
            class="example-chip"
            @click="setExample(q)"
          >{{ q }}</button>
        </div>
      </div>

      <!-- Analysis plan -->
      <AnalysisPlanCard v-if="chat.plan" :plan="chat.plan" />

      <!-- Message rows -->
      <div
        v-for="(msg, i) in chat.messages" :key="i"
        class="chat-row"
        :class="msg.role"
      >
        <div class="chat-row-inner">
          <!-- Tool result -->
          <template v-if="msg.role === 'tool'">
            <div class="tool-result">
              <div class="tool-result-header">
                <FlaskConical :size="14" />
                <strong style="font-size:13px">{{ msg.tool }}</strong>
                <span
                  class="tool-result-status"
                  :class="msg.status === 'success' ? 'success' : 'error'"
                >{{ t(`chat.tool.${msg.status === 'success' ? 'success' : 'error'}`) }}</span>
                <span style="font-size:11px;color:var(--text-muted)">{{ msg.description }}</span>
              </div>
              <div class="tool-result-body">
                <pre>{{ JSON.stringify(msg.data, null, 2) }}</pre>
              </div>
            </div>
          </template>

          <!-- Text message -->
          <template v-else>
            <div class="chat-bubble" :class="msg.role">
              <div
                v-if="msg.role === 'assistant'"
                class="markdown-body"
                v-html="renderMarkdown(msg.content)"
              ></div>
              <template v-else>{{ msg.content }}</template>
            </div>
          </template>
        </div>
      </div>

      <!-- Typing indicator -->
      <div v-if="chat.streaming && chat.messages.length > 0 && chat.messages[chat.messages.length - 1]?.role === 'tool'" class="typing-indicator">
        <span></span><span></span><span></span>
        <strong>{{ t("chat.typing") }}</strong>
      </div>
    </div>

    <!-- Input -->
    <div class="chat-input-wrap">
      <div class="chat-input-shell">
        <textarea
          ref="textareaEl"
          v-model="input"
          :placeholder="t('chat.placeholder')"
          rows="1"
          @keydown="onKeydown"
        ></textarea>
        <button
          v-if="chat.streaming"
          class="stop-button"
          @click="chat.abort()"
        >
          <Square :size="16" />
        </button>
        <button
          v-else
          class="send-button"
          :disabled="!input.trim() && uploadedFiles.length === 0"
          @click="send()"
        >
          <Send :size="16" />
        </button>
      </div>
    </div>
  </div>
</template>
