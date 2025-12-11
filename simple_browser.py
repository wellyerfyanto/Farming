import logging
import time
import random

logger = logging.getLogger(__name__)

class SimpleBrowser:
    """Simple browser simulator untuk kasus Chrome tidak available"""
    
    def __init__(self, device_id):
        self.device_id = device_id
        self.is_active = False
        self.session_start_time = None
        self.browser_type = 'simple_simulator'
        
    def start_session(self, task_config):
        """Simulate browser session"""
        try:
            self.session_start_time = time.time()
            self.is_active = True
            
            # Simulate task execution
            task_type = task_config.get('type', 'browsing')
            logger.info("SimpleBrowser %s simulating %s task", self.device_id, task_type)
            
            # Simulate some work based on task type
            if task_type == 'youtube':
                work_duration = random.randint(60, 180)  # 1-3 minutes for YouTube
            elif task_type == 'search_engine':
                work_duration = random.randint(30, 90)   # 0.5-1.5 minutes for search
            else:
                work_duration = random.randint(30, 120)  # 0.5-2 minutes for general
            
            # Simulate work by sleeping
            time.sleep(work_duration)
            
            logger.info("SimpleBrowser %s completed task after %d seconds", self.device_id, work_duration)
            return True
            
        except Exception as e:
            logger.error("SimpleBrowser %s failed: %s", self.device_id, e)
            return False
    
    def stop_session(self):
        """Stop session"""
        self.is_active = False
        self.session_start_time = None
        logger.info("SimpleBrowser %s session stopped", self.device_id)
    
    def is_running(self):
        """Check if running"""
        return self.is_active
    
    def is_healthy(self):
        """Always healthy"""
        return True
    
    def get_status(self):
        """Get status"""
        session_duration = 0
        if self.session_start_time:
            session_duration = time.time() - self.session_start_time
            
        return {
            'device_id': self.device_id,
            'is_active': self.is_active,
            'google_login_success': False,
            'current_task': None,
            'session_duration': session_duration,
            'browser_type': 'simple_simulator'
        }
