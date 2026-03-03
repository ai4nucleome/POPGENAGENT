"""
API Key Pool Manager - round-robin allocation to avoid single-key thread contention.
Pool entries are loaded from config.yaml.
"""

import threading
import logging
from typing import Dict, Tuple

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config_loader import get_api_pool_config


class APIKeyPool:
    """Manages a pool of API keys with round-robin allocation."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._lock = threading.RLock()
        self.current_index = 0

        pool_cfg = get_api_pool_config()
        self.api_pools = []
        for i, entry in enumerate(pool_cfg):
            self.api_pools.append({
                'api_key': entry['api_key'],
                'base_url': entry['base_url'],
                'name': entry.get('name', f'pool_{i+1}'),
                'active_tasks': set(),
                'max_concurrent': entry.get('max_concurrent', 3),
            })

        self.task_to_pool: Dict[str, int] = {}
        self.logger.info(f"Initialized API key pool with {len(self.api_pools)} pools")

    def allocate_api_key(self, task_id: str) -> Tuple[str, str]:
        """Allocate an API key for a task. Returns (api_key, base_url)."""
        with self._lock:
            if task_id in self.task_to_pool:
                pool_index = self.task_to_pool[task_id]
                pool = self.api_pools[pool_index]
                self.logger.debug(f"Task {task_id} reusing existing pool {pool['name']}")
                return pool['api_key'], pool['base_url']

            best_pool_index = self._find_best_available_pool()

            if best_pool_index is None:
                best_pool_index = self._get_next_pool_by_rotation()
                self.logger.warning(f"All pools at capacity, using rotation for task {task_id}")

            pool = self.api_pools[best_pool_index]
            pool['active_tasks'].add(task_id)
            self.task_to_pool[task_id] = best_pool_index

            self.logger.info(
                f"Allocated {pool['name']} to task {task_id} "
                f"(active: {len(pool['active_tasks'])}/{pool['max_concurrent']})"
            )
            return pool['api_key'], pool['base_url']

    def _find_best_available_pool(self):
        """Find the pool with the lowest utilization that is not at capacity."""
        for i, pool in enumerate(self.api_pools):
            if len(pool['active_tasks']) == 0:
                return i

        best_index = None
        min_usage = float('inf')
        for i, pool in enumerate(self.api_pools):
            if len(pool['active_tasks']) < pool['max_concurrent']:
                if len(pool['active_tasks']) < min_usage:
                    min_usage = len(pool['active_tasks'])
                    best_index = i
        return best_index

    def _get_next_pool_by_rotation(self) -> int:
        """Round-robin to the next pool index."""
        pool_index = self.current_index
        self.current_index = (self.current_index + 1) % len(self.api_pools)
        return pool_index

    def release_api_key(self, task_id: str) -> bool:
        """Release an API key allocation for a finished task."""
        with self._lock:
            if task_id not in self.task_to_pool:
                self.logger.warning(f"Task {task_id} not found in allocation records")
                return False

            pool_index = self.task_to_pool[task_id]
            pool = self.api_pools[pool_index]
            pool['active_tasks'].discard(task_id)
            del self.task_to_pool[task_id]

            self.logger.info(
                f"Released {pool['name']} from task {task_id} "
                f"(remaining: {len(pool['active_tasks'])}/{pool['max_concurrent']})"
            )
            return True

    def get_pool_status(self) -> Dict:
        """Return a status dict for all pools."""
        with self._lock:
            status = {
                'pools': [],
                'total_active_tasks': len(self.task_to_pool),
                'current_rotation_index': self.current_index,
            }
            for i, pool in enumerate(self.api_pools):
                status['pools'].append({
                    'index': i,
                    'name': pool['name'],
                    'base_url': pool['base_url'],
                    'active_tasks': len(pool['active_tasks']),
                    'max_concurrent': pool['max_concurrent'],
                    'utilization': f"{len(pool['active_tasks'])}/{pool['max_concurrent']}",
                    'task_list': list(pool['active_tasks']),
                })
            return status

    def get_task_api_info(self, task_id: str) -> Dict:
        """Return API allocation info for a specific task."""
        with self._lock:
            if task_id not in self.task_to_pool:
                return {'allocated': False, 'message': 'Task not allocated'}

            pool_index = self.task_to_pool[task_id]
            pool = self.api_pools[pool_index]
            return {
                'allocated': True,
                'pool_index': pool_index,
                'pool_name': pool['name'],
                'base_url': pool['base_url'],
                'pool_utilization': f"{len(pool['active_tasks'])}/{pool['max_concurrent']}",
            }

    def cleanup_stale_allocations(self, active_task_ids: set) -> int:
        """Remove allocations for tasks that are no longer active."""
        with self._lock:
            stale_tasks = set(self.task_to_pool.keys()) - active_task_ids
            cleanup_count = 0
            for task_id in stale_tasks:
                if self.release_api_key(task_id):
                    cleanup_count += 1
            if cleanup_count > 0:
                self.logger.info(f"Cleaned up {cleanup_count} stale API allocations")
            return cleanup_count


# Global singleton
api_key_pool = APIKeyPool()
