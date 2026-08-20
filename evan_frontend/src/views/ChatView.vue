
<script setup>
import { ref, onMounted,computed , onBeforeUnmount, watch } from "vue"
import { ElUpload, ElMessage } from "element-plus"
import axios from "axios"
import { marked } from "marked"
import { markedHighlight } from "marked-highlight"
import hljs from "highlight.js"
import "highlight.js/styles/atom-one-dark.css"
import katex from "katex"
import "katex/dist/katex.min.css"
import rabbitImg from '../assets/rabbit.jpg'
import evanImg from '../assets/evan_normal.jpg'
import { useRouter } from 'vue-router'
//TODO:改成websocket

const input = ref("")
const messages = ref([])
const router = useRouter()
const model = ref("gpt-4o-mini")

const currentSessionId = ref(null)
const showSessionIdMenu = ref(null) 

const newSessionTitle = ref("新话题")
const editingSessionId = ref(null)
const editingTitle = ref("")

const currentSystemPrompt = ref("你是Evan...")

const presetPrompts = ref([
  { label: "EVAN", value: "evan" },
  { label: "助手", value: "assistant" },
  { label: "自定义", value: "custom" }
])
const modelOptions = ref([])

const selectedPromptValue = ref("evan")

const showPromptMenu = ref(false) // 控制菜单

const showModelMenu = ref(false)//控制模型菜单

const currentPromptLabel = computed(() => {
  const found = presetPrompts.value.find(p => p.value === selectedPromptValue.value)
  return found ? found.label : "自定义"
})
const currentModelLabel = computed(() => {
  const found = modelOptions.value.find(m => m.value === model.value)
  return found ? found.label : model.value
})

const sessionList = ref([])

const textareaRef = ref(null)
const autoResize = () => {
  const el = textareaRef.value
  if (!el) return

  el.style.height = "auto"  // 先清空
  el.style.height = Math.min(el.scrollHeight, 150) + "px"
}

const imageUrl = ref(null)
const uploading = ref(false)



onMounted(async () => {
  await loadModels();
  await loadSessions();

  const res = await axios.get("http://127.0.0.1:5000/models")
  modelOptions.value = res.data.data || []

  if (sessionList.value.length === 0) {
    await createNewSession();
  } else {
    // 如果有，默认选中第一个
    currentSessionId.value = null; 
    await switchSession(sessionList.value[0].id);
  }
  document.addEventListener("click", handleClickOutside)
})
onBeforeUnmount(() => {
  document.removeEventListener("click", handleClickOutside)
})

marked.use(markedHighlight({
  highlight(code, lang) {
    const language = hljs.getLanguage(lang) ? lang : 'plaintext'
    return hljs.highlight(code, { language }).value
  }
}))
//wao 监听模型列表变化，如果当前选中的模型不在新列表里，自动切换到第一个
watch(modelOptions, (list) => {
  if (list.length && !list.find(m => m.value === model.value)) {
    model.value = list[0].value
  }
})

//woc
const renderMarkdown = (text) => {
  if (!text) return "";

  const mathMap = {};
  let mathIndex = 0;

  // 1. 提取块级公式 $$...$$ 并用占位符替换（注意这里去掉了下划线，改用 @@ 符号）
  text = text.replace(/\$\$([\s\S]+?)\$\$/g, (match, formula) => {
    const placeholder = `@@MATHBLOCK${mathIndex}@@`;
    try {
      mathMap[placeholder] = katex.renderToString(formula, { displayMode: true, throwOnError: false });
    } catch (err) {
      mathMap[placeholder] = match;
    }
    mathIndex++;
    return placeholder;
  });

  // 2. 提取行内公式 $...$ 并用占位符替换
  text = text.replace(/\$([^\n\$]+?)\$/g, (match, formula) => {
    const placeholder = `@@MATHINLINE${mathIndex}@@`;
    try {
      mathMap[placeholder] = katex.renderToString(formula, { displayMode: false, throwOnError: false });
    } catch (err) {
      mathMap[placeholder] = match;
    }
    mathIndex++;
    return placeholder;
  });

  // 3. 让 marked 解析 Markdown（此时公式很安全，变成了不会被转义的占位符）
  let html = marked.parse(text, {
    breaks: true,
    langPrefix: 'hljs language-'
  });

  // 4. 把渲染好的数学公式 HTML 替换回去
  for (const placeholder in mathMap) {
    // 🌟 关键修复：使用 () => mathMap[placeholder] 彻底杜绝 $ 符号带来的转义 BUG！
    html = html.replace(placeholder, () => mathMap[placeholder]);
  }

  return html;
}

