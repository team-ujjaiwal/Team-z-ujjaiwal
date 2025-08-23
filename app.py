from flask import Flask, request, jsonify
import requests
from Leaderboard_pb2 import Leaderboard
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)

# Region credentials
CREDENTIALS = {
    "IND": {
        "uid": "3959793024",
        "password": "CD265B729E2C2FA1882AD14579BA602738670D69B4438C127C31AE08FB9D7C17",
        "base_url": "https://client.ind.freefiremobile.com"
    },
    "SG": {
        "uid": "3943739516",
        "password": "BFA0A0D9DF6D4EE1AA92354746475A429D775BCA4D8DD822ECBC6D0BF7B51886",
        "base_url": "https://clientbp.ggblueshark.com"
    },
    # Add more regions if needed
}

# JWT generate URL
JWT_URL = "https://team-ujjaiwal-jwt.vercel.app/token"

# API Key
API_KEY = "1yearskeysforujjaiwal"


def get_jwt(uid, password):
    try:
        params = {'uid': uid, 'password': password}
        response = requests.get(JWT_URL, params=params)
        if response.status_code == 200:
            jwt_data = response.json()
            return jwt_data.get("token")
        return None
    except Exception as e:
        print(f"Error fetching JWT: {e}")
        return None


@app.route('/leaderboard_info', methods=['GET'])
def leaderboard_info():
    region = request.args.get('region', 'IND').upper()
    rank_type = request.args.get('rank', 'br').lower()  # "br" or "cs"
    key = request.args.get('key')

    if key != API_KEY:
        return jsonify({"error": "Invalid API key"}), 401

    creds = CREDENTIALS.get(region)
    if not creds:
        return jsonify({"error": f"Unsupported region '{region}'"}), 400

    jwt_token = get_jwt(creds["uid"], creds["password"])
    if not jwt_token:
        return jsonify({"error": "Failed to generate JWT"}), 500

    headers = {
        'X-Unity-Version': '2018.4.11f1',
        'ReleaseVersion': 'OB50',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Authorization': f'Bearer {jwt_token}',
        'User-Agent': 'Dalvik/2.1.0 (Linux; U; Android 7.1.2; ASUS_Z01QD Build/QKQ1.190825.002)',
        'Host': creds["base_url"].split("//")[1],
        'Connection': 'Keep-Alive',
        'Accept-Encoding': 'gzip'
    }

    # 🎯 Mode ke hisaab se endpoint decide karo
    if rank_type == "cs":
        url = creds["base_url"] + "/GetCsRankLeaderboardInfo"
    else:
        url = creds["base_url"] + "/GetBattleRoyaleRankLeaderboardInfo"

    try:
        response = requests.post(url, headers=headers, data=b"", verify=False)
    except Exception as e:
        return jsonify({"error": f"Request error: {str(e)}"}), 500

    if response.status_code == 200 and response.content:
        leaderboard = Leaderboard()
        leaderboard.ParseFromString(response.content)

        result = {
            "Credit": "@IndTeamApis",
            "developer": "@Ujjaiwal",
            "mode": rank_type.upper(),
            "entries": []
        }

        for entry in leaderboard.entries:
            result["entries"].append({
                "uid": entry.uid,
                "nickname": entry.player_info.data.nickname,
                "level": entry.player_info.data.level,
                "rank": entry.player_info.data.ranking,
                "score": entry.player_info.score,
                "region": entry.player_info.data.region,
                "tier": entry.player_info.data.tier,
                "lastLogin": entry.player_info.data.last_login
            })

        return jsonify(result)
    else:
        return jsonify({"error": "Failed to fetch leaderboard"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)