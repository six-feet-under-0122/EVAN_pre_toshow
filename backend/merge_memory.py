import sqlite3
import os
from dotenv import load_dotenv
from rag_core import save_memory

# 读取 API_KEY
load_dotenv()
API_KEY = os.getenv("API_KEY")


def migrate():
    print("开始唤醒过去的记忆...")
    # 1. 连上你的老数据库
    conn = sqlite3.connect('evan.db')
    c = conn.cursor()

    # 2. 把用户说过的话全都找出来
    c.execute("SELECT session_id, content FROM chat_history WHERE role = 'user'")
    rows = c.fetchall()
    conn.close()

    print(f"一共找到了 {len(rows)} 条你过去的话！")

    # 3. 一条条变成向量存进新大脑
    count = 0
    for session_id, content in rows:
        # 如果是包含图片的复杂JSON格式，我们先跳过，只存纯文本
        if content.startswith('[') and '{"type":' in content:
            continue

        try:
            save_memory(session_id, content, API_KEY)
            count += 1
            print(f"进度: {count}/{len(rows)}")
        except Exception as e:
            print(f"跳过了一条保存失败的记忆: {e}")

    print("✨ 所有过去的记忆都已经成功注入长期记忆库！")


if __name__ == "__main__":
    migrate()