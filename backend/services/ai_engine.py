"""
ZHOPINGO MED - ADVANCED CLINICAL AI ENGINE v1.0
Path: services/ai_engine.py
Description: Deep Medical Logic Matrix. Processes raw telemetry into actionable clinical insights.
"""

import logging
from datetime import datetime

logger = logging.getLogger("ZHOPINGO_AI_ENGINE")

class ThermalDiagnostics:
    """Analyzes Core Body Temperature drifts."""
    @staticmethod
    def evaluate(temp, age, history):
        advice = []
        severity = 0
        if temp >= 40.0:
            severity = 100
            advice.append({"type": "CRITICAL", "msg": "Hyperpyrexia. Immediate ice-bath protocol. Risk of protein denaturation."})
            advice.append({"type": "MEDICATION", "msg": "Administer IV Paracetamol 1g stat."})
        elif 39.0 <= temp < 40.0:
            severity = 80
            advice.append({"type": "WARNING", "msg": "High-grade fever. Monitor for febrile seizures."})
            advice.append({"type": "ACTION", "msg": "Apply cold compress to carotid, axillary, and femoral arteries."})
            advice.append({"type": "DIET", "msg": "Strict NPO (Nil Per Os). IV fluids 500ml Normal Saline over 2 hrs."})
        elif 37.8 <= temp < 39.0:
            severity = 50
            advice.append({"type": "WARNING", "msg": "Low-grade pyrexia. Metabolic demand elevated."})
            advice.append({"type": "DIET", "msg": "Increase oral hydration. 1L ORS over next 4 hours."})
            if "diabet" in history.lower():
                advice.append({"type": "WARNING", "msg": "Diabetic profile: Fever may induce hyperglycemia. Check CBG Q4H."})
        elif temp <= 35.0:
            severity = 90
            advice.append({"type": "CRITICAL", "msg": "Severe Hypothermia. Enzymatic pathways compromised."})
            advice.append({"type": "ACTION", "msg": "Forced air warming (Bair Hugger). Warmed IV fluids."})
        return severity, advice

class CardiacDiagnostics:
    """Analyzes Heart Rate (BPM) correlations."""
    @staticmethod
    def evaluate(hr, temp, age, history):
        advice = []
        severity = 0
        
        # Compensatory Tachycardia Check (HR elevated due to fever)
        expected_hr = 80 + ((temp - 37.0) * 10) if temp > 37.0 else 80
        
        if hr >= 150:
            severity = 100
            advice.append({"type": "CRITICAL", "msg": "SVT/Arrhythmia risk. Immediate 12-lead ECG required."})
            advice.append({"type": "ACTION", "msg": "Prepare crash cart. Initiate modified Valsalva maneuver."})
        elif 120 <= hr < 150:
            if hr > expected_hr + 20:
                severity = 85
                advice.append({"type": "WARNING", "msg": "Unexplained Tachycardia out of proportion to fever."})
                advice.append({"type": "ACTION", "msg": "Rule out sepsis or internal hemorrhage. Check BP immediately."})
            else:
                severity = 60
                advice.append({"type": "INFO", "msg": "Compensatory Tachycardia due to thermal stress."})
                advice.append({"type": "ACTION", "msg": "Treat underlying fever to lower heart rate."})
        elif hr < 50:
            severity = 80
            advice.append({"type": "WARNING", "msg": "Severe Bradycardia. Risk of hemodynamic collapse."})
            if age > 65:
                advice.append({"type": "ACTION", "msg": "Geriatric profile: Evaluate for sick sinus syndrome or medication toxicity (Beta-blockers)."})
            advice.append({"type": "ACTION", "msg": "Atropine 0.5mg IV standby."})
            
        return severity, advice

class KineticDiagnostics:
    """Analyzes MPU6050 Acceleration vectors for Trauma."""
    @staticmethod
    def evaluate(accel, history):
        advice = []
        severity = 0
        if accel >= 4.0:
            severity = 100
            advice.append({"type": "CRITICAL", "msg": "High-velocity blunt force trauma detected."})
            advice.append({"type": "ACTION", "msg": "C-spine immobilization. Rigid collar application."})
            advice.append({"type": "PROTOCOL", "msg": "Activate Massive Transfusion Protocol (MTP) standby."})
        elif 2.8 <= accel < 4.0:
            severity = 75
            advice.append({"type": "WARNING", "msg": "Fall detected. Potential orthopedic injury."})
            advice.append({"type": "ACTION", "msg": "Assess GCS (Glasgow Coma Scale) immediately."})
            if "osteo" in history.lower() or "cardiac" in history.lower():
                advice.append({"type": "WARNING", "msg": "High risk for pathological fracture or syncope-induced fall."})
        elif accel < 0.3:
            severity = 60
            advice.append({"type": "WARNING", "msg": "Freefall or zero-G state. Syncope / Fainting likely."})
        return severity, advice

class ClinicalIntelligenceMatrix:
    """Master Hub that aggregates all sub-diagnostics."""
    @staticmethod
    def process_telemetry(patient_id, temp, hr, accel, age, history):
        logger.info(f"AI Matrix processing data for {patient_id}")
        
        t_sev, t_adv = ThermalDiagnostics.evaluate(temp, age, history)
        c_sev, c_adv = CardiacDiagnostics.evaluate(hr, temp, age, history)
        k_sev, k_adv = KineticDiagnostics.evaluate(accel, history)
        
        # Calculate Total Risk Score (0-300)
        total_severity = t_sev + c_sev + k_sev
        
        risk_profile = "NORMAL"
        if total_severity >= 150 or t_sev == 100 or c_sev == 100 or k_sev == 100:
            risk_profile = "CRITICAL"
        elif total_severity >= 75:
            risk_profile = "HIGH_RISK"
        elif total_severity >= 30:
            risk_profile = "STABLE_WATCH"
            
        # Aggregate all advice into a structured format
        compiled_advice = t_adv + c_adv + k_adv
        
        if not compiled_advice:
            compiled_advice.append({"type": "GENERAL", "msg": "All biometric parameters within optimal physiological limits."})
            compiled_advice.append({"type": "DIET", "msg": "Maintain prescribed diet chart. Focus on micro-nutrients."})

        return {
            "risk_profile": risk_profile,
            "severity_score": total_severity,
            "instructions": compiled_advice,
            "timestamp": datetime.now().isoformat()
        }