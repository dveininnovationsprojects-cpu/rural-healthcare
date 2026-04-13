import os
import math
import random
import uuid
import logging
import json
import threading
import time
import base64
import hashlib
import re # 🔥 For parsing PDF text and extracting exact values
from functools import wraps
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, make_response, send_file, abort
from flask_cors import CORS
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from io import BytesIO
import PyPDF2

# ==============================================================================
# 1. ENTERPRISE SYSTEM ARCHITECTURE & SECURITY CONFIG
# ==============================================================================
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}}) # Allow all IPs for mobile & hardware testing

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [ZHOPINGO_MASTER] - %(levelname)s - %(message)s')
logger = logging.getLogger("ZHOPINGO_CORE")

class EnterpriseConfig:
    VERSION = "49.0.0 - SMART CARDIAC TRIGGER AI"
    SECRET_KEY = os.environ.get("ZHOPINGO_JWT_SECRET", hashlib.sha256(b"zhopingo_enterprise_vault").hexdigest())
    SIM_INTERVAL = 2  
    DATA_RETENTION = 10000 
    TOKEN_EXPIRY_HOURS = 24
    
    # 🔥 UPDATED CLINICAL LIMITS TO MATCH ESP32 🔥
    CLINICAL_LIMITS = {
        "temp_min": 30.0, "temp_max": 33.2, 
        "hr_min": 50, "hr_max": 100,
        "accel_max": 1.30
    }
    
    # 🔥 TWILIO CREDENTIALS 🔥
    TWILIO_SID = "AC0c4b21d4357d28a0f9d86dadeac98d9e"
    TWILIO_TOKEN = "c865458d4e089728915e315c2f23c973"
    TWILIO_PHONE = "+15015015606" 
    TARGET_PHONE = "+919245798766"

# ==============================================================================
# 2. TWILIO AUTOMATED EMERGENCY CALL LOGIC
# ==============================================================================
def trigger_twilio_emergency(patient_name, node_id):
    """Makes an automated Voice Call to the patient's friend during an emergency."""
    try:
        from twilio.rest import Client
        logger.info(f"Attempting to dial {EnterpriseConfig.TARGET_PHONE} via Twilio...")
        
        client = Client(EnterpriseConfig.TWILIO_SID, EnterpriseConfig.TWILIO_TOKEN)
        
        twiml_msg = (
            f"<Response><Say voice='alice'>"
            f"Emergency Alert from Zho pingo Med. Patient {patient_name}, Node ID {node_id}, "
            f"is in critical condition. Immediate assistance is required."
            f"</Say></Response>"
        )
        
        call = client.calls.create(
            twiml=twiml_msg,
            to=EnterpriseConfig.TARGET_PHONE,
            from_=EnterpriseConfig.TWILIO_PHONE
        )
        logger.info(f"🚨 TWILIO EMERGENCY CALL INITIATED! Call SID: {call.sid}")
    except ImportError:
        logger.error("Twilio library missing. Stop server and run: pip install twilio")
    except Exception as e:
        logger.error(f"Twilio Call Failed: {str(e)}")

# ==============================================================================
# 3. MIDDLEWARE & IN-MEMORY DB
# ==============================================================================
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('X-Zhopingo-Auth')
        if not token:
            return jsonify({'error': 'Token is missing', 'code': 'AUTH_001'}), 401
        return f(*args, **kwargs)
    return decorated

@app.errorhandler(404)
def resource_not_found(e):
    return jsonify(error=str(e), code="SYS_404", message="Requested medical resource not found"), 404

@app.errorhandler(500)
def internal_server_error(e):
    return jsonify(error=str(e), code="SYS_500", message="Internal clinical processing error"), 500

