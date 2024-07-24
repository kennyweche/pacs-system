from flask import Flask, jsonify, request, render_template
import requests
from datetime import datetime
import psycopg2

app = Flask(__name__)

# Orthanc server configuration
ORTHANC_URL = 'http://localhost:8042'

# Database configuration
DB_CONFIG = {
    'dbname': 'pacs',
    'user': 'user',
    'password': 'password',
    'host': 'localhost',
    'port': '5432'
}

def get_db_connection():
    """Create a new database connection."""
    conn = psycopg2.connect(**DB_CONFIG)
    return conn

@app.route('/api/dicom/<string:study_uid>', methods=['GET'])
def get_dicom_images(study_uid):
    """Fetch DICOM images for a specific study from Orthanc."""
    try:
        response = requests.get(f"{ORTHANC_URL}/studies/{study_uid}/series")
        response.raise_for_status()
        series = response.json()
        return jsonify(series), 200
    except requests.exceptions.RequestException as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/dicom/image/<string:image_uid>', methods=['GET'])
def get_dicom_image(image_uid):
    """Fetch a specific DICOM image from Orthanc."""
    try:
        response = requests.get(f"{ORTHANC_URL}/instances/{image_uid}/file")
        response.raise_for_status()
        return response.content, 200, {'Content-Type': 'application/dicom'}
    except requests.exceptions.RequestException as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/dicom/upload', methods=['POST'])
def upload_dicom():
    """Upload a DICOM file to Orthanc."""
    file = request.files['file']
    try:
        response = requests.post(f"{ORTHANC_URL}/instances", files={'file': file})
        response.raise_for_status()
        return jsonify(response.json()), 201
    except requests.exceptions.RequestException as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/reports', methods=['GET', 'POST'])
def reports():
    """Handle report creation and retrieval."""
    if request.method == 'POST':
        # Create a new report
        data = request.get_json()
        report = {
            'patient_id': data['patient_id'],
            'study_uid': data['study_uid'],
            'findings': data['findings'],
            'created_at': datetime.now().isoformat()
        }
        save_report_to_db(report)
        return jsonify(report), 201
    else:
        # Retrieve reports
        reports = get_reports_from_db()
        return jsonify(reports), 200

def save_report_to_db(report):
    """Save a report to the database."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO reports (patient_id, study_uid, findings, created_at)
        VALUES (%s, %s, %s, %s)
    """, (report['patient_id'], report['study_uid'], report['findings'], report['created_at']))
    conn.commit()
    cur.close()
    conn.close()

def get_reports_from_db():
    """Retrieve reports from the database."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM reports")
    reports = cur.fetchall()
    cur.close()
    conn.close()
    return [{'patient_id': r[1], 'study_uid': r[2], 'findings': r[3], 'created_at': r[4]} for r in reports]

@app.route('/')
def index():
    """Render the Cornerstone.js viewer and reporting interface."""
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True, port=5000)