const sendMessage = async () => {
  if (!input.value) return

  messages.value.push({
    role: "user",
    content: input.value
  })

  const userInput = input.value
  input.value = ""

  const res = await axios.post("http://127.0.0.1:5000/chat", {
    message: userInput,
    model: model.value,
    session_id: currentSessionId.value,
    image_url: imageUrl.value
  })

  imageUrl.value = null
  messages.value.push({
    role: "assistant",
    content: res.data.reply,
    model: res.data.model
  })

  const currentSession = sessionList.value.find(
    s => s.id === currentSessionId.value
  )

  if (currentSession && currentSession.title === "新话题"&& messages.value.length <= 2) {
    const newTitle = generateTitle(userInput)

    await axios.post("http://127.0.0.1:5000/update_session", {
      session_id: currentSessionId.value,
      title: newTitle
    })

    currentSession.title = newTitle
  }
}

 const switchSession = async(id) =>{
  if(id === currentSessionId.value) return
  currentSessionId.value = id
  const res = await axios.get("http://127.0.0.1:5000/history",{
    params: {
      session_id: id
    }
  })
  await loadSessions()
  const session = sessionList.value.find(s => s.id === id)
  if (session) {
    selectedPromptValue.value = session.prompt_type || "evan"
    if (session.prompt_type === "custom") {
      currentSystemPrompt.value = session.system_prompt || ""
    }
  }

  messages.value = res.data
 }

 const createNewSession = async() =>{
  const res = await axios.post("http://127.0.0.1:5000/new_session", {
    title: newSessionTitle.value,
    prompt_type: selectedPromptValue.value
  });
  newSessionTitle.value = "新话题"
  const newId = res.data.id;
  currentSessionId.value = newId;
  messages.value = [];
  await loadSessions();
 }


const updateSessionPrompt = async () => {
  if (!currentSessionId.value) return;

  const payload = {
    session_id: currentSessionId.value,
    prompt_type: selectedPromptValue.value
  };

  if (selectedPromptValue.value === "custom") {
    payload.system_prompt = currentSystemPrompt.value;
  }

  await axios.post("http://127.0.0.1:5000/update_session", payload);
}

const deleteSessionAction = async(id) =>{
  const res = await axios.delete(`http://127.0.0.1:5000/delete_session/${id}`) 
  if (res.data.status === "success") {
    messages.value = [];
    await loadSessions();
  }
}
const startEdit = (session) => {
  editingSessionId.value = session.id;
  editingTitle.value = session.title;
  showSessionIdMenu.value = false; 
}

const saveTitle = async(id) => {
  if (!editingTitle.value.trim()) {
    editingTitle.value = "未命名";
  }
  try {
    await axios.post("http://127.0.0.1:5000/update_session", {
      session_id: id,
      title: editingTitle.value
    })
    //直接更新
    const session = sessionList.value.find(s=>s.id === id)
    if (session) {
      session.title = editingTitle.value;
    }
  } catch (error) {
    console.error("更新会话标题失败:", error);
  } finally {
    editingSessionId.value = null;
  }
}

//自动生成标题
const generateTitle = (text) => {
  if (!text) return "新话题"

  text = text.replace(/\n/g, " ")

  let title = text.slice(0, 15)

  if (text.length > 15) {
    title += "..."
  }

  return title
}

