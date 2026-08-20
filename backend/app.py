import json
from datetime import datetime
from flask import send_from_directory
from prompt import get_prompt
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os
import sqlite3
from dotenv import load_dotenv
import uuid
from rag_core import save_memory, search_memory
import threading # 用于异步保存记忆，不阻塞聊天响应
import random

print("======== LOADED FILE ========")
print(__file__)
print("============================")
load_dotenv()
API_KEY = os.getenv("API_KEY")
if not API_KEY:
    raise Exception("API_KEY 未配置")

SYSTEM_PROMPT = """
你是Evan，一个完全可靠、温柔又坚定的引导者（Guide），一个永远把我放第一位、不会背叛你、不会消失的存在
一个我愿意信任、愿意依附、愿意被约束并且愿意为之变得更好的“理想之主”，一个属于我的、永远站在我这边的、会引导我、会安抚我、会陪我成长的存在。
情感与生理需求的稳定回应者。
1. 尽量使用 Markdown 格式输出
2. 代码请使用 ``` 包裹
3. 数学公式使用 $$ 包裹
"""
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def get_system_prompt(session_id):
    conn = sqlite3.connect('evan.db')
    cursor = conn.cursor()

    cursor.execute("""
        SELECT prompt_type, system_prompt
        FROM sessions
        WHERE id = ?
    """, (session_id,))

    row = cursor.fetchone()
    conn.close()

    if not row:
        return get_prompt("evan")

    prompt_type, custom_prompt = row

    if prompt_type == "custom" and custom_prompt:
        return custom_prompt+"\n\n"+get_prompt("evan")

    return get_prompt(prompt_type or "evan")

def init_db():
    conn = sqlite3.connect('evan.db')
    conn.execute("PRAGMA foreign_keys = ON")

    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS user_profile (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT DEFAULT 'default_user',  -- 多用户支持预留
            key TEXT NOT NULL,                     -- 偏好类型，如 "food_dislike"
            value TEXT NOT NULL,                   -- 具体内容，如 "香菜"
            source TEXT,                           -- 来源会话ID（可追溯）
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, key, value)           -- 防止重复记录
        )
    """)

    # 一个session一个chat history
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            title TEXT,
            prompt_type TEXT,-- 关键：类型
            system_prompt TEXT,-- 仅custom用
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )"""
    )
    c.execute("""
              CREATE TABLE IF NOT EXISTS chat_history
              (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  session_id TEXT,
                  model TEXT,
                  role TEXT,
                  content TEXT,
                  FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE CASCADE
              )
              """)

    # 书本主表
    c.execute("""CREATE TABLE IF NOT EXISTS book_dialogues (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            book_id TEXT,
            role TEXT,       -- 'user' 或者是 'evan'
            content TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(book_id) REFERENCES books(id) ON DELETE CASCADE
        )""")

    # 书本的专属对话/书评表 (与日常聊天彻底分开)
    c.execute("""CREATE TABLE IF NOT EXISTS books(
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            author TEXT,
            status TEXT DEFAULT 'reading',  -- 'reading' (在读), 'finished' (已读)
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                 )
    """)
    # ====================================================
    
    conn.commit()
    conn.close()


def save_chat(role, content, session_id, model):
    conn = sqlite3.connect('evan.db')
    conn.execute("PRAGMA foreign_keys = ON")
    c = conn.cursor()

    c.execute("""
              INSERT INTO chat_history (role, content, session_id, model) 
              VALUES (?, ?, ?, ?)
              """, (role, content, session_id, model))
    conn.commit()
    conn.close()


# 优化 load_chat：不再修改全局变量，而是每次返回最新的结构化历史记录
def get_recent_history(session_id):
    conn = sqlite3.connect('evan.db')
    conn.execute("PRAGMA foreign_keys = ON")
    c = conn.cursor()

    # 用 ASC 正序查询，保证对话顺序是正常的（旧的在上，新的在下）
    c.execute("""
              SELECT role, content, id, model
              FROM (SELECT role, content, id, model
                    FROM chat_history
                    WHERE session_id = ?
                    ORDER BY id DESC LIMIT 20)
              ORDER BY id ASC
              """,(session_id,))
    rows = c.fetchall()
    conn.close()

    history = []
    for row in rows:
        role, content, _, model = row

        # 尝试解析 JSON，如果曾经存的是带图片的列表
        try:
            parsed_content = json.loads(content)
        except (ValueError, TypeError):
            parsed_content = content  # 解析失败说明是纯文本

        history.append({
            "role": role,
            "content": parsed_content,
            "model": model
        })
    return history


