<template>
  <div class="pet-container" 
       @mousemove="onDrag" 
       @mouseup="stopDrag">
    
    <!-- 微型聊天区域：绑定鼠标移入和移出 -->
    <div class="bubble-area" 
         :class="{ 'show-bubbles': bubbleVisible }"
         @mouseenter="handleMouseEnter"
         @mouseleave="handleMouseLeave">
      
      <!-- 滚动显示聊天历史 -->
      <div class="message-list" ref="messageListRef">
        <div v-for="(msg, index) in petMessages" :key="index" 
             class="mini-bubble" 
             :class="msg.role === 'user' ? 'user-bubble' : 'evan-bubble'">
          {{ msg.content }}
        </div>
      </div>

      <!-- 迷你输入框 -->
      <div class="mini-input-box">
        <input 
          type="text" 
          v-model="inputMsg" 
          placeholder="..." 
          @focus="isTyping = true"
          @blur="handleBlur"
          @keyup.enter="sendPetMessage"
          :disabled="isSending"
        />
      </div>
      
    </div>

    <!-- 团子本体：绑定鼠标移入和移出 -->
    <div class="pet-body" 
         @mouseenter="handleMouseEnter"
         @mouseleave="handleMouseLeave"
         @mousedown="startDrag"
         @click="handleBodyClick"
         title="点击打开主面板噢~">
        <img class="pet-content" :src="evanImg" alt="Evan" draggable="false" style="width:120px; height:auto;"  />
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { ipcRenderer } from 'electron'
import axios from 'axios'
import evanImg from '../assets/evan_bat.png'

// --- 状态控制 ---
const isHovering = ref(false)
const bubbleVisible = ref(false)
const isTyping = ref(false) // 是否正在打字
let hideTimer = null
let pokeTimer = null

const isPoking = ref(true) // 是否正在被动搭话中
// --- 聊天数据 ---
const petSessionId = ref(null)
const petMessages = ref([])
const inputMsg = ref("")
const isSending = ref(false)
const messageListRef = ref(null)

// --- 初始化专属桌宠会话 ---
const initPetSession = async () => {
  try {
    // 1. 获取所有会话，看看有没有专属会话
    const res = await axios.get("http://127.0.0.1:5000/sessions")
    const sessions = res.data.data || []
    let petSession = sessions.find(s => s.title === "【桌宠专属】")

    // 2. 如果没有，创建一个并限制字数
    if (!petSession) {
      const newRes = await axios.post("http://127.0.0.1:5000/new_session", {
        title: "【桌宠专属】",
        prompt_type: "evan_mini",
        system_prompt: "你是Evan，我的贴身桌宠。由于你的对话框很小，请务必用口语化的1到2句话回答，字数严格控制在40字以内！不需要用markdown格式."
      })
      petSessionId.value = newRes.data.id
    } else {
      petSessionId.value = petSession.id
    }

    // 3. 加载历史记录
    loadPetHistory()
  } catch (error) {
    console.error("初始化桌宠会话失败", error)
  }
}

const loadPetHistory = async () => {
  if (!petSessionId.value) return
  const res = await axios.get(`http://127.0.0.1:5000/history?session_id=${petSessionId.value}`)
  // 桌宠界面只显示最近的 5 条，避免太长
  petMessages.value = res.data.slice(-5).map(msg => ({
    role: msg.role,
  // 如果是带图片的复杂内容，提取纯文本显示
    content: Array.isArray(msg.content) ? msg.content.find(i => i.type === 'text')?.text : msg.content
  }))
  scrollToBottom()
}

const scrollToBottom = () => {
  nextTick(() => {
    if (messageListRef.value) {
      messageListRef.value.scrollTop = messageListRef.value.scrollHeight
    }
  })
}


