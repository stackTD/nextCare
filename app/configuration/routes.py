from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app.configuration import bp
from app.models import Machine, Parameter, db

@bp.route('/')
@login_required
def index():
    """Configuration main page"""
    if current_user.role == 'engineer':
        flash('Access denied. Engineers cannot access configuration.', 'error')
        return redirect(url_for('dashboard.index'))
    
    machines = Machine.query.filter_by(is_active=True).all()
    return render_template('configuration/index.html', machines=machines)

@bp.route('/machines')
@login_required
def list_machines():
    """List all machines"""
    if current_user.role == 'engineer':
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard.index'))
    
    machines = Machine.query.all()
    return render_template('configuration/machines.html', machines=machines)

@bp.route('/machines/create', methods=['GET', 'POST'])
@login_required
def create_machine():
    """Create new machine (admin only)"""
    if current_user.role != 'admin':
        flash('Access denied. Only administrators can create machines.', 'error')
        return redirect(url_for('config.list_machines'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        location = request.form.get('location')
        
        if not name:
            flash('Machine name is required.', 'error')
            return render_template('configuration/create_machine.html')
        
        # Check if machine name already exists
        if Machine.query.filter_by(name=name).first():
            flash('Machine name already exists.', 'error')
            return render_template('configuration/create_machine.html')
        
        machine = Machine(name=name, description=description, location=location)
        db.session.add(machine)
        db.session.commit()
        
        flash(f'Machine "{name}" created successfully.', 'success')
        return redirect(url_for('config.edit_machine', machine_id=machine.machine_id))
    
    return render_template('configuration/create_machine.html')

@bp.route('/machines/<int:machine_id>')
@login_required
def view_machine(machine_id):
    """View machine details"""
    if current_user.role == 'engineer':
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard.index'))
    
    machine = Machine.query.get_or_404(machine_id)
    parameters = Parameter.query.filter_by(machine_id=machine_id).all()
    
    return render_template('configuration/view_machine.html', machine=machine, parameters=parameters)

@bp.route('/machines/<int:machine_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_machine(machine_id):
    """Edit machine (admin only)"""
    if current_user.role != 'admin':
        flash('Access denied. Only administrators can edit machines.', 'error')
        return redirect(url_for('config.view_machine', machine_id=machine_id))
    
    machine = Machine.query.get_or_404(machine_id)
    
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        location = request.form.get('location')
        is_active = bool(request.form.get('is_active'))
        
        if not name:
            flash('Machine name is required.', 'error')
            return render_template('configuration/edit_machine.html', machine=machine)
        
        # Check if machine name already exists (excluding current machine)
        existing_machine = Machine.query.filter_by(name=name).first()
        if existing_machine and existing_machine.machine_id != machine_id:
            flash('Machine name already exists.', 'error')
            return render_template('configuration/edit_machine.html', machine=machine)
        
        machine.name = name
        machine.description = description
        machine.location = location
        machine.is_active = is_active
        
        db.session.commit()
        flash(f'Machine "{name}" updated successfully.', 'success')
        return redirect(url_for('config.view_machine', machine_id=machine_id))
    
    return render_template('configuration/edit_machine.html', machine=machine)

@bp.route('/machines/<int:machine_id>/parameters')
@login_required
def list_parameters(machine_id):
    """List parameters for a machine"""
    if current_user.role == 'engineer':
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard.index'))
    
    machine = Machine.query.get_or_404(machine_id)
    parameters = Parameter.query.filter_by(machine_id=machine_id).all()
    
    return render_template('configuration/parameters.html', machine=machine, parameters=parameters)

@bp.route('/machines/<int:machine_id>/parameters/create', methods=['GET', 'POST'])
@login_required
def create_parameter(machine_id):
    """Create new parameter for a machine (admin only)"""
    if current_user.role != 'admin':
        flash('Access denied. Only administrators can create parameters.', 'error')
        return redirect(url_for('config.list_parameters', machine_id=machine_id))
    
    machine = Machine.query.get_or_404(machine_id)
    
    if request.method == 'POST':
        name = request.form.get('name')
        register_address = request.form.get('register_address')
        unit = request.form.get('unit')
        min_value = request.form.get('min_value')
        max_value = request.form.get('max_value')
        
        if not all([name, register_address, unit]):
            flash('Name, register address, and unit are required.', 'error')
            return render_template('configuration/create_parameter.html', machine=machine)
        
        # Check if register address already exists for this machine
        if Parameter.query.filter_by(machine_id=machine_id, register_address=register_address).first():
            flash('Register address already exists for this machine.', 'error')
            return render_template('configuration/create_parameter.html', machine=machine)
        
        # Convert min/max values
        try:
            min_val = float(min_value) if min_value else None
            max_val = float(max_value) if max_value else None
        except ValueError:
            flash('Invalid min/max values. Please enter numbers.', 'error')
            return render_template('configuration/create_parameter.html', machine=machine)
        
        parameter = Parameter(
            machine_id=machine_id,
            name=name,
            register_address=register_address,
            unit=unit,
            min_value=min_val,
            max_value=max_val
        )
        
        db.session.add(parameter)
        db.session.commit()
        
        flash(f'Parameter "{name}" created successfully.', 'success')
        return redirect(url_for('config.list_parameters', machine_id=machine_id))
    
    return render_template('configuration/create_parameter.html', machine=machine)

@bp.route('/parameters/<int:parameter_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_parameter(parameter_id):
    """Edit parameter (admin only)"""
    if current_user.role != 'admin':
        flash('Access denied. Only administrators can edit parameters.', 'error')
        return redirect(url_for('dashboard.index'))
    
    parameter = Parameter.query.get_or_404(parameter_id)
    machine = parameter.machine
    
    if request.method == 'POST':
        name = request.form.get('name')
        register_address = request.form.get('register_address')
        unit = request.form.get('unit')
        min_value = request.form.get('min_value')
        max_value = request.form.get('max_value')
        is_active = bool(request.form.get('is_active'))
        
        if not all([name, register_address, unit]):
            flash('Name, register address, and unit are required.', 'error')
            return render_template('configuration/edit_parameter.html', parameter=parameter, machine=machine)
        
        # Check if register address already exists for this machine (excluding current parameter)
        existing_param = Parameter.query.filter_by(
            machine_id=parameter.machine_id, 
            register_address=register_address
        ).first()
        if existing_param and existing_param.parameter_id != parameter_id:
            flash('Register address already exists for this machine.', 'error')
            return render_template('configuration/edit_parameter.html', parameter=parameter, machine=machine)
        
        # Convert min/max values
        try:
            min_val = float(min_value) if min_value else None
            max_val = float(max_value) if max_value else None
        except ValueError:
            flash('Invalid min/max values. Please enter numbers.', 'error')
            return render_template('configuration/edit_parameter.html', parameter=parameter, machine=machine)
        
        parameter.name = name
        parameter.register_address = register_address
        parameter.unit = unit
        parameter.min_value = min_val
        parameter.max_value = max_val
        parameter.is_active = is_active
        
        db.session.commit()
        flash(f'Parameter "{name}" updated successfully.', 'success')
        return redirect(url_for('config.list_parameters', machine_id=parameter.machine_id))
    
    return render_template('configuration/edit_parameter.html', parameter=parameter, machine=machine)

@bp.route('/parameters/<int:parameter_id>/delete', methods=['POST'])
@login_required
def delete_parameter(parameter_id):
    """Delete parameter (admin only)"""
    if current_user.role != 'admin':
        flash('Access denied. Only administrators can delete parameters.', 'error')
        return redirect(url_for('dashboard.index'))
    
    parameter = Parameter.query.get_or_404(parameter_id)
    machine_id = parameter.machine_id
    parameter_name = parameter.name
    
    db.session.delete(parameter)
    db.session.commit()
    
    flash(f'Parameter "{parameter_name}" deleted successfully.', 'success')
    return redirect(url_for('config.list_parameters', machine_id=machine_id))

@bp.route('/api/machines', methods=['GET'])
@login_required
def api_machines():
    """API endpoint to get machines list"""
    if current_user.role == 'engineer':
        return jsonify({'error': 'Access denied'}), 403
    
    machines = Machine.query.filter_by(is_active=True).all()
    return jsonify({
        'machines': [machine.to_dict() for machine in machines]
    })

@bp.route('/api/machines/<int:machine_id>/parameters', methods=['GET'])
@login_required
def api_machine_parameters(machine_id):
    """API endpoint to get parameters for a machine"""
    if current_user.role == 'engineer':
        return jsonify({'error': 'Access denied'}), 403
    
    machine = Machine.query.get_or_404(machine_id)
    parameters = Parameter.query.filter_by(machine_id=machine_id, is_active=True).all()
    
    return jsonify({
        'machine': machine.to_dict(),
        'parameters': [param.to_dict() for param in parameters]
    })