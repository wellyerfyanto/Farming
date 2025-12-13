import threading
import time
import json
import logging
import os
from datetime import datetime

logger = logging.getLogger(__name__)

class RotationManager:
    """Manager untuk account rotation system"""
    
    def __init__(self, farm_manager):
        self.farm_manager = farm_manager
        self.is_rotating = False
        self.current_loop = 0
        self.total_loops = 0
        self.current_account_index = 0
        self.total_accounts = 0
        self.rotation_config = {}
        self.rotation_thread = None
        
    def start_rotation(self, devices_config, tasks_config, rotation_config):
        """Start account rotation"""
        try:
            self.rotation_config = rotation_config
            self.total_loops = rotation_config.get('loops', 1)
            self.total_accounts = rotation_config.get('total_accounts', 0)
            
            # Filter hanya tasks yang akan dirotasi
            all_tasks = tasks_config.get('tasks', [])
            
            # Start rotation thread
            self.is_rotating = True
            self.rotation_thread = threading.Thread(
                target=self._rotation_loop,
                args=(devices_config, all_tasks),
                daemon=True
            )
            self.rotation_thread.start()
            
            logger.info(f"Rotation started: {self.total_loops} loops, {self.total_accounts} accounts")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start rotation: {e}")
            return False
    
    def _rotation_loop(self, devices_config, all_tasks):
        """Main rotation loop"""
        try:
            rotation_mode = self.rotation_config.get('mode', 'sequential')
            delay_between = self.rotation_config.get('delay_between_accounts', 30)
            max_concurrent = self.rotation_config.get('max_concurrent_devices', 1)
            
            # Group tasks by loop
            tasks_by_loop = {}
            for task in all_tasks:
                loop_num = task.get('rotation_metadata', {}).get('loop_number', 1)
                if loop_num not in tasks_by_loop:
                    tasks_by_loop[loop_num] = []
                tasks_by_loop[loop_num].append(task)
            
            # Execute each loop
            for loop_num in sorted(tasks_by_loop.keys()):
                if not self.is_rotating:
                    break
                    
                self.current_loop = loop_num
                logger.info(f"Starting rotation loop {loop_num}/{self.total_loops}")
                
                # Process tasks in this loop
                if rotation_mode == 'sequential':
                    self._process_sequential(tasks_by_loop[loop_num], delay_between)
                elif rotation_mode == 'batch':
                    self._process_batch(tasks_by_loop[loop_num], max_concurrent, delay_between)
                else:  # concurrent
                    self._process_concurrent(tasks_by_loop[loop_num], max_concurrent)
                
                logger.info(f"Completed rotation loop {loop_num}/{self.total_loops}")
            
            self.is_rotating = False
            logger.info("Rotation completed successfully")
            
        except Exception as e:
            logger.error(f"Error in rotation loop: {e}")
            self.is_rotating = False
    
    def _process_sequential(self, tasks, delay_between):
        """Process tasks sequentially (one at a time)"""
        for i, task in enumerate(tasks):
            if not self.is_rotating:
                break
                
            self.current_account_index = i
            device_id = task['device_id']
            
            # Start device with this task
            if self._execute_single_task(device_id, task):
                # Wait for task completion
                while (self.is_rotating and 
                       device_id in self.farm_manager.devices and
                       self.farm_manager.devices[device_id].is_active):
                    time.sleep(5)
            
            # Delay between accounts (kecuali yang terakhir)
            if i < len(tasks) - 1 and self.is_rotating:
                logger.info(f"Waiting {delay_between}s before next account...")
                time.sleep(delay_between)
    
    def _process_batch(self, tasks, batch_size, delay_between):
        """Process tasks in batches"""
        # Group tasks by device
        tasks_by_device = {}
        for task in tasks:
            device_id = task['device_id']
            if device_id not in tasks_by_device:
                tasks_by_device[device_id] = []
            tasks_by_device[device_id].append(task)
        
        # Start all devices in batch
        active_devices = {}
        for device_id, device_tasks in list(tasks_by_device.items())[:batch_size]:
            if device_tasks:
                task = device_tasks[0]
                if self._execute_single_task(device_id, task):
                    active_devices[device_id] = device_tasks[1:]  # Remaining tasks
        
        # Monitor and manage batch execution
        while active_devices and self.is_rotating:
            time.sleep(5)
            
            # Check completed devices
            for device_id in list(active_devices.keys()):
                if (device_id not in self.farm_manager.devices or 
                    not self.farm_manager.devices[device_id].is_active):
                    
                    # Device completed, check for next task
                    remaining_tasks = active_devices[device_id]
                    if remaining_tasks:
                        next_task = remaining_tasks[0]
                        if self._execute_single_task(device_id, next_task):
                            active_devices[device_id] = remaining_tasks[1:]
                        else:
                            del active_devices[device_id]
                    else:
                        del active_devices[device_id]
            
            # Update current account index
            self.current_account_index = sum(len(t) for t in tasks_by_device.values()) - sum(len(t) for t in active_devices.values())
    
    def _process_concurrent(self, tasks, max_concurrent):
        """Process tasks concurrently (original behavior)"""
        # Ini adalah mode default yang sudah ada
        available_devices = list(self.farm_manager.devices.keys())[:max_concurrent]
        
        for i, task in enumerate(tasks):
            if not self.is_rotating or i >= len(available_devices):
                break
                
            device_id = available_devices[i % len(available_devices)]
            self._execute_single_task(device_id, task)
    
    def _execute_single_task(self, device_id, task):
        """Execute single task on device"""
        try:
            if device_id not in self.farm_manager.devices:
                logger.error(f"Device {device_id} not found for rotation")
                return False
            
            device = self.farm_manager.devices[device_id]
            
            # Create profile dengan assigned account
            profile = self.farm_manager.profile_manager.create_profile(device_id)
            
            # Update device config dengan assigned account
            if 'assigned_account' in task:
                account = task['assigned_account']
                device.config['google_account'] = account
            
            # Start session
            if device.start_session(profile, task):
                logger.info(f"Rotation: Started {task['type']} for account {task.get('assigned_account', {}).get('email', 'unknown')}")
                return True
            else:
                logger.error(f"Rotation: Failed to start task on {device_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error executing single task in rotation: {e}")
            return False
    
    def stop_rotation(self):
        """Stop rotation"""
        self.is_rotating = False
        if self.rotation_thread:
            self.rotation_thread.join(timeout=10)
        logger.info("Rotation stopped")
    
    def get_status(self):
        """Get current rotation status"""
        return {
            'is_rotating': self.is_rotating,
            'current_loop': self.current_loop,
            'total_loops': self.total_loops,
            'current_account_index': self.current_account_index,
            'total_accounts': self.total_accounts,
            'mode': self.rotation_config.get('mode', 'sequential'),
            'progress_percentage': (
                (self.current_loop - 1) * self.total_accounts + self.current_account_index
            ) / (self.total_loops * self.total_accounts) * 100 if self.total_accounts > 0 else 0
        }


