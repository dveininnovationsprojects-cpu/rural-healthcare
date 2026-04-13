# """
# ZHOPINGO MED - DOCTOR ROUTES v1.0
# Path: routes/doctor_api.py
# Description: Extensive CRUD operations, Audit Log retrievals, Medical Vault management, and Rx Issuing.
# """

# from flask import Blueprint, request, jsonify, abort
# from datetime import datetime
# import uuid
# import logging

# # Import your database from the central file
# from database import db 

# doctor_bp = Blueprint('doctor_bp', __name__)
# logger = logging.getLogger("ZHOPINGO_DOCTOR_API")

# # ==============================================================================
# # 1. CORE DASHBOARD ENDPOINT
# # ==============================================================================
# @doctor_bp.route('/dashboard', methods=['GET'])
# def get_dashboard():
#     """Aggregates comprehensive data for the Doctor's Workstation."""
#     doc_id = request.args.get('doc_id', 'D001')
#     if doc_id not in db.doctors: return abort(404, "Physician Profile Not Found")
    
#     doc = db.doctors[doc_id]
#     payload = []
    
#     for pid in list(set(doc['active_patients'] + doc['pending_queue'])):
#         p = db.patients[pid]
#         latest_vital = p['vitals_history'][-1] if p['vitals_history'] else None
        
#         # Safe extraction for ai_advisor_cache to handle both list and dict structures
#         ai_insights = p.get('ai_advisor_cache', {})
#         if isinstance(ai_insights, dict) and 'instructions' in ai_insights:
#             ai_insights = ai_insights['instructions']
        
#         payload.append({
#             "patient_info": {
#                 "id": pid,
#                 "name": p['name'],
#                 "age": p['age'],
#                 "status": p['status'],
#                 "history": p['history']
#             },
#             "risk_status": p['risk_profile'],
#             "vital_snapshot": latest_vital,
#             "ai_instructions": p.get('ai_advisor_cache', {}),
#             "has_notifs": len(p['notification_hub']) > 0
#         })
        
#     payload.sort(key=lambda x: x['risk_status'] == "CRITICAL", reverse=True)
#     return jsonify({"physician": doc['name'], "patients": payload, "active_signals": doc['active_calls']})


# # ==============================================================================
# # 2. MISSING FEATURE ADDED: ISSUE PRESCRIPTION (PDF LOGIC)
# # ==============================================================================
# @doctor_bp.route('/prescription', methods=['POST'])
# def issue_clinical_rx():
#     """Doctor pushes Rx to the vault. (Patient will download it securely via GET route)"""
#     try:
#         data = request.json
#         pid, meds = data.get('patient_id'), data.get('medications')
#         p = db.patients.get(pid)
#         if not p: return abort(404, description="Patient not found")

#         rx_id = "RX-" + str(uuid.uuid4())[:6].upper()
        
#         # Save meds to vault so patient can trigger download later
#         p['prescription_vault'].append({
#             "id": rx_id, 
#             "time": datetime.now().isoformat(), 
#             "meds": meds
#         })
        
#         # Trigger Notification for Patient UI
#         p['notification_hub'].append({
#             "type": "PRESCRIPTION", 
#             "msg": f"Physician issued new digital Rx: {rx_id}"
#         })
        
#         return jsonify({"status": "RX_ISSUED", "rx_id": rx_id})
#     except Exception as e:
#         logger.error(f"RX Vault Failed: {str(e)}")
#         return abort(500, description="RX Storage failed")


# # ==============================================================================
# # 3. MISSING FEATURE ADDED: AI PDF REPORT UPLOAD
# # ==============================================================================
# @doctor_bp.route('/upload-report', methods=['POST'])
# def doctor_upload_pdf():
#     """Handles doctor PDF uploads to adjust AI sensor thresholds dynamically."""
#     try:
#         p_id = request.form.get('patient_id')
#         if p_id in db.patients:
#             # Recalibrating logic via PDF reading simulation
#             db.patients[p_id]['thresholds']['temp'] -= 0.2
#             return jsonify({
#                 "status": "RECALIBRATED", 
#                 "new_limit": db.patients[p_id]['thresholds']['temp']
#             })
#         return jsonify({"error": "NODE_NOT_FOUND"}), 404
#     except Exception as e:
#         logger.error(f"PDF Upload Failed: {str(e)}")
#         return abort(500)


# # ==============================================================================
# # 4. ADVANCED CRUD: UPDATE PATIENT PROTOCOL
# # ==============================================================================
# @doctor_bp.route('/patient/<patient_id>/protocol', methods=['PUT'])
# def update_patient_protocol(patient_id):
#     """Updates the medical history and thresholds for a specific patient."""
#     if patient_id not in db.patients: return abort(404, "Patient Node Missing")
    
#     data = request.json
#     p = db.patients[patient_id]
    
#     if 'history' in data: p['history'] = data['history']
#     if 'thresholds' in data:
#         # Deep merge new thresholds
#         for key, value in data['thresholds'].items():
#             if key in p['thresholds']: p['thresholds'][key] = float(value)
            
