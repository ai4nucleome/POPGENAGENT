# main/apps.py

from django.apps import AppConfig
import logging

class MainConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'backend'

    def ready(self):
        # Configure logging
        logger = logging.getLogger(__name__)
        logger.info("Starting initialization...")

        from .utils import (
            ensure_directories,
            scan_and_store_files,
            scan_and_sync_sessions,
            get_all_sessions,
            update_execute_agent_status,
            cleanup_stale_processing_status,
            cleanup_stale_sessions
        )

        # 1. Ensure necessary directories exist
        ensure_directories()

        # 2. Scan and store file information
        scan_and_store_files()

        # 3. Sync sessions (only add missing sessions, do not update status)
        scan_and_sync_sessions()

        # 4. Clean up stale processing/running status left after server restart
        cleanup_stale_processing_status()
        logger.info("Cleaned up stale processing statuses")
        
        # 5. Clean up stale sessions
        cleanup_stale_sessions()
        logger.info("Cleaned up stale sessions")

        # 6. Get all sessions and update execute_agent status (unified update here)
        sessions = get_all_sessions()
        for session in sessions:
            session_id = session.get('id')
            if session_id is not None:
                update_execute_agent_status(session_id)
                logger.info(f"Updated execute_agent status for Session ID={session_id}")
            else:
                logger.warning(f"Session without ID found: {session}")

        logger.info("Initialization complete: Directories ensured, files scanned, sessions synchronized, stale statuses cleaned, execute_agent statuses updated.")
