import os
import time
import logging
import shutil
import sys
import json
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS

# Setup proper logging for Railway
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.StreamHandler(sys.stderr)
    ]
)

# Get logger for this module
logger = logging.getLogger(__name__)

app = Flask(__name__, template_folder='templates', static_folder='static')
CORS(app)

# Initialize farm manager with error handling
try:
    from farm_manager import BotFarmManager
    farm_manager = BotFarmManager()
    logger.info("Bot Farm Manager initialized successfully")
    
    # Chrome environment sudah dihandle oleh Dockerfile, tidak perlu init_chrome
    logger.info("Chrome environment should be available via Dockerfile installation")
        
except Exception as e:
    logger.error("Failed to initialize Bot Farm Manager: %s", e)
    farm_manager = None

@app.route('/')
def dashboard():
    return render_template('dashboard.html')

@app.route('/api/farm/start', methods=['POST'])
def start_farm():
    try:
        if not farm_manager:
            return jsonify({'status': 'error', 'message': 'Farm manager not initialized'})
            
        data = request.json
        devices_config = data.get('devices', [])
        tasks_config = data.get('tasks', {})
        
        # Force cleanup jika ada state yang stuck
        if farm_manager.is_running:
            logger.warning("Farm appears to be running, forcing cleanup before restart")
            farm_manager.force_cleanup()
            time.sleep(2)  # Beri waktu untuk cleanup
        
        if farm_manager.start_farm(devices_config, tasks_config):
            logger.info("Bot farm started successfully via API")
            return jsonify({'status': 'success', 'message': 'Bot farm started successfully'})
        else:
            logger.warning("Failed to start bot farm via API")
            return jsonify({'status': 'error', 'message': 'Failed to start bot farm'})
    except Exception as e:
        logger.error("Error starting farm: %s", e)
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/farm/stop')
def stop_farm():
    try:
        if farm_manager:
            farm_manager.stop_farm()
            logger.info("Bot farm stopped via API")
            return jsonify({'status': 'success', 'message': 'Bot farm stopped'})
        else:
            return jsonify({'status': 'error', 'message': 'Farm manager not initialized'})
    except Exception as e:
        logger.error("Error stopping farm: %s", e)
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/farm/force-stop', methods=['POST'])
def force_stop_farm():
    """Force stop endpoint untuk cleanup state yang stuck"""
    try:
        if farm_manager:
            farm_manager.force_cleanup()
            logger.info("Farm force stopped via API")
            return jsonify({'status': 'success', 'message': 'Farm force stopped'})
        else:
            return jsonify({'status': 'error', 'message': 'Farm manager not initialized'})
    except Exception as e:
        logger.error("Error force stopping farm: %s", e)
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/farm/stats')
def get_farm_stats():
    try:
        if farm_manager:
            stats = farm_manager.get_farm_stats()
            return jsonify({'status': 'success', 'data': stats})
        else:
            return jsonify({'status': 'error', 'message': 'Farm manager not initialized'})
    except Exception as e:
        logger.error("Error getting stats: %s", e)
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/devices')
def get_devices():
    try:
        if farm_manager:
            devices = farm_manager.get_devices_status()
            return jsonify({'status': 'success', 'data': devices})
        else:
            return jsonify({'status': 'error', 'message': 'Farm manager not initialized'})
    except Exception as e:
        logger.error("Error getting devices: %s", e)
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/tasks/add', methods=['POST'])
def add_task():
    try:
        if farm_manager:
            data = request.json
            task_id = farm_manager.add_task(data)
            logger.info("Added new task: %s", task_id)
            return jsonify({'status': 'success', 'task_id': task_id})
        else:
            return jsonify({'status': 'error', 'message': 'Farm manager not initialized'})
    except Exception as e:
        logger.error("Error adding task: %s", e)
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/google/accounts', methods=['POST'])
def update_google_accounts():
    try:
        if farm_manager:
            data = request.json
            accounts = data.get('accounts', [])
            farm_manager.update_google_accounts(accounts)
            logger.info("Updated %d Google accounts via API", len(accounts))
            return jsonify({'status': 'success', 'message': 'Google accounts updated'})
        else:
            return jsonify({'status': 'error', 'message': 'Farm manager not initialized'})
    except Exception as e:
        logger.error("Error updating Google accounts: %s", e)
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/scenario/save', methods=['POST'])
def save_scenario_config():
    try:
        data = request.json
        os.makedirs('config', exist_ok=True)
        with open('config/scenario_config.json', 'w') as f:
            json.dump(data, f, indent=2)
        logger.info("Scenario configuration saved via API")
        return jsonify({'status': 'success', 'message': 'Scenario configuration saved'})
    except Exception as e:
        logger.error("Error saving scenario: %s", e)
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/scenario/load')
def load_scenario_config():
    try:
        with open('config/scenario_config.json', 'r') as f:
            config = json.load(f)
        logger.info("Scenario configuration loaded via API")
        return jsonify({'status': 'success', 'data': config})
    except FileNotFoundError:
        logger.warning("No saved scenario found")
        return jsonify({'status': 'error', 'message': 'No saved scenario found'})
    except Exception as e:
        logger.error("Error loading scenario: %s", e)
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/profiles/export/<device_id>')
def export_profile(device_id):
    try:
        if farm_manager:
            profile_data = farm_manager.profile_manager.export_profile(device_id)
            if profile_data:
                logger.info("Exported profile for %s", device_id)
                return jsonify({'status': 'success', 'data': profile_data})
            else:
                logger.warning("Profile not found for %s", device_id)
                return jsonify({'status': 'error', 'message': 'Profile not found'})
        else:
            return jsonify({'status': 'error', 'message': 'Farm manager not initialized'})
    except Exception as e:
        logger.error("Error exporting profile: %s", e)
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/profiles/import', methods=['POST'])
def import_profile():
    try:
        if farm_manager:
            data = request.json
            device_id = data.get('device_id')
            profile_data = data.get('profile_data')
            
            if farm_manager.profile_manager.import_profile(device_id, profile_data):
                logger.info("Imported profile for %s", device_id)
                return jsonify({'status': 'success', 'message': 'Profile imported successfully'})
            else:
                logger.warning("Failed to import profile for %s", device_id)
                return jsonify({'status': 'error', 'message': 'Failed to import profile'})
        else:
            return jsonify({'status': 'error', 'message': 'Farm manager not initialized'})
    except Exception as e:
        logger.error("Error importing profile: %s", e)
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/profiles/list')
def list_profiles():
    try:
        if farm_manager:
            profiles = farm_manager.profile_manager.get_all_profiles()
            logger.info("Listed %d profiles via API", len(profiles))
            return jsonify({'status': 'success', 'data': profiles})
        else:
            return jsonify({'status': 'error', 'message': 'Farm manager not initialized'})
    except Exception as e:
        logger.error("Error listing profiles: %s", e)
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/profiles/delete/<device_id>', methods=['DELETE'])
def delete_profile(device_id):
    try:
        profile_path = f"profiles/profile_{device_id}"
        if os.path.exists(profile_path):
            shutil.rmtree(profile_path)
            logger.info("Deleted profile for %s", device_id)
            return jsonify({'status': 'success', 'message': 'Profile deleted'})
        else:
            logger.warning("Profile not found for deletion: %s", device_id)
            return jsonify({'status': 'error', 'message': 'Profile not found'})
    except Exception as e:
        logger.error("Error deleting profile: %s", e)
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/health')
def health_check():
    """Health check endpoint for Railway"""
    health_status = {
        'status': 'healthy',
        'timestamp': time.time(),
        'farm_manager_initialized': farm_manager is not None,
        'environment': os.environ.get('RAILWAY_ENVIRONMENT', 'development')
    }
    logger.info("Health check: %s", health_status)
    return jsonify(health_status)

