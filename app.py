#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Flask Web Application for Medical Expert System
Provides web interface for symptom selection and diagnosis
"""

from flask import Flask, render_template, request, jsonify, session
from medical_expert import MedicalExpertSystem
import json
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'medical_expert_secret_key_2024'

# Initialize the medical expert system
expert_system = MedicalExpertSystem()

@app.route('/')
def index():
    """Main page with symptom selection interface"""
    # Get all available symptoms for the interface
    all_symptoms = expert_system.kb.get_all_symptoms()
    all_diseases = expert_system.kb.get_all_diseases()
    
    # Get system statistics
    stats = expert_system.get_system_stats()
    
    return render_template('index.html', 
                         symptoms=all_symptoms,
                         diseases=all_diseases,
                         stats=stats)

@app.route('/diagnose', methods=['POST'])
def diagnose():
    """Handle diagnosis request"""
    try:
        data = request.get_json()
        symptoms = data.get('symptoms', [])
        
        if not symptoms:
            return jsonify({
                'success': False,
                'error': 'No symptoms provided'
            })
        
        # Perform diagnosis
        result = expert_system.diagnose(symptoms)
        
        # Format result for web display
        formatted_result = format_diagnosis_result(result)
        
        return jsonify({
            'success': True,
            'result': formatted_result,
            'raw_result': result
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/symptoms')
def get_symptoms():
    """API endpoint to get all available symptoms"""
    symptoms = expert_system.kb.get_all_symptoms()
    return jsonify({
        'success': True,
        'symptoms': symptoms
    })

@app.route('/api/diseases')
def get_diseases():
    """API endpoint to get all available diseases"""
    diseases = expert_system.kb.get_all_diseases()
    disease_info = {}
    
    for disease in diseases:
        info = expert_system.kb.get_disease_info(disease)
        disease_info[disease] = {
            'symptom_count': len(info.get('symptom_weights', {})),
            'symptoms': list(info.get('symptom_weights', {}).keys())
        }
    
    return jsonify({
        'success': True,
        'diseases': disease_info
    })

@app.route('/api/stats')
def get_stats():
    """API endpoint to get system statistics"""
    stats = expert_system.get_system_stats()
    return jsonify({
        'success': True,
        'stats': stats
    })

@app.route('/api/history')
def get_history():
    """API endpoint to get diagnosis history"""
    limit = request.args.get('limit', 10, type=int)
    history = expert_system.get_diagnosis_history(limit)
    return jsonify({
        'success': True,
        'history': history
    })

@app.route('/about')
def about():
    """About page with system information"""
    stats = expert_system.get_system_stats()
    return render_template('about.html', stats=stats)

@app.route('/history')
def history():
    """History page showing past diagnoses"""
    return render_template('history.html')

def format_diagnosis_result(result):
    """Format diagnosis result for web display"""
    formatted = {
        'status': result['status'],
        'timestamp': result.get('timestamp', ''),
        'confidence_percentage': result.get('confidence_percentage', 0),
        'total_symptoms': result.get('total_symptoms', 0)
    }
    
    if result['status'] == 'diagnosis':
        formatted.update({
            'diagnosis': result['diagnosis'],
            'confidence': result['confidence'],
            'message': f"Diagnosis: {result['diagnosis']} with {result['confidence']} points confidence"
        })
    
    elif result['status'] == 'suspected':
        formatted.update({
            'suspected_diseases': result['top_diseases'],
            'message': f"Multiple possible conditions detected. Top {len(result['top_diseases'])} suspected diseases:"
        })
    
    else:  # unknown or error
        formatted.update({
            'message': result.get('message', 'Unable to determine diagnosis'),
            'confidence': result.get('confidence', 0)
        })
    
    return formatted

if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static/css', exist_ok=True)
    os.makedirs('static/js', exist_ok=True)
    
    print("🏥 Medical Expert System Web Server")
    print("=" * 50)
    print(f"📊 Knowledge Base: {len(expert_system.kb.get_all_diseases())} diseases")
    print(f"🔍 Available Symptoms: {len(expert_system.kb.get_all_symptoms())}")
    print(f"📋 Rules: {len(expert_system.kb.rules)}")
    print("=" * 50)
    print("🌐 Starting Flask server...")
    print("📱 Access the web interface at: http://localhost:5000")
    
    app.run(debug=True, host='0.0.0.0', port=5000) 