const handleClickOutside = () => {
  showSessionIdMenu.value = null
  
  if(editingSessionId.value !== null) {
    editingSessionId.value = null;
  }
  
}

const toggleMenu = (sessionId) => {
  if (showSessionIdMenu.value === sessionId) {
    showSessionIdMenu.value = null; 
  } else {
    showSessionIdMenu.value = sessionId; 
  }
}

const loadModels = async () => {
  const res = await axios.get("http://127.0.0.1:5000/models")
  modelOptions.value = res.data.data || []
}

const loadSessions = async () => {
  const res = await axios.get("http://127.0.0.1:5000/sessions");
  sessionList.value = res.data.data || [];
}

const handleSelectPrompt = (val) => {
  selectedPromptValue.value = val;
  showPromptMenu.value = false; // 选完自动关闭菜单
  updateSessionPrompt(); 
}

const handleSelectModel = (val) => {
  model.value = val
  showModelMenu.value = false
}

const customUpload = async (options) => {
  const { file } = options
  uploading.value = true

  try {
    const formData = new FormData()
    formData.append('image', file)

    const API_KEY = 'd4dcfea4c030ca9b8773d0acb155828b'
    
    const response = await axios.post(
      `https://api.imgbb.com/1/upload?key=${API_KEY}`,
      formData
    )
    
    if (response.data.success) {
      imageUrl.value = response.data.data.url
      ElMessage.success('图片上传成功！')
    }
  } catch (error) {
    console.error('上传失败:', error)
    ElMessage.error('图片上传失败')
  } finally {
    uploading.value = false
  }
}


const beforeUpload = (file) => {
  const isImage = file.type.startsWith("image/")
  const isLt5M = file.size / 1024 / 1024 < 5 // ImgBB 免费版限制 5MB
  
  if (!isImage) {
    ElMessage.error("只能上传图片OAO")
    return false
  }
  if (!isLt5M) {
    ElMessage.error("图片大小不能超过 5MB")
    return false
  }
  return true
}

// 提取消息中的文本
const getMessageText = (content) => {
  if (Array.isArray(content)) {
    // 如果是数组，找到 type 为 'text' 的项
    const textObj = content.find(item => item.type === 'text');
    return textObj ? textObj.text : '';
  }
  return content; // 如果是纯文本，直接返回
}

// 提取消息中的图片 URL（如果有的话）
const getMessageImage = (content) => {
  if (Array.isArray(content)) {
    // 找到 type 为 'image_url' 的项
    const imgObj = content.find(item => item.type === 'image_url');
    return imgObj ? imgObj.image_url.url : null;
  }
  return null;
}
const goToHub = () => {
  // window.location.href = "#/hub"
  router.push('/hub')
}

</script>

<template>
<div class="titlebar">
  <div class="titlebar__drag">
    <div class="titlebar__left">
      <!-- mac 风格交通灯（不需要功能也能很好看） -->
      <div class="traffic">
        <span class="dot dot--close" title="关闭"></span>
        <span class="dot dot--min" title="最小化"></span>
        <span class="dot dot--max" title="最大化"></span>
      </div>
    </div>

    <div class="titlebar__center">
      <span class="app-title">Evan</span>
      <span class="app-subtitle">chat</span>
    </div>

    <div class="titlebar__right">
      <!-- 右侧可以放状态：当前模型/连接状态等 -->
      <span class="titlebar-badge">{{ currentModelLabel }}</span>
    </div>
  </div>

  <!-- 如果你要放真的窗口控制按钮，必须放在 no-drag 容器里 -->
  <!-- <div class="titlebar__actions">
    <button class="win-btn">—</button>
    <button class="win-btn">□</button>
    <button class="win-btn win-btn--danger">×</button>
  </div> -->
