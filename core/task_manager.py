# agents/task_manager.py

import threading
import asyncio
import logging
import time
from .GenAgent import GenAgent

class TaskManager:
    def __init__(self):
        self.tasks = {}
        self._lock = threading.RLock()  # Thread lock
        self.logger = logging.getLogger(__name__)
        self.task_timeout = 600  # 600 second timeout
        self.max_retry_count = 5  # Max retry count

    def start_task(self, task_id, task_callable, *args, **kwargs):
        """Start task and store GenAgent instance"""
        with self._lock:
            # First clean up old task with same ID
            if task_id in self.tasks:
                old_task = self.tasks[task_id]
                if old_task.get('status') in ('running', 'retrying'):
                    self.logger.warning(f"Task {task_id} already exists with status {old_task.get('status')}, stopping old task first")
                    self._force_cleanup_task(task_id)
            
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            task = loop.create_task(task_callable(*args, **kwargs))
            
            # Store GenAgent instance
            manager = kwargs.get('manager')
            thread = kwargs.get('thread')  # Optional thread reference
            
            if manager:
                self.tasks[task_id] = {
                    'manager': manager,
                    'task': task,
                    'thread': thread,
                    'status': 'running',
                    'created_at': time.time(),
                    'last_heartbeat': time.time(),
                    'retry_count': 0,
                    'last_retry_time': 0,
                    'is_stalled': False,
                    'original_datalist': kwargs.get('datalist', [])
                }
                self.logger.info(f"Task {task_id} started and stored")
            else:
                self.logger.error(f"No manager provided for task {task_id}")

    def _force_cleanup_task(self, task_id):
        """Force cleanup of old task"""
        task_info = self.tasks.get(task_id)
        if task_info:
            manager = task_info.get('manager')
            async_task = task_info.get('task')
            
            if isinstance(manager, GenAgent):
                manager.stop()
            
            if async_task and not async_task.done():
                async_task.cancel()
            
            # Release API key
            try:
                from backend.api_pool import api_key_pool
                api_key_pool.release_api_key(task_id)
            except:
                pass
            
            del self.tasks[task_id]
            self.logger.info(f"Force cleaned up old task {task_id}")

    def stop_task(self, task_id, force=False):
        """ 
        Stop task 
        Args:
            task_id: Task ID
            force: Whether to force stop (immediate interrupt)
        """
        with self._lock:
            task_info = self.tasks.get(task_id)
            if task_info:
                manager = task_info.get('manager')
                async_task = task_info.get('task')
                thread = task_info.get('thread')
                
                # 1. First set GenAgent stop_flag
                if isinstance(manager, GenAgent):
                    manager.stop()
                    self.logger.info(f"Task {task_id} GenAgent stop flag set")
                
                # 2. Cancel async task
                if async_task and not async_task.done():
                    async_task.cancel()
                    self.logger.info(f"Task {task_id} async task cancelled")
                
                # 3. If thread is running, try to interrupt
                if thread and thread.is_alive():
                    self.logger.info(f"Task {task_id} thread is still alive, waiting for graceful stop...")
                    # Brief wait for graceful task exit
                    if force:
                        # Force stop without waiting
                        self.logger.warning(f"Force stopping task {task_id}")
                    else:
                        # Wait up to 2 seconds
                        thread.join(timeout=2.0)
                        if thread.is_alive():
                            self.logger.warning(f"Task {task_id} thread did not stop gracefully")
                
                # 4. Release API key
                try:
                    from backend.api_pool import api_key_pool
                    api_key_pool.release_api_key(task_id)
                    # Also release chat and analysis keys if present
                    api_key_pool.release_api_key(f"{task_id}_analysis")
                    api_key_pool.release_api_key(f"{task_id}_chat")
                    self.logger.info(f"Released API keys for stopped task {task_id}")
                except ImportError:
                    self.logger.error("Could not import API key pool")
                except Exception as e:
                    self.logger.error(f"Error releasing API keys: {e}")
                
                # 5. Update status
                task_info['status'] = 'stopped'
                task_info['stopped_at'] = time.time()
                self.logger.info(f"Task {task_id} is marked as stopped.")
            else:
                self.logger.warning(f"Task {task_id} not found in task manager.")

    def get_task_status(self, task_id):
        """Get task status"""
        with self._lock:
            task_info = self.tasks.get(task_id)
            if task_info:
                return task_info.get('status', 'unknown')
            return None

    def cleanup_finished_tasks(self):
        """Clean up finished tasks"""
        with self._lock:
            finished_tasks = []
            for task_id, task_info in self.tasks.items():
                async_task = task_info.get('task')
                if async_task and async_task.done():
                    finished_tasks.append(task_id)
            
            for task_id in finished_tasks:
                del self.tasks[task_id]
                self.logger.info(f"Cleaned up finished task {task_id}")

    def update_heartbeat(self, task_id):
        """Update task heartbeat time"""
        with self._lock:
            task_info = self.tasks.get(task_id)
            if task_info:
                task_info['last_heartbeat'] = time.time()
                self.logger.debug(f"Updated heartbeat for task {task_id}")
                return True
            return False

    def check_timeout_tasks(self):
        """Check timeout tasks and cleanup"""
        current_time = time.time()
        timeout_tasks = []
        stalled_tasks = []
        
        with self._lock:
            for task_id, task_info in self.tasks.items():
                last_heartbeat = task_info.get('last_heartbeat', task_info.get('created_at', 0))
                time_since_heartbeat = current_time - last_heartbeat
                
                if time_since_heartbeat > self.task_timeout:
                    # Check if stalled task needs retry
                    retry_count = task_info.get('retry_count', 0)
                    if retry_count < self.max_retry_count and not task_info.get('is_stalled', False):
                        # Mark as stalled, prepare for retry
                        task_info['is_stalled'] = True
                        stalled_tasks.append(task_id)
                        self.logger.warning(f"Task {task_id} appears stalled after {self.task_timeout} seconds, will retry")
                    else:
                        # Exceeded retry count or already abandoned, handle timeout directly
                        timeout_tasks.append(task_id)
                        self.logger.warning(f"Task {task_id} timed out after {self.task_timeout} seconds (retry {retry_count}/{self.max_retry_count})")
        
        # Handle stalled tasks (auto retry)
        for task_id in stalled_tasks:
            self._handle_stalled_task(task_id)
        
        # Handle truly timed out tasks
        for task_id in timeout_tasks:
            self._handle_timeout_task(task_id)
        
        return {'timeout_tasks': timeout_tasks, 'stalled_tasks': stalled_tasks}

    def _handle_stalled_task(self, task_id):
        """Handle stalled task (auto retry)"""
        with self._lock:
            task_info = self.tasks.get(task_id)
            if task_info:
                retry_count = task_info.get('retry_count', 0)
                if retry_count < self.max_retry_count:
                    # Increment retry count
                    task_info['retry_count'] = retry_count + 1
                    task_info['last_retry_time'] = time.time()
                    task_info['is_stalled'] = False  # Reset stalled flag
                    
                    self.logger.info(f"Attempting to retry stalled task {task_id} (attempt {retry_count + 1}/{self.max_retry_count})")
                    
                    # Stop current task
                    manager = task_info.get('manager')
                    async_task = task_info.get('task')
                    
                    if isinstance(manager, GenAgent):
                        manager.stop()
                    
                    if async_task and not async_task.done():
                        async_task.cancel()
                    
                    # Start retry (delayed to avoid immediate retry)
                    self._schedule_retry(task_id)
                else:
                    # Exceeded max retry count, abandon task
                    self.logger.error(f"Task {task_id} failed after {self.max_retry_count} retries, abandoning")
                    self._abandon_task(task_id)

    def _schedule_retry(self, task_id):
        """Schedule task retry"""
        import threading
        
        def retry_task():
            # Delay 5 seconds before retry
            time.sleep(5)
            self._retry_task(task_id)
        
        retry_thread = threading.Thread(target=retry_task, daemon=True)
        retry_thread.start()

    def _retry_task(self, task_id):
        """Retry task"""
        with self._lock:
            task_info = self.tasks.get(task_id)
            if task_info:
                try:
                    # Import re-execute function from utils
                    from backend.utils import update_execute_agent_status_and_attempt
                    
                    # Reset session status to thinking
                    update_execute_agent_status_and_attempt(task_id, 1, 0)
                    
                    # Update heartbeat time
                    task_info['last_heartbeat'] = time.time()
                    task_info['status'] = 'retrying'
                    
                    # Call re-execute API
                    self._trigger_task_restart(task_id, task_info.get('original_datalist', []))
                    
                    self.logger.info(f"Successfully triggered retry for task {task_id}")
                    
                except Exception as e:
                    self.logger.error(f"Failed to retry task {task_id}: {str(e)}")
                    # Retry failed, increment retry count
                    task_info['retry_count'] = task_info.get('retry_count', 0) + 1

    def _trigger_task_restart(self, task_id, datalist):
        """Trigger task restart"""
        try:
            import requests
            import json
            
            # Call execute_plan API to restart task
            url = f"http://localhost:8000/execute_plan/"
            data = {
                'id': task_id,
                'datalist': datalist
            }
            
            response = requests.post(url, json=data, timeout=10)
            
            if response.status_code == 200:
                self.logger.info(f"Successfully restarted task {task_id}")
                # Update task status
                with self._lock:
                    if task_id in self.tasks:
                        self.tasks[task_id]['status'] = 'running'
                        self.tasks[task_id]['last_heartbeat'] = time.time()
            else:
                self.logger.error(f"Failed to restart task {task_id}: HTTP {response.status_code}")
                raise Exception(f"HTTP {response.status_code}")
                
        except Exception as e:
            self.logger.error(f"Error triggering task restart for {task_id}: {str(e)}")
            raise

    def _abandon_task(self, task_id):
        """Abandon task"""
        with self._lock:
            task_info = self.tasks.get(task_id)
            if task_info:
                # Stop task
                manager = task_info.get('manager')
                async_task = task_info.get('task')
                
                if isinstance(manager, GenAgent):
                    manager.stop()
                
                if async_task and not async_task.done():
                    async_task.cancel()
                
                # Update status to abandoned
                task_info['status'] = 'abandoned'
                
                # Release API key
                try:
                    from backend.api_pool import api_key_pool
                    api_key_pool.release_api_key(task_id)
                    self.logger.info(f"Released API key for abandoned task {task_id}")
                except ImportError:
                    self.logger.error("Could not import API key pool")
                
                # Import status update function from utils
                try:
                    from backend.utils import update_execute_agent_status_and_attempt, update_execute_agent_stage
                    # Set task status to error-last (abandoned)
                    update_execute_agent_status_and_attempt(task_id, 4, 0)  # error-last status
                    update_execute_agent_stage(task_id, "ABANDONED")  # Set to abandoned stage
                    self.logger.info(f"Abandoned task {task_id} after {self.max_retry_count} failed retries")
                except ImportError:
                    self.logger.error("Could not import status update function")

    def _handle_timeout_task(self, task_id):
        """Handle timeout task"""
        with self._lock:
            task_info = self.tasks.get(task_id)
            if task_info:
                # Stop task
                manager = task_info.get('manager')
                async_task = task_info.get('task')
                
                if isinstance(manager, GenAgent):
                    manager.stop()
                    self.logger.info(f"Stopped timed out task {task_id}")
                
                if async_task and not async_task.done():
                    async_task.cancel()
                    self.logger.info(f"Cancelled timed out async task {task_id}")
                
                # Update status to timeout
                task_info['status'] = 'timeout'
                
                # Import status update function from utils
                try:
                    from backend.utils import update_execute_agent_status_and_attempt
                    # Set task status to error
                    update_execute_agent_status_and_attempt(task_id, 2, 0)  # error status
                    self.logger.info(f"Updated session status for timed out task {task_id}")
                except ImportError:
                    self.logger.error("Could not import status update function")

    def get_task_info(self, task_id):
        """Get task details"""
        with self._lock:
            task_info = self.tasks.get(task_id)
            if task_info:
                current_time = time.time()
                last_heartbeat = task_info.get('last_heartbeat', task_info.get('created_at', 0))
                retry_count = task_info.get('retry_count', 0)
                return {
                    'status': task_info.get('status', 'unknown'),
                    'created_at': task_info.get('created_at', 0),
                    'last_heartbeat': last_heartbeat,
                    'timeout_in': max(0, self.task_timeout - (current_time - last_heartbeat)),
                    'is_timeout': (current_time - last_heartbeat) > self.task_timeout,
                    'retry_count': retry_count,
                    'max_retry_count': self.max_retry_count,
                    'last_retry_time': task_info.get('last_retry_time', 0),
                    'is_stalled': task_info.get('is_stalled', False)
                }
            return None

    def list_active_tasks(self):
        """List all active tasks"""
        with self._lock:
            active_tasks = {}
            current_time = time.time()
            for task_id, task_info in self.tasks.items():
                async_task = task_info.get('task')
                status = task_info.get('status', 'unknown')
                last_heartbeat = task_info.get('last_heartbeat', task_info.get('created_at', 0))
                retry_count = task_info.get('retry_count', 0)
                
                if async_task and not async_task.done():
                    active_tasks[task_id] = {
                        'status': status,
                        'timeout_in': max(0, self.task_timeout - (current_time - last_heartbeat)),
                        'is_timeout': (current_time - last_heartbeat) > self.task_timeout,
                        'retry_count': retry_count,
                        'max_retry_count': self.max_retry_count,
                        'is_stalled': task_info.get('is_stalled', False)
                    }
            return active_tasks