class ClinicalVault:
    def __init__(self):
        self.doctors = {
            "D001": {
                "id": "D001", "name": "Dr. Peer Mohammed", "specialty": "Critical Care",
                "hospital": "Zhopingo Multi-Speciality", "active_patients": ["P001"],
                "pending_queue": [], 
                "active_calls": {} 
            }
        }
        self.patients = {
            "P001": {
                "id": "P001", "name": "Muthu Pandi", "age": 72, "history": "Cardiac Recovery",
                "status": "ACCEPTED", "doctor_id": "D001", "vitals_history": [],
                "risk_profile": "NORMAL", 
                "thresholds": {"temp": 33.2, "accel": 1.30, "hr_max": 100},
                "chat_vault": [], "notification_hub": [], "prescription_vault": [],
                "ai_advisor_cache": {"diet": [], "action": [], "warning": [], "exercise": [], "clinical": []},
                "biometric_averages": {"temp": 31.5, "hr": 0},
                "security_hash": "session_token_xyz",
                "last_emergency_call": None,
                "historical_baseline": {"temp": 0, "hr": 0, "accel": 0, "status": "No Record", "extracted_text": ""},
                "medical_records": [] 
            }
        }
        self.audit_log = []

db = ClinicalVault()

# ==============================================================================
# 4. CLINICAL AI REASONING ENGINE (SMART CARDIAC TRIGGER)
# ==============================================================================
class MedicalAIIntelligence:
    @staticmethod
    def analyze_physiological_drift(pid, temp, hr, accel, age, history):
        instructions = {"diet": [], "action": [], "warning": [], "exercise": [], "clinical": []}
        
        if temp >= 34.5:
            instructions["warning"].append("SEVERE HYPERTHERMIA: Risk of neurological stress.")
            instructions["action"].append("Initiate active cooling. Apply ice packs to groins/axilla.")
            instructions["diet"].append("NPO (Nil Per Os) - Stop oral feeding. IV fluids only.")
        elif 33.2 <= temp < 34.5:
            instructions["warning"].append("ELEVATED TEMP: Metabolic demand increased.")
            instructions["action"].append("Tepid sponging. Maintain room temp at 22C.")
            instructions["diet"].append("Increase clear fluids. 500ml ORS infused with Vitamin C.")
            
        if hr >= 115:
            instructions["warning"].append("TACHYCARDIA ALERT: Ventricular rate critical.")
            instructions["action"].append("Perform Vagal maneuvers. Prepare for potential cardioversion.")
            instructions["diet"].append("Strictly avoid xanthine derivatives (caffeine).")
        elif 95 <= hr < 115:
            instructions["warning"].append("ELEVATED BPM: Monitoring for arrhythmias.")
            instructions["action"].append("Assume semi-Fowler's position. Deep box breathing.")
            
        if accel >= 1.30:
            instructions["warning"].append("FALL DETECTED (HIGH-G IMPACT): Suspected trauma.")
            instructions["action"].append("DO NOT MOVE. Maintain C-spine immobilization.")
            
        if not instructions["warning"]:
            instructions["action"].append("Homeostasis maintained. Continue routine surveillance.")
            instructions["diet"].append("Standard cardiac diet: Low sodium, DASH protocol.")
            
        return instructions

# ==============================================================================
# 5. ENTERPRISE ENDPOINTS: CORE LOGIC (DOCTOR & PATIENT)
# ==============================================================================

@app.route('/api/v1/doctor/dashboard', methods=['GET'])
def get_physician_dashboard():
    doc = db.doctors['D001']
    results = []
    
    for pid in list(set(doc['active_patients'] + doc['pending_queue'])):
        p = db.patients[pid]
        snapshot = p['vitals_history'][-1] if p['vitals_history'] else None
        results.append({
            "patient_info": {"id": pid, "name": p['name'], "age": p['age'], "status": p['status'], "history": p['history']},
            "risk_status": p['risk_profile'],
            "vital_snapshot": snapshot,
            "ai_instructions": p['ai_advisor_cache'],
            "historical_baseline": p['historical_baseline'], 
            "medical_records": p.get('medical_records', []), 
            "has_notifs": len(p['notification_hub']) > 0
        })
    results.sort(key=lambda x: x['risk_status'] == "CRITICAL", reverse=True)
    return jsonify({"physician": doc['name'], "patients": results, "active_signals": doc['active_calls']})

