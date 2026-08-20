import { ipcMain, app, BrowserWindow, screen } from "electron";
import path from "node:path";
import { fileURLToPath } from "node:url";
const __dirname$1 = path.dirname(fileURLToPath(import.meta.url));
let petWindow = null;
let mainWindow = null;
let popupWindow = null;
function createWindows() {
  petWindow = new BrowserWindow({
    width: 300,
    // 变宽一点，放得下聊天气泡
    height: 500,
    // 变高一点，让气泡有空间往上飘
    frame: false,
    transparent: true,
    alwaysOnTop: true,
    resizable: false,
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false
    }
  });
  mainWindow = new BrowserWindow({
    width: 1e3,
    height: 800,
    show: false,
    // ⭐ 启动时先隐藏！
    frame: false,
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false
    }
  });
  popupWindow = new BrowserWindow({
    width: 280,
    height: 120,
    show: false,
    // 默认隐藏
    frame: false,
    transparent: true,
    alwaysOnTop: true,
    skipTaskbar: true,
    focusable: false,
    // 🌟 绝对不能抢焦点，否则会打断用户打字！
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false
    }
  });
  if (process.env.VITE_DEV_SERVER_URL) {
    petWindow.loadURL(process.env.VITE_DEV_SERVER_URL + "#/pet");
    mainWindow.loadURL(process.env.VITE_DEV_SERVER_URL + "#/chat");
    popupWindow.loadURL(process.env.VITE_DEV_SERVER_URL + "#/popup");
  } else {
    petWindow.loadFile(path.join(__dirname$1, "../dist/index.html"), { hash: "pet" });
    mainWindow.loadFile(path.join(__dirname$1, "../dist/index.html"), { hash: "chat" });
    popupWindow.loadFile(path.join(__dirname$1, "../dist/index.html"), { hash: "popup" });
  }
  ipcMain.on("drag-pet", (event, { x, y }) => {
    if (petWindow) {
      petWindow.setPosition(x, y);
    }
  });
  ipcMain.on("set-ignore-mouse", (event, ignore) => {
    if (petWindow) {
      petWindow.setIgnoreMouseEvents(ignore, { forward: true });
    }
  });
  mainWindow.on("close", (event) => {
    event.preventDefault();
    mainWindow.hide();
  });
}
ipcMain.on("show-mouse-popup", (event, message) => {
  if (!popupWindow) return;
  const point = screen.getCursorScreenPoint();
  popupWindow.setPosition(point.x + 15, point.y + 15);
  popupWindow.webContents.send("set-popup-message", message);
  popupWindow.showInactive();
});
ipcMain.on("hide-mouse-popup", () => {
  if (popupWindow) popupWindow.hide();
});
ipcMain.on("popup-clicked", () => {
  if (popupWindow) popupWindow.hide();
  if (mainWindow) {
    mainWindow.show();
    mainWindow.focus();
  }
});
app.whenReady().then(() => {
  createWindows();
  ipcMain.on("show-main-window", () => {
    if (mainWindow) {
      mainWindow.show();
      mainWindow.focus();
    }
  });
});
app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});
