import requests
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

API_KEY = os.getenv("API_KEY")

headers = {
    "Authorization": f"Bearer {API_KEY}"
}

response = requests.get(
    "https://api.chatanywhere.tech/v1/models",
    headers=headers
)

print(response.json())