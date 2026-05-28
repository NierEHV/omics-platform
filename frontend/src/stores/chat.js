import { defineStore } from "pinia";
import { ref } from "vue";
import { streamChat } from "../api.js";
import { useUiStore } from "./ui.js";

export const useChatStore = defineStore("chat", () => {
  const ui = useUiStore();
  const messages = ref([]);
  const streaming = ref(false);
  const plan = ref(null);
  let abortController = null;

  function addMessage(role, content) {
    messages.value.push({ role, content, timestamp: new Date().toISOString() });
  }

  function addToolResult(tool, status, data, description) {
    messages.value.push({
      role: "tool",
      tool,
      status,
      data,
      description,
      timestamp: new Date().toISOString(),
    });
  }

  async function send(text, files = [], modality = "auto") {
    if (!text.trim() && files.length === 0) return;

    addMessage("user", text);
    streaming.value = true;
    plan.value = null;

    abortController = new AbortController();

    const history = messages.value.slice(0, -1).map((m) => ({
      role: m.role,
      content: m.content || "",
    }));

    try {
      await streamChat(
        text,
        files.map((f) => f.path || f.name || f),
        history,
        {
          signal: abortController.signal,
          onEvent(type, data) {
            switch (type) {
              case "plan":
                plan.value = data;
                break;
              case "message":
                addMessage("assistant", data.content);
                break;
              case "tool":
                addToolResult(data.tool, data.status, data.data, data.description);
                break;
              case "meta":
                break;
            }
          },
          onError(err) {
            ui.setError(err.message);
            addMessage("assistant", `Error: ${err.message}`);
          },
          onDone() {
            streaming.value = false;
            abortController = null;
          },
        }
      );
    } catch (e) {
      if (e.name !== "AbortError") {
        ui.setError(e.message);
      }
      streaming.value = false;
      abortController = null;
    }
  }

  function abort() {
    if (abortController) {
      abortController.abort();
      abortController = null;
      streaming.value = false;
    }
  }

  function clear() {
    messages.value = [];
    plan.value = null;
  }

  return { messages, streaming, plan, send, abort, clear, addMessage, addToolResult };
});
