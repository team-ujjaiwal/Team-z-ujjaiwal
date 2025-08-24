from flask import Flask, request, jsonify
import requests
from Leaderboard_pb2 import Leaderboard
from GetClanAreaLeaderboardInfo_pb2 import GetClanAreaLeaderboardInfo
import urllib3
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

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
        response = requests.get(JWT_URL, params=params, timeout=10)
        logger.debug(f"JWT Response: {response.status_code}, {response.text}")
        if response.status_code == 200:
            token = response.json().get("token")
            logger.debug(f"Generated JWT token: {token}")
            return token
        else:
            logger.error(f"JWT API returned status {response.status_code}: {response.text}")
    except Exception as e:
        logger.error(f"Error fetching JWT: {e}")
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

    url = creds["base_url"] + "/Leaderboard"
    logger.debug(f"Target URL: {url}")

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

    # Try different request formats
    request_data_options = [
        f"type={rank_type.upper()}&area_id=0",
        f"area_id=0&type={rank_type.upper()}",
        f"type={rank_type.upper()}",
        "area_id=0",
        ""
    ]
    
    for i, request_data in enumerate(request_data_options):
        try:
            logger.debug(f"Attempt {i+1}: Trying request data: '{request_data}'")
            response = requests.post(url, headers=headers, data=request_data, verify=False, timeout=15)
            logger.debug(f"Response status: {response.status_code}, content length: {len(response.content)}")
            
            if response.status_code == 200:
                if len(response.content) > 0:
                    try:
                        leaderboard = Leaderboard()
                        leaderboard.ParseFromString(response.content)
                        
                        result = {
                            "Credit": "@IndTeamApis",
                            "developer": "@Ujjaiwal",
                            "mode": "BR" if rank_type == "br" else "CS",
                            "total_entries": len(leaderboard.entries),
                            "entries": []
                        }

                        for entry in leaderboard.entries[:100]:
                            entry_data = {
                                "uid": entry.uid,
                                "score": entry.player_info.score,
                            }
                            
                            if hasattr(entry.player_info, 'data') and entry.player_info.data:
                                entry_data.update({
                                    "nickname": entry.player_info.data.nickname,
                                    "level": entry.player_info.data.level,
                                    "rank": entry.player_info.data.ranking,
                                    "region": entry.player_info.data.region,
                                    "tier": entry.player_info.data.tier,
                                    "lastLogin": entry.player_info.data.last_login
                                })
                            
                            result["entries"].append(entry_data)

                        return jsonify(result)
                        
                    except Exception as parse_error:
                        logger.warning(f"Parse failed: {parse_error}")
                        # Try to see what we got
                        hex_data = response.content.hex()[:100] if response.content else "EMPTY"
                        logger.debug(f"Raw response (first 50 bytes hex): {hex_data}")
                        continue
                else:
                    logger.debug("Empty response content received")
            else:
                logger.debug(f"Non-200 status: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Request error: {str(e)}")
            continue

    return jsonify({
        "error": "Failed to fetch leaderboard after trying all request formats",
        "debug_info": {
            "region": region,
            "jwt_token_generated": bool(jwt_token),
            "target_url": url
        },
        "status": 500
    }), 500


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
    logger.debug(f"Clan Target URL: {url}")

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

    # Try different request formats
    request_data_options = [
        "area_id=0",
        "clan_id=0",
        "area_id=0&clan_id=0",
        ""
    ]
    
    for i, request_data in enumerate(request_data_options):
        try:
            logger.debug(f"Clan Attempt {i+1}: Trying request data: '{request_data}'")
            response = requests.post(url, headers=headers, data=request_data, verify=False, timeout=15)
            logger.debug(f"Clan Response status: {response.status_code}, content length: {len(response.content)}")
            
            if response.status_code == 200:
                if len(response.content) > 0:
                    try:
                        clan_board = GetClanAreaLeaderboardInfo()
                        clan_board.ParseFromString(response.content)
                        
                        result = {
                            "Credit": "@IndTeamApis",
                            "developer": "@Ujjaiwal",
                            "mode": "CLAN",
                            "total_entries": len(clan_board.entries),
                            "entries": []
                        }

                        for entry in clan_board.entries[:100]:
                            entry_data = {
                                "areaId": entry.area_id,
                                "rank": entry.leaderboard_info.rank,
                            }
                            
                            if hasattr(entry.leaderboard_info, 'timestamp'):
                                entry_data["timestamp"] = entry.leaderboard_info.timestamp
                            
                            result["entries"].append(entry_data)

                        return jsonify(result)
                        
                    except Exception as parse_error:
                        logger.warning(f"Clan parse failed: {parse_error}")
                        hex_data = response.content.hex()[:100] if response.content else "EMPTY"
                        logger.debug(f"Clan raw response (first 50 bytes hex): {hex_data}")
                        continue
                else:
                    logger.debug("Empty clan response content received")
            else:
                logger.debug(f"Clan non-200 status: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Clan request error: {str(e)}")
            continue

    return jsonify({
        "error": "Failed to fetch clan leaderboard after trying all request formats",
        "debug_info": {
            "region": region,
            "jwt_token_generated": bool(jwt_token),
            "target_url": url
        },
        "status": 500
    }), 500


@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy", "message": "Server is running"})


@app.route('/debug_jwt', methods=['GET'])
def debug_jwt():
    region = request.args.get('region', 'IND').upper()
    creds = CREDENTIALS.get(region)
    if not creds:
        return jsonify({"error": f"Unsupported region '{region}'"}), 400
    
    jwt_token = get_jwt(creds["uid"], creds["password"])
    return jsonify({
        "region": region,
        "uid": creds["uid"],
        "jwt_token": jwt_token,
        "token_generated": bool(jwt_token)
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)