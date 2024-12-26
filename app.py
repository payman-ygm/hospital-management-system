from flask import Flask, render_template, request, redirect, url_for
from flask.views import MethodView
from patient import Patient
from doctor import Doctor
from admin import Admin

app = Flask(__name__)

# Define classes
class PatientView(MethodView):
    def get(self):
        # Render Patient Interface
        return render_template("patient.html")
    
    def post(self):
        # Handle POST actions for patients
        action = request.form.get('action')
        # Call corresponding methods from Patient class
        patient = Patient()
        if action == 'register':
            # Call register method
            patient.register(request.form)
        elif action == 'update':
            # Call update method
            patient.update(request.form)
        return redirect(url_for('patient'))

class DoctorView(MethodView):
    def get(self):
        # Render Doctor Interface
        return render_template("doctor.html")
    
    def post(self):
        # Handle POST actions for doctors
        action = request.form.get('action')
        doctor = Doctor()
        if action == 'schedule':
            doctor.schedule(request.form)
        elif action == 'diagnose':
            doctor.diagnose(request.form)
        return redirect(url_for('doctor'))

class AdminView(MethodView):
    def get(self):
        # Render Admin Interface
        return render_template("admin.html")
    
    def post(self):
        # Handle POST actions for admin
        action = request.form.get('action')
        admin = Admin()
        if action == 'add_user':
            admin.add_user(request.form)
        elif action == 'remove_user':
            admin.remove_user(request.form)
        return redirect(url_for('admin'))

# Register URL Rules
app.add_url_rule('/patient', view_func=PatientView.as_view('patient'))
app.add_url_rule('/doctor', view_func=DoctorView.as_view('doctor'))
app.add_url_rule('/admin', view_func=AdminView.as_view('admin'))

@app.route('/')
def index():
    return render_template("index.html")  # Home navigation

if __name__ == '__main__':
    app.run(debug=True)
