import os
import json
import uuid
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_file
from datetime import datetime, timedelta
from functools import wraps
import io
import requests
import threading
import time
from apscheduler.schedulers.background import BackgroundScheduler
import atexit
import shutil
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from sqlalchemy import text
from models import db, User, Workspace, Project, Skill, Client, Message, VisitorLog
from config import get_config

app = Flask(__name__)
conf = get_config()
app.config.from_object(conf)

db.init_app(app)

with app.app_context():
    try:
        db.create_all()
        db.session.execute(text('SELECT 1'))
    except Exception as e:
        print(f"DB Error: {e}")

def get_current_theme():
    username = session.get('username')
    if not username: return 'luxury-gold'
    user_data = load_data(username=username)
    return user_data.get('settings', {}).get('theme', 'luxury-gold')

@app.context_processor
def inject_global_vars():
    username = session.get('username')
    return {
        'current_theme': get_current_theme(),
        'is_demo_mode': session.get('is_demo_mode', False),
        'is_admin': session.get('is_admin', False),
        'username': username,
        'current_year': datetime.now().year
    }

ADMIN_CREDENTIALS = {
    'username': os.environ.get('ADMIN_USERNAME', 'admin'),
    'password_hash': generate_password_hash(os.environ.get('ADMIN_PASSWORD', 'Codexx@123456'))
}

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_logged_in' not in session:
            return redirect(url_for('dashboard_login'))
        return f(*args, **kwargs)
    return decorated_function

def disable_in_demo(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('is_demo_mode'):
            flash('Action disabled in demo mode', 'warning')
            return redirect(request.referrer or url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def load_data(username=None):
    if os.path.exists('data.json'):
        with open('data.json', 'r') as f: return json.load(f)
    return {}

@app.route('/')
def landing():
    return render_template('landing.html')

@app.route('/dashboard/login', methods=['GET', 'POST'])
def dashboard_login():
    if request.method == 'POST':
        u = request.form.get('username')
        p = request.form.get('password')
        user = User.query.filter_by(username=u).first()
        if user and check_password_hash(user.password_hash, p):
            session.update({'admin_logged_in':True,'username':u,'user_id':user.id,'is_admin':user.role=='admin','is_demo_mode':user.role=='demo'})
            return redirect(url_for('dashboard'))
        if u == ADMIN_CREDENTIALS['username'] and check_password_hash(ADMIN_CREDENTIALS['password_hash'], p):
            session.update({'admin_logged_in':True,'username':u,'is_admin':True,'is_demo_mode':False})
            return redirect(url_for('dashboard'))
        flash('Invalid credentials', 'error')
    return render_template('dashboard/login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard/index.html')

@app.route('/dashboard/change_password', methods=['GET', 'POST'])
@login_required
@disable_in_demo
def dashboard_change_password():
    if request.method == 'POST':
        curr = request.form.get('current_password')
        new = request.form.get('new_password')
        user = User.query.filter_by(username=session['username']).first()
        if user and check_password_hash(user.password_hash, curr):
            user.password_hash = generate_password_hash(new)
            db.session.commit()
            flash('Password updated', 'success')
            return redirect(url_for('dashboard_settings'))
        flash('Invalid current password', 'error')
    return render_template('dashboard/change_password.html')

@app.route('/dashboard/settings')
@login_required
def dashboard_settings():
    return render_template('dashboard/settings.html', themes=[{'id':'luxury-gold','name':'Luxury Gold','icon':'fas fa-crown','description':'Premium design'}])

@app.route('/dashboard/logout')
def dashboard_logout():
    session.clear()
    return redirect(url_for('dashboard_login'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