@app.route('/api/v1/patient/register', methods=['POST'])
def register_clinical_node():
    data = request.json
    if not data or not data.get('name') or not data.get('age'):
        return jsonify({"error": "Missing required fields", "code": "VAL_001"}), 400
        
    pid = "P-" + str(uuid.uuid4())[:4].upper()
    is_doc = data.get('created_by') == 'D001'
    
    db.patients[pid] = {
        "id": pid, "name": data.get('name'), "age": int(data.get('age')),
        "history": data.get('history', 'Standard Observation'), 
        "status": "ACCEPTED" if is_doc else "PENDING",
        "doctor_id": "D001" if is_doc else None, "vitals_history": [],
        "risk_profile": "NORMAL", "chat_vault": [], "notification_hub": [],
        "prescription_vault": [], "ai_advisor_cache": {}, 
        "thresholds": {"temp": 33.2, "accel": 1.30}, 
        "security_hash": str(uuid.uuid4()),
        "last_emergency_call": None,
        "historical_baseline": {"temp": 0, "hr": 0, "accel": 0, "status": "No Record", "extracted_text": ""},
        "medical_records": [] 
    }
    if is_doc: db.doctors["D001"]['active_patients'].append(pid)
    else: db.doctors["D001"]['pending_queue'].append(pid)
    
    return jsonify({"p_id": pid, "status": "SUCCESS", "auto_link": is_doc})

@app.route('/api/v1/chat/sync', methods=['POST'])
def sync_chat_vault():
    data = request.json
    pid = data.get('patient_id') or data.get('node_id')
    role = data.get('role')
    text = data.get('message')
    
    is_patient = data.get('node_id') is not None
    
    if pid not in db.patients: return jsonify({"error": "NODE_NOT_FOUND"}), 404
    
    if text:
        db.patients[pid]['chat_vault'].append({
            "time": datetime.now().strftime("%H:%M:%S"),
            "sender": "Patient" if is_patient else "Physician",
            "text": text
        })
        
    return jsonify({"history": db.patients[pid]['chat_vault'][-30:]})

@app.route('/api/v1/patient/chat/send', methods=['POST'])
def send_patient_message():
    data = request.json
    p_id = data.get('node_id')
    text = data.get('message')
    if p_id not in db.patients: return abort(404, "Invalid Node")
    if not text: return abort(400, "Message empty")
    
    msg_obj = {"time": datetime.now().strftime("%H:%M"), "sender": "Patient", "text": text}
    db.patients[p_id]['chat_vault'].append(msg_obj)
    return jsonify({"status": "MESSAGE_DELIVERED"})

@app.route('/api/v1/video/signal', methods=['POST'])
def manage_webrtc_signal():
    data = request.json
    pid = data.get('patient_id')
    action = data.get('action')
    doc_calls = db.doctors['D001']['active_calls']
    
    if action == 'CALL':
        doc_calls[pid] = 'RINGING'
    elif action == 'ACCEPT':
        doc_calls[pid] = 'CONNECTED'
    elif action == 'END':
        if pid in doc_calls:
            del doc_calls[pid]
            
    return jsonify({"signalling_hub": doc_calls})

@app.route('/api/v1/doctor/prescription', methods=['POST'])
def generate_clinical_rx():
    try:
        data = request.json
        pid, meds = data.get('patient_id'), data.get('medications')
        p = db.patients.get(pid)
        if not p: return abort(404, description="Patient not found")

        rx_id = "RX-" + str(uuid.uuid4())[:6].upper()
        p['prescription_vault'].append({"id": rx_id, "time": datetime.now().isoformat(), "meds": meds})
        p['notification_hub'].append({"type": "PRESCRIPTION", "msg": f"Physician issued new digital Rx: {rx_id}"})
        
        return jsonify({"status": "SUCCESS", "rx_id": rx_id})
    except Exception as e:
        return abort(500, description="PDF generation failed")