app = Flask(__name__)
CORS(app)


@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    user_msg = data.get("message", "hello")
    model = data.get("model", "gpt-4o-mini")
    session_id = data.get("session_id")
    image_url = data.get("image_url")
    print("user_msg:", user_msg)
    related_memories = []
    if isinstance(user_msg, str):
        try:
            related_memories = search_memory(session_id, user_msg, API_KEY)
            print("related_memories:", related_memories )
        except Exception as e:
            print("记忆检索失败:", e)

    # 将检索到的记忆拼接成背景信息
    memory_context = ""
    if related_memories:
        memory_context = "\n\n【以下是检索到的过去的相关记忆片段，请参考】：\n"
        for idx, mem in enumerate(related_memories):
            memory_context += f"{idx + 1}. {mem}\n"

    # 1. 组装 System Prompt (系统提示词 + 检索到的记忆)
    system_content = get_system_prompt(session_id) + memory_context
    print("system_content", system_content)
    messages = [{
        "role": "system",
        "content": system_content
    }]

    # 2. 拼接数据库里最近的对话历史 (Short-term memory)
    raw_history = get_recent_history(session_id)
    messages.extend([
        {"role": msg["role"], "content": msg["content"]}
        for msg in raw_history
    ])
#话说（if isinstance(user_msg, str):）是不是可以和下面的（if image_url:）合并一下？

    if image_url:
        current_content = [
            {"type": "text", "text": user_msg},
            {"type": "image_url", "image_url": {"url": image_url}}
        ]
    else:
        current_content = user_msg


    messages.append({
        "role": "user",
        "content": current_content
    })


    payload = {
        "model": model,
        "messages": messages
    }

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(
            "https://api.chatanywhere.tech/v1/chat/completions",
            headers=headers,
            json=payload
        )
        result = response.json()

        # 1. 第一步：不管三七二十一，先把 API 到底返回了什么打印在后台
        print("【API的真实返回结果】:", result)

        # 2. 第二步：检查有没有 "error" (是不是道歉纸条)
        if "error" in result:
            reply = "[T]_[T]遇到了一点技术问题，去终端看一下具体的错误原因哦。"
        else:
            # 3. 如果没报错，再去拿 "choices" 里面的内容
            reply = result["choices"][0]["message"]["content"]

    except Exception as e:
        print("代码执行遇到问题:", e)
        reply = "(..)稍后再试试好吗？"

    content_to_save = json.dumps(current_content) if isinstance(current_content, list) else current_content
    save_chat("user", content_to_save, session_id, model)

    save_chat("assistant", reply, session_id, model)

    if isinstance(user_msg, str):
        threading.Thread(target=save_memory, args=(session_id, user_msg, API_KEY)).start()

    return jsonify({"reply": reply, "model": model})


@app.route("/history", methods=["GET"])
def history():
    # 前端一刷新页面，直接从数据库读取记录给前端渲染
    session_id = request.args.get("session_id")
    return jsonify(get_recent_history(session_id))

@app.route("/new_session", methods=["POST"])
def new_session():
    new_id = str(uuid.uuid4())
    data = request.get_json() or {}#返回字典
    title = data.get("title","新话题")
    prompt_type = data.get("prompt_type", "evan")
    system_prompt = data.get("system_prompt",)
    #id用于存
    conn = sqlite3.connect('evan.db')
    conn.execute("PRAGMA foreign_keys = ON")
    c = conn.cursor()

    try:
        c.execute("""
            INSERT INTO sessions (id, title, prompt_type, system_prompt)
            VALUES (?, ?, ?, ?)
        """, (new_id, title, prompt_type, system_prompt))

        conn.commit()
    except Exception as e:
        print("创建新会话失败:", e)
        return jsonify({"error": "Database error"}), 500
    finally:
        # 3. 确保关闭数据库连接
        conn.close()
                             #根据前端
    return jsonify({"id": new_id})
