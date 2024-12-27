import sqlite3
import datetime
from flask import Flask, render_template, request, redirect, url_for, session
from flask.views import MethodView

app = Flask(__name__)
app.config['SECRET_KEY'] = 'hms_2024'

# Database Initialization
def init_db():
    conn = sqlite3.connect('hospital.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS admins (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        email TEXT NOT NULL UNIQUE,
                        phone TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS doctors (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        specialty TEXT NOT NULL,
                        contact TEXT NOT NULL
                    )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS patients (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        age INTEGER NOT NULL,
                        gender TEXT NOT NULL,
                        contact TEXT NOT NULL,
                        medical_history TEXT
                    )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS admin_credentials (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        admin_id INTEGER NOT NULL,
                        username TEXT NOT NULL UNIQUE,
                        password TEXT NOT NULL,
                        FOREIGN KEY(admin_id) REFERENCES admins(id)
                    )''')
    conn.commit()
    conn.close()

init_db()

class Home(MethodView):
    def get(self):
        return render_template('index.html')


# Login MethodView
class Login(MethodView):

    def get(self):
        return render_template('login.html')

    def post(self):
        username = request.form['username']
        password = request.form['password']
        
        conn = sqlite3.connect('hospital.db')
        conn.row_factory = sqlite3.Row
        
        # Check admin credentials
        admin = conn.execute('''SELECT * FROM admin_credentials 
                               JOIN admins ON admin_credentials.admin_id = admins.id 
                               WHERE admin_credentials.username = ? AND admin_credentials.password = ?''',
                             (username, password)).fetchone()
        
        # Check doctor credentials
        doctor = conn.execute('SELECT * FROM doctors WHERE name = ? AND contact = ?', (username, password)).fetchone()
        
        # Check patient credentials
        patient = conn.execute('SELECT * FROM patients WHERE name = ? AND contact = ?', (username, password)).fetchone()
        
        conn.close()
        
        if admin:
            session['user_type'] = 'admin'
            session['admin_id'] = admin['admin_id']
            return redirect(url_for('admin_dashboard'))
        elif doctor:
            session['user_type'] = 'doctor'
            session['doctor_id'] = doctor['id']
            return redirect(url_for('doctor_dashboard'))
        elif patient:
            session['user_type'] = 'patient'
            session['patient_id'] = patient['id']
            return redirect(url_for('patient_dashboard'))
        else:
            return render_template('login.html', error="Invalid username or password")

# Admin Dashboard MethodView
class AdminDashboard(MethodView):

    def get(self):
        return render_template('admin_dashboard.html')

class DoctorDashboard(MethodView):

    def get(self):
        return render_template('doctor_dashboard.html')

class PatientDashboard(MethodView):

    def get(self):
        return render_template('patient_dashboard.html')


class ViewPatients(MethodView):
    def get(self):
        # Fetch patient data from the database
        conn = sqlite3.connect('hospital.db')
        conn.row_factory = sqlite3.Row
        patients = conn.execute('SELECT * FROM patients').fetchall()
        conn.close()

        # Render the template with patient data
        return render_template('view_patients.html', patients=patients)

class UpdatePatientRecords(MethodView):
    def get(self, patient_id):
        # Fetch patient data from the database
        conn = sqlite3.connect('hospital.db')
        conn.row_factory = sqlite3.Row
        patient = conn.execute('SELECT * FROM patients WHERE id = ?', (patient_id,)).fetchone()
        conn.close()
        
        if patient:
            return render_template('update_patient_records.html', patient=patient)
        else:
            return "Patient not found", 404

    def post(self, patient_id):
        # Update patient record in the database
        name = request.form['name']
        age = request.form['age']
        gender = request.form['gender']
        contact = request.form['contact']
        medical_history = request.form['medical_history']
        
        conn = sqlite3.connect('hospital.db')
        conn.execute('''
            UPDATE patients
            SET name = ?, age = ?, gender = ?, contact = ?, medical_history = ?
            WHERE id = ?
        ''', (name, age, gender, contact, medical_history, patient_id))
        conn.commit()
        conn.close()
        
        return redirect(url_for('view_patients'))
    
class ViewSchedule(MethodView):
    def get(self):
        # Fetch schedule data from the database
        conn = sqlite3.connect('hospital.db')
        conn.row_factory = sqlite3.Row
        schedule = conn.execute('''
            SELECT 
                d.name AS doctor_name,
                p.name AS patient_name,
                p.appointment_date,
                p.appointment_time,
                p.notes
            FROM patients p
            JOIN doctors d ON p.doctor_id = d.id
            ORDER BY p.appointment_date, p.appointment_time
        ''').fetchall()
        conn.close()

        # Render the schedule page with the fetched data
        return render_template('view_schedule.html', schedule=schedule)

class AddPatient(MethodView):
    def get(self):
        return render_template('add_patient.html')

    def post(self):
        name = request.form['name']
        age = request.form['age']
        gender = request.form['gender']
        contact = request.form['contact']
        medical_history = request.form['medical_history']

        conn = sqlite3.connect('hospital.db')
        conn.execute('INSERT INTO patients (name, age, gender, contact, medical_history) VALUES (?, ?, ?, ?, ?)',
                     (name, age, gender, contact, medical_history))
        conn.commit()
        conn.close()

        return redirect(url_for('view_patients'))
    
class AddDoctor(MethodView):
    def get(self):
        return render_template('add_doctor.html')

    def post(self):
        name = request.form['name']
        specialty = request.form['specialty']
        contact = request.form['contact']

        conn = sqlite3.connect('hospital.db')
        conn.execute('INSERT INTO doctors (name, specialty, contact) VALUES (?, ?, ?)', 
                     (name, specialty, contact))
        conn.commit()
        conn.close()

        return redirect(url_for('view_doctors'))
    
class ViewDoctors(MethodView):
    def get(self):
        conn = sqlite3.connect('hospital.db')
        conn.row_factory = sqlite3.Row
        doctors = conn.execute('SELECT * FROM doctors').fetchall()
        conn.close()
        return render_template('view_doctors.html', doctors=doctors)

class GenerateManagementReport(MethodView):
    def get(self):
        conn = sqlite3.connect('hospital.db')
        conn.row_factory = sqlite3.Row
        
        total_doctors = conn.execute('SELECT COUNT(*) AS count FROM doctors').fetchone()['count']
        
        # Patients per doctor
        patients_per_doctor = conn.execute('''
            SELECT doctors.name, COUNT(patients.id) AS patient_count 
            FROM doctors LEFT JOIN patients ON doctors.id = patients.doctor_id 
            GROUP BY doctors.name
        ''').fetchall()
        
        # Appointments per month
        appointments_per_month = conn.execute('''
            SELECT doctors.name, COUNT(patients.id) AS appointment_count 
            FROM doctors 
            JOIN patients ON doctors.id = patients.doctor_id 
            WHERE strftime('%Y-%m', patients.created_at) = ?
            GROUP BY doctors.name
        ''', (datetime.datetime.now().strftime('%Y-%m'),)).fetchall()
        
        conn.close()
        return render_template('management_report.html',
                               total_doctors=total_doctors,
                               patients_per_doctor=patients_per_doctor,
                               appointments_per_month=appointments_per_month)

class Logout(MethodView):
    def get(self):
        session.pop('user_type', None)  # Clear the session data
        return redirect(url_for('login'))  # Redirect to login page


app.add_url_rule('/', view_func=Home.as_view('home'))
app.add_url_rule('/login', view_func=Login.as_view('login'))
app.add_url_rule('/admin', view_func=AdminDashboard.as_view('admin_dashboard'))
app.add_url_rule('/doctor', view_func=DoctorDashboard.as_view('doctor_dashboard'))
app.add_url_rule('/patient', view_func=PatientDashboard.as_view('patient_dashboard'))
app.add_url_rule('/view_patients', view_func=ViewPatients.as_view('view_patients'))
app.add_url_rule('/patients/update/<int:patient_id>', view_func=UpdatePatientRecords.as_view('update_patient_records'))
app.add_url_rule('/schedule', view_func=ViewSchedule.as_view('view_schedule'))
app.add_url_rule('/add_patient', view_func=AddPatient.as_view('add_patient'), methods=['GET', 'POST'])
app.add_url_rule('/add_doctor', view_func=AddDoctor.as_view('add_doctor'), methods=['GET', 'POST'])
app.add_url_rule('/view_doctors', view_func=ViewDoctors.as_view('view_doctors'))
app.add_url_rule('/generate_management_report', view_func=GenerateManagementReport.as_view('generate_management_report'))
app.add_url_rule('/logout', view_func=Logout.as_view('logout'))


if __name__ == '__main__':
    app.run(debug=True)

