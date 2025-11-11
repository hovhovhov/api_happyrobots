"""
Carrier Sales API - HappyRobot Integration
Flask API for carrier verification and load management
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import os
from datetime import datetime
import requests
from typing import Dict, List

app = Flask(__name__)
CORS(app)

# ==================== CONFIG ====================
API_KEY = os.environ.get('API_KEY', 'your-secret-api-key-here')
FMCSA_API_KEY = os.environ.get('FMCSA_API_KEY', '')  # put your FMCSA key in env

# Files
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOADS_FILE = os.path.join(BASE_DIR, 'loads.json')
CALLS_DB_FILE = os.path.join(BASE_DIR, 'calls_database.json')

# ==================== UTILS ====================
def load_json_file(filename: str) -> List[Dict]:
    try:
        with open(filename, 'r') as f:
            data = json.load(f)
            print(f"[LOAD] {filename} -> {len(data)} records")
            return data
    except FileNotFoundError:
        print(f"[LOAD] {filename} not found -> returning []")
        return []
    except json.JSONDecodeError as e:
        print(f"[LOAD] {filename} JSON error: {e} -> returning []")
        return []

def save_json_file(filename: str, data: List[Dict]):
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)

def verify_api_key() -> bool:
    return request.headers.get('X-API-Key') == API_KEY

# ==================== ENDPOINTS ====================

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'service': 'Carrier Sales API'
    }), 200

@app.route('/api/verify-carrier', methods=['GET'])
def verify_carrier():
    """
    Verify carrier using FMCSA API (STRICT: verified==True only if FMCSA returns a carrier)
    Query param: mc_number
    """
    if not verify_api_key():
        return jsonify({"error": "Unauthorized"}), 401

    mc_number = (request.args.get("mc_number") or "").strip()
    if not mc_number:
        return jsonify({"success": False, "verified": False, "error": "mc_number required"}), 400

    url = f"https://mobile.fmcsa.dot.gov/qc/services/carriers/{mc_number}"
    params = {"webKey": FMCSA_API_KEY} if FMCSA_API_KEY else {}

    try:
        r = requests.get(url, params=params, timeout=6)
        # best-effort JSON parse
        try:
            data = r.json()
        except ValueError:
            data = {}

        if not isinstance(data, dict):
            data = {}

        content = data.get("content")
        carrier = None

        # FMCSA responses can be dict or list under "content"
        if isinstance(content, dict):
            carrier = content.get("carrier") or content
        elif isinstance(content, list) and content and isinstance(content[0], dict):
            carrier = content[0].get("carrier") or content[0]

        if isinstance(carrier, dict):
            return jsonify({
                "success": True,
                "verified": True,
                "carrier_data": {
                    "mc_number": mc_number,
                    "legal_name": carrier.get("legalName") or carrier.get("name") or "Unknown",
                    "dot_number": carrier.get("dotNumber") or "N/A",
                    "city": carrier.get("phyCity") or "N/A",
                    "state": carrier.get("phyState") or "N/A",
                },
                "message": "Carrier verified via FMCSA"
            }), 200

        # Not found
        return jsonify({
            "success": True,
            "verified": False,
            "carrier_data": None,
            "message": "Carrier not found in FMCSA"
        }), 200

    except Exception as e:
        # Strict: on error we DO NOT verify
        print(f"[ERROR] FMCSA API error: {str(e)}")
        return jsonify({
            "success": True,
            "verified": False,
            "carrier_data": None,
            "message": f"FMCSA API error: {str(e)}"
        }), 200

@app.route('/api/loads', methods=['GET'])
def search_loads():
    """
    Search available loads based on criteria
    Query params: origin|origin_city, origin_state, destination|destination_city, destination_state,
                  equipment_type, commodity, pickup_date
    """
    if not verify_api_key():
        return jsonify({"error": "Unauthorized"}), 401

    def _split_city_state(val: str):
        if ',' in val:
            parts = [p.strip() for p in val.split(',')]
            return (parts[0], parts[1]) if len(parts) == 2 else (parts[0], '')
        return (val, '')

    origin = request.args.get('origin', '')
    destination = request.args.get('destination', '')

    if origin:
        origin_city, origin_state = _split_city_state(origin)
    else:
        origin_city = request.args.get('origin_city', '')
        origin_state = request.args.get('origin_state', '')

    if destination:
        destination_city, destination_state = _split_city_state(destination)
    else:
        destination_city = request.args.get('destination_city', '')
        destination_state = request.args.get('destination_state', '')

    origin_city = origin_city.lower()
    origin_state = origin_state.lower()
    destination_city = destination_city.lower()
    destination_state = destination_state.lower()
    equipment_type = (request.args.get('equipment_type') or '').lower()
    commodity = (request.args.get('commodity') or '').lower()
    pickup_date = request.args.get('pickup_date')  # keep as substring match (ISO)

    all_loads = load_json_file(LOADS_FILE)
    print(f"[DEBUG] Reading {LOADS_FILE} -> {len(all_loads)} loads")

    filtered = []
    for load in all_loads:
        o = (load.get('origin', '') or '').lower()
        d = (load.get('destination', '') or '').lower()
        et = (load.get('equipment_type', '') or '').lower()
        com = (load.get('commodity_type', '') or '').lower()
        if origin_city and origin_city not in o: continue
        if origin_state and origin_state not in o: continue
        if destination_city and destination_city not in d: continue
        if destination_state and destination_state not in d: continue
        if equipment_type and equipment_type not in et: continue
        if commodity and commodity not in com: continue
        if pickup_date:
            if pickup_date not in (load.get('pickup_datetime', '') or ''):
                continue
        filtered.append(load)

    return jsonify({
        'success': True,
        'count': len(filtered),
        'loads': filtered,
        'timestamp': datetime.now().isoformat()
    }), 200

@app.route('/api/loads/<load_id>', methods=['GET'])
def get_load_by_id(load_id):
    if not verify_api_key():
        return jsonify({'error': 'Unauthorized'}), 401
    all_loads = load_json_file(LOADS_FILE)
    for load in all_loads:
        if load.get('load_id') == load_id:
            return jsonify({'success': True, 'load': load, 'timestamp': datetime.now().isoformat()}), 200
    return jsonify({'success': False, 'error': 'Load not found', 'timestamp': datetime.now().isoformat()}), 404

@app.route('/api/call-results', methods=['POST'])
def save_call_results():
    """
    Expected payload:
    {
        'call_id': str,
        'mc_number': str,
        'carrier_name': str,
        'load_id': str,
        'origin': str,
        'destination': str,
        'equipment': str,
        'miles': number,
        'pickup_datetime': str,
        'initial_rate': number,
        'carrier_offer': number|null,
        'agreed_rate': number|null,
        'negotiation_rounds': int,
        'outcome': 'agreed'|'declined'|'no_match',
        'sentiment': 'positive'|'neutral'|'negative',
        'transcript': str,
        'extracted_data': dict
    }
    """
    if not verify_api_key():
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        data = request.get_json(force=True) or {}
        data['timestamp'] = datetime.now().isoformat()
        data['id'] = f"call_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        calls = load_json_file(CALLS_DB_FILE)
        calls.append(data)
        save_json_file(CALLS_DB_FILE, calls)

        return jsonify({
            'success': True,
            'message': 'Call results saved successfully',
            'call_id': data['id'],
            'timestamp': data['timestamp']
        }), 201

    except Exception as e:
        return jsonify({'success': False, 'error': str(e), 'timestamp': datetime.now().isoformat()}), 500

@app.route('/api/analytics', methods=['GET'])
def get_analytics():
    if not verify_api_key():
        return jsonify({'error': 'Unauthorized'}), 401
    try:
        calls = load_json_file(CALLS_DB_FILE)
        if not calls:
            return jsonify({'success': True, 'total_calls': 0, 'message': 'No calls recorded yet'}), 200

        total = len(calls)
        success = sum(1 for c in calls if c.get('outcome') == 'agreed')
        transferred = sum(1 for c in calls if c.get('outcome') == 'transferred')
        sentiments = [c.get('sentiment', 'neutral') for c in calls]
        positive = sentiments.count('positive')
        neutral = sentiments.count('neutral')
        negative = sentiments.count('negative')
        rounds = [c.get('negotiation_rounds', 0) or 0 for c in calls]
        avg_rounds = (sum(rounds)/len(rounds)) if rounds else 0
        rates = [c.get('agreed_rate', 0) or 0 for c in calls]
        avg_rate = (sum(rates)/len(rates)) if rates else 0

        return jsonify({
            'success': True,
            'analytics': {
                'total_calls': total,
                'successful_calls': success,
                'transferred_calls': transferred,
                'conversion_rate': (success / total * 100) if total else 0,
                'sentiment': {
                    'positive': positive,
                    'neutral': neutral,
                    'negative': negative,
                    'positive_rate': (positive / total * 100) if total else 0
                },
                'negotiation': {
                    'avg_rounds': round(avg_rounds, 2),
                    'avg_agreed_rate': round(avg_rate, 2)
                }
            },
            'timestamp': datetime.now().isoformat()
        }), 200

    except Exception as e:
        return jsonify({'success': False, 'error': str(e), 'timestamp': datetime.now().isoformat()}), 500

@app.route('/api/calls', methods=['GET'])
def get_all_calls():
    if not verify_api_key():
        return jsonify({'error': 'Unauthorized'}), 401
    try:
        calls = load_json_file(CALLS_DB_FILE)
        calls.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        limit = request.args.get('limit', type=int)
        if limit:
            calls = calls[:limit]
        return jsonify({'success': True, 'count': len(calls), 'calls': calls, 'timestamp': datetime.now().isoformat()}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e), 'timestamp': datetime.now().isoformat()}), 500

# ==================== ERROR HANDLERS ====================
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found', 'timestamp': datetime.now().isoformat()}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error', 'timestamp': datetime.now().isoformat()}), 500

# ==================== ALIASES ====================
@app.route('/api/save-call-results', methods=['POST'])
def save_call_results_alias():
    return save_call_results()

# ==================== MAIN ====================
if __name__ == '__main__':
    if not os.path.exists(LOADS_FILE):
        save_json_file(LOADS_FILE, [])
    if not os.path.exists(CALLS_DB_FILE):
        save_json_file(CALLS_DB_FILE, [])
    port = int(os.environ.get('PORT', 5160))
    app.run(host='0.0.0.0', port=port, debug=True)