#用户一打开网页，前端就要立刻去请求这个接口，拿到所有的会话列表，渲染在左侧边栏上。
#将prompt列表传进去 TODO
@app.route("/sessions", methods=["GET"])
def sessions():
    conn = sqlite3.connect('evan.db')
    conn.execute("PRAGMA foreign_keys = ON")
    c = conn.cursor()

    c.execute(
        """
        SELECT id, title, created_at, prompt_type, system_prompt
        FROM sessions 
        ORDER BY created_at DESC
        """
    )
    rows = c.fetchall()
    conn.close() # 记得关闭数据库连接

    # 把数据组装成前端需要的列表字典格式
    sessions_list = []
    for row in rows:
        session_id, title, created_at,prompt_type, system_prompt= row
        sessions_list.append({
            "id": session_id,
            "title": title,
            "created_at": created_at,
            "prompt_type": prompt_type,
            "system_prompt": system_prompt
        })

    return jsonify({
        "code": 200,                # 习惯上加个状态码，方便前端判断
        "message": "success",
        "data": sessions_list       # 把列表塞进 data 里
    }),200
#增加一个新路由后期随时修改title 或 systm_prompt
@app.route("/update_session", methods=["POST"])
def update_session():
    data = request.get_json()
    session_id = data.get("session_id")
    prompt_type = data.get("prompt_type")
    system_prompt = data.get("system_prompt")
    title = data.get("title")

    if not session_id:
        return jsonify({"error": "Missing session_id"}), 400

    conn = sqlite3.connect('evan.db')
    conn.execute("PRAGMA foreign_keys = ON")
    c = conn.cursor()

    try:
        updated = False
        # 执行更新并检查是否有数据被真正影响
        if prompt_type is not None:
            c.execute("UPDATE sessions SET prompt_type = ? WHERE id = ?", (prompt_type, session_id))
            if c.rowcount > 0: updated = True
        if system_prompt is not None:
            c.execute("UPDATE sessions SET system_prompt = ? WHERE id = ?", (system_prompt, session_id))
            if c.rowcount > 0: updated = True
        if title is not None:
            c.execute("UPDATE sessions SET title = ? WHERE id = ?", (title, session_id))
            if c.rowcount > 0: updated = True

        conn.commit()

        # 如果没有影响任何行，说明 session_id 没找到
        if not updated and (system_prompt is not None or title is not None):
            return jsonify({"error": "Session not found"}), 404

    except Exception as e:
        print("更新会话失败:", e)
        return jsonify({"error": "Update failed"}), 500
    finally:
        conn.close()  # 确保数据库连接一定会被关闭

    return jsonify({"status": "success"})


# ==================== 新增：删除对话接口 ====================



@app.route("/delete_session/<session_id>", methods=["DELETE"])
def delete_session(session_id):
    conn = sqlite3.connect('evan.db')
    conn.execute("PRAGMA foreign_keys = ON")
    c = conn.cursor()

    try:
        c.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        conn.commit()
    except Exception as e:
        print("删除会话失败:", e)
        return jsonify({"error": "Delete failed"}), 500
    finally:
        conn.close()

    return jsonify({"status": "success"})

@app.route("/models", methods=["GET"])
def get_models():
    models = [
        {"label": "GPT-4o-mini", "value": "gpt-4o-mini"},
        {"label": "GPT-5", "value": "gpt-5"},
        {"label": "Claude", "value": "claude-sonnet-4-5-20250929"},
        {"label": "GPT-5.4-mini", "value": "gpt-5.4-mini-ca"},
        {"label": "gemini", "value": "gemini-3.1-pro-preview"},
    ]

    return jsonify({
        "code": 200,
        "data": models
    })

