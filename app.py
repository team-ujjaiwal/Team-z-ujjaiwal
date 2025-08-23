from flask import Flask, request, jsonify
import requests
from Leaderboard_pb2 import Leaderboard
from GetClanAreaLeaderboardInfo_pb2 import GetClanAreaLeaderboardInfo
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)

# ================== REGION CONFIG ==================
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
}

# JWT generate URL
JWT_URL = "https://team-ujjaiwal-jwt.vercel.app/token"

# API Key
API_KEY = "1yearskeysforujjaiwal"

# ================== JWT FUNCTION ==================
def get_jwt(uid, password):
    try:
        params = {'uid': uid, 'password': password}
        response = requests.get(JWT_URL, params=params)
        if response.status_code == 200:
            return response.json().get("token")
    except Exception as e:
        print(f"Error fetching JWT: {e}")
    return None


# ================== PLAYER LEADERBOARD (BR/CS) ==================
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

    # Select endpoint based on rank
    if rank_type == "cs":
        url = creds["base_url"] + "/GetClashSquadLeaderboardInfo"
    else:
        url = creds["base_url"] + "/GetBattleRoyaleLeaderboardInfo"

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

    try:
        response = requests.post(url, headers=headers, data=b"", verify=False)
    except Exception as e:
        return jsonify({"error": f"Request error: {str(e)}"}), 500

    if response.status_code == 200 and response.content:
        leaderboard = Leaderboard()
        try:
            leaderboard.ParseFromString(response.content)
        except Exception as e:
            return jsonify({"error": f"Protobuf parse error: {str(e)}"}), 500

        result = {
            "Credit": "@IndTeamApis",
            "developer": "@Ujjaiwal",
            "mode": rank_type.upper(),
            "entries": []
        }

        for entry in leaderboard.entries[:100]:  # Only top 100
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

    return jsonify({"error": "Failed to fetch leaderboard", "status": response.status_code}), 500


# ================== CLAN LEADERBOARD ==================
@app.route('/clan_leaderboard_info', methods=['GET'])
def clan_leaderboard_info():
    region = request.args.get('region', 'IND').upper()
    key = request.args.get('key')

    if key != API_KEY:
        return jsonify({"error": "Invalid API key"}), 401

    creds = CREDENTIALS.get(region)
    if not creds:
        return jsonify({"error": f"Unsupported region '{region}'"}), 400

    jwt_token = get_jwt(creds["uid"], creds["password"])
    if not jwt_token:
        return jsonify({"error": "Failed to generate JWT"}), 500

    url = creds["base_url"] + "/GetClanAreaLeaderboardInfo"

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

    try:
        response = requests.post(url, headers=headers, data=b"", verify=False)
    except Exception as e:
        return jsonify({"error": f"Request error: {str(e)}"}), 500

    if response.status_code == 200 and response.content:
        clan_board = GetClanAreaLeaderboardInfo()
        try:
            clan_board.ParseFromString(response.content)
        except Exception as e:
            return jsonify({"error": f"Protobuf parse error: {str(e)}"}), 500

        result = {
            "Credit": "@IndTeamApis",
            "developer": "@Ujjaiwal",
            "mode": "CLAN",
            "entries": []
        }

        for entry in clan_board.entries[:100]:  # Only top 100
            result["entries"].append({
                "areaId": entry.area_id,
                "rank": entry.leaderboard_info.rank,
                "timestamp": entry.leaderboard_info.timestamp if entry.leaderboard_info.HasField("timestamp") else None
            })

        return jsonify(result)

    return jsonify({"error": "Failed to fetch clan leaderboard", "status": response.status_code}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)