</div>
  <div class="layout">
    <div class ="sidebar">
      <div style="display: flex; justify-content: space-between; align-items: center;">
        <h3>对话列表</h3>
        <!-- 增加新建按钮 -->
        <button @click="createNewSession" 
        style="padding: 6px 12px; font-size: 12px;">
        + 新对话
        </button>
        <button @click="goToHub" style="margin-top: 10px; background: #a48c8c;">
        📖 打开 Hub
        </button>
      </div>
      <ul>
        <li v-for="session in sessionList" 
        :key="session.id"
        @click="switchSession(session.id)"
        :class ="{'active': session.id === currentSessionId}"
        >
          <!-- active部分似乎没有css?或者无效？TODO -->
          <!-- 选中高亮 -->
          <div class="session-info">
            <input
              v-if="editingSessionId === session.id"
              v-model="editingTitle"
              @click.stop
              @keyup.enter="saveTitle(session.id)"
              @blur="saveTitle(session.id)"
            />
            <span v-else class="title">
              {{ session.title }}
            </span>
            <span class="date">{{ session.created_at }}</span>
          </div>
          <!-- 操作区：加一个类名 action-btn-container -->
          <div class="action-btn-container">
            <button @click.stop="toggleMenu(session.id)" class="more-btn">...</button>

            <!-- 复用你的 custom-dropdown-menu！ -->
            <div v-if="showSessionIdMenu === session.id" class="custom-dropdown-menu" style="right: 0; left: auto; top: 30px;">
              <!-- 复用 dropdown-item -->
              <div class="dropdown-item" @click.stop="startEdit(session)">重命名</div>
              <div class="dropdown-item" @click.stop="deleteSessionAction(session.id); showSessionIdMenu = null">删除</div>
            </div>
          </div>

        </li>
      </ul>
    </div>
    <div class="main">

      <!-- 注意这里加了 position: relative，为了让弹出的菜单相对于它定位 -->
      <div style="display: flex; align-items: flex-end; margin-bottom: 15px; position: relative;">
        
        <!-- 假装是标题的触发器 (替代了原来的 select) -->
        <div 
          class="hidden-select-title" 
          @click="showPromptMenu = !showPromptMenu"
          title="点击切换人设"
        >
          {{ currentPromptLabel }}
        </div>
        
        <!-- 真正漂亮、带圆角的弹出菜单！ -->
        <div v-if="showPromptMenu" class="custom-dropdown-menu">
          <div 
            v-for="opt in presetPrompts" 
            :key="opt.value"
            class="dropdown-item"
            :class="{ 'active-item': opt.value === selectedPromptValue }"
            @click="handleSelectPrompt(opt.value)"
          >
            {{ opt.label }}
          </div>
        </div>

        <span class="model" style="margin-bottom: 2px; margin-left: 5px;">{{ model }}</span>
      </div>
      <!-- 如果选了自定义，在标题下面优雅地弹出一个输入框 -->
      <input  
        v-if="selectedPromptValue === 'custom'" 
        class="custom-prompt-input"
        v-model="currentSystemPrompt" 
        @blur="updateSessionPrompt" 
        placeholder="写下你的自定义提示词... (写完点击空白处自动保存)" 
      />
      <div class="chat">

        <div
          v-for="(msg, index) in messages"
          :key="index"
          :class="['message', msg.role]"
        >

          <img
            v-if="msg.role === 'assistant'"
            :src="evanImg"
            class="avatar"
          />

          <div class="bubble">
            <div v-if="msg.role === 'assistant'"
            v-html="renderMarkdown(getMessageText(msg.content))"
            class ="assistant"></div>
              <div 
              v-if="msg.role === 'assistant'"
              class="model-tag"
              >
                {{ msg.model }}
              </div>
            <div v-if="msg.role === 'user'" class="user">
              <!-- 如果有图片，显示图片 -->
              <img 
                v-if="getMessageImage(msg.content)" 
                :src="getMessageImage(msg.content)" 
                alt="这是一张图片~" 
                style="max-width: 200px; border-radius: 8px; margin-bottom: 8px; display: block;"
              />
              <!-- 显示文字 -->
              <span>{{ getMessageText(msg.content) }}</span>
            </div>

          </div>

          <img
            v-if="msg.role === 'user'"
            :src="rabbitImg"
            class="avatar"
          />

        </div>

      </div>

      <div class="input-box">
        <div style="position: relative; margin-right: 5px;">
          
          <!-- 当前模型 -->
          <div 
            class="model"
            @click="showModelMenu = !showModelMenu"
            title="切换模型"
            style="cursor: pointer;"
          >
            {{ currentModelLabel }}
          </div>

          <!-- 下拉菜单 -->
          <div v-if="showModelMenu" class="custom-dropdown-menu" style="top: auto; bottom: 110%;">
            <div
              v-for="m in modelOptions"
              :key="m.value"
              class="dropdown-item"
              :class="{ 'active-item': m.value === model }"
              @click="handleSelectModel(m.value)"
            >
              {{ m.label }}
            </div>
          </div>

        </div>
        <el-upload
        class="upload-demo"
        :http-request="customUpload"
        accept="image/*"
        :show-file-list="false"
        :before-upload="beforeUpload"
        drag
        :disabled="uploading"
        >
          <el-button size="small" type="primary" :loading="uploading">
          {{ uploading ? '上传中...' : '上传图片噢~ovo' }}
          </el-button>
        </el-upload>
        <div v-if="imageUrl" class="image-preview">
          <img :src="imageUrl" alt="preview" />
          <button @click="imageUrl = null" class="remove-image"></button>
        </div>
        <textarea
          ref="textareaRef"
          v-model="input"
          @input="autoResize"
          @keydown.enter.exact.prevent="sendMessage"
          @keydown.enter.shift.exact.prevent="input += '\n'" 
        ></textarea>
        <button @click="sendMessage">发送</button>
      </div>

    </div>
  </div>
