from flask import render_template, request, jsonify
from flask_login import login_required, current_user
from flask_socketio import emit
from sqlalchemy import and_
from datetime import datetime, timedelta
from app.dashboard import bp
from app.models import Machine, Parameter, SensorData, Alert, db
from app import socketio

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    print(f'Client connected: {request.sid}')

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    print(f'Client disconnected: {request.sid}')

@socketio.on('heartbeat')
def handle_heartbeat():
    """Handle client heartbeat"""
    emit('pong')

def broadcast_sensor_update(parameter_id, value, timestamp):
    """Broadcast sensor data update to all connected clients"""
    socketio.emit('sensor_data_update', {
        'parameter_id': parameter_id,
        'value': value,
        'timestamp': timestamp.isoformat()
    })

def broadcast_alert(alert):
    """Broadcast new alert to all connected clients"""
    socketio.emit('alert_created', {
        'alert_id': alert.alert_id,
        'parameter_id': alert.parameter_id,
        'parameter_name': alert.parameter.name,
        'message': alert.message,
        'severity': alert.severity,
        'created_at': alert.created_at.isoformat()
    })

@bp.route('/')
@login_required
def index():
    """Dashboard main page"""
    # Get machines based on user role
    if current_user.role == 'engineer':
        # Engineers can only see assigned machines
        assigned_machine_ids = [assignment.machine_id for assignment in current_user.machine_assignments]
        machines = Machine.query.filter(
            and_(Machine.machine_id.in_(assigned_machine_ids), Machine.is_active == True)
        ).all() if assigned_machine_ids else []
    else:
        # Managers and admins can see all machines
        machines = Machine.query.filter_by(is_active=True).all()
    
    # Get recent alerts
    recent_alerts = Alert.query.filter_by(is_acknowledged=False)\
                              .order_by(Alert.created_at.desc())\
                              .limit(10).all()
    
    return render_template('dashboard/index.html', machines=machines, recent_alerts=recent_alerts)

@bp.route('/machine/<int:machine_id>')
@login_required
def machine_detail(machine_id):
    """Machine detail dashboard"""
    machine = Machine.query.get_or_404(machine_id)
    
    # Check access permissions
    if current_user.role == 'engineer' and not current_user.can_access_machine(machine_id):
        return jsonify({'error': 'Access denied'}), 403
    
    parameters = Parameter.query.filter_by(machine_id=machine_id, is_active=True).all()
    
    # Get latest values for each parameter
    parameter_data = []
    for param in parameters:
        latest_data = SensorData.query.filter_by(parameter_id=param.parameter_id)\
                                    .order_by(SensorData.timestamp.desc()).first()
        
        param_dict = param.to_dict()
        param_dict['latest_data'] = latest_data.to_dict() if latest_data else None
        parameter_data.append(param_dict)
    
    return render_template('dashboard/machine_detail.html', 
                         machine=machine, 
                         parameters=parameter_data)

@bp.route('/parameter/<int:parameter_id>')
@login_required
def parameter_detail(parameter_id):
    """Parameter detail view with historical data"""
    parameter = Parameter.query.get_or_404(parameter_id)
    machine = parameter.machine
    
    # Check access permissions
    if current_user.role == 'engineer' and not current_user.can_access_machine(machine.machine_id):
        return jsonify({'error': 'Access denied'}), 403
    
    # Get time range from query parameters
    hours = request.args.get('hours', default=24, type=int)
    start_time = datetime.utcnow() - timedelta(hours=hours)
    
    # Get historical data
    historical_data = SensorData.query.filter(
        and_(
            SensorData.parameter_id == parameter_id,
            SensorData.timestamp >= start_time
        )
    ).order_by(SensorData.timestamp.asc()).all()
    
    # Get parameter alerts
    parameter_alerts = Alert.query.filter_by(parameter_id=parameter_id)\
                                 .order_by(Alert.created_at.desc())\
                                 .limit(20).all()
    
    return render_template('dashboard/parameter_detail.html',
                         parameter=parameter,
                         machine=machine,
                         historical_data=historical_data,
                         alerts=parameter_alerts,
                         hours=hours)

@bp.route('/api/machine/<int:machine_id>/live-data')
@login_required
def api_machine_live_data(machine_id):
    """API endpoint for live machine data"""
    machine = Machine.query.get_or_404(machine_id)
    
    # Check access permissions
    if current_user.role == 'engineer' and not current_user.can_access_machine(machine_id):
        return jsonify({'error': 'Access denied'}), 403
    
    parameters = Parameter.query.filter_by(machine_id=machine_id, is_active=True).all()
    
    live_data = []
    for param in parameters:
        latest_data = SensorData.query.filter_by(parameter_id=param.parameter_id)\
                                    .order_by(SensorData.timestamp.desc()).first()
        
        if latest_data:
            live_data.append({
                'parameter_id': param.parameter_id,
                'name': param.name,
                'value': float(latest_data.value),
                'unit': param.unit,
                'timestamp': latest_data.timestamp.isoformat(),
                'register_address': param.register_address,
                'min_value': float(param.min_value) if param.min_value else None,
                'max_value': float(param.max_value) if param.max_value else None
            })
    
    return jsonify({
        'machine_id': machine_id,
        'machine_name': machine.name,
        'timestamp': datetime.utcnow().isoformat(),
        'parameters': live_data
    })

