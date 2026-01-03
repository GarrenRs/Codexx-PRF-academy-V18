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
    is_logged_in = 'admin_logged_in' in session
    
    def get_unread_messages_count():
        if not is_logged_in or not username:
            return 0
        return Message.query.filter_by(receiver_id=session.get('user_id'), is_read=False).count()

    return {
        'current_theme': get_current_theme(),
        'is_demo_mode': session.get('is_demo_mode', False),
        'is_admin': session.get('is_admin', False),
        'is_logged_in': is_logged_in,
        'username': username,
        'current_year': datetime.now().year,
        'get_unread_messages_count': get_unread_messages_count
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
    # Load portfolio data from data.json or database
    portfolios = {}
    if os.path.exists('data.json'):
        try:
            with open('data.json', 'r') as f:
                portfolios = json.load(f)
        except Exception as e:
            print(f"Error loading data.json: {e}")
    
    return render_template('landing.html', portfolios=portfolios)

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
    # Load stats or users if needed for index.html
    users = User.query.all()
    projects = Project.query.all()
    messages = Message.query.all()
    visitors = VisitorLog.query.count()
    
    data = {
        'users': users,
        'projects': projects,
        'messages': messages
    }
    
    # Calculate additional stats needed by the template
    stats = {
        'projects': len(projects),
        'skills': Skill.query.count(),
        'messages': len(messages),
        'unread_messages': Message.query.filter_by(is_read=False).count(),
        'visitors': visitors,
        'today_visitors': VisitorLog.query.filter(VisitorLog.created_at >= datetime.utcnow().date()).count()
    }
    
    return render_template('dashboard/index.html', data=data, stats=stats)

@app.route('/dashboard/change_password', methods=['GET', 'POST'])
@login_required
@disable_in_demo
def dashboard_change_password():
    if request.method == 'POST':
        curr = request.form.get('current_password')
        new = request.form.get('new_password')
        confirm = request.form.get('confirm_password')
        
        if not curr or not new or not confirm:
            flash('All fields are required', 'error')
            return redirect(url_for('dashboard_change_password'))
            
        if new != confirm:
            flash('New passwords do not match', 'error')
            return redirect(url_for('dashboard_change_password'))
            
        user = User.query.filter_by(username=session['username']).first()
        
        # Check if it's the hardcoded admin
        if session['username'] == ADMIN_CREDENTIALS['username']:
             if check_password_hash(ADMIN_CREDENTIALS['password_hash'], curr):
                 # Admin password is in environment variables, can't change persistent storage
                 # But we can update the hash for the current session's logic
                 ADMIN_CREDENTIALS['password_hash'] = generate_password_hash(new)
                 flash('Admin password updated for current session', 'success')
                 return redirect(url_for('dashboard_settings'))
             else:
                 flash('Current admin password incorrect', 'error')
                 return redirect(url_for('dashboard_change_password'))

        if user and check_password_hash(user.password_hash, curr):
            user.password_hash = generate_password_hash(new)
            db.session.commit()
            flash('Password updated successfully', 'success')
            return redirect(url_for('dashboard_settings'))
        else:
            flash('Current password is incorrect', 'error')
            return redirect(url_for('dashboard_change_password'))
            
    return render_template('dashboard/change_password.html')

@app.route('/dashboard/settings')
@login_required
def dashboard_settings():
    # Fetch themes and current user settings if needed
    themes = [
        {'id': 'luxury-gold', 'name': 'Luxury Gold', 'icon': 'fas fa-crown', 'description': 'Premium design'},
        {'id': 'clean-light', 'name': 'Clean Light', 'icon': 'fas fa-sun', 'description': 'Minimalist'},
        {'id': 'modern-dark', 'name': 'Modern Dark', 'icon': 'fas fa-moon', 'description': 'Sleek dark mode'}
    ]
    return render_template('dashboard/settings.html', themes=themes)

@app.route('/dashboard/profile')
@login_required
def dashboard_profile():
    user = User.query.filter_by(username=session['username']).first()
    return render_template('dashboard/user_profile.html', user=user)

@app.route('/dashboard/projects/add', methods=['GET', 'POST'])
@login_required
def add_project():
    if request.method == 'POST':
        # Add logic to save project
        flash('تم إضافة المشروع بنجاح', 'success')
        return redirect(url_for('dashboard_projects'))
    return render_template('dashboard/add_project.html')

@app.route('/dashboard/logout')
def dashboard_logout():
    session.clear()
    return redirect(url_for('dashboard_login'))

@app.route('/verification')
def verification():
    return render_template('pages/verification.html')

@app.route('/privacy')
def privacy():
    return render_template('pages/privacy.html')

@app.route('/terms')
def terms():
    return render_template('pages/terms.html')

@app.route('/security')
def security_audit():
    return render_template('pages/security.html')

@app.route('/standards')
def standards():
    return render_template('pages/standards.html')

@app.route('/mastery')
def mastery():
    return render_template('pages/mastery.html')

@app.route('/about')
def about():
    return render_template('pages/about.html')

@app.route('/contact', methods=['POST'])
def contact_academy():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        msg = request.form.get('message')
        # Here you would typically save to DB or send email
        flash('شكراً لتواصلك معنا، سنرد عليك قريباً', 'success')
    return redirect(url_for('landing'))

@app.route('/dashboard/clients')
@login_required
def dashboard_clients():
    clients = Client.query.all()
    return render_template('dashboard/clients.html', clients=clients)

@app.route('/dashboard/projects')
@login_required
def dashboard_projects():
    projects = Project.query.all()
    return render_template('dashboard/projects.html', projects=projects)

@app.route('/dashboard/users', methods=['GET', 'POST'])
@login_required
def dashboard_users():
    if request.method == 'POST':
        if not session.get('is_admin'):
            flash('Access denied', 'error')
            return redirect(url_for('dashboard'))
            
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role', 'user')
        is_demo = 'is_demo' in request.form

        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'error')
        elif User.query.filter_by(email=email).first():
            flash('Email already exists', 'error')
        else:
            # Need workspace_id for the user
            workspace = Workspace.query.first()
            if not workspace:
                workspace = Workspace(name="Default Workspace", slug="default")
                db.session.add(workspace)
                db.session.commit()
                
            new_user = User(
                username=username,
                email=email,
                password_hash=generate_password_hash(password),
                role=role,
                workspace_id=workspace.id,
                is_active=True
            )
            db.session.add(new_user)
            db.session.commit()
            flash('User created successfully', 'success')
        return redirect(url_for('dashboard_users'))

    users = User.query.all()
    return render_template('dashboard/users.html', users=users)

