import sqlite3
from flask import Flask, render_template, redirect, request, session
from flask.views import MethodView

app = Flask(__name__)
app.config['SECRET_KEY'] = 'hms_2024'

class login(MethodView):
    def get(self):
        return render_template('login.html')
    

    

app.add_url_rule('/login', view_func=login.as_view('login'))

if __name__ == '__main__':
    app.run(debug=True)