@app.route('/api/debug/info')
def debug_info():
    """Debug endpoint to check system information"""
    import platform
    info = {
        'python_version': platform.python_version(),
        'platform': platform.platform(),
        'environment_variables': {
            'RAILWAY_ENVIRONMENT': os.environ.get('RAILWAY_ENVIRONMENT'),
            'PORT': os.environ.get('PORT'),
            'PYTHON_VERSION': os.environ.get('PYTHON_VERSION')
        },
        'farm_manager': 'initialized' if farm_manager else 'not initialized',
        'working_directory': os.getcwd(),
        'files_in_wd': os.listdir('.')
    }
    return jsonify(info)

@app.route('/api/chrome/check')
def check_chrome():
    """Check Chrome availability"""
    try:
        from chrome_setup import check_chrome_availability
        chrome_available = check_chrome_availability()
        return jsonify({
            'status': 'success',
            'chrome_available': chrome_available,
            'message': 'Chrome is available' if chrome_available else 'Chrome is not available'
        })
    except Exception as e:
        logger.error("Chrome check failed: %s", e)
        return jsonify({
            'status': 'error',
            'chrome_available': False,
            'message': str(e)
        })

@app.route('/api/debug/chrome')
def debug_chrome():
    """Debug endpoint untuk Chrome setup"""
    try:
        from chrome_setup import check_chrome_availability, find_system_chromedriver, get_browser_info
        
        chrome_available = check_chrome_availability()
        chromedriver_path = find_system_chromedriver()
        browser_info = get_browser_info()
        
        return jsonify({
            'chrome_available': chrome_available,
            'chromedriver_path': chromedriver_path,
            'browser_info': browser_info,
            'chrome_bin': os.environ.get('CHROME_BIN'),
            'chromedriver_path_env': os.environ.get('CHROMEDRIVER_PATH')
        })
    except Exception as e:
        return jsonify({'error': str(e)})

def create_app():
    return app

# Production configuration
if __name__ == "__main__":
    # Get port from environment (Railway provides this)
    port = int(os.environ.get('PORT', 5000))
    
    # Check if running in production (Railway sets PORT and other env vars)
    is_production = os.environ.get('RAILWAY_ENVIRONMENT') or os.environ.get('PORT') or os.environ.get('RAILWAY_SERVICE_NAME')
    
    if is_production:
        # Production settings
        logger.info("Starting production server on port %d", port)
        
        # Use Waitress as production WSGI server
        try:
            from waitress import serve
            serve(app, host='0.0.0.0', port=port)
        except ImportError:
            logger.error("Waitress not available, falling back to development server")
            app.run(host='0.0.0.0', port=port, debug=False)
    else:
        # Development settings
        logger.info("Starting development server on port %d", port)
        app.run(host='0.0.0.0', port=port, debug=False)