</template>

<style>

html, body {
  height: 100%;
  overflow: hidden; /* ⭐ 禁止页面滚动 */
  background-color: transparent; /* 背景必须是透明的！ */
}



.layout {
  display: flex;
  /* 默认横向排列 */
  background:#fff5ee;
  height: 100vh;
  
}
.sidebar {
  width: 260px;
  height : 100vh;
  background: #efded8;
  padding: 20px;
  border-radius: 6px;
  padding-top: 44px;
  position: sticky; 
  top: 0; 
  box-sizing: border-box; /* 让 padding 包含在 100vh 内部，防止页面被撑爆 */
  overflow-y: auto;
}
.sidebar ul {
  list-style: none; /* 去掉前面的小黑点 */
  padding: 0;
  margin: 0;
}
.sidebar li {
  padding: 12px;
  margin-bottom: 8px;
  border-radius: 8px;
  cursor: pointer; /* 鼠标放上去变小手 */
  transition: background 0.2s; /* 增加一点悬浮动画 */
}
.title {
  font-size: 14px;
}
.date {
  font-size: 12px;
  color: #888;
  margin-left: 10px;
}

.sidebar li:hover {
  background: #f5f5f5;
  color:#888;
  
}
.sidebar li:hover .date {
  color: #888; /*后代选择器+：hover*/
  
}

.active {
  background: #c2b0b0;
  color: white;
  /* TODO:高亮？换一个颜色？（应该是颜色有点多） */
}
.active .date {
  color: #eee; /* 高亮时日期颜色变浅一点，好看些 */
}


.main{
  flex:1;
  /* 占满剩余空间 */
  margin : 10px 20px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  min-height : 0; /* 解决子元素高度撑开父元素导致的布局问题 */
    padding-top: 44px;
  box-sizing: border-box;

}


/* 标题样式 */
.hidden-select-title {
  font-size: 24px;
  font-weight: bold;
  cursor: pointer;
  color: #000;
  user-select: none; /* 防止双击时不小心选中文字 */
}
.hidden-select-title:hover {
  color: #a48c8c;
}

/* --- 下面是自定义下拉多选的魔法 --- */

