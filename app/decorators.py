from functools import wraps
from flask import redirect, url_for, flash
from flask_login import current_user


def sales_required(f):
    """Decorator to require sales role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('login'))
        if current_user.role != 'sales':
            flash('Access denied. Sales role required.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function 