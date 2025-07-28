from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from app.auth import bp
from app.models import User, Machine, UserMachineAssignment, db

@bp.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = bool(request.form.get('remember'))
        
        if not username or not password:
            flash('Please enter both username and password.', 'error')
            return render_template('auth/login.html')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password) and user.is_active:
            login_user(user, remember=remember)
            next_page = request.args.get('next')
            if not next_page or not next_page.startswith('/'):
                next_page = url_for('dashboard.index')
            return redirect(next_page)
        else:
            flash('Invalid username or password.', 'error')
    
    return render_template('auth/login.html')

@bp.route('/logout')
@login_required
def logout():
    """Handle user logout"""
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('auth.login'))

@bp.route('/users')
@login_required
def list_users():
    """List all users (admin and manager only)"""
    if current_user.role not in ['admin', 'manager']:
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard.index'))
    
    users = User.query.all()
    return render_template('auth/users.html', users=users)

@bp.route('/users/create', methods=['GET', 'POST'])
@login_required
def create_user():
    """Create new user (admin and manager only)"""
    if current_user.role not in ['admin', 'manager']:
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard.index'))
    
    # Managers can only create engineers
    allowed_roles = ['engineer'] if current_user.role == 'manager' else ['admin', 'manager', 'engineer']
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role')
        
        # Validation
        if not all([username, email, password, role]):
            flash('All fields are required.', 'error')
            return render_template('auth/create_user.html', allowed_roles=allowed_roles)
        
        if role not in allowed_roles:
            flash('Invalid role selected.', 'error')
            return render_template('auth/create_user.html', allowed_roles=allowed_roles)
        
        # Check if user already exists
        if User.query.filter_by(username=username).first():
            flash('Username already exists.', 'error')
            return render_template('auth/create_user.html', allowed_roles=allowed_roles)
        
        if User.query.filter_by(email=email).first():
            flash('Email already exists.', 'error')
            return render_template('auth/create_user.html', allowed_roles=allowed_roles)
        
        # Create new user
        user = User(username=username, email=email, role=role)
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        flash(f'User {username} created successfully.', 'success')
        return redirect(url_for('auth.list_users'))
    
    return render_template('auth/create_user.html', allowed_roles=allowed_roles)

@bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_user(user_id):
    """Edit user (admin only, or manager editing engineers)"""
    if current_user.role not in ['admin', 'manager']:
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard.index'))
    
    user = User.query.get_or_404(user_id)
    
    # Managers can only edit engineers
    if current_user.role == 'manager' and user.role != 'engineer':
        flash('Access denied.', 'error')
        return redirect(url_for('auth.list_users'))
    
    allowed_roles = ['engineer'] if current_user.role == 'manager' else ['admin', 'manager', 'engineer']
    
    if request.method == 'POST':
        email = request.form.get('email')
        role = request.form.get('role')
        is_active = bool(request.form.get('is_active'))
        password = request.form.get('password')
        
        if not email or not role:
            flash('Email and role are required.', 'error')
            return render_template('auth/edit_user.html', user=user, allowed_roles=allowed_roles)
        
        if role not in allowed_roles:
            flash('Invalid role selected.', 'error')
            return render_template('auth/edit_user.html', user=user, allowed_roles=allowed_roles)
        
        # Check email uniqueness
        existing_user = User.query.filter_by(email=email).first()
        if existing_user and existing_user.user_id != user_id:
            flash('Email already exists.', 'error')
            return render_template('auth/edit_user.html', user=user, allowed_roles=allowed_roles)
        
        # Update user
        user.email = email
        user.role = role
        user.is_active = is_active
        
        if password:
            user.set_password(password)
        
        db.session.commit()
        flash(f'User {user.username} updated successfully.', 'success')
        return redirect(url_for('auth.list_users'))
    
    return render_template('auth/edit_user.html', user=user, allowed_roles=allowed_roles)

@bp.route('/users/<int:user_id>/assign-machines', methods=['GET', 'POST'])
@login_required
def assign_machines(user_id):
    """Assign machines to engineer (manager and admin only)"""
    if current_user.role not in ['admin', 'manager']:
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard.index'))
    
    user = User.query.get_or_404(user_id)
    
    if user.role != 'engineer':
        flash('Can only assign machines to engineers.', 'error')
        return redirect(url_for('auth.list_users'))
    
    machines = Machine.query.filter_by(is_active=True).all()
    assigned_machine_ids = [assignment.machine_id for assignment in user.machine_assignments]
    
    if request.method == 'POST':
        selected_machine_ids = request.form.getlist('machine_ids')
        selected_machine_ids = [int(mid) for mid in selected_machine_ids if mid.isdigit()]
        
        # Remove old assignments
        UserMachineAssignment.query.filter_by(user_id=user_id).delete()
        
        # Add new assignments
        for machine_id in selected_machine_ids:
            assignment = UserMachineAssignment(user_id=user_id, machine_id=machine_id)
            db.session.add(assignment)
        
        db.session.commit()
        flash(f'Machine assignments updated for {user.username}.', 'success')
        return redirect(url_for('auth.list_users'))
    
    return render_template('auth/assign_machines.html', 
                         user=user, 
                         machines=machines, 
                         assigned_machine_ids=assigned_machine_ids)