@bp.route('/api/parameter/<int:parameter_id>/history')
@login_required
def api_parameter_history(parameter_id):
    """API endpoint for parameter historical data"""
    parameter = Parameter.query.get_or_404(parameter_id)
    
    # Check access permissions
    if current_user.role == 'engineer' and not current_user.can_access_machine(parameter.machine_id):
        return jsonify({'error': 'Access denied'}), 403
    
    # Get time range from query parameters
    hours = request.args.get('hours', default=24, type=int)
    start_time = datetime.utcnow() - timedelta(hours=hours)
    
    # Get historical data
    historical_data = SensorData.query.filter(
        and_(
            SensorData.parameter_id == parameter_id,
            SensorData.timestamp >= start_time
        )
    ).order_by(SensorData.timestamp.asc()).all()
    
    data_points = []
    for data in historical_data:
        data_points.append({
            'timestamp': data.timestamp.isoformat(),
            'value': float(data.value),
            'quality_code': data.quality_code
        })
    
    return jsonify({
        'parameter_id': parameter_id,
        'parameter_name': parameter.name,
        'unit': parameter.unit,
        'min_value': float(parameter.min_value) if parameter.min_value else None,
        'max_value': float(parameter.max_value) if parameter.max_value else None,
        'data_points': data_points,
        'total_points': len(data_points)
    })

@bp.route('/api/alerts')
@login_required
def api_alerts():
    """API endpoint for alerts"""
    # Get alerts based on user role
    if current_user.role == 'engineer':
        # Engineers can only see alerts for assigned machines
        assigned_machine_ids = [assignment.machine_id for assignment in current_user.machine_assignments]
        if not assigned_machine_ids:
            return jsonify({'alerts': []})
        
        alerts = db.session.query(Alert).join(Parameter).join(Machine)\
                          .filter(Machine.machine_id.in_(assigned_machine_ids))\
                          .order_by(Alert.created_at.desc()).all()
    else:
        # Managers and admins can see all alerts
        alerts = Alert.query.order_by(Alert.created_at.desc()).all()
    
    # Filter by acknowledged status if requested
    show_acknowledged = request.args.get('acknowledged', default='false').lower() == 'true'
    if not show_acknowledged:
        alerts = [alert for alert in alerts if not alert.is_acknowledged]
    
    # Limit results
    limit = request.args.get('limit', default=50, type=int)
    alerts = alerts[:limit]
    
    return jsonify({
        'alerts': [alert.to_dict() for alert in alerts],
        'total_count': len(alerts)
    })

@bp.route('/api/alerts/<int:alert_id>/acknowledge', methods=['POST'])
@login_required
def api_acknowledge_alert(alert_id):
    """API endpoint to acknowledge an alert"""
    alert = Alert.query.get_or_404(alert_id)
    
    # Check access permissions
    parameter = alert.parameter
    if current_user.role == 'engineer' and not current_user.can_access_machine(parameter.machine_id):
        return jsonify({'error': 'Access denied'}), 403
    
    alert.is_acknowledged = True
    alert.acknowledged_by = current_user.user_id
    alert.acknowledged_at = datetime.utcnow()
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Alert acknowledged successfully',
        'alert': alert.to_dict()
    })

@bp.route('/api/dashboard-summary')
@login_required
def api_dashboard_summary():
    """API endpoint for dashboard summary data"""
    # Get machines based on user role
    if current_user.role == 'engineer':
        assigned_machine_ids = [assignment.machine_id for assignment in current_user.machine_assignments]
        machines = Machine.query.filter(
            and_(Machine.machine_id.in_(assigned_machine_ids), Machine.is_active == True)
        ).all() if assigned_machine_ids else []
    else:
        machines = Machine.query.filter_by(is_active=True).all()
    
    # Count total parameters
    total_parameters = sum(len(machine.parameters) for machine in machines)
    
    # Count active alerts
    if current_user.role == 'engineer':
        assigned_machine_ids = [assignment.machine_id for assignment in current_user.machine_assignments]
        if assigned_machine_ids:
            active_alerts = db.session.query(Alert).join(Parameter).join(Machine)\
                                    .filter(
                                        and_(
                                            Machine.machine_id.in_(assigned_machine_ids),
                                            Alert.is_acknowledged == False
                                        )
                                    ).count()
        else:
            active_alerts = 0
    else:
        active_alerts = Alert.query.filter_by(is_acknowledged=False).count()
    
    # Get latest data timestamp
    latest_data = SensorData.query.order_by(SensorData.timestamp.desc()).first()
    last_update = latest_data.timestamp.isoformat() if latest_data else None
    
    return jsonify({
        'total_machines': len(machines),
        'total_parameters': total_parameters,
        'active_alerts': active_alerts,
        'last_update': last_update,
        'user_role': current_user.role
    })