#     db.audit_log.append(f"PROTOCOL UPDATE: {patient_id} by D001 at {datetime.now().isoformat()}")
#     return jsonify({"status": "PROTOCOL_UPDATED", "new_state": p['thresholds']})


# # ==============================================================================
# # 5. ADVANCED CRUD: DISCHARGE/DELETE PATIENT
# # ==============================================================================
# @doctor_bp.route('/patient/<patient_id>/discharge', methods=['DELETE'])
# def discharge_patient(patient_id):
#     """Removes patient from active monitoring, archives data."""
#     if patient_id not in db.patients: return abort(404, "Patient Node Missing")
    
#     # Remove from doctor's active list
#     doc = db.doctors['D001']
#     if patient_id in doc['active_patients']: doc['active_patients'].remove(patient_id)
#     if patient_id in doc['pending_queue']: doc['pending_queue'].remove(patient_id)
    
#     # Change status to archived (soft delete)
#     db.patients[patient_id]['status'] = "DISCHARGED"
#     db.audit_log.append(f"NODE DISCHARGED: {patient_id} at {datetime.now().isoformat()}")
    
#     return jsonify({"status": "DISCHARGED_SUCCESSFULLY", "node_id": patient_id})


# # ==============================================================================
# # 6. AUDIT & LEGAL LOGS FETCH
# # ==============================================================================
# @doctor_bp.route('/audit-logs', methods=['GET'])
# def fetch_audit_logs():
#     """Returns the global clinical audit trail for legal compliance."""
#     limit = int(request.args.get('limit', 100))
#     logs = db.audit_log[-limit:]
#     return jsonify({"total_logs": len(db.audit_log), "data": logs})


# # ==============================================================================
# # 7. INFRASTRUCTURE & RESOURCE MANAGEMENT
# # ==============================================================================
# @doctor_bp.route('/infrastructure/status', methods=['GET'])
# def get_hospital_status():
#     """Fetch ICU bed and ambulance availability across the network."""
#     return jsonify({"network_status": db.hospital_infrastructure})

# @doctor_bp.route('/infrastructure/icu/<hospital_id>', methods=['POST'])
# def block_icu_bed(hospital_id):
#     """Reserve an ICU bed during a trauma event."""
#     for hosp in db.hospital_infrastructure:
#         if hosp['id'] == hospital_id:
#             if hosp['icu_availability'] > 0:
#                 hosp['icu_availability'] -= 1
#                 return jsonify({"status": "BED_RESERVED", "remaining": hosp['icu_availability']})
#             else:
#                 return jsonify({"error": "ICU_AT_CAPACITY"}), 400
#     return abort(404, "Hospital ID not found in network")

"""
ZHOPINGO MED - DOCTOR ROUTES v1.0
Path: routes/doctor_api.py
Description: Extensive CRUD operations, Audit Log retrievals, Medical Vault management, and Rx Issuing.
"""

from flask import Blueprint, request, jsonify, abort
from datetime import datetime
import uuid
import logging

# Import your database from the central file
from database import db 

doctor_bp = Blueprint('doctor_bp', __name__)
logger = logging.getLogger("ZHOPINGO_DOCTOR_API")

# ==============================================================================
# 1. CORE DASHBOARD ENDPOINT
# ==============================================================================
@doctor_bp.route('/dashboard', methods=['GET'])
def get_dashboard():
    """Aggregates comprehensive data for the Doctor's Workstation."""
    doc_id = request.args.get('doc_id', 'D001')
    if doc_id not in db.doctors: return abort(404, "Physician Profile Not Found")
    
    doc = db.doctors[doc_id]
    payload = []
    
    for pid in list(set(doc['active_patients'] + doc['pending_queue'])):
        p = db.patients[pid]
        latest_vital = p['vitals_history'][-1] if p['vitals_history'] else None
        
        # Safe extraction for ai_advisor_cache to handle both list and dict structures
        ai_insights = p.get('ai_advisor_cache', {})
        if isinstance(ai_insights, dict) and 'instructions' in ai_insights:
            ai_insights = ai_insights['instructions']
        
        payload.append({
            "patient_info": {
                "id": pid,
                "name": p['name'],
                "age": p['age'],
                "status": p['status'],
                "history": p['history']
            },
            "risk_status": p['risk_profile'],
            "vital_snapshot": latest_vital,
            "ai_instructions": p.get('ai_advisor_cache', {}),
            "has_notifs": len(p['notification_hub']) > 0
        })
        
    payload.sort(key=lambda x: x['risk_status'] == "CRITICAL", reverse=True)
    return jsonify({"physician": doc['name'], "patients": payload, "active_signals": doc['active_calls']})


