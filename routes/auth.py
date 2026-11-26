from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash
from functools import wraps
from services.db_model import User

auth_bp = Blueprint('auth', __name__)

def roles_required(*roles):
    """
    Decorator to restrict route access based on User Role.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login', next=request.url))
            if current_user.role not in roles:
                flash("Access Denied: You do not possess the required clinical privileges.", "danger")
                return redirect(url_for('main.dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
        
    next_url = request.args.get('next')
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        remember = True if request.form.get('remember') else False
        
        user = User.query.filter_by(username=username).first()
        
        if not user or not check_password_hash(user.password_hash, password):
            flash("Invalid username or password. Please try again.", "danger")
            return redirect(url_for('auth.login', next=next_url))
            
        login_user(user, remember=remember)
        flash(f"Welcome back, {user.name}!", "success")
        
        if next_url:
            return redirect(next_url)
        return redirect(url_for('main.dashboard'))
        
    return render_template('auth/login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash("You have successfully signed out.", "success")
    return redirect(url_for('auth.login'))
