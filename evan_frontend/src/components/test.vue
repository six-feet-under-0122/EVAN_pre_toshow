<script setup>
import { ref } from "vue"
import axios from "axios"

const input = ref("")
const messages = ref([])

const sendMessage = async () => {
  if (!input.value) return

  // 用户消息
  messages.value.push({
    role: "user",
    content: input.value
  })

  const userInput = input.value
  input.value = ""

  // 请求后端
  const res = await axios.post("http://127.0.0.1:5000/chat", {
    message: userInput
  })

  // AI回复
  messages.value.push({
    role: "assistant",
    content: res.data.reply
  })
}
</script>

<template>
  <div class="container">

    <h2>Evan</h2>

    <div class="chat">

      <div 
        v-for="(msg, index) in messages" 
        :key="index"
        :class="msg.role"
      >
        {{ msg.content }}
      </div>

    </div>

    <div class="input-box">
      <input v-model="input" @keyup.enter="sendMessage"/>
      <button @click="sendMessage">发送</button>
    </div>

  </div>
</template>

<style>
.container {
  width: 500px;
  margin: auto;
  padding-top: 40px;
}

.chat {
  height: 400px;
  border: 1px solid #ccc;
  padding: 10px;
  overflow-y: auto;
}

.user {
  text-align: right;
  margin: 10px;
}

.assistant {
  text-align: left;
  margin: 10px;
}

.input-box {
  display: flex;
  margin-top: 10px;
}

input {
  flex: 1;
  padding: 10px;
}

button {
  padding: 10px;
}
</style>