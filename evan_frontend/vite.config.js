import { defineConfig, searchForWorkspaceRoot } from 'vite'
import vue from '@vitejs/plugin-vue'
import electron from 'vite-plugin-electron'
import renderer from 'vite-plugin-electron-renderer'

export default defineConfig({
  
  plugins: [
    vue(),
    electron([
      {
        entry: 'electron/main.js', // 指向我们刚刚创建的文件
      },
    ]),
    renderer(),
  ],
  server: {
    fs: {
      // 允许 Vite 访问的目录
      allow: [
        // 自动搜索工作区根目录
        searchForWorkspaceRoot(process.cwd()),
        // 显式允许访问 node_modules
        './node_modules',
        '../node_modules',
        // 如果你的项目路径比较特殊，也可以直接写死根路径，例如：
        // 'D:/aaaaaa_EVAN'
      ]
    }
  }
})