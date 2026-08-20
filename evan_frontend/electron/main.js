import { app, BrowserWindow, ipcMain, screen } from 'electron'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))

// 全局变量保存窗口引用，防止被垃圾回收
let petWindow = null
let mainWindow = null
let popupWindow = null 
function createWindows() {
  // 1. 创建桌宠窗口 (小尺寸、透明、无边框、置顶)
   petWindow = new BrowserWindow({
    width: 300,          // 变宽一点，放得下聊天气泡
    height: 500,         // 变高一点，让气泡有空间往上飘
    frame: false,
    transparent: true,
    alwaysOnTop: true,
    resizable: false,
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false
    }
  })

  mainWindow = new BrowserWindow({
    width: 1000,
    height: 800,
    show: false,         // ⭐ 启动时先隐藏！
    frame: false,
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false
    }
  })

  popupWindow = new BrowserWindow({
    width: 280,
    height: 120,
    show: false,         // 默认隐藏
    frame: false,
    transparent: true,
    alwaysOnTop: true,
    skipTaskbar: true, 
    focusable: false,    // 🌟 绝对不能抢焦点，否则会打断用户打字！
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false
    }
  })

  // 3. 为两个窗口加载不同的路由
  if (process.env.VITE_DEV_SERVER_URL) {
    petWindow.loadURL(process.env.VITE_DEV_SERVER_URL + '#/pet')
    mainWindow.loadURL(process.env.VITE_DEV_SERVER_URL + '#/chat')
    popupWindow.loadURL(process.env.VITE_DEV_SERVER_URL + '#/popup')
  } else {
    petWindow.loadFile(path.join(__dirname, '../dist/index.html'), { hash: 'pet' })
    mainWindow.loadFile(path.join(__dirname, '../dist/index.html'), { hash: 'chat' })
    popupWindow.loadFile(path.join(__dirname, '../dist/index.html'), { hash: 'popup' })
  }
  // 接收渲染进程传来的坐标，移动桌宠窗口
  ipcMain.on('drag-pet', (event, { x, y }) => {
    if (petWindow) {
      petWindow.setPosition(x, y)
    }
  })

 
  ipcMain.on('set-ignore-mouse', (event, ignore) => {
    if (petWindow) {
      petWindow.setIgnoreMouseEvents(ignore, { forward: true })
    }
  })
  // ⭐ 关键逻辑：如果你点击主窗口的 X（关闭），我们不能真把它销毁，而是把它隐藏起来。
  // 否则下次点击团子时，主窗口就找不到了。
  mainWindow.on('close', (event) => {
    event.preventDefault() // 阻止默认的关闭销毁行为
    mainWindow.hide()      // 退回后台隐藏
  })
}

  ipcMain.on('show-mouse-popup', (event, message) => {
    if (!popupWindow) return

    // 获取系统当前鼠标绝对坐标
    const point = screen.getCursorScreenPoint()
    
    // 将窗口移动到鼠标右下方一点点 (防止挡住鼠标点击)
    popupWindow.setPosition(point.x + 15, point.y + 15)
    
    // 把消息发给 Popup.vue 渲染
    popupWindow.webContents.send('set-popup-message', message)
    
    // 🌟 showInactive: 显示窗口但不抢夺当前应用焦点 (极其重要)
    popupWindow.showInactive()
  })

  ipcMain.on('hide-mouse-popup', () => {
    if (popupWindow) popupWindow.hide()
  })

  ipcMain.on('popup-clicked', () => {
    if (popupWindow) popupWindow.hide()
    if (mainWindow) {
      mainWindow.show()
      mainWindow.focus()
    }
  })

app.whenReady().then(() => {
  createWindows()
  
  
  // ⭐ 接收来自团子（渲染进程）的呼唤，显示聊天窗口
  ipcMain.on('show-main-window', () => {
    if (mainWindow) {
      mainWindow.show()
      mainWindow.focus() // 让聊天窗口获取焦点
    }
  })
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit()
})