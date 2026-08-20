<template>
  <div class="popup-container">
    <!-- 绑定左键点击打开聊天，右键点击(contextmenu)关闭弹窗 -->
    <div 
      class="bubble" 
      @click.left="handleClick" 
      @contextmenu.prevent="closePopup"
    >
      <div class="text">{{ message }}</div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { ipcRenderer } from 'electron'

const message = ref("")
let autoCloseTimer = null

onMounted(() => {
  // 监听主进程发来的消息
  ipcRenderer.on('set-popup-message', (event, text) => {
    message.value = text
    
    // 收到消息后，8秒如果不理它，自动消失
    if (autoCloseTimer) clearTimeout(autoCloseTimer)
    autoCloseTimer = setTimeout(() => {
      closePopup()
    }, 8000)
  })
})

onUnmounted(() => {
  ipcRenderer.removeAllListeners('set-popup-message')
})

const handleClick = () => {
  ipcRenderer.send('popup-clicked')
}

const closePopup = () => {
  ipcRenderer.send('hide-mouse-popup')
}
</script>

<style scoped>
html, body {
  margin: 0; padding: 0;
  overflow: hidden;
  background: transparent !important;
}
.popup-container {
  width: 100vw; height: 100vh;
  display: flex; justify-content: flex-start; align-items: flex-start;
  padding: 10px; box-sizing: border-box;
}
.bubble {
  background: rgba(255, 255, 255, 0.95);
  border: 2px solid rgb(84, 28, 28);
  border-radius: 12px;
  padding: 12px 16px;
  box-shadow: 0 4px 15px rgba(84, 28, 28, 0.2);
  cursor: pointer;
  max-width: 240px;
  animation: popIn 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
  
  display: flex;
  align-items: center; 
}
.bubble:hover {
  background: #fdfdfd;
  transform: scale(1.02);
  transition: all 0.2s;
}

.text {
  font-size: 13px;
  color: rgb(84, 28, 28);
  line-height: 1.4;
  word-break: break-all;
}

@keyframes popIn {
  from { opacity: 0; transform: scale(0.8) translateY(10px); }
  to { opacity: 1; transform: scale(1) translateY(0); }
}
</style>