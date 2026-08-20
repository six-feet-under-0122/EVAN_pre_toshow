<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'

// 书单数据
const books = ref([])
const newBookTitle = ref('')
const newBookAuthor = ref('')

// 当前展开对话的书本ID
const expandedBookId = ref(null)
// 某本书的专属对话列表
const currentDialogues = ref([])
// 书评输入框
const bookInput = ref('')

// 页面加载时获取书单
onMounted(async () => {
  await loadBooks()
})

const loadBooks = async () => {
  try {
    const res = await axios.get("http://127.0.0.1:5000/books")
    books.value = res.data.data || []
  } catch (error) {
    console.error("加载书单失败", error)
  }
}

const addBook = async () => {
  if (!newBookTitle.value.trim()) return
  
  await axios.post("http://127.0.0.1:5000/new_book", {
    title: newBookTitle.value,
    author: newBookAuthor.value || "未知作者"
  })
  
  newBookTitle.value = ''
  newBookAuthor.value = ''
  await loadBooks()
}

// 点击书本卡片，展开/收起 对话
const toggleBook = async (bookId) => {
  if (expandedBookId.value === bookId) {
    expandedBookId.value = null // 再次点击则收起
    return
  }
  
  expandedBookId.value = bookId
  currentDialogues.value = [] // 清空之前的加载
  bookInput.value = ''
  
  // 获取这本书的专属历史对话
  try {
    const res = await axios.get(`http://127.0.0.1:5000/book_dialogues?book_id=${bookId}`)
    currentDialogues.value = res.data.data || []
  } catch (error) {
    console.error("加载书本对话失败", error)
  }
}

// 发送书评/感悟
const sendBookMessage = async (bookId) => {
  if (!bookInput.value.trim()) return

  
  // 先把你的话推到界面上
  currentDialogues.value.push({ role: 'user', content: content })
  
  try {
    const res = await axios.post("http://127.0.0.1:5000/add_book_dialogue", {
      book_id: bookId,
      content: content
    })
    
    // 把 Evan 的回复推到界面上
    if (res.data.status === "success") {
      currentDialogues.value.push({ role: 'assistant', content: res.data.reply })
    }
  } catch (error) {
    console.error("发送感悟失败", error)
    currentDialogues.value.push({ role: 'assistant', content: "(..) 好像遇到点小问题，没听清你说什么。" })
  } finally {
    isSending.value = false
  }
}
</script>

<template>
  <div class="hub-container">
    <div class="hub-header">
      <h2>我的书单宇宙</h2>
      <p>写下你想读的书，或者和我分享你的感悟。</p>
    </div>

    <!-- 添加新书区 -->
    <div class="add-book-box">
      <input v-model="newBookTitle" placeholder="书名..." class="book-input" />
      <input v-model="newBookAuthor" placeholder="作者 (选填)..." class="book-input" />
      <button @click="addBook" class="add-btn">+ 收录书本</button>
    </div>

    <!-- 书单列表 -->
    <div class="book-list">
      <div 
        v-for="book in books" 
        :key="book.id" 
        class="book-card"
        :class="{'expanded': expandedBookId === book.id}"
      >
        <!-- 书本基本信息 (点击展开/收起) -->
        <div class="book-info" @click="toggleBook(book.id)">
          <div class="book-title-area">
            <span class="book-icon">📖</span>
            <span class="book-title">{{ book.title }}</span>
            <span class="book-author">—— {{ book.author }}</span>
          </div>
          <div class="expand-hint">
            {{ expandedBookId === book.id ? '收起感悟 向上' : '展开交流 向下' }}
          </div>
        </div>

        <!-- 专属微型对话区 (附在书名后面) -->
        <div v-if="expandedBookId === book.id" class="book-dialogue-area" @click.stop>
          <div class="dialogue-history">
            <div 
              v-for="(msg, idx) in currentDialogues" 
              :key="idx"
              :class="['mini-msg', msg.role]"
            >
              <div class="mini-bubble">{{ msg.content }}</div>
            </div>
            
            <div v-if="currentDialogues.length === 0" class="empty-hint">
              还没有感悟呢，和我分享一下你看到了哪一段？
            </div>
          </div>

          <!-- 输入区 -->
          <div class="dialogue-input-area">
            <textarea 
              v-model="bookInput" 
              placeholder="分享你的摘抄或感想..."
              @keydown.enter.exact.prevent="sendBookMessage(book.id)"
            ></textarea>
            <button @click="sendBookMessage(book.id)">
              发送
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.hub-container {
  height: 100vh;
  padding: 60px 40px 40px 40px;
  background: #fff5ee;
  box-sizing: border-box;
  overflow-y: auto;
  font-family: inherit;
}

.hub-header h2 {
  color: rgba(84, 28, 28, 0.92);
  margin-bottom: 5px;
}
.hub-header p {
  color: #a48c8c;
  font-size: 14px;
  margin-bottom: 20px;
}

.add-book-box {
  display: flex;
  gap: 10px;
  margin-bottom: 30px;
  background: #efded8;
  padding: 15px;
  border-radius: 12px;
}

.book-input {
  flex: 1;
  padding: 10px 15px;
  border: none;
  border-radius: 8px;
  background: white;
  outline: none;
}

.add-btn {
  background: #c2b0b0;
  color: white;
  border: none;
  border-radius: 8px;
  padding: 0 20px;
  cursor: pointer;
  transition: background 0.2s;
}
.add-btn:hover {
  background: #a48c8c;
}

.book-list {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.book-card {
  background: white;
  border-radius: 12px;
  padding: 15px 20px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.04);
  transition: all 0.3s ease;
  border: 1px solid #f2e0e8;
}
.book-card.expanded {
  border: 1px solid #c2b0b0;
  box-shadow: 0 4px 15px rgba(0,0,0,0.08);
}

.book-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: pointer;
}

.book-icon {
  margin-right: 10px;
}
.book-title {
  font-weight: bold;
  font-size: 16px;
  color: #333;
}
.book-author {
  font-size: 13px;
  color: #888;
  margin-left: 10px;
}

.expand-hint {
  font-size: 12px;
  color: #c2b0b0;
}

/* 微型对话区 */
.book-dialogue-area {
  margin-top: 15px;
  padding-top: 15px;
  border-top: 1px dashed #efded8;
}

.dialogue-history {
  max-height: 300px;
  overflow-y: auto;
  margin-bottom: 15px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding-right: 5px;
}

.empty-hint {
  text-align: center;
  color: #c2b0b0;
  font-size: 13px;
  padding: 20px 0;
}

.mini-msg {
  display: flex;
  width: 100%;
}
.mini-msg.user {
  justify-content: flex-end;
}
.mini-msg.assistant {
  justify-content: flex-start;
}

.mini-bubble {
  max-width: 80%;
  padding: 8px 14px;
  border-radius: 12px;
  font-size: 14px;
  line-height: 1.5;
  white-space: pre-wrap;
}

.user .mini-bubble {
  background: #f2e0e8;
  color: rgb(84, 28, 28);
  border-bottom-right-radius: 4px;
}

.assistant .mini-bubble {
  background: #f5f5f5;
  color: #333;
  border-bottom-left-radius: 4px;
}

.dialogue-input-area {
  display: flex;
  gap: 10px;
}
.dialogue-input-area textarea {
  flex: 1;
  height: 40px;
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 8px;
  resize: none;
  font-family: inherit;
  font-size: 13px;
}
.dialogue-input-area button {
  background: #c2b0b0;
  color: white;
  border: none;
  border-radius: 8px;
  padding: 0 15px;
  cursor: pointer;
}
</style>