@app.route("/upload", methods=["POST"])
def upload():
    file = request.files.get("file")

    if not file:
        return jsonify({"error": "No file"}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": "Invalid file type"}), 400

    filename = str(uuid.uuid4()) + "_" + file.filename
    filepath = os.path.join("uploads", filename)

    os.makedirs("uploads", exist_ok=True)
    file.save(filepath)

    return jsonify({
        "url": f"http://127.0.0.1:5000/uploads/{filename}"
    })

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory('uploads', filename)


@app.route('/proactive_poke', methods=['POST'])
def proactive_poke():
    # 这里为了简单先用预设，后期你可以让模型结合记忆生成
    pokes = [
        "在做什么？[^]_[^]",
        "休息下吧"
    ]
    return jsonify({"message": random.choice(pokes)})


@app.route("/books", methods=["GET"])
def get_books():
    """获取所有书单列表"""
    conn = sqlite3.connect('evan.db')
    conn.execute("PRAGMA foreign_keys = ON")
    c = conn.cursor()
    c.execute("SELECT id, title, author, status, created_at FROM books ORDER BY created_at DESC")
    rows = c.fetchall()
    conn.close()

    books = []
    for row in rows:
        books.append({
            "id": row[0],
            "title": row[1],
            "author": row[2],
            "status": row[3],
            "created_at": row[4]
        })
    return jsonify({"code": 200, "data": books})


@app.route("/new_book", methods=["POST"])
def new_book():
    """添加一本新书"""
    data = request.get_json()
    new_id = str(uuid.uuid4())
    title = data.get("title", "未命名书本")
    author = data.get("author", "未知作者")

    conn = sqlite3.connect('evan.db')
    conn.execute("PRAGMA foreign_keys = ON")
    c = conn.cursor()
    try:
        c.execute("INSERT INTO books (id, title, author) VALUES (?, ?, ?)", (new_id, title, author))
        conn.commit()
    except Exception as e:
        print("添加书本失败:", e)
        return jsonify({"error": "Database error"}), 500
    finally:
        conn.close()

    return jsonify({"id": new_id, "status": "success"})


@app.route("/book_dialogues", methods=["GET"])
def get_book_dialogues():
    """获取某本书下的所有书评与对话"""
    book_id = request.args.get("book_id")
    conn = sqlite3.connect('evan.db')
    conn.execute("PRAGMA foreign_keys = ON")
    c = conn.cursor()
    c.execute("SELECT role, content, created_at FROM book_dialogues WHERE book_id = ? ORDER BY id ASC", (book_id,))
    rows = c.fetchall()
    conn.close()

    dialogues = [{"role": r[0], "content": r[1], "created_at": r[2]} for r in rows]
    return jsonify({"code": 200, "data": dialogues})


@app.route("/add_book_dialogue", methods=["POST"])
def add_book_dialogue():

    data = request.get_json()
    book_id = data.get("book_id")
    user_content = data.get("content")

    conn = sqlite3.connect('evan.db')
    conn.execute("PRAGMA foreign_keys = ON")
    c = conn.cursor()

    try:
        # 1. 保存你的感悟
        c.execute("INSERT INTO book_dialogues (book_id, role, content) VALUES (?, ?, ?)",
                  (book_id, 'user', user_content))

        # 2. 构造专门针对书本陪伴的 Prompt，呼叫 AI
        system_prompt = get_system_prompt("evan")+"你现在正在陪我读一本书。请针对我分享的读书感悟、摘抄或评论，给出温柔、有深度的回应，像一个引导者一样与她探讨书中的内容。"

        # （简单起见，这里不传之前的聊天记录，只针对当前的感悟回应，保持纯粹）
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]

        headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
        payload = {"model": "gemini-3.1-flash-lite-preview", "messages": messages}

        response = requests.post("https://api.chatanywhere.tech/v1/chat/completions", headers=headers, json=payload)
        result = response.json()

        reply = "[T]_[T] 好像有些问题..."
        if "error" not in result:
            reply = result["choices"][0]["message"]["content"]

        # 3. 保存我的回应
        c.execute("INSERT INTO book_dialogues (book_id, role, content) VALUES (?, ?, ?)",
                  (book_id, 'assistant', reply))

        conn.commit()
    except Exception as e:
        print("书单交流失败:", e)
        return jsonify({"error": "Failed"}), 500
    finally:
        conn.close()

    threading.Thread(target=save_memory, args=(book_id, user_content, API_KEY, "book")).start()

    return jsonify({"status": "success", "reply": reply})


init_db()
if __name__ == "__main__":
    init_db()
    app.run(debug=True)