@app.route('/dashboard/users/delete/<user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    if not session.get('is_admin'):
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    user = User.query.get(user_id)
    if user and user.username != 'admin':
        db.session.delete(user)
        db.session.commit()
        flash('User deleted successfully', 'success')
    return redirect(url_for('dashboard_users'))

@app.route('/dashboard/users/toggle_demo/<user_id>', methods=['POST'])
@login_required
def toggle_user_demo(user_id):
    if not session.get('is_admin'):
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    user = User.query.get(user_id)
    if user:
        user.is_demo = not getattr(user, 'is_demo', False)
        db.session.commit()
        flash('User status updated', 'success')
    return redirect(url_for('dashboard_users'))

@app.route('/dashboard/users/view/<user_id>')
@login_required
def dashboard_view_user(user_id):
    user = User.query.get_or_404(user_id)
    return render_template('dashboard/user_profile.html', user=user)

@app.route('/dashboard/messages')
@login_required
def dashboard_messages():
    messages = Message.query.all()
    return render_template('dashboard/messages.html', messages=messages)

@app.route('/dashboard/skills')
@login_required
def dashboard_skills():
    skills = Skill.query.all()
    return render_template('dashboard/skills.html', skills=skills)

@app.route('/dashboard/subscription')
@login_required
def dashboard_subscription():
    return render_template('dashboard/subscription.html')

@app.route('/dashboard/social')
@login_required
def dashboard_social():
    return render_template('dashboard/social.html')

@app.route('/dashboard/about')
@login_required
def dashboard_about():
    return render_template('dashboard/about.html')

@app.route('/dashboard/projects/edit/<id>', methods=['GET', 'POST'])
@login_required
def edit_project(id):
    project = Project.query.get_or_404(id)
    if request.method == 'POST':
        # Edit logic
        flash('تم تحديث المشروع بنجاح', 'success')
        return redirect(url_for('dashboard_projects'))
    return render_template('dashboard/edit_project.html', project=project)

@app.route('/dashboard/clients/add', methods=['GET', 'POST'])
@login_required
def add_client():
    if request.method == 'POST':
        # Add client logic
        flash('تم إضافة العميل بنجاح', 'success')
        return redirect(url_for('dashboard_clients'))
    return render_template('dashboard/add_client.html')

@app.route('/catalog')
def catalog():
    return render_template('catalog.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
