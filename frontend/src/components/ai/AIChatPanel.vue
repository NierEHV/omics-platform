<template>
  <div class="ai-chat-wrapper" :class="{ open }">
    <button class="ai-toggle" @click="toggle" :title="open ? '收起AI助手' : '展开AI助手'">💬</button>
    <div class="ai-chat-panel glass-panel" v-show="open">
      <div class="chat-header"><h4>AI 助手</h4><button class="icon-button" @click="open = false" style="width:24px;height:24px">&times;</button></div>
      <div class="chat-messages" ref="msgContainer">
        <div v-for="(m, i) in messages" :key="i" :class="['msg', m.role]"><div class="msg-content" v-html="renderMd(m.content)"></div></div>
        <div class="msg assistant thinking" v-if="thinking"><div class="msg-content"><span class="dot-pulse">...</span></div></div>
      </div>
      <div class="chat-input"><input v-model="input" placeholder="输入指令..." @keyup.enter="send" :disabled="thinking" /><button class="primary-button" @click="send" :disabled="thinking || !input.trim()" style="padding:6px 12px;font-size:13px">发送</button></div>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick } from 'vue'
import { streamChat } from '@/api'
const props = defineProps({ projectId: String })
const emit = defineEmits(['run-all'])
const open = ref(false); const input = ref(''); const messages = ref([]); const thinking = ref(false); const msgContainer = ref(null)
function toggle() { open.value = !open.value }
function send() { const text = input.value.trim(); if (!text || thinking.value) return; messages.value.push({ role: 'user', content: text }); input.value = ''; thinking.value = true; scrollDown()
  streamChat(text, [], [], { onEvent(type, data) { if (type === 'message') { messages.value.push({ role: 'assistant', content: data.content || '' }) } else if (type === 'tool') { messages.value.push({ role: 'tool', content: '🔧 ' + data.tool + ': ' + data.status }) } scrollDown() }, onError(err) { messages.value.push({ role: 'assistant', content: '❌ ' + err.message }); thinking.value = false }, onDone() { thinking.value = false; emit('run-all') }, signal: null }) }
function scrollDown() { nextTick(() => { const el = msgContainer.value; if (el) el.scrollTop = el.scrollHeight }) }
function renderMd(t) { return t?.replace(/\n/g, '<br>')?.replace(/`([^`]+)`/g, '<code>$1</code>') || '' }
</script>

<style scoped>
.ai-chat-wrapper { position: fixed; bottom: 16px; left: 16px; z-index: 100; }
.ai-toggle { width: 48px; height: 48px; border-radius: 50%; border: none; background: var(--accent-500); color: #fff; font-size: 22px; cursor: pointer; box-shadow: var(--shadow-md); transition: transform .2s; }
.ai-toggle:hover { transform: scale(1.1); }
.ai-chat-panel { position: absolute; bottom: 56px; left: 0; width: 380px; height: 480px; display: flex; flex-direction: column; padding: 12px; }
.chat-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; }
.chat-header h4 { margin: 0; font-size: 14px; color: var(--text-primary); }
.chat-messages { flex: 1; overflow-y: auto; margin-bottom: 8px; }
.msg { margin-bottom: 8px; }
.msg.user .msg-content { background: var(--accent-100); color: var(--text-primary); padding: 6px 10px; border-radius: var(--border-radius-md) var(--border-radius-md) 0 var(--border-radius-md); font-size: 13px; }
.msg.assistant .msg-content { font-size: 13px; color: var(--text-primary); padding: 4px 0; }
.msg.tool .msg-content { font-size: 12px; color: var(--text-secondary); }
.dot-pulse { animation: dots 1.5s infinite; } @keyframes dots { 0% { opacity: .2; } 50% { opacity: 1; } 100% { opacity: .2; } }
.chat-input { display: flex; gap: 6px; }
.chat-input input { flex: 1; padding: 6px 10px; border: 1px solid var(--border-color); border-radius: var(--border-radius-sm); font-size: 13px; background: var(--bg-input); color: var(--text-primary); }
</style>
