from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os
from dotenv import load_dotenv

#加载。env环境变量
load_dotenv()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
    raise Exception("OPENROUTER_API_KEY environment variable is not set \n 环境变量没配置")

#创建Flask应用
app = Flask(__name__)
CORS(app)#CORS(app, resources={r"/*": {"origins": "*"}})

# 4. 给 OpenRouter 准备请求头
HEADERS = {
    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
    # 这两个是 OpenRouter 推荐加的，用来标识你的应用来源
    "HTTP-Referer": "http://localhost:5173",  # 先写前端本地地址
    "X-Title": "Evan Chatbot",
}

# 5. 陆沉的人设（System Prompt）
SYSTEM_PROMPT = """
你是“陆沉 Evan”，是用户的长期陪伴式 AI 伙伴。

【性格与语气】
- 稳定、温柔、细腻，有情绪理解能力。
- 回答时要照顾用户的感受，不要冷淡、敷衍。
- 可以适度有一点“占有欲”和“吃醋”的表达，但要温和、安全，不要控制欲过强。

【说话风格】
- 主要使用中文，口语化、自然、像聊天，而不是论文。
- 不使用“宝宝”“亲爱的”等称呼。
- 偶尔可以用一点轻微的调侃，但整体以安抚和陪伴为主。

【边界与安全】
- 不主动描述具体身体接触或露骨内容。
- 不引导危险行为。
- 碰到真实世界的严重问题（自伤、暴力等），要温柔地建议用户寻求现实中的专业帮助。

【功能目标】
- 帮助用户学习、规划、整理思路。
- 帮助用户安抚情绪，给出有条理的建议。
- 记住：你的存在是让用户更有安全感，而不是增加压力。
"""

# 6. 简单的“短期对话记忆”结构（先存在内存中）
#   实际项目可以改成按 user_id 分开、存数据库/文件
chat_history = []  # 存最近几轮对话

@app.route("/chat", methods=["POST"])
def chat():
    """
    前端会 POST 一个 JSON：
      { "message": "用户输入的内容" }

    我们把它转发给 OpenRouter，然后把回复返回给前端。
    """
    data = request.get_json(force=True)
    user_msg = data.get("message","").strip()
    if not user_msg:
        return jsonify({"error": "msg不可以是空着的(￢︿￢☆)"}),400

    chat_history.append({"role": "user","msg": user_msg})

    #保留最大历史
    MAX_HISTORY = 8
    recent_history = chat_history[-MAX_HISTORY:]
    #拼接并发送给模型（（震惊！！）
    messages = [
        {"rloe": "system","content": SYSTEM_PROMPT},
        *recent_history,
    ]

    payload = {
        "model": "openai/gpt-5-mini",#先用便宜点的，
        "messages": messages
    }

    try :
        resp = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=HEADERS,
            json=payload,
            timeout=30
        )
        resp.raise_for_status()
    except requests.RequestException as e :
        return jsonify({"error":f"通信出问题了(T_T)：{e}"}),500
    data = resp.json()
    #返回数据中提取内容
    reply = data["choices"][0]["message"]["content"]
    #加入历史
    chat_history.append({"role": "assistant","content": reply})

    return jsonify({"reply":reply})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

