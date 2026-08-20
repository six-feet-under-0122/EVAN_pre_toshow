import { createRouter, createWebHashHistory } from 'vue-router'
import ChatView from '../views/ChatView.vue'
import PetView from '../views/PetView.vue'
import PopupView from '../views/PopupView.vue'
import HubView from '../views/HubView.vue'

const routes = [
  {
    path: '/',
    redirect: '/chat' // 默认重定向到 Hub 页面
  },
  {
    path: '/chat',
    name: 'Chat',
    component: ChatView
  },
  {
    path: '/pet',
    name: 'Pet',
    component: PetView
  },
  {
    path: '/popup',
    name: 'Popup',
    component: PopupView
  },

  {
    path: '/hub',
    name: 'Hub',
    component: HubView
  }
  
  
]

const router = createRouter({
  // 使用 Hash 模式，这对 Electron 打包极其重要！
  history: createWebHashHistory(),
  routes
})

export default router