// --- 鼠标移入移出与自动隐藏 ---
const startHideTimer = () => {
  if (hideTimer) clearTimeout(hideTimer)
  hideTimer = setTimeout(() => {
    // 只有在没打字、且鼠标不在区域内时，才隐藏
    if (!isTyping.value && !isHovering.value) {
      bubbleVisible.value = false
    }
  }, 4000)
}

const handleMouseEnter = () => {
  isHovering.value = true
  // 鼠标一进来，立刻清除隐藏计时器，保证绝对不消失
  if (hideTimer) {
    clearTimeout(hideTimer)
    hideTimer = null
  }
  
  if (!isDragging.value) {
    bubbleVisible.value = true
  }
}

const handleMouseLeave = () => {
  isHovering.value = false
  // 移出时，如果没有在打字，才开始准备隐藏
  if (!isTyping.value) {
    startHideTimer()
  }
  // 拖拽判断
  stopDrag()
}

// 处理输入框失去焦点
const handleBlur = () => {
  isTyping.value = false
  // 失去焦点后，如果鼠标也不在区域内，就开始倒计时隐藏
  if (!isHovering.value) {
    startHideTimer()
  }
}
// --- 处理窗口失去焦点 ---
const handleWindowBlur = () => {
  // 当点击桌面或其他应用时，强制取消打字和悬浮状态
  isTyping.value = false
  isHovering.value = false
  
  // 开启隐藏定时器，或者你也可以直接写 bubbleVisible.value = false 让它瞬间消失
  startHideTimer()
}

const sendPetMessage = async () => {
  if (!inputMsg.value.trim() || isSending.value) return
  
  const text = inputMsg.value
  inputMsg.value = ""
  petMessages.value.push({ role: "user", content: text })
  scrollToBottom()
  
  isSending.value = true
  try {
    const res = await axios.post("http://127.0.0.1:5000/chat", {
      message: text,
      model: "gpt-5.4-mini",
      session_id: petSessionId.value
    })
    petMessages.value.push({ role: "assistant", content: res.data.reply })
    scrollToBottom()
  } catch (error) {
    console.error(error)
  } finally {
    isSending.value = false
    // 发送完毕后，如果鼠标不在元素上且没在打字了，重新开启隐藏定时器
    if (!isHovering.value && !isTyping.value) {
      startHideTimer()
    }
  }
}

// --- 鼠标穿透逻辑 ---
let isIgnoring = true 
const handleGlobalMouseMove = (e) => {
  const isBackground = e.target.classList.contains('pet-container') || e.target.tagName === 'HTML' || e.target.tagName === 'BODY'
  if (isBackground && !isIgnoring) {
    ipcRenderer.send('set-ignore-mouse', true)
    isIgnoring = true
  } else if (!isBackground && isIgnoring) {
    ipcRenderer.send('set-ignore-mouse', false)
    isIgnoring = false
  }
}

const startProactivePoke = () => {
  if (pokeTimer) return 
  pokeTimer = setInterval(async () => {
    if (Math.random() < 0.3) {
      try {
        const res = await axios.post("http://127.0.0.1:5000/proactive_poke")
        const msg = res.data.message
        ipcRenderer.send('show-mouse-popup', msg)
      } catch (e) {
        console.error("搭话失败", e)
      }
    }
  }, 6000)// 每 6 秒尝试一次

}
onMounted(() => {
  ipcRenderer.send('set-ignore-mouse', true)
  window.addEventListener('mousemove', handleGlobalMouseMove)
  
  window.addEventListener('blur', handleWindowBlur)
  
  initPetSession()
  if(isPoking.value) {
    startProactivePoke()
  }
})

onUnmounted(() => {
  window.removeEventListener('mousemove', handleGlobalMouseMove)
  
  window.removeEventListener('blur', handleWindowBlur)

  if (pokeTimer) clearInterval(pokeTimer)
})


const isDragging = ref(false)
let hasMoved = false
let offsetX = 0; let offsetY = 0
let initialScreenX = 0; let initialScreenY = 0

