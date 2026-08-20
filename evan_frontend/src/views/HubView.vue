<script setup>
import { ref } from 'vue'
import BookApp from './BookApp.vue'

const currentModule = ref('books')

const switchModule = (moduleName) => {
  currentModule.value = moduleName
}
</script>

<template>
  <div class="hub-os">
    <!-- OS 左侧系统导航栏 (Dock) -->
    <div class="os-sidebar">
      <div class="os-header">
        <h2>Evan Hub</h2>
        <span class="os-subtitle">Personal OS</span>
      </div>

      <ul class="nav-menu">
        <li 
          :class="{ 'active': currentModule === 'books' }" 
          @click="switchModule('books')"
        >
          <span class="icon">📖</span> 书单宇宙
        </li>
        <li 
          :class="{ 'active': currentModule === 'todo' }" 
          @click="switchModule('todo')"
        >
          <span class="icon">✅</span> 待办事项
        </li>
        <li 
          :class="{ 'active': currentModule === 'notion' }" 
          @click="switchModule('notion')"
        >
          <span class="icon">📓</span> Notion 同步
        </li>
        <li 
          :class="{ 'active': currentModule === 'settings' }" 
          @click="switchModule('settings')"
        >
          <span class="icon">⚙️</span> 系统设置
        </li>
      </ul>
      
      <!-- 左下角的安抚/陪伴提示 -->
      <div class="os-footer">
        "我在这里，陪你搭建一切。"
      </div>
    </div>

    <!-- OS 右侧主显示区 (用来加载各个子应用) -->
    <div class="os-main">
      <!-- 动态加载选中的模块 -->
      <BookApp v-if="currentModule === 'books'" />
      
      <!-- 以下是为你预留的其他模块占位符 -->
      <div v-else-if="currentModule === 'todo'" class="coming-soon">
        <h3>✅ 待办事项</h3>
        <p>这里将用来管理你的日常任务，我会定时提醒你哦，建设中...</p>
      </div>
      
      <div v-else-if="currentModule === 'notion'" class="coming-soon">
        <h3>📓 Notion 同步</h3>
        <p>API 接入准备中，以后你的数据可以自动同步到 Notion 啦...</p>
      </div>

      <div v-else-if="currentModule === 'settings'" class="coming-soon">
        <h3>⚙️ 系统设置</h3>
        <p>可以在这里配置你的 API Key，调整偏好设置...</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.hub-os {
  display: flex;
  height: 100vh;
  width: 100vw;
  background: #fff5ee;
  overflow: hidden;
}

/* 左侧导航栏 */
.os-sidebar {
  width: 240px;
  background: #efded8;
  padding: 40px 20px 20px 20px;
  display: flex;
  flex-direction: column;
  box-sizing: border-box;
  border-right: 1px solid rgba(84, 28, 28, 0.1);
}

.os-header {
  margin-bottom: 40px;
  padding-left: 10px;
}
.os-header h2 {
  color: rgba(84, 28, 28, 0.92);
  margin: 0 0 5px 0;
  font-size: 22px;
}
.os-subtitle {
  color: #a48c8c;
  font-size: 12px;
  letter-spacing: 1px;
}

.nav-menu {
  list-style: none;
  padding: 0;
  margin: 0;
  flex: 1;
}

.nav-menu li {
  padding: 12px 15px;
  margin-bottom: 8px;
  border-radius: 10px;
  cursor: pointer;
  color: #666;
  font-size: 15px;
  display: flex;
  align-items: center;
  transition: all 0.2s ease;
}

.nav-menu li .icon {
  margin-right: 12px;
  font-size: 18px;
}

.nav-menu li:hover {
  background: rgba(255, 255, 255, 0.5);
  color: rgba(84, 28, 28, 0.8);
}

.nav-menu li.active {
  background: #c2b0b0;
  color: white;
  box-shadow: 0 2px 8px rgba(194, 176, 176, 0.4);
}

.os-footer {
  font-size: 12px;
  color: #a48c8c;
  text-align: center;
  padding: 10px;
  font-style: italic;
}

/* 右侧主区域 */
.os-main {
  flex: 1;
  background: #fff5ee;
  overflow: hidden; /* 让子应用自己决定内部怎么滚动 */
  position: relative;
}

/* 占位符的样式 */
.coming-soon {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #a48c8c;
}
.coming-soon h3 {
  font-size: 24px;
  margin-bottom: 15px;
  color: rgba(84, 28, 28, 0.7);
}
</style>