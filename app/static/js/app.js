/**
 * NextCare Industrial Monitoring System - Main JavaScript
 * Handles real-time updates, WebSocket connections, and UI interactions
 */

class NextCareApp {
    constructor() {
        this.socket = null;
        this.refreshIntervals = {};
        this.charts = {};
        this.isOnline = true;
        
        this.init();
    }
    
    init() {
        this.initializeWebSocket();
        this.setupEventListeners();
        this.startHeartbeat();
        
        console.log('NextCare application initialized');
    }
    
    initializeWebSocket() {
        // Initialize Socket.IO connection for real-time updates
        this.socket = io();
        
        this.socket.on('connect', () => {
            console.log('Connected to server');
            this.setConnectionStatus(true);
        });
        
        this.socket.on('disconnect', () => {
            console.log('Disconnected from server');
            this.setConnectionStatus(false);
        });
        
        this.socket.on('sensor_data_update', (data) => {
            this.handleSensorDataUpdate(data);
        });
        
        this.socket.on('alert_created', (alert) => {
            this.handleNewAlert(alert);
        });
        
        this.socket.on('system_status', (status) => {
            this.handleSystemStatusUpdate(status);
        });
    }
    
    setupEventListeners() {
        // Global error handler
        window.addEventListener('error', (event) => {
            console.error('Application error:', event.error);
            this.showNotification('An error occurred. Please refresh the page.', 'error');
        });
        
        // Handle visibility change to pause/resume updates
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                this.pauseUpdates();
            } else {
                this.resumeUpdates();
            }
        });
        
        // Setup navigation active states
        this.updateNavigation();
    }
    
    startHeartbeat() {
        // Send heartbeat every 30 seconds to maintain connection
        setInterval(() => {
            if (this.socket && this.socket.connected) {
                this.socket.emit('heartbeat');
            }
        }, 30000);
    }
    
    setConnectionStatus(isConnected) {
        this.isOnline = isConnected;
        const statusElement = document.getElementById('connectionStatus');
        
        if (statusElement) {
            statusElement.className = isConnected ? 'status-good' : 'status-danger';
            statusElement.title = isConnected ? 'Connected' : 'Disconnected';
        }
        
        // Show notification if disconnected
        if (!isConnected) {
            this.showNotification('Connection lost. Attempting to reconnect...', 'warning', 5000);
        }
    }
    
    handleSensorDataUpdate(data) {
        // Update parameter values in real-time
        const { parameter_id, value, timestamp } = data;
        
        // Update value display
        const valueElement = document.getElementById(`param-${parameter_id}-value`);
        if (valueElement) {
            valueElement.textContent = parseFloat(value).toFixed(2);
        }
        
        // Update timestamp
        const timestampElement = document.getElementById(`param-${parameter_id}-timestamp`);
        if (timestampElement) {
            timestampElement.textContent = new Date(timestamp).toLocaleTimeString();
        }
        
        // Update chart if exists
        this.updateParameterChart(parameter_id, value, timestamp);
        
        // Update status indicator
        this.updateParameterStatus(parameter_id, data);
    }
    
    handleNewAlert(alert) {
        // Show new alert notification
        this.showNotification(
            `New ${alert.severity} alert: ${alert.message}`,
            alert.severity === 'critical' ? 'error' : 'warning',
            10000
        );
        
        // Update alert count
        this.updateAlertCount();
        
        // Add alert to alerts list if visible
        this.addAlertToList(alert);
    }
    
    handleSystemStatusUpdate(status) {
        // Update system status indicators
        const { plc_connected, data_collection_active, last_update } = status;
        
        // Update PLC status
        const plcStatusElement = document.getElementById('plcStatus');
        if (plcStatusElement) {
            plcStatusElement.className = plc_connected ? 'status-good' : 'status-danger';
            plcStatusElement.title = plc_connected ? 'PLC Connected' : 'PLC Disconnected';
        }
        
        // Update data collection status
        const dataStatusElement = document.getElementById('dataCollectionStatus');
        if (dataStatusElement) {
            dataStatusElement.className = data_collection_active ? 'status-good' : 'status-warning';
            dataStatusElement.title = data_collection_active ? 'Data Collection Active' : 'Data Collection Paused';
        }
        
        // Update last update time
        const lastUpdateElement = document.getElementById('lastUpdate');
        if (lastUpdateElement && last_update) {
            lastUpdateElement.textContent = new Date(last_update).toLocaleTimeString();
        }
    }
    
    updateParameterChart(parameterId, value, timestamp) {
        const chart = this.charts[parameterId];
        if (chart) {
            const time = new Date(timestamp);
            
            // Add new data point
            chart.data.labels.push(time.toLocaleTimeString());
            chart.data.datasets[0].data.push(parseFloat(value));
            
            // Keep only last 50 points
            if (chart.data.labels.length > 50) {
                chart.data.labels.shift();
                chart.data.datasets[0].data.shift();
            }
            
            chart.update('none');
        }
    }
    
    updateParameterStatus(parameterId, data) {
        const { value, min_value, max_value } = data;
        const statusElement = document.getElementById(`param-${parameterId}-status`);
        
        if (statusElement) {
            let status = 'good';
            let icon = 'check-circle';
            
            if (min_value !== null && value < min_value) {
                status = 'danger';
                icon = 'exclamation-triangle';
            } else if (max_value !== null && value > max_value) {
                status = 'danger';
                icon = 'exclamation-triangle';
            }
            
            statusElement.className = `status-${status}`;
            statusElement.innerHTML = `<i class="bi bi-${icon}"></i>`;
        }
    }
    
    updateAlertCount() {
        fetch('/dashboard/api/alerts')
            .then(response => response.json())
            .then(data => {
                const alertCountElement = document.getElementById('activeAlerts');
                if (alertCountElement) {
                    alertCountElement.textContent = data.total_count;
                }
            })
            .catch(error => console.error('Error updating alert count:', error));
    }
    
    addAlertToList(alert) {
        const alertsList = document.getElementById('alertsList');
        if (alertsList) {
            const alertElement = this.createAlertElement(alert);
            alertsList.insertBefore(alertElement, alertsList.firstChild);
            
            // Remove old alerts if more than 10
            const alerts = alertsList.children;
            if (alerts.length > 10) {
                alertsList.removeChild(alerts[alerts.length - 1]);
            }
        }
    }
    
    createAlertElement(alert) {
        const div = document.createElement('div');
        div.className = `alert-item alert-${alert.severity}`;
        div.innerHTML = `
            <div class="d-flex justify-content-between align-items-start">
                <div>
                    <strong>${alert.parameter_name}</strong>
                    <br>
                    <small>${alert.message}</small>
                    <br>
                    <small class="text-muted">
                        <i class="bi bi-clock"></i> ${new Date(alert.created_at).toLocaleTimeString()}
                    </small>
                </div>
                <button class="btn btn-sm btn-outline-secondary" 
                        onclick="nextCareApp.acknowledgeAlert(${alert.alert_id})">
                    <i class="bi bi-check"></i>
                </button>
            </div>
        `;
        return div;
    }
    
    acknowledgeAlert(alertId) {
        fetch(`/dashboard/api/alerts/${alertId}/acknowledge`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                this.showNotification('Alert acknowledged', 'success');
                // Remove alert from UI
                const alertElement = document.querySelector(`[data-alert-id="${alertId}"]`);
                if (alertElement) {
                    alertElement.remove();
                }
                this.updateAlertCount();
            }
        })
        .catch(error => {
            console.error('Error acknowledging alert:', error);
            this.showNotification('Failed to acknowledge alert', 'error');
        });
    }
    
    showNotification(message, type = 'info', duration = 5000) {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show position-fixed`;
        notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
        
        notification.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        document.body.appendChild(notification);
        
        // Auto-remove after duration
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, duration);
    }
    
    startRefreshInterval(name, callback, interval) {
        this.stopRefreshInterval(name);
        this.refreshIntervals[name] = setInterval(callback, interval);
    }
    
    stopRefreshInterval(name) {
        if (this.refreshIntervals[name]) {
            clearInterval(this.refreshIntervals[name]);
            delete this.refreshIntervals[name];
        }
    }
    
    pauseUpdates() {
        // Pause all refresh intervals when page is hidden
        Object.keys(this.refreshIntervals).forEach(name => {
            clearInterval(this.refreshIntervals[name]);
        });
    }
    
    resumeUpdates() {
        // Resume updates when page becomes visible again
        if (document.location.pathname.includes('/dashboard')) {
            this.startDashboardUpdates();
        }
    }
    
    startDashboardUpdates() {
        // Start dashboard-specific updates
        this.startRefreshInterval('dashboard', () => {
            this.refreshDashboardData();
        }, 30000); // 30 seconds
    }
    
    refreshDashboardData() {
        if (!this.isOnline) return;
        
        // Refresh summary data
        fetch('/dashboard/api/dashboard-summary')
            .then(response => response.json())
            .then(data => {
                this.updateDashboardSummary(data);
            })
            .catch(error => console.error('Error refreshing dashboard:', error));
    }
    
    updateDashboardSummary(data) {
        const elements = {
            'totalMachines': data.total_machines,
            'totalParameters': data.total_parameters,
            'activeAlerts': data.active_alerts
        };
        
        Object.entries(elements).forEach(([id, value]) => {
            const element = document.getElementById(id);
            if (element) {
                element.textContent = value;
            }
        });
        
        if (data.last_update) {
            const lastUpdateElement = document.getElementById('lastUpdate');
            if (lastUpdateElement) {
                lastUpdateElement.textContent = new Date(data.last_update).toLocaleTimeString();
            }
        }
    }
    
    updateNavigation() {
        // Update active navigation state
        const currentPath = window.location.pathname;
        const navLinks = document.querySelectorAll('.nav-link');
        
        navLinks.forEach(link => {
            const href = link.getAttribute('href');
            if (href && currentPath.startsWith(href)) {
                link.classList.add('active');
            } else {
                link.classList.remove('active');
            }
        });
    }
    
    // Utility methods
    formatValue(value, unit = '') {
        if (value === null || value === undefined) return 'N/A';
        
        const numValue = parseFloat(value);
        if (isNaN(numValue)) return 'N/A';
        
        return `${numValue.toFixed(2)} ${unit}`.trim();
    }
    
    formatTimestamp(timestamp) {
        if (!timestamp) return 'N/A';
        return new Date(timestamp).toLocaleString();
    }
    
    getStatusColor(value, minValue, maxValue) {
        if (minValue !== null && value < minValue) return 'danger';
        if (maxValue !== null && value > maxValue) return 'danger';
        return 'success';
    }
    
    // Chart utilities
    createMiniChart(canvasId, data, options = {}) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return null;
        
        const defaultOptions = {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    data: [],
                    borderColor: '#667eea',
                    backgroundColor: 'rgba(102, 126, 234, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    x: { display: false },
                    y: { display: false }
                },
                elements: { point: { radius: 0 } }
            }
        };
        
        const chartOptions = { ...defaultOptions, ...options };
        const chart = new Chart(ctx.getContext('2d'), chartOptions);
        
        this.charts[canvasId] = chart;
        return chart;
    }
    
    // Page-specific initialization
    initializePage() {
        const path = window.location.pathname;
        
        if (path.includes('/dashboard')) {
            this.initializeDashboard();
        } else if (path.includes('/configuration')) {
            this.initializeConfiguration();
        }
    }
    
    initializeDashboard() {
        this.startDashboardUpdates();
        
        // Initialize any charts on the page
        document.querySelectorAll('[id^="chart-"]').forEach(canvas => {
            const parameterId = canvas.id.replace('chart-', '');
            this.createMiniChart(canvas.id);
        });
    }
    
    initializeConfiguration() {
        // Configuration page specific initialization
        console.log('Configuration page initialized');
    }
}

// Global utility functions
function refreshDashboard() {
    if (window.nextCareApp) {
        window.nextCareApp.refreshDashboardData();
    }
}

function acknowledgeAlert(alertId) {
    if (window.nextCareApp) {
        window.nextCareApp.acknowledgeAlert(alertId);
    }
}

// Initialize application when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    window.nextCareApp = new NextCareApp();
    window.nextCareApp.initializePage();
});

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = NextCareApp;
}