const startDrag = (e) => {
  isDragging.value = true
  hasMoved = false
  bubbleVisible.value = false
  if (hideTimer) clearTimeout(hideTimer)
  offsetX = e.clientX; offsetY = e.clientY
  initialScreenX = e.screenX; initialScreenY = e.screenY
}

const onDrag = (e) => {
  if (!isDragging.value) return
  if (Math.abs(e.screenX - initialScreenX) > 3 || Math.abs(e.screenY - initialScreenY) > 3) hasMoved = true
  ipcRenderer.send('drag-pet', { x: e.screenX - offsetX, y: e.screenY - offsetY })
}

const stopDrag = () => { isDragging.value = false }

// --- 处理点击 ---
const handleBodyClick = () => {
  if (hasMoved) return 
  ipcRenderer.send('show-main-window')
}
</script>

<style scoped>
.pet-container {
  width: 100vw; height: 100vh;
  display: flex; flex-direction: column; justify-content: flex-end; align-items: center;
  overflow: hidden; background: transparent; padding-bottom: 80px;  box-sizing: border-box;
}

/* 气泡区域包裹列表和输入框 */
.bubble-area {
  width: 100%; max-height: 350px; 
  display: flex; flex-direction: column; align-items: center;
  margin-bottom: 15px; opacity: 0; transform: translateY(20px); transition: all 0.3s ease; pointer-events: none;
}
.show-bubbles { opacity: 1; transform: translateY(0); }
.show-bubbles .message-list, .show-bubbles .mini-input-box { pointer-events: auto; }

/* 聊天记录列表 */
.message-list {
  width: 100%; max-height: 250px; overflow-y: auto;
  display: flex; flex-direction: column; padding-bottom: 10px;
}
.message-list::-webkit-scrollbar { width: 0; display: none; }

.mini-bubble {
  max-width: 80%; padding: 8px 12px; border-radius: 12px; margin-bottom: 8px;
  font-size: 13px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); word-break: break-word;
} 
.user-bubble { background: #f2e0e8; color: rgb(84, 28, 28); align-self: flex-end; margin-right: 20px; }
.evan-bubble { background: rgb(84, 28, 28); color: white; align-self: flex-start; margin-left: 20px; }

/* 迷你输入框 */
.mini-input-box {
  width: 80%;
  background: white; border-radius: 20px;
  box-shadow: 0 4px 10px rgba(0,0,0,0.15); padding: 5px 15px;
}
.mini-input-box input {
  width: 100%; border: none; outline: none; font-size: 13px; background: transparent; padding: 5px 0;
}

.pet-body {
  width: 80px; height: 80px; 
  background: rgba(255, 196, 192, 0.688);
  backdrop-filter: blur(6px);
  border-radius: 50%;
  display: flex; justify-content: center; align-items: center;
  animation: breathe 2s infinite ease-in-out; flex-shrink: 0; cursor: grab;
    box-shadow: 
    0 0 15px rgba(255, 196, 192, 0.688),
    0 0 35px rgba(255, 183, 178, 0.4),
    0 0 60px rgba(255, 183, 178, 0.15);
  -webkit-user-drag: none; 
  user-select: none;
  will-change: transform, box-shadow; 
}
.pet-body:active { cursor: grabbing; transform: scale(0.95); }
.pet-content { color: white; font-weight: bold; text-align: center; pointer-events: none; -webkit-user-drag: none; }

@keyframes breathe { 
  0%, 100% { transform: scale(1); 
    box-shadow:
    0 0 15px rgba(255, 183, 178, 0.7),
    0 0 35px rgba(255, 183, 178, 0.4),
    0 0 60px rgba(255, 183, 178, 0.15);
  }
  50% { transform: scale(1.05); 
    box-shadow:
    0 0 20px rgba(255, 183, 178, 0.9),
    0 0 45px rgba(255, 183, 178, 0.55),
    0 0 80px rgba(255, 183, 178, 0.25);  
  } 
}

input::placeholder {
  user-select: none;
}

</style>