# ==============================================================================
# 🔥 UPLOAD, DECODE AND BUILD STRUCTURED RECORD ARRAY 🔥
# ==============================================================================
@app.route('/api/v1/patient/upload-history', methods=['POST'])
def upload_medical_history():
    """Parses document into structured data and appends as a new record."""
    p_id = request.form.get('node_id')
    if not p_id or p_id not in db.patients: return abort(404, "Patient Not Found")
    
    file = request.files.get('document')
    if not file: return jsonify({"error": "No document provided"}), 400
    
    extracted_text = ""
    try:
        if file.filename.endswith('.pdf'):
            reader = PyPDF2.PdfReader(file)
            for page in reader.pages:
                extracted_text += page.extract_text() + "\n"
        else:
            extracted_text = file.read().decode('utf-8', errors='ignore')
    except Exception as e:
        logger.error(f"Doc parsing error: {e}")
        extracted_text = "Error parsing document."

    old_temp = 36.5  
    old_hr = 72.0
    bp = "120/80"
    spo2 = "98%"

    temp_match = re.search(r'(?i)temp(?:erature)?.*?([\d\.]+)', extracted_text)
    hr_match = re.search(r'(?i)(?:hr|heart\s*rate|pulse).*?([\d\.]+)', extracted_text)
    bp_match = re.search(r'(?i)blood\s*pressure.*?([\d]+/[\d]+)', extracted_text)
    spo2_match = re.search(r'(?i)spo2.*?([\d]+)', extracted_text)
    
    if temp_match: old_temp = float(temp_match.group(1))
    if hr_match: old_hr = float(hr_match.group(1))
    if bp_match: bp = bp_match.group(1)
    if spo2_match: spo2 = spo2_match.group(1) + "%"
    
    condition = "Stable"
    checkup_freq = "12 Hours"
    
    if old_temp > 33.2 or old_hr > 100:
        condition = "Critical"
        checkup_freq = "2 Hours"
    elif old_temp > 32.5 or old_hr > 85:
        condition = "Guarded"
        checkup_freq = "6 Hours"
        
    # 🔥 FIX: SCHEDULE FOR TODAY (1 HOUR FROM NOW INSTEAD OF 1 DAY) 🔥
    call_time = (datetime.now() + timedelta(hours=1)).strftime('%d-%b %H:%M')

    record_id = "DOC-" + str(uuid.uuid4())[:6].upper()
    new_record = {
        "id": record_id,
        "date": datetime.now().strftime('%d-%b-%Y %H:%M'),
        "filename": file.filename,
        "temp": old_temp,
        "hr": old_hr,
        "bp": bp,
        "spo2": spo2,
        "condition": condition,
        "checkup_freq": checkup_freq,
        "scheduled_call": call_time,
        "extracted_text": extracted_text
    }
    
    p = db.patients[p_id]
    
    if "medical_records" not in p:
        p["medical_records"] = []
    p["medical_records"].append(new_record)
    
    p['historical_baseline'] = {
        "temp": old_temp, "hr": old_hr, "accel": 1.0, 
        "status": f"Latest: {file.filename}", "extracted_text": extracted_text 
    }
    
    p['thresholds']['temp'] = round(old_temp + 1.2, 1) 
    
    db.audit_log.append({"time": datetime.now().isoformat(), "event": "DOCUMENT_UPLOADED", "node": p_id, "doc": file.filename})
    
    return jsonify({
        "status": "UPLOAD_SUCCESS", 
        "new_temp_limit": p['thresholds']['temp'],
        "record": new_record
    })

# ==============================================================================
# 6. PATIENT-SPECIFIC FRONTEND SYNC ENDPOINTS
# ==============================================================================

@app.route('/api/v1/patient/auth/handshake', methods=['POST'])
def verify_patient_node():
    data = request.json
    p_id = data.get('node_id')
    if p_id in db.patients:
        p = db.patients[p_id]
        return jsonify({
            "status": "AUTHORIZED",
            "patient_name": p['name'],
            "protocol": p['history'],
            "session_token": p.get('security_hash', 'token_xyz')
        })
    return jsonify({"error": "NODE_NOT_FOUND", "code": "AUTH_404"}), 404

@app.route('/api/v1/patient/vault/sync', methods=['GET'])
def get_patient_vault():
    p_id = request.args.get('node_id')
    if p_id not in db.patients: return abort(404, "Invalid Node")
    p = db.patients[p_id]
    return jsonify({
        "chat_history": p['chat_vault'][-50:], 
        "prescriptions": p['prescription_vault'],
        "active_notifications": p['notification_hub'],
        "medical_records": p.get('medical_records', []), 
        "historical_baseline": p['historical_baseline']
    })

@app.route('/api/v1/patient/rescue/cdss-status', methods=['GET'])
def get_emergency_protocols():
    p_id = request.args.get('node_id')
    if p_id not in db.patients: return abort(404, "Invalid Node")
    
    p = db.patients[p_id]
    if p['risk_profile'] == "CRITICAL":
        return jsonify({
            "status": "CRITICAL_OVERRIDE_ACTIVE",
            "ambulance_eta": "06:42 MIN",
            "first_aid_steps": ["Maintain airway", "Do not move abruptly", "Wait for emergency unit"],
            "physician_on_call": "Dr. Peer Mohammed"
        })
    return jsonify({"status": "MONITORING_STABLE"})

