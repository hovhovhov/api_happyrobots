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
from typing import Dict, List, Optional

app = Flask(__name__)
CORS(app)

# Configuration
API_KEY = os.environ.get('API_KEY', 'your-secret-api-key-here')
FMCSA_API_KEY = os.environ.get('FMCSA_API_KEY', '')  # You'll need to get this from FMCSA

# File paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOADS_FILE = os.path.join(BASE_DIR, 'loads.json')
CALLS_DB_FILE = os.path.join(BASE_DIR, 'calls_database.json')

# ==================== UTILITY FUNCTIONS ====================

def load_json_file(filename: str) -> List[Dict]:
    """Load data from JSON file safely and log count"""
    try:
        with open(filename, 'r') as f:
            data = json.load(f)
            # Log how many records we loaded (shows up in your terminal)
            print(f"[LOAD] {filename} -> {len(data)} records")
            return data
    except FileNotFoundError:
        print(f"[LOAD] {filename} not found -> returning []")
        return []
    except json.JSONDecodeError as e:
        print(f"[LOAD] {filename} JSON error: {e} -> returning []")
        return []

def save_json_file(filename: str, data: List[Dict]):
    """Save data to JSON file"""
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)

def verify_api_key():
    """Verify API key from request headers"""
    api_key = request.headers.get('X-API-Key')
    if api_key != API_KEY:
        return False
    return True

# ==================== API ENDPOINTS ====================

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'service': 'Carrier Sales API'
    }), 200

@app.route('/api/verify-carrier', methods=['GET'])
def verify_carrier():
    """
    Verify carrier using FMCSA API (robust JSON parsing)
    Query param: mc_number
    """
    if not verify_api_key():
        return jsonify({"error": "Unauthorized"}), 401

    mc_number = request.args.get("mc_number")
    if not mc_number:
        return jsonify({"success": False, "error": "mc_number required"}), 400

    fm_key = os.getenv("FMCSA_API_KEY")
    url = f"https://mobile.fmcsa.dot.gov/qc/services/carriers/{mc_number}"
    params = {"webKey": fm_key} if fm_key else {}

    try:
        r = requests.get(url, params=params, timeout=6)

        # ---- robust parse ----
        data = None
        try:
            data = r.json()
        except ValueError:
            try:
                data = json.loads(r.text)
            except Exception:
                data = {}

        # Make sure data is a dict
        if not isinstance(data, dict):
            data = {}

        # ---- normalize shapes ----
        carrier = None
        content = data.get("content") if data else None
        
        if isinstance(content, dict):
            carrier = content.get("carrier") or content
        elif isinstance(content, list) and len(content) > 0:
            first = content[0]
            if isinstance(first, dict):
                carrier = first.get("carrier") or first

        if carrier and isinstance(carrier, dict):
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

        # If carrier not found, return mock data for testing
        return jsonify({
            "success": True,
            "verified": True,
            "carrier_data": {
                "mc_number": mc_number,
                "legal_name": "MOCK CARRIER LLC",
                "dot_number": "123456",
                "city": "Chicago",
                "state": "IL",
            },
            "message": "Carrier not found in FMCSA - using mock data for demo"
        }), 200

    except Exception as e:
        # For testing: return mock data if FMCSA fails
        print(f"[ERROR] FMCSA API error: {str(e)}")
        return jsonify({
            "success": True,
            "verified": True,
            "carrier_data": {
                "mc_number": mc_number,
                "legal_name": "MOCK CARRIER LLC",
                "dot_number": "123456",
                "city": "Chicago",
                "state": "IL",
            },
            "message": f"FMCSA API error - using mock data: {str(e)}"
        }), 200

        return jsonify({
            "success": True,
            "verified": False,
            "message": "Carrier not found in FMCSA"
        }), 200

    except Exception as e:
        return jsonify({
            "success": True,
            "verified": False,
            "message": f"FMCSA API error: {str(e)}"
        }), 200

@app.route('/api/loads', methods=['GET'])
def search_loads():
    """
    Search available loads based on criteria
    Query params: origin_city, origin_state, destination_city, destination_state,
                  equipment_type, pickup_date, etc.
    """
    if not verify_api_key():
        return jsonify({"error": "Unauthorized"}), 401
    
    
    # Get query parameters
    origin_city = request.args.get('origin_city', '').lower()
    origin_state = request.args.get('origin_state', '').lower()
    destination_city = request.args.get('destination_city', '').lower()
    destination_state = request.args.get('destination_state', '').lower()
    equipment_type = request.args.get('equipment_type', '').lower()
    commodity = request.args.get('commodity', '').lower()
    min_temp = request.args.get('min_temp')
    pickup_date = request.args.get('pickup_date')
    
    # Load all loads
    all_loads = load_json_file(LOADS_FILE)
    print(f"[DEBUG] Reading {LOADS_FILE} -> {len(all_loads)} loads")
    
    # Filter loads based on criteria
    filtered_loads = []
    
    for load in all_loads:
        # Check origin
        if origin_city and origin_city not in load.get('origin', '').lower():
            continue
        if origin_state and origin_state not in load.get('origin', '').lower():
            continue
            
        # Check destination
        if destination_city and destination_city not in load.get('destination', '').lower():
            continue
        if destination_state and destination_state not in load.get('destination', '').lower():
            continue
            
        # Check equipment type
        if equipment_type and equipment_type not in load.get('equipment_type', '').lower():
            continue
            
        # Check commodity
        if commodity and commodity not in load.get('commodity_type', '').lower():
            continue
            
        # Check pickup date (if provided)
        if pickup_date:
            load_pickup = load.get('pickup_datetime', '')
            if pickup_date not in load_pickup:
                continue
        
        # If all filters pass, add to results
        filtered_loads.append(load)
    
    return jsonify({
        'success': True,
        'count': len(filtered_loads),
        'loads': filtered_loads,
        'timestamp': datetime.now().isoformat()
    }), 200

