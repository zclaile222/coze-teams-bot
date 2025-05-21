from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

COZE_CLIENT_ID = os.getenv("COZE_CLIENT_ID")
COZE_CLIENT_SECRET = os.getenv("COZE_CLIENT_SECRET")
COZE_BOT_ID = os.getenv("COZE_BOT_ID")

coze_access_token = None

def get_coze_token():
    global coze_access_token
    if coze_access_token:
        return coze_access_token

    token_url = "https://api.coze.cn/open/oauth/token"
    payload = {
        "grant_type": "client_credentials",
        "client_id": COZE_CLIENT_ID,
        "client_secret": COZE_CLIENT_SECRET
    }
    response = requests.post(token_url, data=payload)
    if response.status_code == 200:
        coze_access_token = response.json()['access_token']
        return coze_access_token
    else:
        raise Exception("无法获取 Coze Access Token")

@app.route("/api/messages", methods=["POST"])
def messages():
    data = request.get_json()
    user_text = data.get("text", "")

    token = get_coze_token()
    coze_url = "https://api.coze.cn/open/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    payload = {
        "bot_id": COZE_BOT_ID,
        "user": "user_from_teams",
        "query": user_text
    }

    try:
        r = requests.post(coze_url, json=payload, headers=headers)
        r.raise_for_status()
        reply = r.json().get("messages", [{}])[0].get("content", "(无响应)")
    except Exception as e:
        reply = f"[错误] 无法连接 Coze：{str(e)}"

    return jsonify({
        "type": "message",
        "text": reply
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3978))
    app.run(host="0.0.0.0", port=port)