/* 弹出的菜单外框 */
.custom-dropdown-menu {
  position: absolute;
  top: 100%; /* 贴在标题的正下方 */
  left: 0; 
  margin-top: 5px;
  background: #ffffff;
  border: 1px solid #eee;
  border-radius: 12px; 
  box-shadow: 0 4px 12px rgba(0,0,0,0.1); /* 加一点悬浮阴影，高级感拉满 */
  padding: 6px;
  z-index: 100;
  min-width: 120px;
}

.dropdown-item {
  padding: 8px 12px;
  border-radius: 8px; 
  cursor: pointer;
  font-size: 14px;
  color: #333;
  transition: background 0.2s; /* 颜色渐变动画 */
}

.dropdown-item:hover {
  background: #f0e6e6;
}

/* 当前选中的那个选项的特殊颜色 */
.active-item {
  background: #c2b0b0;
  color: white;
}
.active-item:hover {
  background: #a48c8c;  
}
.custom-prompt-input {
  width: 100%;
  padding: 10px;
  margin-bottom: 15px;
  border: 1px dashed #c2b0b0;
  border-radius: 8px;
  background: #fffdfd;
  box-sizing: border-box;
  font-size: 13px;
  color: #666;
}
.custom-prompt-input:focus {
  border: 1px solid #c2b0b0;
  outline: none;
}

.chat {
  flex:1;
  border: 1px solid #ddd;
  padding: 20px;
  border-radius: 6px;
  overflow-y: auto;
  background: #fffbfb;
  min-height: 0; /* 解决输入框被挤出屏幕的布局问题 */
}

.message {
  display: flex;
  margin-bottom: 15px;
  align-items: flex-start;
}

.assistant {
  justify-content: flex-start;
}

.user {
  justify-content: flex-end;
  white-space: pre-wrap;
}

.avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
}

.bubble {
  max-width: 70%;
  padding: 10px 15px;
  border-radius: 12px;
  margin: 0 10px;
}

.bubble pre {
  background: #2d1717; /* 整块背景 */
  border-radius: 12px;
  padding: 14px;
  margin: 10px 0;
  overflow-x: auto;
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
}

.user .bubble {
  background: #f2e0e8;
  color: rgb(84, 28, 28);
}

.assistant .bubble {
  background: rgb(84, 28, 28);
  border: 1px solid #ddd;
  color: #fff;
}

/* 行内代码（重点！） */
.bubble code {
  background: rgba(135, 131, 120, 0.15);
  color: #eb5757;
  padding: 3px 6px;
  border-radius: 4px;
  font-family: "JetBrains Mono", monospace;
}

/* 如果是 assistant 深色气泡，要单独适配 */
.assistant .bubble code {
  background: rgba(255, 255, 255, 0.15);
  color: #ffd866;
}

.assistant .bubble pre code {
  background: none;
  padding: 0;
  font-family: "JetBrains Mono", "Fira Code", monospace;
  
}

.model-tag{
  width: fit-content;
  font-size: 10px;
  background: #c2b0b0;
  color: white;
  padding: 2px 6px;
  border-radius: 8px;
  margin-top: 5px;

  
}
/* .model-select select {
  height: 44px;
  padding: 0 12px;
  border-radius: 8px;
  border: none;
  background: #e0d0d0;
  margin-right: 5px;
  top : 0;
} */

.prompt-settings select {
  height: 30px;
  padding: 0 8px;
  border-radius: 6px;
  border: none;
  background: #e0d0d0;
  margin: 10px;
}

.input-box {
  display: flex;
  align-items: flex-end;
  align-items: stretch; 
  margin-top: 10px;
  position: sticky;
  bottom: 0;
  background: #fff5ee;

}

input {
  flex: 1;
  padding: 12px;
  border: 1px solid #ddd;
  border-radius: 8px;
  margin-right: 5px;
}

button {
  padding: 12px 20px;
  background: #c2b0b0;
  border: none;
  border-radius: 8px;
}

.model {
  display: flex;
  align-items: center;
  height: 30px;
  padding: 0 12px;           /* 改成横向 padding */
  font-size: 12px;
  background: #c2b0b0;
  color: white;
  border-radius: 8px;
  margin-left: 10px;
}

