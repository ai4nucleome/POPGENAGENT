# main/timeout_monitor.py

import threading
import time
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.task_manager import TaskManager

class TimeoutMonitor:
    """
    Timeout monitor - periodically checks if tasks have timed out and handles them automatically
    """
    
    def __init__(self, task_manager: 'TaskManager', check_interval: int = 60):
        """
        Initialize the timeout monitor
        
        Args:
            task_manager: Task manager instance
            check_interval: Check interval in seconds, default 60 seconds
        """
        self.task_manager = task_manager
        self.check_interval = check_interval
        self.monitor_thread = None
        self.stop_flag = threading.Event()
        self.logger = logging.getLogger(__name__)
        
    def start_monitoring(self):
        """Start the monitoring thread"""
        if self.monitor_thread is not None and self.monitor_thread.is_alive():
            self.logger.warning("Monitor thread is already running")
            return
            
        self.stop_flag.clear()
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        self.logger.info(f"Timeout monitor started with {self.check_interval}s interval")
        
    def stop_monitoring(self):
        """Stop the monitoring thread"""
        if self.monitor_thread is None:
            return
            
        self.stop_flag.set()
        if self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5)
            
        self.logger.info("Timeout monitor stopped")
        
    def _monitor_loop(self):
        """Monitoring loop"""
        while not self.stop_flag.is_set():
            try:
                # Check for timeout tasks
                timeout_tasks = self.task_manager.check_timeout_tasks()
                if timeout_tasks:
                    self.logger.warning(f"Automatically handled {len(timeout_tasks)} timeout tasks: {timeout_tasks}")
                    
                # Wait for next check
                if not self.stop_flag.wait(self.check_interval):
                    continue  # If returned due to timeout, continue loop
                else:
                    break  # If returned because stop_flag was set, exit loop
                    
            except Exception as e:
                self.logger.error(f"Error in timeout monitor loop: {e}")
                # Wait for a while before continuing after error
                if not self.stop_flag.wait(min(self.check_interval, 30)):
                    continue
                else:
                    break
                    
        self.logger.info("Timeout monitor loop ended")
        
    def is_monitoring(self):
        """Check if monitoring is active"""
        return (self.monitor_thread is not None and 
                self.monitor_thread.is_alive() and 
                not self.stop_flag.is_set())
