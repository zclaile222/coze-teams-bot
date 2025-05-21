# ✅ Coze 接入 Microsoft Teams 的完整中间层服务模板（Python Flask 版本）

# 功能：
# - 接收来自 Azure Bot Framework（即 Teams）的消息
# - 向 Coze API 请求 Bot 回答（JWT 模式，v3/chat 接口）
# - 将结果打印在日志中（Teams 侧返回空响应，避免格式不符）

from flask import Flask, request
import requests
import os
import time
import jwt
import uuid

app = Flask(__name__)

# === 配置参数 ===
COZE_CLIENT_ID = os.getenv("COZE_CLIENT_ID")           # OAuth App 中的 client_id
COZE_BOT_ID = os.getenv("COZE_BOT_ID")                 # Bot 控制台 URL 提取的 ID
COZE_PUBLIC_KEY_ID = os.getenv("COZE_PUBLIC_KEY_ID")   # 创建 OAuth 应用生成的 key_id
COZE_PRIVATE_KEY = os.getenv("COZE_PRIVATE_KEY")       # PEM 格式私钥字符串（建议使用多行字符串保存在环境变量中）

access_token_cache = {
    "token": None,
    "expires_at": 0
}

# === JWT 生成函数 ===
def create_jwt():
    now = int(time.time())
    payload = {
        "iss": COZE_CLIENT_ID,
        "aud": "api.coze.cn",
        "iat": now,
        "exp": now + 3600,
        "jti": str(uuid.uuid4())
    }
    headers = {
        "kid": COZE_PUBLIC_KEY_ID,
        "alg": "RS256",
        "typ": "JWT"
    }
    return jwt.encode(payload, COZE_PRIVATE_KEY, algorithm="RS256", headers=headers)

# === 获取 Access Token ===
def get_access_token():
    if access_token_cache["token"] and access_token_cache["expires_at"] > time.time():
        return access_token_cache["token"]

    jwt_token = create_jwt()
    headers = {
        "Authorization": f"Bearer {jwt_token}",
        "Content-Type": "application/json"
    }
    body = {
        "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
        "duration_seconds": 86399
    }
    response = requests.post("https://api.coze.cn/api/permission/oauth2/token", json=body, headers=headers)
    if response.status_code == 200:
        data = response.json()
        access_token_cache["token"] = data["access_token"]
        access_token_cache["expires_at"] = time.time() + (data.get("expires_in", 900)) - 60
        return data["access_token"]
    else:
        raise Exception(f"无法获取 Access Token: {response.text}")

# === 处理来自 Teams 的消息 ===
@app.route("/api/messages", methods=["POST"])
def messages():
    data = request.get_json()
    user_text = data.get("text", "")

    try:
        token = get_access_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        payload = {
            "bot_id": COZE_BOT_ID,
            "user_id": "user_from_teams",
            "stream": False,
            "auto_save_history": True,
            "additional_messages": [
                {
                    "role": "user",
                    "content": user_text,
                    "content_type": "text"
                }
            ]
        }
        r = requests.post("https://api.coze.cn/v3/chat", json=payload, headers=headers)
        r.raise_for_status()
        reply = r.json().get("choices", [{}])[0].get("message", {}).get("content", "(无响应)")
        print(f"[Coze 回复] {reply}")
    except Exception as e:
        print(f"[错误] {str(e)}")

    return "", 200  # 返回空响应，避免 Bot Framework 报错

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3978))
    app.run(host="0.0.0.0", port=port)
