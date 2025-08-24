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
        if response.status_code == 200:
            return response.json().get("token")
        else:
            logger.error(f"JWT API returned status {response.status_code}: {response.text}")
    except Exception as e:
        logger.error(f"Error fetching JWT: {e}")
    return None

def parse_protobuf_response(response_content, proto_class):
    """Try multiple methods to parse protobuf response"""
    try:
        # Method 1: Direct parsing
        proto_obj = proto_class()
        proto_obj.ParseFromString(response_content)
        return proto_obj
    except Exception as e1:
        logger.warning(f"Direct protobuf parsing failed: {e1}")
        
        try:
            # Method 2: Try to handle potential length prefix
            # Protobuf messages are sometimes length-prefixed
            if len(response_content) > 1:
                # Try to find the start of the protobuf message
                # Look for common protobuf field markers
                for i in range(min(10, len(response_content))):
                    try:
                        proto_obj = proto_class()
                        proto_obj.ParseFromString(response_content[i:])
                        return proto_obj
                    except:
                        continue
        except Exception as e2:
            logger.warning(f"Length-prefix parsing failed: {e2}")
    
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

    # Prepare request data based on rank type
    request_data = f"type={rank_type.upper()}&area_id=0".encode('utf-8')
    
    try:
        logger.debug(f"Requesting leaderboard from {url} with data: {request_data}")
        response = requests.post(url, headers=headers, data=request_data, verify=False, timeout=15)
        logger.debug(f"Response status: {response.status_code}, length: {len(response.content)}")
        
    except Exception as e:
        logger.error(f"Request error: {str(e)}")
        return jsonify({"error": f"Request error: {str(e)}"}), 500

    if response.status_code == 200 and response.content:
        leaderboard = parse_protobuf_response(response.content, Leaderboard)
        
        if not leaderboard:
            # Try to debug what we received
            content_start = response.content[:100].hex() if len(response.content) > 0 else "EMPTY"
            logger.error(f"Failed to parse protobuf response. Content start: {content_start}")
            return jsonify({
                "error": "Failed to parse leaderboard data",
                "content_length": len(response.content),
                "content_start_hex": content_start,
                "status": response.status_code
            }), 500

        result = {
            "Credit": "@IndTeamApis",
            "developer": "@Ujjaiwal",
            "mode": "BR" if rank_type == "br" else "CS",
            "total_entries": len(leaderboard.entries),
            "entries": []
        }

        # Sirf top 100
        for entry in leaderboard.entries[:100]:
            entry_data = {
                "uid": entry.uid,
                "score": entry.player_info.score,
            }
            
            # Add player info if available
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

    return jsonify({
        "error": "Failed to fetch leaderboard", 
        "status": response.status_code,
        "response_text": response.text[:200] if response.text else "No text response"
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

    # Prepare request data
    request_data = "area_id=0".encode('utf-8')
    
    try:
        logger.debug(f"Requesting clan leaderboard from {url} with data: {request_data}")
        response = requests.post(url, headers=headers, data=request_data, verify=False, timeout=15)
        logger.debug(f"Response status: {response.status_code}, length: {len(response.content)}")
        
    except Exception as e:
        logger.error(f"Request error: {str(e)}")
        return jsonify({"error": f"Request error: {str(e)}"}), 500

    if response.status_code == 200 and response.content:
        clan_board = parse_protobuf_response(response.content, GetClanAreaLeaderboardInfo)
        
        if not clan_board:
            # Try to debug what we received
            content_start = response.content[:100].hex() if len(response.content) > 0 else "EMPTY"
            logger.error(f"Failed to parse protobuf response. Content start: {content_start}")
            return jsonify({
                "error": "Failed to parse clan leaderboard data",
                "content_length": len(response.content),
                "content_start_hex": content_start,
                "status": response.status_code
            }), 500

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
            
            # Add timestamp if available
            if hasattr(entry.leaderboard_info, 'timestamp'):
                entry_data["timestamp"] = entry.leaderboard_info.timestamp
            
            result["entries"].append(entry_data)

        return jsonify(result)

    return jsonify({
        "error": "Failed to fetch clan leaderboard", 
        "status": response.status_code,
        "response_text": response.text[:200] if response.text else "No text response"
    }), 500


@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy", "message": "Server is running"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)