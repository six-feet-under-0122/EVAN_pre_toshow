<template>
  <div class="app">
    <h2 class="title">Evan · 陆沉</h2>

    <div class="chat-window">
      <div
        v-for="(msg, index) in messages"
        :key="index"
        class="chat-line"
        :class="msg.role"
      >
        <div class="label">
          {{ msg.role === 'user' ? '你' : '陆沉' }}
        </div>
        <div class="bubble">
          {{ msg.content }}
        </div>
      </div>
    </div>

    <div class="input-area">
      <textarea
        v-model="currentInput"
        placeholder="对陆沉说点什么..."
        @keydown.enter.exact.prevent="sendMessage"
      ></textarea>
      <button :disabled="loading || !currentInput.trim()" @click="sendMessage">
        {{ loading ? '思考中...' : '发送' }}
        <!-- 阻止发送 -->
      </button>
    </div>
  </div>
</template>

<script>
import axios from "axios";

export default {
  name: "App",
  data() {
    return {
      currentInput: "",
      messages: [
        {
          role: "assistant",
          content: "我在。今天想从哪件小事开始跟我讲？",
        },
      ],
      loading: false,
    };
  },
  methods: {
    async sendMessage() {
      const text = this.currentInput.trim();
      if (!text || this.loading) return;

      // 先把用户消息推到界面上
      this.messages.push({
        role: "user",
        content: text,
      });
      this.currentInput = "";
      this.loading = true;

      try {
        const res = await axios.post("http://127.0.0.1:5000/chat", {
          message: text,
        });

        if (res.data && res.data.reply) {
          this.messages.push({
            role: "assistant",
            content: res.data.reply,
          });
        } else if (res.data && res.data.error) {
          this.messages.push({
            role: "assistant",
            content:
              "刚刚和后端通信出了一点问题：" +
              res.data.error +
              "（不过我还在，不用紧张。）",
          });
        }
      } catch (err) {
        this.messages.push({
          role: "assistant",
          content:
            "网络好像出了一点小问题，我暂时没收到回复。你等等再试一次，或者稍后再来找我。",
        });
      } finally {
        this.loading = false;
        this.$nextTick(() => {
          const chatWindow = document.querySelector(".chat-window");
          if (chatWindow) {
            chatWindow.scrollTop = chatWindow.scrollHeight;
          }
        });
      }
    },
  },
};
</script>

<style scoped>
.app {
  max-width: 720px;
  margin: 0 auto;
  padding: 16px;
  font-family: system-ui, -apple-system, BlinkMacSystemFont, "PingFang SC",
    "Microsoft YaHei", sans-serif;
}

.title {
  text-align: center;
  margin-bottom: 16px;
}

.chat-window {
  border: 1px solid #ddd;
  border-radius: 8px;
  padding: 12px;
  height: 420px;
  overflow-y: auto;
  background: #fafafa;
}

.chat-line {
  display: flex;
  margin-bottom: 8px;
}

.chat-line .label {
  font-size: 12px;
  color: #666;
  margin-right: 8px;
  width: 40px;
  text-align: right;
  flex-shrink: 0;
}

.chat-line .bubble {
  padding: 8px 10px;
  border-radius: 8px;
  max-width: 80%;
  word-break: break-word;
}

/* 用户气泡 */
.chat-line.user {
  justify-content: flex-end;
}
.chat-line.user .label {
  order: 2;
  text-align: left;
}
.chat-line.user .bubble {
  order: 1;
  background: #d1ecff;
}

/* 陆沉气泡 */
.chat-line.assistant .bubble {
  background: #f0f0f0;
}

.input-area {
  margin-top: 12px;
  display: flex;
  gap: 8px;
}

textarea {
  flex: 1;
  resize: none;
  min-height: 60px;
  padding: 8px;
}

button {
  width: 86px;
  height: 60px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
}
button:disabled {
  opacity: 0.6;
  cursor: default;
}
</style>