@app.route('/api/v1/patient/clear-notifs', methods=['POST'])
def clear_patient_notifs():
    p_id = request.json.get('p_id')
    if p_id in db.patients:
        db.patients[p_id]['notification_hub'] = []
        return jsonify({"status": "CLEARED"})
    return jsonify({"error": "NOT_FOUND"}), 404

@app.route('/api/v1/patient/prescription/download', methods=['GET'])
def download_patient_rx():
    pid = request.args.get('node_id')
    p = db.patients.get(pid)
    if not p: return abort(404, description="Patient not found")

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    pdf.setFont("Helvetica-Bold", 24)
    pdf.drawString(50, 750, "ZHOPINGO MED - CLINICAL Rx")
    pdf.setFont("Helvetica", 12)
    pdf.drawString(50, 725, f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    pdf.line(50, 715, 550, 715)
    pdf.drawString(50, 690, f"PATIENT IDENTITY: {p['name']} | NODE: {pid}")
    pdf.drawString(50, 670, f"DIAGNOSIS: {p['history']}")
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(50, 630, "PRESCRIBED CARE PLAN:")
    pdf.setFont("Helvetica", 12)
    
    y_pos = 610
    latest_rx = p['prescription_vault'][-1]['meds'] if p['prescription_vault'] else "Standard Observation."
    for line in latest_rx.split('\n'):
        if line.strip():
            pdf.drawString(70, y_pos, f"• {line.strip()}")
            y_pos -= 20
            
    pdf.save()
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name=f"Zhopingo_Rx_{pid}.pdf", mimetype='application/pdf')

# 🔥 REAL HARDWARE INGESTION ROUTE (WITH SMART HR TRIGGER) 🔥
@app.route('/api/v1/patient/telemetry/ingest', methods=['POST'])
def ingest_hardware_data():
    try:
        data = request.json
        p_id = data.get('node_id')
        if p_id not in db.patients: return abort(401)
        
        p = db.patients[p_id]
        
        raw_temp = float(data.get('temp', 31.5))
        raw_accel = float(data.get('accel', 1.0))

        # 🔥 DYNAMIC HEART RATE LOGIC 🔥
        # HR is strictly 0 unless an emergency threshold is breached
        is_fever = raw_temp > p['thresholds']['temp']
        is_fall = raw_accel > p['thresholds']['accel']
        
        if is_fever or is_fall:
            # Emergency Mode: Simulate HR spike from wearable sensor activating
            base_hr = 95 if is_fever else 110
            raw_hr = float(data.get('hr', base_hr + random.uniform(-5, 15))) 
            risk = "CRITICAL"
        else:
            # Normal Mode: Wearable in power-save / not reading HR
            raw_hr = 0.0
            risk = "NORMAL"

        ai_analysis = MedicalAIIntelligence.analyze_physiological_drift(p_id, raw_temp, raw_hr, raw_accel, p['age'], p['history'])
        
        p['ai_advisor_cache'] = ai_analysis
        p['risk_profile'] = risk
        
        entry = {"time": datetime.now().isoformat(), "temp": raw_temp, "hr": raw_hr, "accel": raw_accel, "risk": risk}
        p['vitals_history'].append(entry)
        
        if len(p['vitals_history']) > 1000: p['vitals_history'].pop(0)
        
        hw_cmd = "STANDBY"
        
        if risk == "CRITICAL":
            hw_cmd = "TRIGGER_ALARM" 
            now = datetime.now()
            last_call = p.get('last_emergency_call')
            if last_call is None or (now - last_call).total_seconds() > 120:
                p['last_emergency_call'] = now
                threading.Thread(target=trigger_twilio_emergency, args=(p['name'], p_id)).start()
        
        return jsonify({"status": "SYNC_SUCCESS", "risk_profile": risk, "hardware_command": hw_cmd})
    except Exception as e:
        logger.error(f"Telemetry Error: {str(e)}")
        return abort(500)

if __name__ == '__main__':
    logger.info(f"Booting Zhopingo Core v{EnterpriseConfig.VERSION}...")
    app.run(host='0.0.0.0', port=5000, debug=True)