import os
import requests
import chromadb
import uuid
import hashlib
import json

chroma_client = chromadb.PersistentClient(path="./memory_db")
# 我们可以只用一个 collection，通过 metadata 里的 type 来区分记忆类型
collection = chroma_client.get_or_create_collection(name="user_memories")


def get_embedding(text, api_key):
    url = "https://api.chatanywhere.tech/v1/embeddings"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"model": "text-embedding-3-small", "input": text}
    result = requests.post(url, headers=headers, json=payload).json()
    return result['data'][0]['embedding']


def is_valid_chat(text):
    """过滤掉纯代码和太长的文本，留下的存为【流水账记忆】"""
    if not text or len(text) < 2 or len(text) > 400:
        return False
    if "```" in text or "<template>" in text or "{" in text:  # 粗略判断代码
        return False
    return True


def extract_core_memory(text, api_key):
    """
    【关键魔法】让 LLM 帮忙判断这句话里有没有核心信息（喜好、事实、设定）
    """
    url = "https://api.chatanywhere.tech/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    prompt = f"""
    请分析以下用户的发言，提取出重要的、长期有效的事实、用户偏好、情感状态或重要事件。
    如果发言只是普通的寒暄（如“你好”、“在吗”）、或者无关紧要的闲聊、或者是代码段，请直接回复严格的四个大写字母：NONE。
    如果有重要事实，请用第一人称（用户视角）简短总结，例如：“我喜欢猫”、“我正在开发一个桌宠程序”、“我今天心情很低落”。
    用户发言：{text}
    """

    payload = {
        "model": "gpt-4o-mini",  # 用最便宜快的模型做信息提取
        "messages": [{"role": "user", "content": prompt}]
    }

    try:
        response = requests.post(url, headers=headers, json=payload).json()
        result = response["choices"][0]["message"]["content"].strip()
        if result == "NONE" or "NONE" in result:
            return None
        return result
    except Exception as e:
        print("提取核心记忆失败:", e)
        return None


def save_memory(session_id, text, api_key, source="chat"):
    """
    双轨制保存：
    1. 判断是否存为普通聊天
    2. 尝试提取并存为核心事实
    """
    # 1. 尝试提取核心记忆 (Core Memory)
    core_fact = extract_core_memory(text, api_key)
    if core_fact:
        core_hash = hashlib.md5(core_fact.encode('utf-8')).hexdigest()
        # 🌟 变化在这里：ID 拼接加上了 source，metadata 也加上了 source
        collection.upsert(
            ids=[f"core_{source}_{session_id}_{core_hash}"],
            embeddings=[get_embedding(core_fact, api_key)],
            documents=[core_fact],
            metadatas=[{"session_id": session_id, "type": "core", "source": source}]
        )
        print(f"🌟 记录核心事实 [{source}]: {core_fact}")

    # 2. 保存普通流水账 (Chat Memory)
    if is_valid_chat(text):
        chat_hash = hashlib.md5(text.encode('utf-8')).hexdigest()
        # 🌟 变化在这里：ID 拼接加上了 source，metadata 也加上了 source
        collection.upsert(
            ids=[f"chat_{source}_{session_id}_{chat_hash}"],
            embeddings=[get_embedding(text, api_key)],
            documents=[text],
            metadatas=[{"session_id": session_id, "type": "chat", "source": source}]
        )
        print(f"📝 记录日常聊天 [{source}]: {text[:15]}...")


# 搜索的时候，如果我们想要区分，也可以加上 source 的过滤（目前你可以先不限制，全库搜索）
def search_memory(session_id, query_text, api_key, limit_source=None):
    """
    混合检索：分别从“核心记忆”和“普通聊天”中捞取信息，然后合并
    """
    query_embedding = get_embedding(query_text, api_key)

    # 构建基础的过滤条件
    where_core = {"type": "core"}
    where_chat = {"type": "chat"}

    # 如果指定了只搜书单或只搜聊天，就加上过滤条件
    if limit_source:
        where_core = {"$and": [{"type": "core"}, {"source": limit_source}]}
        where_chat = {"$and": [{"type": "chat"}, {"source": limit_source}]}

    # 1. 捞取最相关的 2 条核心事实
    core_results = collection.query(
        query_embeddings=[query_embedding],
        n_results=2,
        where=where_core
    )
    core_docs = core_results['documents'][0] if core_results['documents'] else []

    # 2. 捞取最相关的 2 条日常聊天
    chat_results = collection.query(
        query_embeddings=[query_embedding],
        n_results=2,
        where=where_chat
    )
    chat_docs = chat_results['documents'][0] if chat_results['documents'] else []

    final_memories = [f"[核心事实] {doc}" for doc in core_docs] + \
                     [f"[历史对话] {doc}" for doc in chat_docs]

    return final_memories