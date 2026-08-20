# EVAN - AI 对话助手

一个基于 Vue3 + Electron + Flask 的面向个人ai助理桌面应用，支持多模型切换、会话管理、记忆检索和桌面宠物功能。

## ✨ 功能特性

- 🤖 **多模型支持** - 支持多种 AI 模型切换（GPT-4o-mini 等）
- 💬 **多会话管理** - 独立的对话会话，互不干扰
- 🧠 **记忆系统** - 基于 RAG（检索增强生成）的长期记忆功能
- 🎨 **桌面宠物** - 可拖拽的桌面宠物交互
- 📝 **Markdown 渲染** - 支持代码高亮和 LaTeX 数学公式
- 🖼️ **图片上传** - 支持多模态对话
- 🎯 **自定义提示词** - 可切换不同的系统提示词

## 🛠️ 技术栈

### 前端
- **Vue 3** - 渐进式 JavaScript 框架
- **Vite** - 下一代前端构建工具
- **Electron** - 跨平台桌面应用框架
- **Element Plus** - Vue 3 组件库
- **Vue Router** - 路由管理
- **Axios** - HTTP 客户端
- **Marked** - Markdown 解析
- **Highlight.js** - 代码高亮
- **KaTeX** - 数学公式渲染

### 后端
- **Flask** - Python Web 框架
- **SQLite** - 轻量级数据库
- **ChromaDB** - 向量数据库（用于记忆检索）
- **Flask-CORS** - 跨域支持

## 📦 安装与运行

### 环境要求
- Node.js >= 16
- Python >= 3.8

### 后端启动

```bash
# 进入后端目录
cd backend

# 创建虚拟环境（可选）
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
# 创建 .env 文件，添加：
# API_KEY=your_api_key_here

# 启动后端服务
python app.py
```

后端服务默认运行在 `http://127.0.0.1:5000`

### 前端启动

```bash
# 进入前端目录
cd evan_frontend

# 安装依赖
npm install

# 开发模式启动
npm run dev

# 构建桌面应用
npm run build
```

## 📁 项目结构

```
.
├── backend/                 # 后端服务
│   ├── app.py              # Flask 主应用
│   ├── rag_core.py         # RAG 记忆核心
│   ├── prompt.py           # 系统提示词配置
│   └── memory_db/          # 向量数据库存储
├── evan_frontend/          # 前端应用
│   ├── src/
│   │   ├── views/          # 页面组件
│   │   │   ├── ChatView.vue    # 聊天界面
│   │   │   ├── PetView.vue     # 桌宠界面
│   │   │   └── HubView.vue     # 中枢系统
│   │   ├── components/     # 公共组件
│   │   └── assets/         # 静态资源
│   └── electron/           # Electron 配置
└── README.md
```

## 🎯 核心功能说明

### 会话管理
- 支持创建、切换、删除会话
- 每个会话独立的对话历史
- 可自定义会话标题

### 记忆系统
- 自动提取关键信息存入向量数据库
- 检索相关历史记忆增强对话上下文
- 支持长期记忆保持

### 提示词切换
- 预设多种人格提示词
- 支持自定义系统提示词
- 不同会话可使用不同提示词

## 🔧 配置说明

### 后端配置
在 `backend/.env` 中配置：
```env
API_KEY=你的API密钥
```

### 数据库
- SQLite 存储会话和聊天历史
- ChromaDB 存储向量化记忆

  ## 📝 关于此项目

  早期实现版本，功能完整可运行。目前已开启新仓库进行重构。