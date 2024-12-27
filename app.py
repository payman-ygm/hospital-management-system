from flask import Flask, request, jsonify
from flask.views import MethodView
import sqlite3
import matplotlib.pyplot as plt

app = Flask(__name__)
DATABASE = 'hospital.db'

def get_db_connection():
    """Helper function to connect to the database."""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row  # For dict-like row access
    return conn

def create_tables():
    """Create tables if they do not exist."""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    # Create Admins Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS admins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        name TEXT,
        address TEXT
    );
    ''')

    # Create Doctors Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS doctors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        name TEXT,
        specialization TEXT,
        mobile TEXT
    );
    ''')

    # Create Patients Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS patients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        surname TEXT NOT NULL,
        symptoms TEXT,
        age INTEGER,
        mobile TEXT,
        address TEXT,
        doctor_id INTEGER,
        FOREIGN KEY (doctor_id) REFERENCES doctors(id)
    );
    ''')

    # Create Discharged Patients Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS discharged_patients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id INTEGER,
        discharge_date DATE,
        doctor_id INTEGER,
        FOREIGN KEY (patient_id) REFERENCES patients(id),
        FOREIGN KEY (doctor_id) REFERENCES doctors(id)
    );
    ''')

    # Create Appointments Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS appointments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        doctor_id INTEGER,
        patient_id INTEGER,
        date DATE,
        FOREIGN KEY (doctor_id) REFERENCES doctors(id),
        FOREIGN KEY (patient_id) REFERENCES patients(id)
    );
    ''')

    conn.commit()
    conn.close()

class AdminView(MethodView):
    def get(self):
        """Get Admin Reports or Views"""
        action = request.args.get('action')
        conn = get_db_connection()
        cursor = conn.cursor()

        if action == 'view_doctors':
            cursor.execute("SELECT id, name, specialization FROM doctors")
            doctors = [dict(row) for row in cursor.fetchall()]
            conn.close()
            return jsonify(doctors), 200

        elif action == 'view_patients':
            cursor.execute("SELECT id, name, surname, doctor_id FROM patients")
            patients = [dict(row) for row in cursor.fetchall()]
            conn.close()
            return jsonify(patients), 200

        elif action == 'report':
            # Generate management report
            cursor.execute("SELECT COUNT(*) FROM doctors")
            total_doctors = cursor.fetchone()[0]

            cursor.execute("SELECT doctors.name, COUNT(patients.id) AS patient_count FROM doctors LEFT JOIN patients ON doctors.id = patients.doctor_id GROUP BY doctors.name")
            patients_per_doctor = cursor.fetchall()

            cursor.execute("SELECT symptoms, COUNT(*) FROM patients GROUP BY symptoms")
            patients_by_illness = cursor.fetchall()

            conn.close()
            return jsonify({
                "total_doctors": total_doctors,
                "patients_per_doctor": [dict(row) for row in patients_per_doctor],
                "patients_by_illness": [dict(row) for row in patients_by_illness]
            }), 200

        return jsonify({"message": "Invalid action"}), 400

    def post(self):
        """Handle Admin Actions"""
        action = request.args.get('action')
        data = request.json
        conn = get_db_connection()
        cursor = conn.cursor()

        if action == 'add_doctor':
            cursor.execute("INSERT INTO doctors (username, password, name, specialization, mobile) VALUES (?, ?, ?, ?, ?)",
                           (data['username'], data['password'], data['name'], data['specialization'], data['mobile']))
            conn.commit()
            conn.close()
            return jsonify({"message": "Doctor added successfully"}), 201

        elif action == 'assign_doctor':
            cursor.execute("UPDATE patients SET doctor_id = ? WHERE id = ?", (data['doctor_id'], data['patient_id']))
            conn.commit()
            conn.close()
            return jsonify({"message": "Doctor assigned successfully"}), 200

        return jsonify({"message": "Invalid action"}), 400

    def put(self):
        """Update Admin or Other Entities"""
        data = request.json
        conn = get_db_connection()
        cursor = conn.cursor()

        # Update Admin Details
        if 'admin_id' in data:
            cursor.execute("UPDATE admins SET name = ?, address = ? WHERE id = ?",
                           (data['name'], data['address'], data['admin_id']))
            conn.commit()
            conn.close()
            return jsonify({"message": "Admin details updated successfully"}), 200

        return jsonify({"message": "Invalid action"}), 400

    def delete(self):
        """Discharge a Patient"""
        patient_id = request.args.get('patient_id')
        conn = get_db_connection()
        cursor = conn.cursor()

        # Move patient to discharged table
        cursor.execute("INSERT INTO discharged_patients (patient_id, discharge_date, doctor_id) SELECT id, date('now'), doctor_id FROM patients WHERE id = ?", (patient_id,))
        cursor.execute("DELETE FROM patients WHERE id = ?", (patient_id,))
        conn.commit()
        conn.close()
        return jsonify({"message": "Patient discharged successfully"}), 200


# Doctor Class-Based View
class DoctorView(MethodView):
    def get(self):
        """View assigned patients."""
        doctor_id = request.args.get('doctor_id')
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, surname, symptoms FROM patients WHERE doctor_id = ?", (doctor_id,))
        patients = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return jsonify(patients), 200


# Patient Class-Based View
class PatientView(MethodView):
    def get(self):
        """View assigned doctor."""
        patient_id = request.args.get('patient_id')
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT doctors.name, doctors.specialization FROM doctors JOIN patients ON doctors.id = patients.doctor_id WHERE patients.id = ?", (patient_id,))
        doctor = cursor.fetchone()
        conn.close()

        if doctor:
            return jsonify(dict(doctor)), 200
        return jsonify({"message": "Doctor not found"}), 404


# Visualization Endpoint
@app.route('/admin/report/visualize', methods=['GET'])
def visualize_report():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT doctors.name, COUNT(patients.id) FROM doctors LEFT JOIN patients ON doctors.id = patients.doctor_id GROUP BY doctors.name")
    data = cursor.fetchall()

    doctors = [row[0] for row in data]
    patient_counts = [row[1] for row in data]

    plt.bar(doctors, patient_counts)
    plt.title("Patients per Doctor")
    plt.xlabel("Doctors")
    plt.ylabel("Number of Patients")
    plt.savefig('static/patients_per_doctor.png')
    plt.close()

    conn.close()
    return jsonify({"message": "Visualization created", "url": "/static/patients_per_doctor.png"}), 200


# Register Class-Based Views
admin_view = AdminView.as_view('admin_view')
doctor_view = DoctorView.as_view('doctor_view')
patient_view = PatientView.as_view('patient_view')

app.add_url_rule('/admin', view_func=admin_view, methods=['GET', 'POST', 'PUT', 'DELETE'])
app.add_url_rule('/doctor', view_func=doctor_view, methods=['GET'])
app.add_url_rule('/patient', view_func=patient_view, methods=['GET'])

if __name__ == '__main__':
    app.run(debug=True)