/* 侧栏 */
.action-btn-container {

  position: relative;
}

/* 默认按钮是半透明 */
.more-btn {
  opacity: 0.3;
  transition: opacity 0.2s;
}

/* hover 整个 li 时 → 按钮变清晰 */
.sidebar li:hover .more-btn {
  opacity: 1;
}

.custom-dropdown-menu {
  opacity: 1 !important;
}

/* 简单的 ... 按钮样式（去背景去边框） */
.more-btn {
  background: transparent;
  border: none;
  font-weight: bold;
  color: #888;
  cursor: pointer;
  padding: 0 5px;
}
.more-btn:hover {
  color: #333;
}
textarea {
  flex: 1;
  padding: 12px;
  border: 1px solid #ddd;
  border-radius: 8px;
  margin-right: 5px;
  resize: none;          /* 禁止拖动 */
  min-height: 44px;
  max-height: 150px;
  overflow-y: auto;
  font-family: inherit;
}

.image-preview {
  position: absolute;
  bottom: 60px; /* 位于输入框上方 */
  left: 10px;
  background: white;
  padding: 5px;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.2);
  display: flex;
  align-items: center;
}

.image-preview img {
  max-width: 80px;
  max-height: 80px;
  border-radius: 4px;
}

.remove-image {
  position: absolute;
  top: -8px;
  right: -8px;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #ff4d4f;
  color: white;
  border: none;
  cursor: pointer;
  line-height: 1;
}
.remove-image::after {
  content: "×";
}


/* 顶部标题栏：统一高度 + 磨砂效果 + 细边框 */
.titlebar{
  position: fixed;   /* 关键 */
  top: 0;
  left: 0;
  right: 0;
  height: 44px;
  z-index: 9999;


  background: rgba(255, 245, 238, 0.65); /* 贴合你整体 #fff5ee */
  backdrop-filter: blur(18px);
  -webkit-backdrop-filter: blur(18px);

  border-bottom: 1px solid rgba(84, 28, 28, 0.10);
}

/* 可拖拽区域 */
.titlebar__drag {
  height: 44px;
  display: grid;
  grid-template-columns: 160px 1fr 160px;
  align-items: center;
  padding: 0 12px;

  -webkit-app-region: drag;
}

/* 左中右三块 */
.titlebar__left,
.titlebar__center,
.titlebar__right {
  display: flex;
  align-items: center;
}

.titlebar__left {
  justify-content: flex-start;
}

.titlebar__center {
  justify-content: center;
  gap: 8px;
  min-width: 0;
}

.titlebar__right {
  justify-content: flex-end;
}

/* 标题文字更精致 */
.app-title {
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 0.2px;
  color: rgba(84, 28, 28, 0.92);
}

.app-subtitle {
  font-size: 12px;
  color: rgba(84, 28, 28, 0.55);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* 右侧小徽章（显示当前模型等） */
.titlebar-badge {
  font-size: 11px;
  padding: 4px 8px;
  border-radius: 999px;
  background: rgba(194, 176, 176, 0.55);
  border: 1px solid rgba(194, 176, 176, 0.5);
  color: rgba(84, 28, 28, 0.9);
}

/* macOS 交通灯 */
.traffic {
  display: flex;
  gap: 8px;
  padding: 6px 8px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.35);
  border: 1px solid rgba(0, 0, 0, 0.06);

  /* 交通灯只是装饰也建议 no-drag，这样鼠标交互更正常 */
  -webkit-app-region: no-drag;
}

.dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  display: inline-block;
  box-shadow: inset 0 0 0 1px rgba(0,0,0,0.12);
}

.dot--close { background: #ff5f57; }
.dot--min   { background: #febc2e; }
.dot--max   { background: #28c840; }

/* 如果你启用右侧真正的窗口按钮（Windows 风格），用这些 */
.titlebar__actions {
  position: absolute;
  right: 8px;
  top: 6px;
  display: flex;
  gap: 6px;

  -webkit-app-region: no-drag;
}



</style>