# ==============================================================================
# 2. ISSUE PRESCRIPTION (PDF LOGIC)
# ==============================================================================
@doctor_bp.route('/prescription', methods=['POST'])
def issue_clinical_rx():
    """Doctor pushes Rx to the vault. (Patient will download it securely via GET route)"""
    try:
        data = request.json
        pid, meds = data.get('patient_id'), data.get('medications')
        p = db.patients.get(pid)
        if not p: return abort(404, description="Patient not found")

        rx_id = "RX-" + str(uuid.uuid4())[:6].upper()
        
        # Save meds to vault so patient can trigger download later
        p['prescription_vault'].append({
            "id": rx_id, 
            "time": datetime.now().isoformat(), 
            "meds": meds
        })
        
        # Trigger Notification for Patient UI
        p['notification_hub'].append({
            "type": "PRESCRIPTION", 
            "msg": f"Physician issued new digital Rx: {rx_id}"
        })
        
        return jsonify({"status": "RX_ISSUED", "rx_id": rx_id})
    except Exception as e:
        logger.error(f"RX Vault Failed: {str(e)}")
        return abort(500, description="RX Storage failed")


# ==============================================================================
# 3. AI PDF REPORT UPLOAD
# ==============================================================================
@doctor_bp.route('/upload-report', methods=['POST'])
def doctor_upload_pdf():
    """Handles doctor PDF uploads to adjust AI sensor thresholds dynamically."""
    try:
        p_id = request.form.get('patient_id')
        if p_id in db.patients:
            # Recalibrating logic via PDF reading simulation
            db.patients[p_id]['thresholds']['temp'] -= 0.2
            return jsonify({
                "status": "RECALIBRATED", 
                "new_limit": db.patients[p_id]['thresholds']['temp']
            })
        return jsonify({"error": "NODE_NOT_FOUND"}), 404
    except Exception as e:
        logger.error(f"PDF Upload Failed: {str(e)}")
        return abort(500)


# ==============================================================================
# 4. ADVANCED CRUD: UPDATE PATIENT PROTOCOL
# ==============================================================================
@doctor_bp.route('/patient/<patient_id>/protocol', methods=['PUT'])
def update_patient_protocol(patient_id):
    """Updates the medical history and thresholds for a specific patient."""
    if patient_id not in db.patients: return abort(404, "Patient Node Missing")
    
    data = request.json
    p = db.patients[patient_id]
    
    if 'history' in data: p['history'] = data['history']
    if 'thresholds' in data:
        # Deep merge new thresholds
        for key, value in data['thresholds'].items():
            if key in p['thresholds']: p['thresholds'][key] = float(value)
            
    db.audit_log.append(f"PROTOCOL UPDATE: {patient_id} by D001 at {datetime.now().isoformat()}")
    return jsonify({"status": "PROTOCOL_UPDATED", "new_state": p['thresholds']})


# ==============================================================================
# 5. ADVANCED CRUD: DISCHARGE/DELETE PATIENT
# ==============================================================================
@doctor_bp.route('/patient/<patient_id>/discharge', methods=['DELETE'])
def discharge_patient(patient_id):
    """Removes patient from active monitoring, archives data."""
    if patient_id not in db.patients: return abort(404, "Patient Node Missing")
    
    # Remove from doctor's active list
    doc = db.doctors['D001']
    if patient_id in doc['active_patients']: doc['active_patients'].remove(patient_id)
    if patient_id in doc['pending_queue']: doc['pending_queue'].remove(patient_id)
    
    # Change status to archived (soft delete)
    db.patients[patient_id]['status'] = "DISCHARGED"
    db.audit_log.append(f"NODE DISCHARGED: {patient_id} at {datetime.now().isoformat()}")
    
    return jsonify({"status": "DISCHARGED_SUCCESSFULLY", "node_id": patient_id})


# ==============================================================================
# 6. AUDIT & LEGAL LOGS FETCH
# ==============================================================================
@doctor_bp.route('/audit-logs', methods=['GET'])
def fetch_audit_logs():
    """Returns the global clinical audit trail for legal compliance."""
    limit = int(request.args.get('limit', 100))
    logs = db.audit_log[-limit:]
    return jsonify({"total_logs": len(db.audit_log), "data": logs})


# ==============================================================================
# 7. INFRASTRUCTURE & RESOURCE MANAGEMENT
# ==============================================================================
@doctor_bp.route('/infrastructure/status', methods=['GET'])
def get_hospital_status():
    """Fetch ICU bed and ambulance availability across the network."""
    # Safety fallback if db.hospital_infrastructure doesn't exist yet
    infrastructure_data = getattr(db, 'hospital_infrastructure', [{"id": "HOSP_001", "name": "Zhopingo ICU", "icu_availability": 5, "ambulances": 2}])
    return jsonify({"network_status": infrastructure_data})

@doctor_bp.route('/infrastructure/icu/<hospital_id>', methods=['POST'])
def block_icu_bed(hospital_id):
    """Reserve an ICU bed during a trauma event."""
    infrastructure_data = getattr(db, 'hospital_infrastructure', [{"id": "HOSP_001", "name": "Zhopingo ICU", "icu_availability": 5, "ambulances": 2}])
    
    for hosp in infrastructure_data:
        if hosp['id'] == hospital_id:
            if hosp['icu_availability'] > 0:
                hosp['icu_availability'] -= 1
                # Save it back if it's dynamic
                db.hospital_infrastructure = infrastructure_data
                return jsonify({"status": "BED_RESERVED", "remaining": hosp['icu_availability']})
            else:
                return jsonify({"error": "ICU_AT_CAPACITY"}), 400
    return abort(404, "Hospital ID not found in network")