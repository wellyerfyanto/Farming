import time
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class TaskScheduler:
    def __init__(self):
        self.tasks = []
        self.task_id_counter = 1
        
    def load_tasks_config(self, tasks_config):
        """Load tasks configuration"""
        self.tasks = []
        for task in tasks_config.get('tasks', []):
            task['status'] = 'pending'
            task['created_at'] = datetime.now()
            self.tasks.append(task)
        
        logger.info(f"📋 Loaded {len(self.tasks)} tasks")
    
    def get_pending_tasks(self):
        """Get list of pending tasks"""
        return [task for task in self.tasks if task.get('status') == 'pending']
    
    def mark_task_assigned(self, task_id):
        """Mark task as assigned"""
        for task in self.tasks:
            if task.get('id') == task_id:
                task['status'] = 'assigned'
                task['assigned_at'] = datetime.now()
                break
    
    def add_task(self, task_config):
        """Add new task"""
        task_id = f"task_{self.task_id_counter}"
        self.task_id_counter += 1
        
        task = {
            'id': task_id,
            **task_config,
            'status': 'pending',
            'created_at': datetime.now()
        }
        
        self.tasks.append(task)
        logger.info(f"➕ Added new task: {task_id}")
        return task_id