class BotFarmManager:
    def __init__(self, config_file="config/farm_config.json"):
        logger.info("Initializing Bot Farm Manager...")
        
        self.config = self.load_config(config_file)
        
        # Railway optimization - limit devices based on memory
        if os.environ.get('RAILWAY_ENVIRONMENT'):
            logger.info("🚂 Railway environment detected - applying optimizations")
            self.config['max_concurrent_devices'] = 1  # Force 1 device for Railway
            self.config['chrome_memory_limit'] = 256  # MB
            
        self.devices = {}
        self.google_accounts = []
        self.active_sessions = 0
        self.completed_tasks = 0
        
        # State management dengan lock
        self._lock = threading.Lock()
        self._is_running = False
        self._startup_complete = False
        
        # Rotation manager
        self.rotation_manager = RotationManager(self)
        
        try:
            from task_scheduler import TaskScheduler
            from profile_manager import ProfileManager
            from google_login import GoogleLoginManager
            
            self.profile_manager = ProfileManager()
            self.task_scheduler = TaskScheduler()
            self.google_login_manager = GoogleLoginManager()
            
            self.stats = {
                'total_devices': 0,
                'active_devices': 0,
                'total_tasks_completed': 0,
                'start_time': None,
                'uptime': 0,
                'google_logins_successful': 0,
                'google_logins_failed': 0,
                'enhanced_search_stats': {
                    'total_searches': 0,
                    'target_urls_found': 0,
                    'pages_read': 0,
                    'internal_links_clicked': 0
                }
            }
            
            self.farm_thread = None
            self.stats_thread = None
            
            logger.info("Bot Farm Manager initialized successfully")
            
        except Exception as e:
            logger.error("Failed to initialize Bot Farm Manager: %s", e)
            self.profile_manager = None
            self.task_scheduler = None
            self.google_login_manager = None

    @property
    def is_running(self):
        """Thread-safe property untuk cek status"""
        with self._lock:
            return self._is_running and self._startup_complete

    def load_config(self, config_file):
        """Load configuration dari JSON file"""
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
            logger.info("Loaded configuration from %s", config_file)
            return config
        except FileNotFoundError:
            logger.warning("Config file %s not found, using defaults", config_file)
            return {
                "max_concurrent_devices": 1,
                "task_interval_min": 300,
                "task_interval_max": 600,
                "rotation_enabled": False,
                "proxy_rotation": False,
                "headless": True,
                "save_session": True,
                "railway_optimized": True,
                "rotation_settings": {
                    "mode": "sequential",
                    "loops": 1,
                    "delay_between_accounts": 30,
                    "randomize_order": True
                }
            }
        except Exception as e:
            logger.error("Error loading config: %s", e)
            return {
                "max_concurrent_devices": 1,
                "task_interval_min": 300,
                "task_interval_max": 600,
                "rotation_enabled": False,
                "proxy_rotation": False,
                "headless": True,
                "save_session": True,
                "railway_optimized": True,
                "rotation_settings": {
                    "mode": "sequential",
                    "loops": 1,
                    "delay_between_accounts": 30,
                    "randomize_order": True
                }
            }

    def update_google_accounts(self, accounts):
        """Update Google accounts list"""
        self.google_accounts = accounts
        logger.info("Updated Google accounts: %d accounts", len(accounts))

    def initialize_devices(self, devices_config):
        """Initialize devices dari configuration"""
        if not self.profile_manager:
            logger.error("Profile manager not initialized")
            return False
            
        try:
            self.devices.clear()
            
            for i, device_config in enumerate(devices_config):
                device_id = f"device_{i+1}"
                
                # Assign Google account jika available
                if i < len(self.google_accounts):
                    device_config['google_account'] = self.google_accounts[i]
                else:
                    device_config['google_account'] = None
                
                try:
                    # Coba gunakan DeviceController dengan Chrome
                    from device_controller import DeviceController
                    self.devices[device_id] = DeviceController(device_id, device_config, self.profile_manager)
                    logger.info("Device %s initialized with Chrome", device_id)
                except Exception as e:
                    logger.error("Failed to initialize device %s with Chrome: %s", device_id, e)
                    
                    # Fallback ke SimpleBrowser
                    try:
                        from simple_browser import SimpleBrowser
                        self.devices[device_id] = SimpleBrowser(device_id)
                        logger.info("Device %s initialized with SimpleBrowser fallback", device_id)
                    except Exception as fallback_e:
                        logger.error("Failed to initialize device %s with fallback: %s", device_id, fallback_e)
                        return False
            
            self.stats['total_devices'] = len(self.devices)
            logger.info("Total devices initialized: %d", len(self.devices))
            return True
            
        except Exception as e:
            logger.error("Error initializing devices: %s", e)
            return False

    def start_device(self, device_id, task_config):
        """Start single device dengan specific task"""
        try:
            if device_id not in self.devices:
                logger.error(f"Device {device_id} not found")
                return False
                
            device = self.devices[device_id]
            
            # Generate unique profile
            profile = self.profile_manager.create_profile(device_id)
            
            # Start device session
            if device.start_session(profile, task_config):
                self.active_sessions += 1
                self.stats['active_devices'] = self.active_sessions
                
                # Update enhanced search stats jika task enhanced search
                if task_config.get('type') == 'enhanced_search':
                    self.stats['enhanced_search_stats']['total_searches'] += 1
                
                # Monitor device
                monitor_thread = threading.Thread(
                    target=self.monitor_device, 
                    args=(device_id, task_config),
                    daemon=True
                )
                monitor_thread.start()
                
                logger.info("Device %s started successfully with task: %s", device_id, task_config.get('type'))
                return True
                
        except Exception as e:
            logger.error("Error starting device %s: %s", device_id, e)
        
        return False

    def start_farm_with_rotation(self, devices_config, tasks_config, rotation_config):
        """Start farm dengan rotation system"""
        with self._lock:
            if self._is_running:
                logger.warning("Farm is already running - cannot start again")
                return False

            try:
                # Set state to starting
                self._is_running = True
                self._startup_complete = False
                
                logger.info("Starting bot farm with rotation...")
                
                # Initialize devices dengan fallback mechanism
                if not self.initialize_devices(devices_config):
                    logger.error("Failed to initialize devices")
                    self._is_running = False
                    return False
                
                # Set stats
                self.stats['start_time'] = datetime.now()
                self.active_sessions = 0
                self.completed_tasks = 0
                
                # Start rotation manager
                if not self.rotation_manager.start_rotation(devices_config, tasks_config, rotation_config):
                    logger.error("Failed to start rotation manager")
                    self._is_running = False
                    return False
                
                # Start stats monitor
                self.stats_thread = threading.Thread(target=self._stats_monitor, daemon=True)
                self.stats_thread.start()
                
                # Mark startup complete
                self._startup_complete = True
                
                logger.info("Bot Farm with rotation started successfully")
                return True
                
            except Exception as e:
                logger.error("Failed to start rotation farm: %s", e)
                self._is_running = False
                self._startup_complete = False
                return False

    def start_farm(self, devices_config, tasks_config):
        """Start the entire bot farm dengan thread-safe"""
        with self._lock:
            if self._is_running:
                logger.warning("Farm is already running - cannot start again")
                return False

            try:
                # Set state to starting
                self._is_running = True
                self._startup_complete = False
                
                logger.info("Starting bot farm...")
                
                # Initialize devices dengan fallback mechanism
                if not self.initialize_devices(devices_config):
                    logger.error("Failed to initialize devices")
                    self._is_running = False
                    return False
                
                # Initialize tasks
                if self.task_scheduler:
                    self.task_scheduler.load_tasks_config(tasks_config)
                
                # Set stats
                self.stats['start_time'] = datetime.now()
                self.active_sessions = 0
                self.completed_tasks = 0
                
                # Start farm loop
                self.farm_thread = threading.Thread(target=self._farm_loop, daemon=True)
                self.farm_thread.start()
                
                # Start stats monitor
                self.stats_thread = threading.Thread(target=self._stats_monitor, daemon=True)
                self.stats_thread.start()
                
                # Mark startup complete
                self._startup_complete = True
                
                logger.info("Bot Farm started successfully")
                return True
                
            except Exception as e:
                logger.error("Failed to start farm: %s", e)
                self._is_running = False
                self._startup_complete = False
                return False

    def monitor_device(self, device_id, task_config):
        """Monitor device execution dengan stats tracking"""
        device = self.devices[device_id]
        task_type = task_config.get('type', 'unknown')
        
        # Track enhanced search metrics
        if task_type == 'enhanced_search':
            task_start_time = time.time()
            target_urls = task_config.get('target_urls', [])
            target_urls_found = 0
        
        while device.is_running() and self._is_running:
            time.sleep(10)
            
            # Check device health
            if hasattr(device, 'is_healthy'):
                if not device.is_healthy():
                    logger.warning("Device %s not healthy, restarting...", device_id)
                    try:
                        # Get current status untuk tracking
                        status = device.get_status()
                        if task_type == 'enhanced_search' and status.get('enhanced_metrics'):
                            metrics = status.get('enhanced_metrics', {})
                            self.stats['enhanced_search_stats']['pages_read'] += metrics.get('pages_read', 0)
                            self.stats['enhanced_search_stats']['internal_links_clicked'] += metrics.get('internal_links_clicked', 0)
                        
                        # Restart session
                        if hasattr(device, 'restart_session'):
                            device.restart_session()
                        else:
                            # For SimpleBrowser, just mark as completed
                            device.is_active = False
                    except Exception as e:
                        logger.error("Failed to restart device %s: %s", device_id, e)
        
        # Device completed
        if device_id in self.devices:
            self.active_sessions -= 1
            self.completed_tasks += 1
            self.stats['active_devices'] = self.active_sessions
            self.stats['total_tasks_completed'] = self.completed_tasks
            
            # Update Google login stats jika tersedia
            if hasattr(device, 'google_login_success'):
                if device.google_login_success:
                    self.stats['google_logins_successful'] += 1
                else:
                    self.stats['google_logins_failed'] += 1
            
            # Update enhanced search stats
            if task_type == 'enhanced_search':
                task_duration = time.time() - task_start_time
                logger.info("Enhanced search task completed for %s, duration: %.1f seconds", 
                           device_id, task_duration)
                
                # Get final metrics dari device
                status = device.get_status()
                if status.get('enhanced_metrics'):
                    metrics = status.get('enhanced_metrics', {})
                    self.stats['enhanced_search_stats']['pages_read'] += metrics.get('pages_read', 0)
                    self.stats['enhanced_search_stats']['internal_links_clicked'] += metrics.get('internal_links_clicked', 0)
                    self.stats['enhanced_search_stats']['target_urls_found'] += metrics.get('target_urls_found', 0)
            
            logger.info("Device %s completed %s task", device_id, task_type)

    def _farm_loop(self):
        """Main farm loop dengan error handling dan enhanced task management"""
        logger.info("Farm loop started")
        
        while self._is_running:
            try:
                # Cari devices yang available
                available_devices = [
                    device_id for device_id, device in self.devices.items()
                    if hasattr(device, 'is_active') and not device.is_active
                ]
                
                # Cari pending tasks
                if self.task_scheduler:
                    pending_tasks = self.task_scheduler.get_pending_tasks()
                else:
                    pending_tasks = []
                
                # Assign tasks ke available devices
                for i, task in enumerate(pending_tasks[:len(available_devices)]):
                    if i < len(available_devices):
                        device_id = available_devices[i]
                        if self.start_device(device_id, task):
                            if self.task_scheduler:
                                self.task_scheduler.mark_task_assigned(task['id'])
                
                # Check for any devices that need restart atau maintenance
                self._check_device_health()
                
                time.sleep(10)  # Interval check
                
            except Exception as e:
                logger.error("Error in farm loop: %s", e)
                time.sleep(30)  # Longer sleep on error

    def _check_device_health(self):
        """Check health of all devices dan restart jika perlu"""
        for device_id, device in self.devices.items():
            try:
                if hasattr(device, 'is_active') and device.is_active:
                    if hasattr(device, 'is_healthy'):
                        if not device.is_healthy():
                            logger.warning("Device %s is unhealthy, attempting restart...", device_id)
                            # Get current task sebelum restart
                            current_task = device.current_task if hasattr(device, 'current_task') else None
                            
                            # Stop current session
                            if hasattr(device, 'stop_session'):
                                device.stop_session()
                                time.sleep(2)
                            
                            # Restart dengan task yang sama
                            profile = self.profile_manager.create_profile(device_id)
                            if device.start_session(profile, current_task):
                                logger.info("Device %s restarted successfully", device_id)
                            else:
                                logger.error("Failed to restart device %s", device_id)
            except Exception as e:
                logger.error("Error checking health for device %s: %s", device_id, e)

    def _stats_monitor(self):
        """Monitor dan update statistics"""
        logger.info("Stats monitor started")
        
        while self._is_running:
            try:
                current_time = datetime.now()
                if self.stats['start_time']:
                    self.stats['uptime'] = (current_time - self.stats['start_time']).total_seconds()
                
                # Update device status
                for device_id, device in self.devices.items():
                    try:
                        status = device.get_status()
                        # Update enhanced metrics jika ada
                        if 'enhanced_metrics' in status:
                            metrics = status['enhanced_metrics']
                            self.stats['enhanced_search_stats']['pages_read'] = max(
                                self.stats['enhanced_search_stats']['pages_read'],
                                metrics.get('pages_read', 0)
                            )
                    except Exception as e:
                        logger.debug("Error updating stats for %s: %s", device_id, e)
                
                time.sleep(5)  # Update stats every 5 seconds
                
            except Exception as e:
                logger.error("Error in stats monitor: %s", e)
                time.sleep(10)

    def stop_farm(self):
        """Stop the bot farm dengan thread-safe dan graceful shutdown"""
        with self._lock:
            if not self._is_running:
                logger.info("Farm is not running - nothing to stop")
                return True
                
            logger.info("Stopping Bot Farm...")
            
            # Set state to stopping
            self._is_running = False
            self._startup_complete = False
            
            # Stop rotation manager jika aktif
            if self.rotation_manager.is_rotating:
                self.rotation_manager.stop_rotation()
            
            # Stop all devices dengan graceful shutdown
            successful_stops = 0
            for device_id, device in self.devices.items():
                try:
                    # Save session data sebelum stop jika device mendukung
                    if hasattr(device, 'is_active') and device.is_active:
                        logger.info("Gracefully stopping device %s...", device_id)
                        # Beri waktu untuk menyelesaikan task saat ini
                        time.sleep(2)
                    
                    # Stop session jika device mendukung
                    if hasattr(device, 'stop_session'):
                        device.stop_session()
                    else:
                        # For SimpleBrowser, just mark as inactive
                        if hasattr(device, 'is_active'):
                            device.is_active = False
                        
                    successful_stops += 1
                except Exception as e:
                    logger.error("Error stopping device %s: %s", device_id, e)
            
            # Reset state
            self.active_sessions = 0
            self.stats['active_devices'] = 0
            
            # Tunggu thread untuk berhenti
            if self.farm_thread:
                self.farm_thread.join(timeout=5)
            if self.stats_thread:
                self.stats_thread.join(timeout=5)
            
            logger.info("Bot Farm stopped successfully (%d devices stopped)", successful_stops)
            return True

    def get_farm_stats(self):
        """Get current farm statistics dengan enhanced metrics"""
        if self.stats['start_time'] and self._is_running:
            self.stats['uptime'] = (datetime.now() - self.stats['start_time']).total_seconds()
        
        # Calculate additional metrics
        total_devices_configured = len(self.devices)
        active_percentage = (self.stats['active_devices'] / total_devices_configured * 100) if total_devices_configured > 0 else 0
        
        # Build enhanced search summary
        enhanced_stats = self.stats['enhanced_search_stats']
        search_success_rate = (enhanced_stats['target_urls_found'] / enhanced_stats['total_searches'] * 100) if enhanced_stats['total_searches'] > 0 else 0
        
        return {
            **self.stats,
            'is_running': self.is_running,
            'active_sessions': self.active_sessions,
            'completed_tasks': self.completed_tasks,
            'total_google_accounts': len(self.google_accounts),
            'total_devices_configured': total_devices_configured,
            'active_percentage': round(active_percentage, 1),
            'enhanced_search_summary': {
                'total_searches': enhanced_stats['total_searches'],
                'target_urls_found': enhanced_stats['target_urls_found'],
                'target_success_rate': round(search_success_rate, 1),
                'pages_read': enhanced_stats['pages_read'],
                'internal_links_clicked': enhanced_stats['internal_links_clicked'],
                'avg_engagement_per_search': round(enhanced_stats['pages_read'] / max(enhanced_stats['total_searches'], 1), 1)
            },
            'performance_metrics': {
                'tasks_per_hour': round(self.completed_tasks / (self.stats['uptime'] / 3600), 1) if self.stats['uptime'] > 0 else 0,
                'avg_task_duration': round(self.stats['uptime'] / max(self.completed_tasks, 1), 1) if self.completed_tasks > 0 else 0,
                'google_login_success_rate': round(self.stats['google_logins_successful'] / max(self.stats['google_logins_successful'] + self.stats['google_logins_failed'], 1) * 100, 1)
            }
        }

    def get_devices_status(self):
        """Get status semua devices dengan enhanced metrics"""
        devices_status = {}
        for device_id, device in self.devices.items():
            try:
                status = device.get_status()
                
                # Add enhanced metrics jika ada
                if hasattr(device, 'enhanced_metrics'):
                    status['enhanced_metrics'] = device.enhanced_metrics
                
                # Determine activity status
                if status['is_active']:
                    if hasattr(device, 'google_login_success') and device.google_login_success:
                        status['status_text'] = 'Active (Google logged in)'
                        status['status_icon'] = '🟢'
                    else:
                        status['status_text'] = 'Active (No Google)'
                        status['status_icon'] = '🟡'
                else:
                    status['status_text'] = 'Inactive'
                    status['status_icon'] = '🔴'
                
                # Format session duration
                if status['session_duration']:
                    minutes = int(status['session_duration'] // 60)
                    seconds = int(status['session_duration'] % 60)
                    status['session_duration_formatted'] = f"{minutes}m {seconds}s"
                else:
                    status['session_duration_formatted'] = '0m'
                
                devices_status[device_id] = status
            except Exception as e:
                logger.error("Error getting status for %s: %s", device_id, e)
                devices_status[device_id] = {
                    'device_id': device_id,
                    'is_active': False,
                    'google_login_success': False,
                    'current_task': None,
                    'session_duration': 0,
                    'session_duration_formatted': '0m',
                    'browser_type': 'unknown',
                    'status_text': 'Error',
                    'status_icon': '❌',
                    'error': str(e)
                }
        return devices_status

    def get_rotation_status(self):
        """Get rotation manager status"""
        return self.rotation_manager.get_status()

    def add_task(self, task_config):
        """Add new task ke scheduler dengan enhanced task support"""
        try:
            if self.task_scheduler:
                # Validate enhanced search task
                if task_config.get('type') == 'enhanced_search':
                    if not task_config.get('keywords'):
                        logger.warning("Enhanced search task requires keywords")
                        return None
                
                task_id = self.task_scheduler.add_task(task_config)
                logger.info("Added new task: %s (type: %s)", task_id, task_config.get('type'))
                return task_id
            else:
                logger.error("Task scheduler not initialized")
                return None
        except Exception as e:
            logger.error("Error adding task: %s", e)
            return None

    def force_cleanup(self):
        """Force cleanup semua resources dengan comprehensive reset"""
        logger.warning("Performing forced cleanup...")
        
        with self._lock:
            self._is_running = False
            self._startup_complete = False
            
            # Stop semua devices dengan force
            for device_id, device in self.devices.items():
                try:
                    if hasattr(device, 'stop_session'):
                        device.stop_session()
                    else:
                        # For SimpleBrowser, just mark as inactive
                        if hasattr(device, 'is_active'):
                            device.is_active = False
                    logger.info("Force stopped device %s", device_id)
                except Exception as e:
                    logger.error("Error force stopping device %s: %s", device_id, e)
            
            # Stop rotation manager
            if self.rotation_manager.is_rotating:
                self.rotation_manager.stop_rotation()
            
            # Tunggu thread untuk berhenti
            if self.farm_thread:
                self.farm_thread.join(timeout=2)
            if self.stats_thread:
                self.stats_thread.join(timeout=2)
            
            # Reset semua state
            self.devices.clear()
            self.active_sessions = 0
            self.completed_tasks = 0
            self.stats.update({
                'active_devices': 0,
                'total_tasks_completed': 0,
                'start_time': None,
                'uptime': 0,
                'google_logins_successful': 0,
                'google_logins_failed': 0,
                'enhanced_search_stats': {
                    'total_searches': 0,
                    'target_urls_found': 0,
                    'pages_read': 0,
                    'internal_links_clicked': 0
                }
            })
            
            # Reset task scheduler jika ada
            if self.task_scheduler:
                self.task_scheduler.tasks = []
                self.task_scheduler.task_id_counter = 1
        
        logger.info("Forced cleanup completed")
        return True