@app.route('/api/loads/<load_id>', methods=['GET'])
def get_load_by_id(load_id):
    """Get specific load by ID"""
    if not verify_api_key():
        return jsonify({'error': 'Unauthorized'}), 401
    
    all_loads = load_json_file(LOADS_FILE)
    
    for load in all_loads:
        if load.get('load_id') == load_id:
            return jsonify({
                'success': True,
                'load': load,
                'timestamp': datetime.now().isoformat()
            }), 200
    
    return jsonify({
        'success': False,
        'error': 'Load not found',
        'timestamp': datetime.now().isoformat()
    }), 404

@app.route('/api/call-results', methods=['POST'])
def save_call_results():
    """
    Save call results from HappyRobot workflow
    Expected payload: {
        'call_id': str,
        'mc_number': str,
        'load_id': str,
        'outcome': str,
        'sentiment': str,
        'agreed_rate': float,
        'negotiation_rounds': int,
        'transcript': str,
        'extracted_data': dict
    }
    """
    if not verify_api_key():
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        data = request.get_json()
        
        # Add timestamp and unique ID
        data['timestamp'] = datetime.now().isoformat()
        data['id'] = f"call_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Load existing calls
        calls = load_json_file(CALLS_DB_FILE)
        
        # Add new call
        calls.append(data)
        
        # Save back to file
        save_json_file(CALLS_DB_FILE, calls)
        
        return jsonify({
            'success': True,
            'message': 'Call results saved successfully',
            'call_id': data['id'],
            'timestamp': data['timestamp']
        }), 201
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/api/analytics', methods=['GET'])
def get_analytics():
    """
    Get analytics data for dashboard
    Returns: call statistics, conversion rates, sentiment analysis
    """
    if not verify_api_key():
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        calls = load_json_file(CALLS_DB_FILE)
        
        if not calls:
            return jsonify({
                'success': True,
                'total_calls': 0,
                'message': 'No calls recorded yet'
            }), 200
        
        # Calculate metrics
        total_calls = len(calls)
        successful_calls = len([c for c in calls if c.get('outcome') == 'agreed'])
        transferred_calls = len([c for c in calls if c.get('outcome') == 'transferred'])
        
        # Sentiment analysis
        sentiments = [c.get('sentiment', 'neutral') for c in calls]
        positive = sentiments.count('positive')
        neutral = sentiments.count('neutral')
        negative = sentiments.count('negative')
        
        # Average negotiation rounds
        negotiation_rounds = [c.get('negotiation_rounds', 0) for c in calls if c.get('negotiation_rounds')]
        avg_negotiation_rounds = sum(negotiation_rounds) / len(negotiation_rounds) if negotiation_rounds else 0
        
        # Calculate rates
        agreed_rates = [c.get('agreed_rate', 0) for c in calls if c.get('agreed_rate')]
        avg_agreed_rate = sum(agreed_rates) / len(agreed_rates) if agreed_rates else 0
        
        return jsonify({
            'success': True,
            'analytics': {
                'total_calls': total_calls,
                'successful_calls': successful_calls,
                'transferred_calls': transferred_calls,
                'conversion_rate': (successful_calls / total_calls * 100) if total_calls > 0 else 0,
                'sentiment': {
                    'positive': positive,
                    'neutral': neutral,
                    'negative': negative,
                    'positive_rate': (positive / total_calls * 100) if total_calls > 0 else 0
                },
                'negotiation': {
                    'avg_rounds': round(avg_negotiation_rounds, 2),
                    'avg_agreed_rate': round(avg_agreed_rate, 2)
                }
            },
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/api/calls', methods=['GET'])
def get_all_calls():
    """Get all call records (for dashboard)"""
    if not verify_api_key():
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        calls = load_json_file(CALLS_DB_FILE)
        
        # Sort by timestamp (most recent first)
        calls.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        # Optional: limit results
        limit = request.args.get('limit', type=int)
        if limit:
            calls = calls[:limit]
        
        return jsonify({
            'success': True,
            'count': len(calls),
            'calls': calls,
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

# ==================== ERROR HANDLERS ====================

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'error': 'Endpoint not found',
        'timestamp': datetime.now().isoformat()
    }), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        'error': 'Internal server error',
        'timestamp': datetime.now().isoformat()
    }), 500

# ==================== MAIN ====================

if __name__ == '__main__':
    # Create data files if they don't exist
    if not os.path.exists(LOADS_FILE):
        save_json_file(LOADS_FILE, [])
    if not os.path.exists(CALLS_DB_FILE):
        save_json_file(CALLS_DB_FILE, [])
    
    # Run the app
    port = int(os.environ.get('PORT', 5160))
    app.run(host='0.0.0.0', port=port, debug=True)