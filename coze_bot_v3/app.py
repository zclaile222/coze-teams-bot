# ✅ Coze 接入 Microsoft Teams 的完整中间层服务模板（Python Flask 版本）

# 功能：
# - 接收来自 Azure Bot Framework（即 Teams）的消息
# - 向 Coze API 请求 Bot 回答（JWT 模式，v3/chat 接口）
# - 将结果返回给 Teams 用户

from flask import Flask, request, jsonify
import requests
import os
import time
import jwt

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
        "sub": COZE_CLIENT_ID,
        "aud": "https://api.coze.cn/open/oauth/token",
        "iat": now,
        "exp": now + 3600
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
    response = requests.post("https://api.coze.cn/open/oauth/token", data={
        "grant_type": "client_credentials",
        "assertion": jwt_token,
    })
    if response.status_code == 200:
        data = response.json()
        access_token_cache["token"] = data["access_token"]
        access_token_cache["expires_at"] = time.time() + data["expires_in"] - 60
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
    except Exception as e:
        reply = f"[错误] {str(e)}"

    return jsonify({
        "type": "message",
        "text": reply
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3978))
    app.run(host="0.0.0.0", port=port)
