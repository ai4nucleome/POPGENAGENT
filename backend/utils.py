# main/utils.py

import os
import json
import threading
import logging
import re
import base64
from PIL import Image
import io
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("debug.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Define paths for JSON files
FILE_INFO_PATH = os.path.join(os.getcwd(), 'knowledge', 'file_info.json')
SESSION_STATUS_PATH = os.path.join(os.getcwd(), 'knowledge', 'session_status.json')

# Create thread locks for thread safety
file_info_lock = threading.Lock()
session_lock = threading.Lock()

import shutil

def delete_session_and_files(session_id: int) -> bool:
    """
    Remove the session with ID session_id from session_status.json;
    and delete:
    1. Corresponding PLAN.json, Step_*.sh, DEBUG_*.json and subfolder under ./output/
    2. All contents under ./history/{id}/
    Returns True on success, False if session not found.
    """
    # 1. Remove the session from session_status.json
    sessions = load_sessions()
    original_len = len(sessions)
    updated_sessions = [s for s in sessions if s.get('id') != session_id]

    # If no session was removed, session_id does not exist
    if len(updated_sessions) == original_len:
        return False  # Session not found

    # Save updated session list
    save_sessions(updated_sessions)

    # 2. Delete related files under ./output/
    sid_str = f"{session_id:03d}"  # Format ID as 3 digits, e.g. 5 -> 005

    # 2.1 Delete plan file: 005_PLAN.json
    output_dir = os.path.join(os.getcwd(), 'output')
    plan_file = os.path.join(output_dir, f"{sid_str}_PLAN.json")
    if os.path.exists(plan_file):
        os.remove(plan_file)
        logger.info(f"Removed plan file: {plan_file}")

    # 2.2 Delete Step scripts (005_Step_*.sh) and Debug files (005_DEBUG_*.json)
    for file_name in os.listdir(output_dir):
        if file_name.startswith(f"{sid_str}_Step_") and file_name.endswith(".sh"):
            step_file_path = os.path.join(output_dir, file_name)
            os.remove(step_file_path)
            logger.info(f"Removed step file: {step_file_path}")
        if file_name.startswith(f"{sid_str}_DEBUG_") and file_name.endswith(".json"):
            debug_file_path = os.path.join(output_dir, file_name)
            os.remove(debug_file_path)
            logger.info(f"Removed debug file: {debug_file_path}")

    # 2.3 Delete output/005 folder
    subfolder = os.path.join(output_dir, sid_str)
    if os.path.isdir(subfolder):
        shutil.rmtree(subfolder)
        logger.info(f"Removed folder: {subfolder}")

    # 3. Delete ./history/{id}/ directory and its contents
    history_dir = os.path.join(os.getcwd(), 'history', sid_str)
    if os.path.exists(history_dir):
        shutil.rmtree(history_dir)
        logger.info(f"Removed history directory: {history_dir}")

    return True

def ensure_directories():
    """
    Ensure necessary directories exist.
    """
    directories = [
        os.path.join(os.getcwd(), 'output'),
        os.path.join(os.getcwd(), 'knowledge'),
        os.path.join(os.getcwd(), 'data')  # Ensure data directory exists
    ]
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        logger.info(f"Ensured directory exists: {directory}")


def get_next_id(file_info):
    """
    Get the next available ID, incrementing from 1.
    """
    if not file_info:
        return 1
    else:
        # Get current max ID and add 1
        max_id = max(item['id'] for item in file_info)
        return max_id + 1


def scan_and_store_files():
    """
    Iterate over all files in the data directory and store file info in file_info.json.
    Includes generating incremental IDs and recording absolute paths.
    For new files, description is empty and metadata is empty dict.
    If a file has been deleted, remove it from the JSON.
    """
    DATA_PATH = os.path.join(os.getcwd(), 'data')  # Ensure this path points to your data directory

    if not os.path.exists(DATA_PATH):
        logger.warning(f"Data path {DATA_PATH} does not exist.")
        return

    current_files = set(os.listdir(DATA_PATH))
    file_info = load_file_info()
    existing_files = set(item['filename'] for item in file_info)

    new_files = current_files - existing_files
    deleted_files = existing_files - current_files

    # Get next available ID
    next_id = get_next_id(file_info)

    # Add new files
    for file_name in sorted(new_files):  # Sort to maintain ID consistency
        absolute_path = os.path.abspath(os.path.join(DATA_PATH, file_name))
        file_info.append({
            'id': next_id,
            'filename': file_name,
            'absolute_path': absolute_path,
            'description': '',
            'metadata': {}
        })
        logger.info(f"Added new file: {file_name} with ID: {next_id}")
        next_id += 1

    # Remove deleted files
    if deleted_files:
        file_info = [item for item in file_info if item['filename'] not in deleted_files]
        for file_name in deleted_files:
            logger.info(f"Removed deleted file: {file_name}")

    save_file_info(file_info)

    logger.info(f"Scanned {len(current_files)} files. Added {len(new_files)} new files and removed {len(deleted_files)} deleted files.")


def load_sessions():
    """
    Read session_status.json and return data.
    If file does not exist, return empty list and create file.
    """
    if not os.path.exists(SESSION_STATUS_PATH):
        # Create empty session_status.json file
        with session_lock:
            with open(SESSION_STATUS_PATH, 'w', encoding='utf-8') as f:
                json.dump([], f, ensure_ascii=False, indent=4)
        logger.info(f"Created new session_status.json at {SESSION_STATUS_PATH}")
        return []

    with session_lock:
        with open(SESSION_STATUS_PATH, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
                return data
            except json.JSONDecodeError:
                logger.error("JSON Decode Error: Invalid JSON format in session_status.json")
                return []
def load_file_info():
    """
    Load file info list.
    """
    if os.path.exists(FILE_INFO_PATH):
        try:
            with open(FILE_INFO_PATH, 'r', encoding='utf-8') as file:
                return json.load(file)
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON from {FILE_INFO_PATH}: {e}")
            return []
    return []

def save_file_info(file_info):
    """
    Save file info list.
    """
    try:
        with open(FILE_INFO_PATH, 'w', encoding='utf-8') as file:
            json.dump(file_info, file, ensure_ascii=False, indent=4)
    except Exception as e:
        logger.error(f"Error saving file info to {FILE_INFO_PATH}: {e}")

    
def update_file_description(filename, description):
    """
    Update the description of the specified file.
    
    :param filename: Filename to update
    :param description: New description for the file
    :return: Whether update succeeded
    """
    file_info = load_file_info()
    print(file_info)
    updated = False

    for item in file_info:
        if item['filename'] == filename:
            item['description'] = description
            updated = True
            logger.info(f"Updated description for file {filename}")
            break

    if updated:
        save_file_info(file_info)
    else:
        logger.warning(f"File {filename} not found in file info")

    return updated
def update_file_description_for_session(session_id, filename, description):
    """
    Update file description based on session_id and filename.
    """
    file_info = load_file_info()
    session_found = False
    file_found = False

    for session in file_info:
        if session.get('id') == session_id:
            session_found = True
            for file in session.get('files', []):
                if file.get('filename') == filename:
                    file['description'] = description
                    file_found = True
                    break

    if not session_found:
        return False, f"Session ID {session_id} not found"
    if not file_found:
        return False, f"File {filename} not found in session {session_id}"

    save_file_info(file_info)
    return True, "File description updated successfully"


def save_sessions(data):
    """
    Write data to session_status.json file.
    """
    with session_lock:
        with open(SESSION_STATUS_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    # logger.info("Saved session_status.json successfully.")


def get_next_session_id(sessions):
    """
    Get the next available session ID, incrementing from 1.
    """
    if not sessions:
        return 1
    else:
        max_id = max(session['id'] for session in sessions)
        return max_id + 1


def create_session(title):
    """
    Create a new session, including:
    - Assign unique ID
    - Create output directory
    - Create PLAN file
    - Initialize session state
    """
    sessions = load_sessions()
    next_id = get_next_session_id(sessions)
    formatted_id = f"{next_id:03d}"  # Format as 3 digits with leading zeros

    # Create output directory
    output_dir = os.path.join(os.getcwd(), 'output')
    os.makedirs(output_dir, exist_ok=True)
    logger.info(f"Ensured output directory exists: {output_dir}")

    # Create PLAN file
    plan_file_path = os.path.join(output_dir, f"{formatted_id}_PLAN.json")
    # initial_plan = {
    #     "shell": [],
    #     "analyze": "",
    #     "output_filename": [],
    #     "stats": False,
    #     "plan": []  # Add plan field
    # }
    initial_plan = {
        "plan": []  # Add plan field
    }
    with open(plan_file_path, 'w', encoding='utf-8') as f:
        json.dump(initial_plan, f, ensure_ascii=False, indent=4)
    logger.info(f"Created PLAN file: {plan_file_path}")

    # Get total step count
    total_steps = len(initial_plan["plan"])  # Initially 0

    # Initialize session state
    new_session = {
        "id": next_id,
        "title": title,
        "chat_agent": {
            "status": "idle", #thinking,error,using_tools,
            "message":"",
            "lastupdate":"2024-12-09:17:48"
        },
        "execute_agent": {
            "step_completion": "0%",
            "current_step": 0,
            "total_steps": total_steps,  # Add total_steps field
            "is_execute": False,
            "status": "not working",
            "attempt": 0,
            "bug": "",
            "output": "",
            "stage": "PLAN",#task excute/debug
            "status": "idle", #thinking,error,using_tools
            "message":"",
            "lastupdate":"2024-12-09:17:48"
        },
        "analysis_agent": {
            "status": "idle", #thinking,error,using_tools
            "message":"",
            "lastupdate":"2024-12-09:17:48"
        }
    }

    sessions.append(new_session)
    save_sessions(sessions)

    logger.info(f"Created new session: ID={formatted_id}, Title={title}")
    return new_session


def get_all_sessions():
    """
    Get information for all sessions.
    """
    return load_sessions()


def get_session_by_id(session_id):
    """
    Get information for a specific session by ID.
    """
    sessions = load_sessions()
    for session in sessions:
        if session['id'] == session_id:
            return session
    return None


def update_session(session_id, agent, key, value):
    """
    Update a specific field of a specific agent in a session.
    """
    sessions = load_sessions()
    for session in sessions:
        if session['id'] == session_id:
            # Ensure agent field exists
            if agent not in session:
                session[agent] = {'status': 'idle', 'lastupdate': ''}
            
            if agent == 'chat_agent':
                session['chat_agent'][key] = value
                session['chat_agent']['lastupdate'] = datetime.now().strftime('%Y-%m-%d:%H:%M')
            elif agent == 'execute_agent':
                session['execute_agent'][key] = value
                session['execute_agent']['lastupdate'] = datetime.now().strftime('%Y-%m-%d:%H:%M')
            elif agent == 'analysis_agent':
                session['analysis_agent'][key] = value
                session['analysis_agent']['lastupdate'] = datetime.now().strftime('%Y-%m-%d:%H:%M')
            else:
                logger.error(f"Unknown agent: {agent}")
                return False
            save_sessions(sessions)
            logger.info(f"Updated session ID={session_id}, Agent={agent}, {key}={value}")
            return True
    logger.error(f"Session ID={session_id} not found.")
    return False


def create_step_files(session_id, step_number, shell_commands):
    """
    Create execution step scripts and debug input/output files.
    """
    formatted_id = f"{session_id:03d}"
    base_output_path = os.path.join(os.getcwd(), 'output')

    # Create Step script
    step_script_path = os.path.join(base_output_path, f"{formatted_id}_Step_{step_number}.sh")
    with open(step_script_path, 'w', encoding='utf-8') as f:
        for cmd in shell_commands:
            f.write(cmd + "\n")
    logger.info(f"Created Step script: {step_script_path}")

    # Create Debug Input file
    debug_input_path = os.path.join(base_output_path, f"{formatted_id}_DEBUG_Input_{step_number}.json")
    debug_input_content = {
        "input": f"Sample debug input for step {step_number}"
    }
    with open(debug_input_path, 'w', encoding='utf-8') as f:
        json.dump(debug_input_content, f, ensure_ascii=False, indent=4)
    logger.info(f"Created Debug Input file: {debug_input_path}")

    # Create Debug Output file
    debug_output_path = os.path.join(base_output_path, f"{formatted_id}_DEBUG_Output_{step_number}.json")
    debug_output_content = {
        "output": "",
        "error": "",
        "stats": False,  # Initially False
        "analyze": "",
        "output_filename": []
    }
    with open(debug_output_path, 'w', encoding='utf-8') as f:
        json.dump(debug_output_content, f, ensure_ascii=False, indent=4)
    logger.info(f"Created Debug Output file: {debug_output_path}")


def get_total_steps(session_id):
    """
    Read {formatted_id}_PLAN.json file and count total steps.
    """
    formatted_id = f"{session_id:03d}"
    plan_file_path = os.path.join(os.getcwd(), 'output', f"{formatted_id}_PLAN.json")
    # logger.info(f"Checking plan file: {plan_file_path}")
    if os.path.exists(plan_file_path):
        with open(plan_file_path, 'r', encoding='utf-8') as f:
            plan = json.load(f)
            steps_len = len(plan.get('plan', []))
            # logger.info(f"Found {steps_len} steps for session {session_id}")
            return steps_len
    else:
        logger.warning(f"Plan file not found for session {session_id} at {plan_file_path}")
    return 0


def get_current_step(session_id):
    """
    Read all DEBUG_Output_{step_number}.json files to get current step number.
    Apply logic to ensure current_step does not exceed total_steps.
    """
    formatted_id = f"{session_id:03d}"
    base_output_path = os.path.join(os.getcwd(), 'output')
    if not os.path.exists(base_output_path):
        logger.warning(f"Output directory {base_output_path} does not exist.")
        return 0

    # Search for debug files in output root directory
    debug_files = [f for f in os.listdir(base_output_path) 
                   if f.startswith(f"{formatted_id}_DEBUG_Output_") and f.endswith(".json")]

    max_step = 0
    last_stats = False

    for file in debug_files:
        match = re.match(rf"{formatted_id}_DEBUG_Output_(\d+)\.json", file)
        if match:
            step_number = int(match.group(1))
            if step_number > max_step:

                
                debug_output_path = os.path.join(base_output_path, file)
                try:
                    with open(debug_output_path, 'r', encoding='utf-8') as f:
                        debug_output = json.load(f)
                        last_stats = debug_output.get('stats', False)
                        if last_stats!=False:
                            max_step = step_number
                except FileNotFoundError:
                    logger.error(f"Debug output file not found: {debug_output_path}")
                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON format in debug output file: {debug_output_path}")

    # Get total step count
    total_steps = get_total_steps(session_id)

    # Calculate current_step per logic
    # if last_stats:
    #     # If previous step succeeded, ensure does not exceed total_steps
    #     if max_step < total_steps:
    #         current_step = max_step + 1
    #     else:
    #         current_step = max_step
    # else:
    #     current_step = max_step
    current_step = max_step
    logger.info(f"Session ID={session_id}: current_step={current_step}, total_steps={total_steps}")
    return current_step


def update_execute_agent_status(session_id):
    """
    Update execute_agent status, including:
    - current_step, step_completion, bug, total_steps, stage
    - When last step fails (last_stats=False), read analyze and output_filename from last DEBUG output file into bug and output fields
    - Update stage based on file existence and completion:
      * Default "PLAN"
      * "EXECUTE" when Step_{step_number}.sh exists
      * "DEBUG" when DEBUG_Output_{step_number}.json exists
      * "FINISH" when completion is 100%
      
    session_id: Can be numeric (1) or string format ('001') ID
    """
    # Convert session_id to numeric format
    try:
        if isinstance(session_id, str):
            numeric_id = int(session_id.lstrip('0') or '0')
        else:
            numeric_id = int(session_id)
    except (ValueError, TypeError):
        logger.error(f"Invalid session_id format: {session_id}")
        return False

    sessions = load_sessions()
    updated = False
    for session in sessions:
        if session['id'] == numeric_id:  # Compare using converted numeric ID
            formatted_id = f"{numeric_id:03d}"  # Formatted ID for filenames
            base_output_path = os.path.join(os.getcwd(), 'output')

            # Get total steps and current step
            total_steps = get_total_steps(numeric_id)
            session['execute_agent']['total_steps'] = total_steps

            current_step = get_current_step(numeric_id)
            session['execute_agent']['current_step'] = current_step

            # Calculate completion percentage
            if total_steps > 0:
                completion_percentage = f"{(current_step / total_steps) * 100:.2f}%"
            else:
                completion_percentage = "0%"
            session['execute_agent']['step_completion'] = completion_percentage
            
            # Check file existence to update stage
            step_files = [f for f in os.listdir(base_output_path) 
                         if f.startswith(f"{formatted_id}_Step_") and f.endswith(".sh")]
            debug_files = [f for f in os.listdir(base_output_path) 
                         if f.startswith(f"{formatted_id}_DEBUG_Output_") and f.endswith(".json")]

            # Update stage status
            if completion_percentage == "100.00%":
                session['execute_agent']['stage'] = "FINISH"
            elif session['execute_agent']['stage']=="PAUSED":
                break
            elif debug_files:
                session['execute_agent']['stage'] = "DEBUG"
            elif step_files:
                session['execute_agent']['stage'] = "EXECUTE"
            else:
                session['execute_agent']['stage'] = "PLAN"

            # Default clear bug and output
            session['execute_agent']['bug'] = ""
            session['execute_agent']['output'] = ""

            # Search all DEBUG files to determine last step and execution result
            max_step = 0
            last_step_stats = True
            last_debug_output = {}

            for file in debug_files:
                match = re.match(rf"{formatted_id}_DEBUG_Output_(\d+)\.json", file)
                if match:
                    step_num = int(match.group(1))
                    if step_num > max_step:
                        max_step = step_num
                        debug_output_path = os.path.join(base_output_path, file)
                        try:
                            with open(debug_output_path, 'r', encoding='utf-8') as f:
                                debug_output = json.load(f)
                                last_step_stats = debug_output.get('stats', False)
                                last_debug_output = debug_output
                        except FileNotFoundError:
                            logger.error(f"Debug output file not found: {debug_output_path}")
                        except json.JSONDecodeError:
                            logger.error(f"Invalid JSON format in debug output file: {debug_output_path}")

            # If last step failed (last_step_stats=False), read analyze and output_filename from DEBUG output
            if not last_step_stats and last_debug_output:
                analyze = last_debug_output.get('analyze', '')
                output_filenames = last_debug_output.get('output_filename', [])
                session['execute_agent']['bug'] = analyze
                # Convert output_filename list to string for storage
                if isinstance(output_filenames, list):
                    session['execute_agent']['output'] = ", ".join(output_filenames)
                else:
                    session['execute_agent']['output'] = str(output_filenames)

            save_sessions(sessions)
            # logger.info(f"Updated execute_agent status for Session ID={numeric_id}")
            updated = True
            break

    if not updated:
        logger.error(f"Session ID={numeric_id} not found for updating execute_agent status.")
    return updated


def clean_up_sessions():
    """
    Clean up invalid sessions: if no corresponding PLAN or DEBUG files in output directory, remove session from session_status.json.
    """
    sessions = load_sessions()
    base_output_path = os.path.join(os.getcwd(), 'output')

    updated_sessions = []
    for session in sessions:
        session_id = session.get('id')
        if session_id is None:
            # Skip sessions without id
            continue

        formatted_id = f"{session_id:03d}"
        plan_file_path = os.path.join(base_output_path, f"{formatted_id}_PLAN.json")
        # Search for DEBUG files
        debug_files = [f for f in os.listdir(base_output_path)
                       if f.startswith(f"{formatted_id}_DEBUG_Output_") and f.endswith(".json")]

        plan_exists = os.path.exists(plan_file_path)
        debug_exists = len(debug_files) > 0

        if plan_exists or debug_exists:
            # Keep session if at least PLAN or DEBUG file exists
            updated_sessions.append(session)
        else:
            # No PLAN or DEBUG file, remove this session
            logger.info(f"No files found for session ID={session_id}. Removing this session from session_status.json.")

    # Save cleaned sessions
    save_sessions(updated_sessions)
    logger.info("Clean up completed. Removed sessions with no corresponding files.")


def scan_and_sync_sessions():
    """
    Scan session files in ./output/ directory and sync with session_status.json.
    After sync, call clean_up_sessions to clean sessions with no corresponding files.
    """
    output_path = os.path.join(os.getcwd(), 'output')
    if not os.path.exists(output_path):
        logger.warning(f"Output path {output_path} does not exist.")
        return

    sessions = load_sessions()
    existing_session_ids = {session['id'] for session in sessions if 'id' in session}

    # Identify new sessions or update existing ones per your logic.
    # E.g. for each {formatted_id}_PLAN.json or DEBUG file infer session_id,
    # create new session if not exists, call update_execute_agent_status(session_id) if exists.
    #
    # Example (illustrative only):
    all_files = os.listdir(output_path)
    # Try to identify new session IDs from PLAN files
    plan_files = [f for f in all_files if re.match(r'\d{3}_PLAN\.json', f)]
    for pf in plan_files:
        match = re.match(r'(\d{3})_PLAN\.json', pf)
        if match:
            formatted_id = match.group(1)
            session_id = int(formatted_id)
            # If session not in sessions, add an initialized session entry
            if session_id not in existing_session_ids:
                new_session = {
                    "id": session_id,
                    "title": f"Untitled Session {formatted_id}",
                   "chat_agent": {
                        "status": "idle", #thinking,error,using_tools,
                        "message":"",
                        "lastupdate":"2024-12-09:17:48"
                    },
                    "execute_agent": {
                        "step_completion": "0%",
                        "current_step": 0,
                        "total_steps": 0,  # Add total_steps field
                        "is_execute": False,
                        "status": "not working",
                        "attempt": 0,
                        "bug": "",
                        "output": "",
                        "stage": "PLAN",#task excute/debug
                        "status": "idle", #thinking,error,using_tools
                        "message":"",
                        "lastupdate":"2024-12-09:17:48"
                    },
                    "analysis_agent": {
                        "status": "idle", #thinking,error,using_tools
                        "message":"",
                        "lastupdate":"2024-12-09:17:48"
                    }
                }
                sessions.append(new_session)
                existing_session_ids.add(session_id)
                logger.info(f"Added new session: ID={session_id}")

            # Call update_execute_agent_status for both new and existing to ensure latest status
            update_execute_agent_status(session_id)

    # Save updated session info
    save_sessions(sessions)
    logger.info("Synchronized sessions with output directory.")

    # Execute cleanup after sync
    clean_up_sessions()

def update_execute_agent_status_and_attempt(session_id, status_code: int, attempt: int):
    """
    Update execute_agent status and attempt fields
    
    session_id: Can be numeric (1) or string format ('001') ID
    status_code:
    - 0: idle
    - 1: thinking
    - 2: error
    - 3: using_tools
    - 4: error-last
    
    attempt: Integer 0-10
    
    Returns:
    - True: Update succeeded
    - False: Update failed (session not found or invalid params)
    """
    # Validate input parameters
    if status_code not in [0, 1, 2, 3,4] or not (0 <= attempt <= 10):
        logger.error(f"Invalid parameters: status_code={status_code}, attempt={attempt}")
        return False

    # Convert session_id to numeric format
    try:
        if isinstance(session_id, str):
            numeric_id = int(session_id.lstrip('0') or '0')
        else:
            numeric_id = int(session_id)
    except (ValueError, TypeError):
        logger.error(f"Invalid session_id format: {session_id}")
        return False

    # Status mapping
    status_map = {
        0: "idle",
        1: "thinking",
        2: "error",
        3: "using_tools",
        4: "error-last"
    }

    sessions = load_sessions()
    updated = False

    for session in sessions:
        if session['id'] == numeric_id:  # Compare using converted numeric ID
            # Update status and attempt
            session['execute_agent']['status'] = status_map[status_code]
            session['execute_agent']['attempt'] = attempt
            session['execute_agent']['lastupdate'] = datetime.now().strftime('%Y-%m-%d:%H:%M')  # Update timestamp
            if status_code==4:
                session['execute_agent']['stage']='ERROR'
            # Save updated sessions
            save_sessions(sessions)
            # logger.info(f"Updated execute_agent for Session ID={numeric_id}: status={status_map[status_code]}, attempt={attempt}")
            updated = True
            break

    if not updated:
        logger.error(f"Session ID={numeric_id} not found for updating status and attempt")
        return False

    return True

def update_execute_agent_stage(session_id, stage: str):
    """
    Update execute_agent stage field
    
    session_id: Can be numeric (1) or string format ('001') ID
    stage: Stage to set, e.g. "PLAN", "EXECUTE", "DEBUG", "FINISH", "PAUSED"
    
    Returns:
    - True: Update succeeded
    - False: Update failed (session not found)
    """
    # Convert session_id to numeric format
    try:
        if isinstance(session_id, str):
            numeric_id = int(session_id.lstrip('0') or '0')
        else:
            numeric_id = int(session_id)
    except (ValueError, TypeError):
        logger.error(f"Invalid session_id format: {session_id}")
        return False

    sessions = load_sessions()
    updated = False

    for session in sessions:
        if session['id'] == numeric_id:  # Compare using converted numeric ID
            # Update stage
            session['execute_agent']['stage'] = stage
            session['execute_agent']['lastupdate'] = datetime.now().strftime('%Y-%m-%d:%H:%M')  # Update timestamp
            
            # Save updated sessions
            save_sessions(sessions)
            # logger.info(f"Updated execute_agent stage for Session ID={numeric_id} to {stage}")
            updated = True
            break

    if not updated:
        logger.error(f"Session ID={numeric_id} not found for updating stage")
        return False

    return True

def get_session_content_index(session_id):
    """
    Scan all files in ./output/{id}/ directory, process different file types:
    - Photo files: collect file paths
    - PDF files: convert to photo format and collect paths
    - Other files: try to read first 10 lines or 100 bytes
    
    Result saved as JSON to ./output/{id}_result.json
    
    :param session_id: Session ID (numeric or string format)
    :return: True on success, False on failure
    """
    # Convert session_id to formatted ID string (e.g. 5 -> "005")
    try:
        if isinstance(session_id, str):
            numeric_id = int(session_id.lstrip('0') or '0')
        else:
            numeric_id = int(session_id)
        formatted_id = f"{numeric_id:03d}"
    except (ValueError, TypeError):
        logger.error(f"Invalid session_id format: {session_id}")
        return False
    
    # Build output directory path
    base_output_path = os.path.join(os.getcwd(), 'output')
    session_dir = os.path.join(base_output_path, formatted_id)
    
    # Check if directory exists
    if not os.path.exists(session_dir) or not os.path.isdir(session_dir):
        logger.warning(f"Session directory not found: {session_dir}")
        return False
    
    # Initialize result dict
    result = {
        "photo": [],
        "doc": {}
    }
    
    # Photo file extensions
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'}
    
    # Scan all files in directory
    for filename in os.listdir(session_dir):
        file_path = os.path.join(session_dir, filename)
        
        # Skip directories
        if os.path.isdir(file_path):
            continue
        
        # Get file extension
        _, ext = os.path.splitext(filename)
        ext = ext.lower()
        
        # Process photo files
        if ext in image_extensions:
            result["photo"].append(file_path)
            logger.info(f"Added image file: {file_path}")
            continue
        
        # Process PDF files (try to convert to photo)
        if ext == '.pdf':
            try:
                # Try to import pdf2image
                try:
                    from pdf2image import convert_from_path
                    # Convert PDF first page to photo
                    images = convert_from_path(file_path, first_page=1, last_page=1)
                    if images:
                        # Build photo output path
                        image_filename = os.path.splitext(filename)[0] + '.jpg'
                        image_path = os.path.join(session_dir, image_filename)
                        # Save photo
                        images[0].save(image_path, 'JPEG')
                        result["photo"].append(image_path)
                        logger.info(f"Converted PDF to image: {image_path}")
                except ImportError:
                    logger.warning("pdf2image library not available. PDF conversion skipped.")
                    # Treat PDF as file
                    result["doc"][filename] = "PDF file (conversion to image failed)"
            except Exception as e:
                logger.error(f"Error processing PDF file {filename}: {e}")
                result["doc"][filename] = f"Error: {str(e)[:100]}"
            continue
        
        # Process other files, try to read text content
        try:
            content = ""
            try:
                # Try to read in text mode
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = []
                    total_bytes = 0
                    max_line_length = 10  # Max length per line
                    total_max_bytes = 50  # Total max bytes
                    
                    for _ in range(10):  # Read at most 10 lines
                        line = f.readline()
                        if not line:
                            break
                            
                        # Truncate if line too long
                        if len(line) > max_line_length:
                            line = line[:max_line_length]
                            
                        lines.append(line.rstrip())
                        total_bytes += len(line.encode('utf-8'))
                        if total_bytes >= total_max_bytes:  # Stop if exceeded byte limit
                            break
                    content = '\n'.join(lines)
            except UnicodeDecodeError:
                # If text mode failed, try binary mode
                with open(file_path, 'rb') as f:
                    binary_data = f.read(100)  # Read at most 100 bytes
                    # Try to convert to text
                    try:
                        content = binary_data.decode('utf-8', errors='replace')
                        if len(content) > 50:
                            content = content[:50] 
                    except:
                        content = f"Binary file, preview not available"
            
            # Add content to result
            if content:
                result["doc"][filename] = content
                logger.info(f"Added file content preview: {filename}")
            else:
                result["doc"][filename] = "(Empty file or reading error)"
                
        except Exception as e:
            logger.error(f"Error reading file {filename}: {e}")
            # Skip unreadable doc, only log error
            result["doc"][filename] = f"Error reading file: {str(e)[:100]}"
    
    # Save result to JSON
    result_path = os.path.join(base_output_path, f"{formatted_id}_result.json")
    try:
        with open(result_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        logger.info(f"Session content index saved to: {result_path}")
        return True
    except Exception as e:
        logger.error(f"Error saving session content index: {e}")
        return False

def update_history_execute_json(session_id):
    """
    Scans all Debug Output files for a session and updates the history/{id}/execute.json file.
    
    For each Debug Output file, it checks if there's a corresponding Step file for the next step
    and updates the execute.json accordingly.
    
    Args:
        session_id: Session ID (can be numeric or string format)
        
    Returns:
        bool: True if update successful, False otherwise
    """
    try:
        # Convert session_id to formatted string (e.g., 5 -> "005")
        if isinstance(session_id, str):
            numeric_id = int(session_id.lstrip('0') or '0')
        else:
            numeric_id = int(session_id)
        formatted_id = f"{numeric_id:03d}"
    except (ValueError, TypeError):
        logger.error(f"Invalid session_id format: {session_id}")
        return False
    
    # Define paths
    base_output_path = os.path.join(os.getcwd(), 'output')
    history_dir = os.path.join(os.getcwd(), 'history', formatted_id)
    execute_json_path = os.path.join(history_dir, 'execute.json')
    
    # Create history directory if it doesn't exist
    os.makedirs(history_dir, exist_ok=True)
    
    # Initialize or load existing execute.json
    execute_data = []
    if os.path.exists(execute_json_path):
        try:
            with open(execute_json_path, 'r', encoding='utf-8') as f:
                execute_data = json.load(f)
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON format in {execute_json_path}")
            execute_data = []
    
    # Get plan data
    plan_file_path = os.path.join(base_output_path, f"{formatted_id}_PLAN.json")
    plan_data = None
    if os.path.exists(plan_file_path):
        try:
            with open(plan_file_path, 'r', encoding='utf-8') as f:
                plan_data = json.load(f)
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON format in {plan_file_path}")
    
    # Find all Debug Output files for this session
    debug_files = [f for f in os.listdir(base_output_path) 
                   if f.startswith(f"{formatted_id}_DEBUG_Output_") and f.endswith(".json")]
    
    # Sort debug files by step number
    debug_files.sort(key=lambda f: int(re.match(rf"{formatted_id}_DEBUG_Output_(\d+)\.json", f).group(1)))
    
    # Track processed steps to avoid duplicates
    processed_steps = set()
    if execute_data:
        # Extract steps that are already in execute_data
        for entry in execute_data:
            if 'execute' in entry and 'steps' in entry['execute']:
                for i, step in enumerate(entry['execute']['steps']):
                    if step and ('debug' in step or 'shell' in step):
                        processed_steps.add(i)
    
    # Process each debug file
    for debug_file in debug_files:
        match = re.match(rf"{formatted_id}_DEBUG_Output_(\d+)\.json", debug_file)
        if not match:
            continue
        
        step_number = int(match.group(1))
        if step_number in processed_steps:
            logger.info(f"Step {step_number} already processed, skipping")
            continue
        
        # Read debug output file
        debug_output_path = os.path.join(base_output_path, debug_file)
        debug_data = None
        try:
            with open(debug_output_path, 'r', encoding='utf-8') as f:
                debug_data = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            logger.error(f"Error reading debug file: {debug_output_path}")
            continue
        
        # Update execute_data with new information
        if not execute_data:
            # Create initial entry if execute_data is empty
            entry = {
                "asking": None,
                "plan": {"plan": plan_data.get("plan", []) if plan_data else []},
                "execute": {
                    "steps": [],  # Initialize as empty list, not list with empty object
                    "status": "completed"
                }
            }
            execute_data.append(entry)
        
        # Get the last entry or create a new one if needed
        entry = execute_data[-1]
        
        # Check if steps has only one empty object, if so clear steps
        if 'execute' in entry and 'steps' in entry['execute']:
            steps = entry['execute']['steps']
            if len(steps) == 1 and steps[0] == {}:
                steps.clear()  # Clear empty object from list
        
        # Ensure execute and steps fields exist
        if 'execute' not in entry:
            entry['execute'] = {'steps': [], 'status': 'completed'}
        elif 'steps' not in entry['execute']:
            entry['execute']['steps'] = []
            
        steps = entry['execute']['steps']
        
        # Ensure there are enough steps in the entry
        while len(steps) <= step_number:
            steps.append({})
        
        # Add debug data to the step
        current_step = steps[step_number]
        current_step['step_number'] = step_number  # Ensure each step has step_number field
        
        # Get shell commands from debug data
        shell_commands = debug_data.get("shell", [])
        if isinstance(shell_commands, list) and shell_commands:
            # Convert shell commands to string if they're in a list
            shell_script = "#!/bin/bash\n" + "\n".join(shell_commands)
        else:
            shell_script = debug_data.get("shell", "#!/bin/bash\n")
        
        # Update current step with debug data
        current_step["debug"] = {
            "shell": shell_commands if isinstance(shell_commands, list) else 
                     [cmd.strip() for cmd in shell_script.split('\n') if cmd.strip()],
            "analyze": debug_data.get("analyze", ""),
            "output_filename": debug_data.get("output_filename", []),
            "stats": debug_data.get("stats", False)
        }
        
        # If shell script is not empty, add it
        if shell_script and not shell_script.isspace():
            current_step["shell"] = shell_script
        
        # Mark this step as processed
        processed_steps.add(step_number)
    
    # Save updated execute.json
    try:
        with open(execute_json_path, 'w', encoding='utf-8') as f:
            json.dump(execute_data, f, ensure_ascii=False, indent=4)
        # logger.info(f"Updated history execute.json for session {formatted_id}")
        return True
    except Exception as e:
        logger.error(f"Error saving execute.json: {e}")
        return False

def cleanup_stale_sessions():
    """
    Clean up stale sessions and expired tasks
    """
    try:
        sessions = load_sessions()
        current_time = datetime.now().timestamp()
        
        updated_sessions = []
        for session in sessions:
            session_id = session.get('id')
            execute_agent = session.get('execute_agent', {})
            
            # Check if zombie session (status thinking but no update for long time)
            last_update = execute_agent.get('lastupdate', '2024-12-09:17:48')
            try:
                # Parse timestamp
                last_update_time = datetime.strptime(last_update, '%Y-%m-%d:%H:%M').timestamp()
                time_diff = current_time - last_update_time
                
                # If no update for 30+ minutes and status is thinking, set to error
                if time_diff > 1800 and execute_agent.get('status') == 'thinking':
                    execute_agent['status'] = 'error'
                    execute_agent['stage'] = 'ERROR'
                    execute_agent['message'] = 'Session timed out'
                    logger.warning(f"Session {session_id} marked as error due to timeout")
                    
            except Exception as e:
                logger.error(f"Error parsing timestamp for session {session_id}: {e}")
            
            updated_sessions.append(session)
        
        save_sessions(updated_sessions)
        logger.info("Completed cleanup of stale sessions")
        return True
        
    except Exception as e:
        logger.error(f"Error in cleanup_stale_sessions: {e}")
        return False

def monitor_session_health():
    """
    Monitor session health status
    """
    try:
        sessions = load_sessions()
        health_report = {
            'total_sessions': len(sessions),
            'active_sessions': 0,
            'error_sessions': 0,
            'idle_sessions': 0
        }
        
        for session in sessions:
            execute_agent = session.get('execute_agent', {})
            status = execute_agent.get('status', 'unknown')
            
            if status == 'thinking' or status == 'using_tools':
                health_report['active_sessions'] += 1
            elif status == 'error' or status == 'error-last':
                health_report['error_sessions'] += 1
            elif status == 'idle':
                health_report['idle_sessions'] += 1
        
        logger.info(f"Session health report: {health_report}")
        return health_report
        
    except Exception as e:
        logger.error(f"Error in monitor_session_health: {e}")
        return None

def create_initial_history_entry(session_id, message="Task started", is_execute_phase=False):
    """
    Create history entry immediately when task starts, only write asking, update after task completes
    
    Parameters:
    - session_id: Session ID
    - message: Task description/user input
    - is_execute_phase: Whether execution phase (True = update existing entry instead of creating new)
    """
    try:
        # Convert session_id to formatted ID string (e.g. 5 -> "005")
        if isinstance(session_id, str):
            numeric_id = int(session_id.lstrip('0') or '0')
        else:
            numeric_id = int(session_id)
        formatted_id = f"{numeric_id:03d}"
        
        # Create history directory
        history_dir = os.path.join(os.getcwd(), 'history', formatted_id)
        os.makedirs(history_dir, exist_ok=True)
        
        execute_json_path = os.path.join(history_dir, 'execute.json')
        
        # Read existing history or create new
        execute_data = []
        if os.path.exists(execute_json_path):
            try:
                with open(execute_json_path, 'r', encoding='utf-8') as f:
                    execute_data = json.load(f)
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON format in {execute_json_path}")
                execute_data = []
        
        # Read plan data
        plan_file_path = os.path.join(os.getcwd(), 'output', f"{formatted_id}_PLAN.json")
        plan_data = None
        if os.path.exists(plan_file_path):
            try:
                with open(plan_file_path, 'r', encoding='utf-8') as f:
                    plan_data = json.load(f)
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON format in {plan_file_path}")
        
        current_plan = plan_data.get("plan", []) if plan_data else []
        
        # If execution phase, update last entry instead of creating new
        if is_execute_phase and execute_data:
            last_entry = execute_data[-1]
            last_execute_status = last_entry.get('execute', {}).get('status')
            
            # Only update entries with pending or running status
            if last_execute_status in ['pending', 'running']:
                execute_data[-1]['execute']['status'] = 'running'
                execute_data[-1]['execute']['started_at'] = datetime.now().isoformat()
                # Update plan (if new plan data)
                if current_plan:
                    execute_data[-1]['plan'] = {"plan": current_plan}
                
                # Save updated history
                with open(execute_json_path, 'w', encoding='utf-8') as f:
                    json.dump(execute_data, f, ensure_ascii=False, indent=4)
                    
                logger.info(f"Updated execute status for session {formatted_id}")
                return True
        
        # Check if new entry needed
        should_create_new = True
        
        if execute_data:
            last_entry = execute_data[-1]
            last_execute_status = last_entry.get('execute', {}).get('status')
            last_plan = last_entry.get('plan', {}).get('plan', [])
            last_asking = last_entry.get('asking', '')
            
            # If last entry is running, don't create new, just update
            if last_execute_status == 'running':
                # Update existing entry
                if not last_asking or last_asking in ['Task started', 'Execute task started', 'Execute task in progress']:
                    execute_data[-1]['asking'] = message
                if current_plan:
                    execute_data[-1]['plan'] = {"plan": current_plan}
                execute_data[-1]['execute']['started_at'] = datetime.now().isoformat()
                should_create_new = False
            # If last entry is pending and plan is empty, update it
            elif last_execute_status == 'pending' and not last_plan:
                execute_data[-1]['asking'] = message
                if current_plan:
                    execute_data[-1]['plan'] = {"plan": current_plan}
                execute_data[-1]['execute']['status'] = 'running'
                execute_data[-1]['execute']['started_at'] = datetime.now().isoformat()
                should_create_new = False
        
        # Create new entry
        if should_create_new:
            new_entry = {
                "asking": message,
                "plan": {"plan": current_plan},
                "execute": {
                    "steps": [],
                    "status": "running",
                    "started_at": datetime.now().isoformat()
                }
            }
            execute_data.append(new_entry)
        
        # Save updated history
        with open(execute_json_path, 'w', encoding='utf-8') as f:
            json.dump(execute_data, f, ensure_ascii=False, indent=4)
            
        logger.info(f"Created/updated history entry for session {formatted_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error creating initial history entry for session {session_id}: {e}")
        return False

def update_history_with_result(session_id, result_data):
    """
    Update history with result after task completes
    """
    try:
        if isinstance(session_id, str):
            numeric_id = int(session_id.lstrip('0') or '0')
        else:
            numeric_id = int(session_id)
        formatted_id = f"{numeric_id:03d}"
        
        history_dir = os.path.join(os.getcwd(), 'history', formatted_id)
        execute_json_path = os.path.join(history_dir, 'execute.json')
        
        if not os.path.exists(execute_json_path):
            logger.error(f"History file not found for session {formatted_id}")
            return False
        
        # Read existing history
        with open(execute_json_path, 'r', encoding='utf-8') as f:
            execute_data = json.load(f)
        
        # Update last entry result
        if execute_data:
            last_entry = execute_data[-1]
            
            # Check current entry status, only update running entries
            if last_entry.get('execute', {}).get('status') == 'running':
                last_entry['execute']['status'] = 'completed'
                last_entry['execute']['completed_at'] = datetime.now().isoformat()
                
                # If result data exists, add to history
                if result_data:
                    last_entry['result'] = result_data
            else:
                # If last entry not running, log warning
                logger.warning(f"Attempted to update non-running entry for session {formatted_id}")
        else:
            logger.warning(f"No history entries found for session {formatted_id}")
        
        # Save updated history
        with open(execute_json_path, 'w', encoding='utf-8') as f:
            json.dump(execute_data, f, ensure_ascii=False, indent=4)
            
        logger.info(f"Updated history with result for session {formatted_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error updating history with result for session {session_id}: {e}")
        return False


def cleanup_stale_processing_status():
    """
    Clean up processing status left after server restart
    Update all processing status to interrupted
    """
    try:
        history_base_dir = os.path.join(os.getcwd(), 'history')
        if not os.path.exists(history_base_dir):
            return True
            
        cleanup_count = 0
        
        for session_dir in os.listdir(history_base_dir):
            session_path = os.path.join(history_base_dir, session_dir)
            if not os.path.isdir(session_path):
                continue
                
            # Clean up processing status in chat.json
            chat_file = os.path.join(session_path, 'chat.json')
            if os.path.exists(chat_file):
                try:
                    with open(chat_file, 'r', encoding='utf-8') as f:
                        chat_data = json.load(f)
                    
                    updated = False
                    for entry in chat_data:
                        if entry.get('status') == 'processing':
                            entry['status'] = 'interrupted'
                            entry['response'] = entry.get('response') or "Request was interrupted"
                            entry['timestamp'] = datetime.now().isoformat()
                            updated = True
                            cleanup_count += 1
                    
                    if updated:
                        with open(chat_file, 'w', encoding='utf-8') as f:
                            json.dump(chat_data, f, ensure_ascii=False, indent=4)
                except Exception as e:
                    logger.error(f"Error cleaning up chat for {session_dir}: {e}")
            
            # Clean up processing status in analysis.json
            analysis_file = os.path.join(session_path, 'analysis.json')
            if os.path.exists(analysis_file):
                try:
                    with open(analysis_file, 'r', encoding='utf-8') as f:
                        analysis_data = json.load(f)
                    
                    updated = False
                    for entry in analysis_data:
                        if entry.get('status') == 'processing':
                            entry['status'] = 'interrupted'
                            entry['response'] = entry.get('response') or "Request was interrupted"
                            entry['timestamp'] = datetime.now().isoformat()
                            updated = True
                            cleanup_count += 1
                    
                    if updated:
                        with open(analysis_file, 'w', encoding='utf-8') as f:
                            json.dump(analysis_data, f, ensure_ascii=False, indent=4)
                except Exception as e:
                    logger.error(f"Error cleaning up analysis for {session_dir}: {e}")
            
            # Clean up running status in execute.json (if no actual running task)
            execute_file = os.path.join(session_path, 'execute.json')
            if os.path.exists(execute_file):
                try:
                    with open(execute_file, 'r', encoding='utf-8') as f:
                        execute_data = json.load(f)
                    
                    updated = False
                    for entry in execute_data:
                        execute_status = entry.get('execute', {}).get('status')
                        if execute_status == 'running':
                            entry['execute']['status'] = 'interrupted'
                            entry['execute']['completed_at'] = datetime.now().isoformat()
                            updated = True
                            cleanup_count += 1
                    
                    if updated:
                        with open(execute_file, 'w', encoding='utf-8') as f:
                            json.dump(execute_data, f, ensure_ascii=False, indent=4)
                except Exception as e:
                    logger.error(f"Error cleaning up execute for {session_dir}: {e}")
        
        logger.info(f"Cleaned up {cleanup_count} stale processing entries")
        return True
        
    except Exception as e:
        logger.error(f"Error in cleanup_stale_processing_status: {e}")
        return False
