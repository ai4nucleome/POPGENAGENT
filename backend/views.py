import os
import json
import mimetypes
import asyncio
import sys
import re
import time
import signal
import atexit
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from django.http import JsonResponse, FileResponse, Http404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST
from django.shortcuts import render, get_object_or_404
from django.conf import settings
from django.db import transaction
from asgiref.sync import sync_to_async

import requests
import gdown

# Import Agent classes
from core.GenAgent import GenAgent
from core.ChatAgent import ChatAgent
from core.AnaAgent import AnaAgent
from core.task_manager import TaskManager

# Move Google API related functionality into try-except block
GOOGLE_API_ENABLED = False
try:
    from googleapiclient.discovery import build
    from google.oauth2 import service_account
    GOOGLE_API_ENABLED = True
except ImportError:
    print("Google API libraries not available. Google Drive features will be disabled.")

from .utils import (
    ensure_directories,
    get_session_content_index,
    scan_and_store_files,
    scan_and_sync_sessions,
    create_session,
    get_all_sessions,
    get_session_by_id,
    delete_session_and_files,
    logger,
    save_sessions,
    update_history_execute_json,
    update_session,
    load_sessions,
    update_execute_agent_status,
    update_execute_agent_status_and_attempt,
    update_file_description,
    update_file_description_for_session,
    create_step_files,
    update_execute_agent_stage,
    cleanup_stale_sessions,
    monitor_session_health,
    create_initial_history_entry,
    update_history_with_result,
)
from .utils import load_file_info, save_file_info, update_file_description

import sys as _sys
_sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config_loader import get_llm_config as _get_llm_config
_llm_cfg = _get_llm_config()
GLOBAL_API_KEY = _llm_cfg.get("api_key", "")
GLOBAL_BASE_URL = _llm_cfg.get("base_url", "")

GLOBAL_EXECUTOR = True
task_manager = TaskManager()

# Import and start timeout monitor
from .timeout_monitor import TimeoutMonitor
timeout_monitor = TimeoutMonitor(task_manager, check_interval=60)  # Check every 60 seconds
timeout_monitor.start_monitoring()

# Import API key pool manager
from .api_pool import api_key_pool

FILE_INFO_PATH = os.path.join(os.getcwd(), 'knowledge', 'file_info.json')
SESSION_STATUS_PATH = os.path.join(os.getcwd(), 'knowledge', 'session_status.json')

# Note: Imports below already done at top of file, duplicate imports removed

@csrf_exempt
@require_POST
def delete_session_files_view(request, session_id):
    """
    Remove session with ID session_id from session_status.json,
    and delete corresponding plan, step, debug files and subfolders under ./output/.
    curl example:
    curl -X POST http://localhost:8000/api/sessions/5/delete_all/
    """
    try:
        session_id = int(session_id)
    except ValueError:
        return JsonResponse({'status': 'error', 'message': 'Invalid session ID'}, status=400)

    success = delete_session_and_files(session_id)
    if success:
        return JsonResponse({
            'status': 'success',
            'message': f'Session {session_id} and related files deleted successfully.'
        }, status=200)
    else:
        return JsonResponse({
            'status': 'error',
            'message': f'Session ID={session_id} not found.'
        }, status=404)


@csrf_exempt
@require_GET
def get_session_analysis_history(request, session_id):
    """
    API: Get analysis conversation records for a session (Markdown format), returns format:
    [
        {
            "asking": "original text 1",
            "response": "markdown text 1"
        },
        {
            "asking": "original text 2",
            "response": "markdown text 2"
        }
    ]
    """
    # Format session_id as 001, 002, etc.
    formatted_id = f"{session_id:03d}"
    history_dir = os.path.join('./history', formatted_id)
    analysis_file_path = os.path.join(history_dir, 'analysis.json')

    if not os.path.exists(analysis_file_path):
        return JsonResponse({
            'status': 'error',
            'message': f'Analysis file not found for session {formatted_id}'
        }, status=404)

    try:
        with open(analysis_file_path, 'r', encoding='utf-8') as f:
            analysis_data = json.load(f)
    except json.JSONDecodeError as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Invalid JSON format in analysis file: {e}'
        }, status=500)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    # Check if non-empty list
    if not isinstance(analysis_data, list) or not analysis_data:
        return JsonResponse({
            'status': 'error',
            'message': f'No analysis history found or invalid data format for session {formatted_id}'
        }, status=404)

    # Build new response, keep all fields including status for frontend state detection
    history_list = []
    for entry in analysis_data:
        asking = entry.get('asking', 'N/A')
        original_response = entry.get('response', 'N/A')
        status = entry.get('status', 'completed')  # Default to completed status
        timestamp = entry.get('timestamp', '')
        session_id = entry.get('session_id', formatted_id)

        # If processing status and response empty, keep as-is for frontend detection
        if status == 'processing' and not original_response:
            markdown_response = ""
        else:
            # Wrap original response in Markdown format
            markdown_response = f"**A:** {original_response}"

        history_list.append({
            "asking": asking,
            "response": markdown_response,
            "status": status,
            "timestamp": timestamp,
            "session_id": session_id
        })

    return JsonResponse({
        "status": "success",
        "history": history_list
    }, status=200)


# return JsonResponse({'status': 'success', 'history': chat_history}, status=200)


@csrf_exempt
@require_GET
def get_session_chat(request, session_id):
    """
    API: Get chat_agent info for a session
    GET /api/sessions/<int:session_id>/chat/

    Response example:
    {
        "status": "success",
        "chat_agent": {
            "status": "working"
        }
    }

    curl example:
    curl -X GET http://localhost:8000/api/sessions/1/chat/
    """
    try:
        session = get_session_by_id(session_id)
        if session:
            return JsonResponse({'status': 'success', 'chat_agent': session['chat_agent']}, status=200)
        else:
            return JsonResponse({'status': 'error', 'message': 'Session not found'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
@csrf_exempt
@require_GET
def get_session_execute(request, session_id):
    """
    API: Get execute_agent info for a session
    GET /api/sessions/<int:session_id>/execute/

    Response example:
    {
        "status": "success",
        "execute_agent": {
            "step_completion": "50%",
            "current_step": 2,
            "total_steps": 4,
            "is_execute": true,
            "status": "working",
            "current_step_status": 0,
            "bug": "",
            "output": ""
        }
    }

    curl example:
    curl -X GET http://localhost:8000/api/sessions/1/execute/
    """
    try:
        session = get_session_by_id(session_id)
        if session:
            return JsonResponse({'status': 'success', 'execute_agent': session['execute_agent']}, status=200)
        else:
            return JsonResponse({'status': 'error', 'message': 'Session not found'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
@csrf_exempt
@require_GET
def get_session_analysis(request, session_id):
    """
    API: Get analysis_agent info for a session
    GET /api/sessions/<int:session_id>/analysis/

    Response example:
    {
        "status": "success",
        "analysis_agent": {
            "status": "not working",
            "bug": ""
        }
    }

    curl example:
    curl -X GET http://localhost:8000/api/sessions/1/analysis/
    """
    try:
        session = get_session_by_id(session_id)
        if session:
            return JsonResponse({'status': 'success', 'analysis_agent': session['analysis_agent']}, status=200)
        else:
            return JsonResponse({'status': 'error', 'message': 'Session not found'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@csrf_exempt
@require_GET
def get_session_list(request):
    """
    API: Get list of all sessions
    GET /api/sessions/

    Response example:
    {
        "status": "success",
        "sessions": [
            {"id": 2, "title": "Population Study"},
            {"id": 1, "title": "Genome Analysis Session"}
        ]
    }

    curl example:
    curl -X GET http://localhost:8000/api/sessions/
    """
    try:
        sessions = get_all_sessions()  # Call utils function to get all sessions
        session_list = [{"id": session["id"], "title": session["title"]} for session in sessions]
        
        # Sort by session["id"] descending
        session_list = sorted(session_list, key=lambda x: x["id"], reverse=True)
        
        return JsonResponse({'status': 'success', 'sessions': session_list}, status=200)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@csrf_exempt
@require_POST
def update_session_title_view(request, session_id):
    """
    API: Update title of a session
    POST /api/sessions/<int:session_id>/update_title/
    Request example:
    {
        "title": "New Session Title"
    }

    Response example:
    {
      "status": "success",
      "message": "Session title updated successfully"
    }

    curl example:
    curl -X POST http://localhost:8000/api/sessions/1/update_title/ \
    -H "Content-Type: application/json" \
    -d '{"title": "Genome Analysis Session Updated"}'
    """
    try:
        session_id = int(session_id)
    except ValueError:
        return JsonResponse({'status': 'error', 'message': 'Invalid session ID'}, status=400)

    data = json.loads(request.body)
    new_title = data.get('title')
    if not new_title:
        return JsonResponse({'status': 'error', 'message': 'Title is required'}, status=400)

    sessions = load_sessions()
    updated = False
    for session in sessions:
        if session.get('id') == session_id:
            session['title'] = new_title
            updated = True
            break

    if not updated:
        return JsonResponse({'status': 'error', 'message': 'Session not found'}, status=404)

    save_sessions(sessions)
    return JsonResponse({'status': 'success', 'message': 'Session title updated successfully'}, status=200)

@csrf_exempt
def get_chat_history(request, session_id):
    """
    API: Get chat history for specified ID
    """
    # Define history path
        # formatted_id = f"{session_id:03d}"
    # history_dir = os.path.join('./history', formatted_id)
    # analysis_file_path = os.path.join(history_dir, 'analysis.json')
    session_id = f"{session_id:03d}"
    history_dir = os.path.join('./history', session_id)
    chat_file_path = os.path.join(history_dir, 'chat.json')

    try:
        # If file does not exist, return empty history
        if not os.path.exists(chat_file_path):
            return JsonResponse({'status': 'success', 'history': []}, status=200)

        # If file exists, read chat.json
        with open(chat_file_path, 'r', encoding='utf-8') as file:
            chat_history = json.load(file)

        # Return JSON response
        return JsonResponse({'status': 'success', 'history': chat_history}, status=200)

    except Exception as e:
        # Handle other exceptions
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@csrf_exempt
@require_POST
def update_file_description_view(request):
    """
    Update description of specified file
    POST /api/files/update_description/
    Request example:
    {
        "id": 2,
        "filename": "1000GP_pruned.bim",
        "description": "File description"
    }

    curl example:
    curl -X POST http://localhost:8000/api/files/update_description/ \
    -H "Content-Type: application/json" \
    -d '{"id": 2, "filename": "1000GP_pruned.bim", "description": "New description"}'
    """
    try:
        data = json.loads(request.body)
        session_id = data.get('id')
        filename = data.get('filename')
        description = data.get('description', '')

        if not session_id:
            return JsonResponse({'status': 'error', 'message': 'Session ID is missing'}, status=400)
        if not filename:
            return JsonResponse({'status': 'error', 'message': 'Filename is missing'}, status=400)

        # Call update file description function
        success, message = update_file_description_for_session(session_id, filename, description)

        if success:
            return JsonResponse({'status': 'success', 'message': 'Description updated successfully'}, status=200)
        else:
            return JsonResponse({'status': 'error', 'message': message}, status=404)

    except json.JSONDecodeError as e:
        return JsonResponse({'status': 'error', 'message': f'Invalid JSON format: {e}'}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)



@csrf_exempt
def save_file_content(request):
    data = json.loads(request.body)
    file_id = data.get('id')
    file_type = data.get('fileType')
    content = data.get('content')

    file_map = {
        'tpl': 'simulation.tpl',
        'par': 'simulation.par',
        'est': 'simulation.est',
        'run_ana': 'run_ana.sh'
    }

    file_name = file_map.get(file_type)
    if not file_name:
        return JsonResponse({'status': 'error', 'message': 'Invalid file type'})

    file_path = os.path.join('output', file_id.zfill(3), file_name)

    try:
        with open(file_path, 'w') as file:
            file.write(content)
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})
    
@require_GET
def get_file_content(request):
    file_id = request.GET.get('id')
    file_names = {
        'tpl': 'simulation.tpl',
        'par': 'simulation.par',
        'est': 'simulation.est',
        'run_ana': 'run_ana.sh'
    }
    file_contents = {
        'tpl': '',
        'par': '',
        'est': '',
        'run_ana': ''
    }

    for key, file_name in file_names.items():
        file_path = os.path.join('output', file_id.zfill(3), file_name)
        try:
            with open(file_path, 'r') as file:
                file_contents[key] = file.read()
                print("____________________________________________")
                print(file_contents[key])
        except FileNotFoundError:
            file_contents[key] = f'{file_name} not found for ID {file_id}'
        except Exception as e:
            file_contents[key] = f'Error reading {file_name}: {str(e)}'

    return JsonResponse({'status': 'success', 'contents': file_contents})

def index(request):
    base_dir = os.path.dirname(settings.BASE_DIR)
    plan_file_path = os.path.join(base_dir, 'output', '001_PLAN.json')  # Default value '001'

    if os.path.exists(plan_file_path):
        with open(plan_file_path, 'r', encoding='utf-8') as file:
            plan_data = json.load(file)
    else:
        plan_data = {}

    context = {
        'plan': plan_data
    }
    return render(request, 'main/index.html', context)


# Use service account for authentication, ensure your service account JSON file path is in a secure location
SERVICE_ACCOUNT_FILE = './service_account.json'
SCOPES = ['https://www.googleapis.com/auth/drive']

# Function: Get original name of Google Drive file
def get_file_name(file_id):
    """Get the original name of a Google Drive file"""
    if not GOOGLE_API_ENABLED:
        return f"downloaded_file_{file_id}"
        
    try:
        credentials = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        service = build('drive', 'v3', credentials=credentials)
        file = service.files().get(fileId=file_id, fields='name').execute()
        return file.get('name')
    except Exception as e:
        logger.error(f"Error getting file name from Google Drive: {str(e)}")
        return f"downloaded_file_{file_id}"

# main/views.py

@csrf_exempt
@require_GET
def get_file_info(request):
    """
    API: Get filename and description for all files
    """
    file_info = load_file_info()
    return JsonResponse({'status': 'success', 'files': file_info}, status=200)

# main/views.py

@csrf_exempt
@require_POST
def update_file_description(request):
    """
    API: Update description of specified file
    Request example:
    {
        "filename": "example1.txt",
        "description": "File description"
    }
    """
    try:
        data = json.loads(request.body)
        filename = data.get('filename')
        description = data.get('description', '')

        if not filename:
            return JsonResponse({'status': 'error', 'message': 'Filename is missing'}, status=400)

        file_info = load_file_info()
        updated = False
        for item in file_info:
            if item['filename'] == filename:
                item['description'] = description
                updated = True
                break

        if not updated:
            return JsonResponse({'status': 'error', 'message': 'File not found'}, status=404)

        save_file_info(file_info)
        return JsonResponse({'status': 'success', 'message': 'Description updated successfully'}, status=200)

    except json.JSONDecodeError as e:
        return JsonResponse({'status': 'error', 'message': f'Invalid JSON format: {e}'}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@csrf_exempt
@require_POST
def create_new_session(request):
    """
    Create a new session
    POST /api/sessions/create/
    Request example:
    {
        "title": "Session Title"
    }

    Response example:
    {
      "status": "success",
      "session": { ...session data... }
    }

    curl example:
    curl -X POST http://localhost:8000/api/sessions/create/ \
    -H "Content-Type: application/json" \
    -d '{"title": "My New Session"}'
    """
    try:
        data = json.loads(request.body)
        title = data.get('title', 'Untitled Session')

        new_session = create_session(title)

        return JsonResponse({'status': 'success', 'session': new_session}, status=201)

    except json.JSONDecodeError as e:
        return JsonResponse({'status': 'error', 'message': f'Invalid JSON format: {e}'}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@require_GET
def get_all_sessions_view(request):
    """
    Get all sessions
    GET /api/sessions/

    Response example:
    {
      "status": "success",
      "sessions": [ ...all session data... ]
    }

    curl example:
    curl -X GET http://localhost:8000/api/sessions/
    """
    sessions = get_all_sessions()
    sessions.sort(key=lambda s: s['id'], reverse=True)
    return JsonResponse({'status': 'success', 'sessions': sessions}, status=200)

@require_GET
def get_session_view(request, session_id):
    """
    Get info for a specific session
    GET /api/sessions/<int:session_id>/

    Response example:
    {
      "status": "success",
      "session": { ...session data... }
    }

    curl example:
    curl -X GET http://localhost:8000/api/sessions/1/
    """
    try:
        session_id = int(session_id)
    except ValueError:
        return JsonResponse({'status': 'error', 'message': 'Invalid session ID'}, status=400)

    session = get_session_by_id(session_id)
    if session:
        return JsonResponse({'status': 'success', 'session': session}, status=200)
    else:
        return JsonResponse({'status': 'error', 'message': 'Session not found'}, status=404)

@csrf_exempt
@require_POST
def update_session_status_view(request, session_id):
    """
    Update status of a specific session
    POST /api/sessions/<int:session_id>/update/
    Request example:
    {
        "agent": "execute_agent",
        "key": "status",
        "value": "working"
    }

    Response example:
    {
      "status": "success",
      "message": "Session updated successfully"
    }

    curl example:
    curl -X POST http://localhost:8000/api/sessions/1/update/ \
    -H "Content-Type: application/json" \
    -d '{"agent": "execute_agent", "key": "status", "value": "working"}'
    """
    try:
        session_id = int(session_id)
    except ValueError:
        return JsonResponse({'status': 'error', 'message': 'Invalid session ID'}, status=400)

    data = json.loads(request.body)
    agent = data.get('agent')
    key = data.get('key')
    value = data.get('value')

    if not agent or not key:
        return JsonResponse({'status': 'error', 'message': 'Agent and key are required'}, status=400)

    success = update_session(session_id, agent, key, value)
    if success:
        return JsonResponse({'status': 'success', 'message': 'Session updated successfully'}, status=200)
    else:
        return JsonResponse({'status': 'error', 'message': 'Failed to update session'}, status=400)
    
    
@csrf_exempt
@require_POST
def execute_step(request, step_id, step_number):
    """
    Execute a step for a specific id and update corresponding plan.json and session_status.json.
    
    POST /api/execute_step/<str:step_id>/<int:step_number>/
    Request example:
    {
        "shell_commands": [
            "conda install -y plink",
            "mkdir -p ./output/001/",
            "plink --bfile ./data/1000GP_pruned --geno 0.05 --mind 0.05 --maf 0.05 --recode vcf --out ./output/001/filtered"
        ]
    }

    Response example:
    {
      "status": "success",
      "message": "Step 1 executed successfully",
      "output": "Shell script output..."
    }

    curl example:
    curl -X POST http://localhost:8000/api/execute_step/001/1/ \
    -H "Content-Type: application/json" \
    -d '{"shell_commands": ["conda install -y plink", "mkdir -p ./output/001/", "plink ..."]}'
    """
    try:
        data = json.loads(request.body)
        shell_commands = data.get('shell_commands', [])

        if not shell_commands:
            return JsonResponse({'status': 'error', 'message': 'No shell commands provided'}, status=400)

        # Initialize GenAgent instance
        agent = GenAgent(
            api_key=os.environ.get('OPENAI_API_KEY', ''),
            base_url=settings.BASE_URL,  # Ensure BASE_URL is defined in settings.py
            id=step_id
        )

        # Update or add step to plan.json
        plan_file_path = os.path.join(settings.OUTPUT_DIR, f"{step_id}_PLAN.json")
        if os.path.exists(plan_file_path):
            with open(plan_file_path, 'r', encoding='utf-8') as f:
                plan_data = json.load(f)
        else:
            plan_data = {
                "id": step_id,
                "plan": []
            }

        # Check if step already exists
        step_found = False
        for step in plan_data['plan']:
            if step['step_number'] == step_number:
                step['description'] = "\n".join(shell_commands)
                step_found = True
                break

        # If step does not exist, add new step
        if not step_found:
            plan_data['plan'].append({
                "step_number": step_number,
                "description": "\n".join(shell_commands)
            })

        # Save updated plan.json
        with open(plan_file_path, 'w', encoding='utf-8') as f:
            json.dump(plan_data, f, indent=4)

        # Generate Shell script
        shell_script_path = agent.shell_writing(shell_commands, step_number)

        # Execute Shell script
        result = subprocess.run(["bash", shell_script_path], capture_output=True, text=True)

        # Process execution result
        if result.returncode == 0:
            status = 'success'
            message = f'Step {step_number} executed successfully.'
            output = result.stdout
        else:
            status = 'failed'
            message = f'Step {step_number} failed to execute.'
            output = result.stderr

        # Update session_status.json
        session_status_path = os.path.join(settings.DOC_DIR, "session_status.json")
        if os.path.exists(session_status_path):
            with open(session_status_path, 'r', encoding='utf-8') as f:
                session_status = json.load(f)
        else:
            session_status = {}

        # Update status for specific id and step
        if step_id not in session_status:
            session_status[step_id] = {}

        session_status[step_id][str(step_number)] = {
            "status": status,
            "message": message,
            "output": output
        }

        # Save updated session_status.json
        with open(session_status_path, 'w', encoding='utf-8') as f:
            json.dump(session_status, f, indent=4)

        return JsonResponse({'status': status, 'message': message, 'output': output})

    except json.JSONDecodeError as e:
        return JsonResponse({'status': 'error', 'message': f'Invalid JSON format: {e}'}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

def create_shell_script(output_dir, session_id, step_number, shell_commands):
    """
    Generate .sh script file from provided shell commands.

    :param output_dir: Output directory
    :param session_id: Session ID
    :param step_number: Step number
    :param shell_commands: List of shell commands
    :return: Path to the script file
    """
    shell_script_filename = f"{session_id}_Step_{step_number}.sh"
    shell_script_path = os.path.join(output_dir, shell_script_filename)

    code_prefix = [
        '#!/bin/bash',
        'set -e'  # If any command fails, script exits immediately
    ]

    with open(shell_script_path, "w", encoding="utf-8") as file:
        # Write prefix commands
        for command in code_prefix:
            file.write(command + "\n")

        # Write actual shell commands
        for command in shell_commands:
            file.write(f"{command}\n")

    # Ensure script has executable permission
    os.chmod(shell_script_path, 0o755)

    return shell_script_path
    
@require_GET
def get_file_info_view(request):
    """
    Get filename and description for all files
    GET /api/files/
    
    Response example:
    {
      "status": "success",
      "files": [ ...file info... ]
    }

    curl example:
    curl -X GET http://localhost:8000/api/files/
    """
    file_info_data = get_file_info()
    return JsonResponse({'status': 'success', 'files': file_info_data}, status=200)

def total_steps(session):
    """
    Get total step count for session.
    """
    # Implement based on actual needs, e.g. read step count from PLAN file
    formatted_id = f"{session['id']:03d}"
    plan_file_path = os.path.join(os.getcwd(), 'output', formatted_id, f"{formatted_id}_PLAN.json")
    if os.path.exists(plan_file_path):
        with open(plan_file_path, 'r', encoding='utf-8') as f:
            plan = json.load(f)
            return len(plan.get('shell', []))
    return 0
@csrf_exempt
async def upload_file(request):
    DATA_PATH = os.path.join(os.getcwd(), 'data')  # Ensure this path points to your data directory
    if request.method == 'POST':
        data = json.loads(request.body)
        google_drive_link = data.get('link', '')

        if not re.match(r'^https://drive\.google\.com/', google_drive_link):
            return JsonResponse({'status': 'error', 'message': 'Invalid Google Drive link'}, status=400)

        try:
            file_id_match = re.search(r'/d/([a-zA-Z0-9_-]+)', google_drive_link)
            if not file_id_match:
                return JsonResponse({'status': 'error', 'message': 'Could not parse Google Drive file ID'}, status=400)

            file_id = file_id_match.group(1)
            download_url = f'https://drive.google.com/uc?id={file_id}'

            # Get filename (simplified, does not depend on Google API)
            file_name = f"downloaded_file_{file_id}"
            if GOOGLE_API_ENABLED:
                try:
                    file_name = get_file_name(file_id) or file_name
                except Exception as e:
                    logger.warning(f"Failed to get file name from Google API: {e}")

            output_file = os.path.join(DATA_PATH, file_name)
            
            # Use gdown to download file
            try:
                gdown.download(download_url, output_file, quiet=False)
            except Exception as e:
                return JsonResponse({
                    'status': 'error',
                    'message': f'Download failed: {str(e)}'
                }, status=500)

            # Run scan function to update file table
            scan_and_store_files()

            return JsonResponse({
                'status': 'success',
                'message': 'Download complete',
                'file_path': output_file
            })

        except requests.exceptions.RequestException as e:
            return JsonResponse({
                'status': 'error',
                'message': f'Download interrupted: {str(e)}'
            }, status=500)
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': f'Unexpected error: {str(e)}'
            }, status=500)

    else:
        return JsonResponse({
            'status': 'error',
            'message': 'Invalid request method'
        }, status=405)
    
@csrf_exempt
async def upload_file_from_google_drive(request):
    if request.method == 'POST':
        # Implement logic
        data = json.loads(request.body)
        google_drive_link = data.get('link', '')

        # Validate link and handle download logic
        if not re.match(r'^https://drive\.google\.com/', google_drive_link):
            return JsonResponse({'status': 'error', 'message': 'Invalid Google Drive link'}, status=400)

        # Assume download started
        return JsonResponse({'status': 'info', 'message': 'Starting download...'})
    else:
        return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=405)
    
@csrf_exempt
def delete_plan_and_steps(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            id = data.get('id')
            if not id:
                return JsonResponse({'status': 'error', 'message': 'ID is missing'}, status=400)

            base_dir = settings.BASE_DIR
            plan_file_path = os.path.join(base_dir, 'output', f'{id}_PLAN.json')
            steps_dir = os.path.join(base_dir, 'output')
            steps_files = [f for f in os.listdir(steps_dir) if f.startswith(f'{id}_Step_') and f.endswith('.sh')]

            # Delete plan file
            if os.path.exists(plan_file_path):
                os.remove(plan_file_path)
            
            # Delete all step files
            for step_file in steps_files:
                step_file_path = os.path.join(steps_dir, step_file)
                if os.path.exists(step_file_path):
                    os.remove(step_file_path)

            return JsonResponse({'status': 'success', 'message': f'Plan and steps for ID {id} deleted successfully'})

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    else:
        return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=405)

def get_plan_data(request):
    id = request.GET.get('id', '001')  # Get URL param 'id', default '001' if not provided
    base_dir = settings.BASE_DIR
    plan_file_path = os.path.join(base_dir, 'output', f'{id}_PLAN.json')

    if os.path.exists(plan_file_path):
        with open(plan_file_path, 'r', encoding='utf-8') as file:
            plan_data = json.load(file)
    else:
        plan_data = {}

    return JsonResponse(plan_data)


def get_step_data(request):
    id = request.GET.get('id', '001')  # Get URL param 'id', default '001' if not provided
    base_dir = settings.BASE_DIR
    steps_dir = os.path.join(base_dir, 'output')
    steps_files = [f for f in os.listdir(steps_dir) if f.startswith(f'{id}_Step_') and f.endswith('.sh')]

    # Sort by numeric part in filename
    steps_files.sort(key=lambda x: int(re.search(r'Step_(\d+)', x).group(1)))

    steps_data = []
    for step_file in steps_files:
        step_file_path = os.path.join(steps_dir, step_file)
        if os.path.exists(step_file_path):
            with open(step_file_path, 'r', encoding='utf-8') as file:
                step_data = file.read()
                steps_data.append(step_data)

    return JsonResponse({'steps': steps_data})


def get_all_ids(request):
    """Iterate over all files in output folder, extract ID before filename and return array of unique IDs"""
    base_dir = settings.BASE_DIR
    output_dir = os.path.join(base_dir, 'output')
    
    ids = set()  # Use set to store unique IDs
    if os.path.exists(output_dir):
        for file_name in os.listdir(output_dir):
            match = re.match(r'^(\d{3})_', file_name)  # Match first 3 digits of filename as ID
            if match:
                ids.add(match.group(1))  # Extract ID and add to set
    
    # Return ID list sorted in descending order
    return JsonResponse({'ids': sorted(list(ids), reverse=True)})  # Reverse sort


@csrf_exempt
def create_new_plan(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            new_id = data.get('id')

            if not new_id:
                return JsonResponse({'status': 'error', 'message': 'ID is missing'}, status=400)

            # Create path for plan.json
            plan_dir = os.path.join(settings.BASE_DIR, 'output')
            if not os.path.exists(plan_dir):
                os.makedirs(plan_dir)
            plan_file_path = os.path.join(plan_dir, f'{new_id}_PLAN.json')

            # Create blank plan.json file
            with open(plan_file_path, 'w') as file:
                json.dump({"plan": []}, file)  # Create blank JSON structure

            return JsonResponse({'status': 'success', 'message': f'Plan {new_id}_PLAN.json created successfully'})

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    else:
        return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=405)


def get_initial_settings(request):
    global GLOBAL_API_KEY, GLOBAL_BASE_URL, GLOBAL_EXECUTOR

    # Get settings from global variables or environment
    settings_data = {
        'api_key': GLOBAL_API_KEY,
        'base_url': GLOBAL_BASE_URL,
        'executor': GLOBAL_EXECUTOR
    }

    return JsonResponse(settings_data)


def execute_task_async(task_id, datalist, manager):
    """Execute task in background thread"""
    if not manager:
        logger.error(f"No GenAgent instance found for ID {task_id}")
        update_execute_agent_status_and_attempt(task_id, 2, 0)
        return {"status": "error", "message": "Agent not found"}
    
    heartbeat_stop_event = threading.Event()
    
    try:
        logger.info(f"Starting execution for task {task_id}")
        update_execute_agent_status_and_attempt(task_id, 1, 0)  # thinking status
        
        # Periodically update heartbeat, use Event to control stop
        def heartbeat_updater():
            while not heartbeat_stop_event.is_set() and not manager.is_stopped():
                task_manager.update_heartbeat(task_id)
                # Use wait instead of sleep for faster response to stop request
                heartbeat_stop_event.wait(timeout=15)  # Update heartbeat every 15 seconds
        
        # Start heartbeat thread
        heartbeat_thread = threading.Thread(target=heartbeat_updater, daemon=True)
        heartbeat_thread.start()
        
        # Execute task
        result = manager.execute_TASK(datalist)
        
        # Stop heartbeat thread
        heartbeat_stop_event.set()
        
        logger.info(f"Task {task_id} execution completed with result: {result}")
        
        # Execution success, set to idle status
        update_execute_agent_status_and_attempt(task_id, 0, 0)
        
        # Release API key
        try:
            api_key_pool.release_api_key(task_id)
        except Exception as e:
            logger.warning(f"Error releasing API key for task {task_id}: {e}")
        
        # Clean up completed tasks
        task_manager.cleanup_finished_tasks()
        
        return {"status": "success", "results": result}
        
    except Exception as e:
        # Stop heartbeat thread
        heartbeat_stop_event.set()
        
        error_msg = str(e)
        is_user_stop = "stopped by user" in error_msg.lower() or manager.is_stopped()
        
        if is_user_stop:
            logger.info(f"Task {task_id} was stopped by user request")
            update_execute_agent_stage(task_id, "PAUSED")
            update_execute_agent_status_and_attempt(task_id, 0, 0)  # idle status
            return {"status": "stopped", "message": "Task stopped by user"}
        else:
            logger.error(f"Error during task execution for ID {task_id}: {error_msg}")
            update_execute_agent_status_and_attempt(task_id, 2, 0)  # error status
            return {"status": "error", "message": error_msg}
        
    finally:
        # Ensure heartbeat thread stops
        heartbeat_stop_event.set()
        
        # Release API key
        try:
            api_key_pool.release_api_key(task_id)
        except:
            pass
            
        # Try to clean up task
        try:
            task_manager.cleanup_finished_tasks()
        except:
            pass


# Create thread pool executor for background task execution
executor = ThreadPoolExecutor(max_workers=5)

@csrf_exempt
async def execute_plan(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            id = data.get('id', '001')
            datalist = data.get('datalist', [])
            
            # Assign API key to task
            api_key, base_url = api_key_pool.allocate_api_key(id)
            print(f"Allocated API key for task {id}: {base_url}")
            
            # Check if task with same ID already running
            current_status = task_manager.get_task_status(id)
            if current_status == 'running':
                return JsonResponse({
                    'status': 'error',
                    'message': f'Task with ID {id} is already running'
                }, status=409)
            
            # Immediately update status to EXECUTE and thinking so frontend sees change
            update_execute_agent_stage(id, "EXECUTE")
            update_execute_agent_status_and_attempt(id, 1, 0)  # Set to thinking status immediately
            
            print(f"Starting task with ID: {id}")
            
            try:
                # Clean up any previously existing task
                task_manager.cleanup_finished_tasks()
                
                # Update history entry status to running (do not create new entry)
                create_initial_history_entry(id, "Execute task started", is_execute_phase=True)
                
                # Create GenAgent instance and store, using assigned API key
                manager = GenAgent(api_key, base_url, excutor=GLOBAL_EXECUTOR, tools_dir="./tools", id=id)
                print("Creating GenAgent instance...")
                
                # Store GenAgent instance in task manager
                with task_manager._lock:
                    task_manager.tasks[id] = {
                        'manager': manager,
                        'status': 'running',  # Set to running immediately
                        'created_at': time.time(),
                        'last_heartbeat': time.time(),
                        'retry_count': 0,
                        'last_retry_time': 0,
                        'is_stalled': False,
                        'original_datalist': datalist  # Save original data list for retry
                    }
                print("GenAgent stored in task_manager")
                
                # Run background task using async thread pool
                loop = asyncio.get_event_loop()
                future = loop.run_in_executor(executor, execute_task_async, id, datalist, manager)
                
                # Add completion callback
                def task_completed(future_result):
                    task_id = id  # Capture current id
                    try:
                        result = future_result.result()
                        logger.info(f"Task {task_id} completed with result status: {result.get('status')}")
                        
                        status = result.get('status', 'error')
                        
                        if status == 'success':
                            update_execute_agent_status_and_attempt(task_id, 0, 0)  # idle status
                            update_history_with_result(task_id, result.get('results'))
                        elif status == 'stopped':
                            # User-initiated stop, not an error
                            logger.info(f"Task {task_id} was stopped by user")
                            update_execute_agent_stage(task_id, "PAUSED")
                            update_execute_agent_status_and_attempt(task_id, 0, 0)
                        else:
                            update_execute_agent_status_and_attempt(task_id, 2, 0)  # error status
                            update_history_with_result(task_id, {'error': result.get('message', 'Unknown error')})
                            
                    except Exception as e:
                        error_msg = str(e)
                        # Check if exception was caused by user stop
                        if 'stopped by user' in error_msg.lower() or 'cancelled' in error_msg.lower():
                            logger.info(f"Task {task_id} stopped by user")
                            update_execute_agent_stage(task_id, "PAUSED")
                            update_execute_agent_status_and_attempt(task_id, 0, 0)
                        else:
                            logger.error(f"Task {task_id} failed with exception: {e}")
                            update_execute_agent_status_and_attempt(task_id, 4, 0)  # error-last status
                            update_history_with_result(task_id, {'error': error_msg})
                    finally:
                        # Release API key and clean up task regardless of result
                        try:
                            api_key_pool.release_api_key(task_id)
                            logger.info(f"Released API key for task {task_id}")
                        except Exception as e:
                            logger.warning(f"Error releasing API key for task {task_id}: {e}")
                        
                        # Remove completed task from task manager
                        try:
                            with task_manager._lock:
                                if task_id in task_manager.tasks:
                                    task_manager.tasks[task_id]['status'] = 'completed'
                            task_manager.cleanup_finished_tasks()
                        except Exception as e:
                            logger.warning(f"Error cleaning up task {task_id}: {e}")
                
                future.add_done_callback(task_completed)
                
                # Return response immediately, do not wait for task completion
                return JsonResponse({
                    "status": "success", 
                    "message": "Task is being processed asynchronously.",
                    "task_status": "thinking"  # Tell frontend current status
                })
                
            except Exception as e:
                print(f"Error creating task: {str(e)}")
                update_execute_agent_status_and_attempt(id, 2, 0)  # Set to error status
                return JsonResponse({
                    'status': 'error',
                    'message': f'Failed to create task: {str(e)}'
                }, status=500)
            
        except json.JSONDecodeError as e:
            print(f"Error parsing request data: {str(e)}")
            return JsonResponse({
                'status': 'error',
                'message': f'Invalid JSON data: {str(e)}'
            }, status=400)
    else:
        return JsonResponse({
            'status': 'error',
            'message': 'Invalid request method'
        }, status=405)


@csrf_exempt
def stop_plan(request):
    """
    Stop Execute Agent plan execution
    POST /stop_plan/
    """
    if request.method == 'POST':
        task_id = None
        try:
            data = json.loads(request.body)
            task_id = data.get('id', '001')
            force = data.get('force', False)  # Whether to force stop
            logger.info(f"Stop plan request received for Task ID: {task_id}, force: {force}")
            
            # Convert task_id to number (remove leading zeros)
            numeric_id = int(task_id.lstrip('0') or '0')
            
            # 1. First stop task in task manager
            task_manager.stop_task(task_id, force=force)
            
            # 2. Release API key
            try:
                api_key_pool.release_api_key(task_id)
            except Exception as e:
                logger.warning(f"Error releasing API key for task {task_id}: {e}")
            
            # 3. Update session status
            update_execute_agent_stage(numeric_id, "PAUSED")
            update_execute_agent_status_and_attempt(numeric_id, 0, 0)  # Set to idle status
            
            # 4. Update history
            try:
                formatted_id = str(task_id).zfill(3)
                history_dir = os.path.join('./history', formatted_id)
                execute_file = os.path.join(history_dir, 'execute.json')
                if os.path.exists(execute_file):
                    with open(execute_file, 'r', encoding='utf-8') as f:
                        execute_data = json.load(f)
                    if execute_data and isinstance(execute_data, list) and len(execute_data) > 0:
                        # Update status of last record
                        if 'execute' not in execute_data[-1]:
                            execute_data[-1]['execute'] = {}
                        execute_data[-1]['execute']['status'] = 'stopped_by_user'
                        execute_data[-1]['execute']['stopped_at'] = time.strftime('%Y-%m-%d %H:%M:%S')
                        with open(execute_file, 'w', encoding='utf-8') as f:
                            json.dump(execute_data, f, ensure_ascii=False, indent=4)
            except Exception as e:
                logger.warning(f"Error updating history for stopped task {task_id}: {e}")
            
            logger.info(f"Stop plan processed for Task ID: {task_id}")
            return JsonResponse({
                'status': 'success', 
                'message': f'Task {task_id} stopped successfully.',
                'task_id': task_id
            })
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in stop_plan request: {e}")
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON data'}, status=400)
        except Exception as e:
            logger.error(f"Error stopping task {task_id}: {str(e)}")
            # Try to update status even on error
            if task_id:
                try:
                    numeric_id = int(task_id.lstrip('0') or '0')
                    update_execute_agent_stage(numeric_id, "ERROR")
                    update_execute_agent_status_and_attempt(numeric_id, 2, 0)
                except:
                    pass
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    else:
        return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=405)


@csrf_exempt
def stop_task(request):
    """
    Stop Chat Agent or Analysis Agent task
    POST /stop_task/
    """
    if request.method == 'POST':
        task_id = None
        try:
            data = json.loads(request.body)
            task_id = data.get('id', '001')
            agent_type = data.get('agent_type', 'chat')  # 'chat' or 'analysis'
            force = data.get('force', False)
            
            logger.info(f"Stop task request received for Task ID: {task_id}, agent: {agent_type}")
            
            # 1. Stop task in task manager
            task_manager.stop_task(task_id, force=force)
            
            # 2. Also try to stop task of specific agent type
            if agent_type == 'chat':
                task_manager.stop_task(f"{task_id}_chat", force=force)
            elif agent_type == 'analysis':
                task_manager.stop_task(f"{task_id}_analysis", force=force)
            
            # 3. Release API key
            try:
                api_key_pool.release_api_key(task_id)
                api_key_pool.release_api_key(f"{task_id}_chat")
                api_key_pool.release_api_key(f"{task_id}_analysis")
            except Exception as e:
                logger.warning(f"Error releasing API keys: {e}")
            
            # 4. Update history status
            try:
                formatted_id = str(task_id).zfill(3)
                history_dir = os.path.join('./history', formatted_id)
                
                if agent_type == 'chat':
                    history_file = os.path.join(history_dir, 'chat.json')
                else:
                    history_file = os.path.join(history_dir, 'analysis.json')
                
                if os.path.exists(history_file):
                    with open(history_file, 'r', encoding='utf-8') as f:
                        history_data = json.load(f)
                    
                    # Update last record with processing status
                    if history_data and isinstance(history_data, list):
                        for entry in reversed(history_data):
                            if entry.get('status') == 'processing':
                                entry['status'] = 'interrupted'
                                entry['response'] = entry.get('response', '') or 'Request was interrupted by user'
                                break
                        
                        with open(history_file, 'w', encoding='utf-8') as f:
                            json.dump(history_data, f, ensure_ascii=False, indent=4)
            except Exception as e:
                logger.warning(f"Error updating history for stopped task: {e}")
            
            logger.info(f"Stop task processed for Task ID: {task_id}")
            return JsonResponse({
                'status': 'success', 
                'message': f'Task {task_id} stopped.',
                'task_id': task_id
            })
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in stop_task request: {e}")
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON data'}, status=400)
        except Exception as e:
            logger.error(f"Error stopping task: {str(e)}")
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    else:
        return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=405)


@csrf_exempt
@require_GET
def get_task_status(request):
    """
    Get status of all active tasks
    GET /api/tasks/status/
    """
    try:
        # First check timeout tasks
        check_result = task_manager.check_timeout_tasks()
        timeout_tasks = check_result.get('timeout_tasks', [])
        stalled_tasks = check_result.get('stalled_tasks', [])
        
        if timeout_tasks or stalled_tasks:
            print(f"Found {len(timeout_tasks)} timeout tasks and {len(stalled_tasks)} stalled tasks")
        
        active_tasks = task_manager.list_active_tasks()
        task_manager.cleanup_finished_tasks()  # Clean up completed tasks
        
        return JsonResponse({
            'status': 'success',
            'active_tasks': active_tasks,
            'total_active': len(active_tasks),
            'timeout_tasks_handled': timeout_tasks,
            'stalled_tasks_retried': stalled_tasks
        }, status=200)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@csrf_exempt
@require_GET
def check_timeout_tasks(request):
    """
    Manually check and handle timeout tasks
    GET /api/tasks/check_timeout/
    
    Response example:
    {
        "status": "success",
        "timeout_tasks": ["001", "002"],
        "message": "Found and handled 2 timeout tasks"
    }
    
    curl example:
    curl -X GET http://localhost:8000/api/tasks/check_timeout/
    """
    try:
        check_result = task_manager.check_timeout_tasks()
        timeout_tasks = check_result.get('timeout_tasks', [])
        stalled_tasks = check_result.get('stalled_tasks', [])
        
        return JsonResponse({
            'status': 'success',
            'timeout_tasks': timeout_tasks,
            'stalled_tasks': stalled_tasks,
            'total_timeout': len(timeout_tasks),
            'total_stalled': len(stalled_tasks),
            'message': f'Found and handled {len(timeout_tasks)} timeout tasks and {len(stalled_tasks)} stalled tasks for retry'
        }, status=200)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@csrf_exempt
@require_GET
def get_task_info(request, task_id):
    """
    Get detailed info for specific task, including timeout status
    GET /api/tasks/<str:task_id>/info/
    
    Response example:
    {
        "status": "success",
        "task_info": {
            "status": "running",
            "created_at": 1642671234.5,
            "last_heartbeat": 1642671240.1,
            "timeout_in": 285.2,
            "is_timeout": false
        }
    }
    
    curl example:
    curl -X GET http://localhost:8000/api/tasks/001/info/
    """
    try:
        task_info = task_manager.get_task_info(task_id)
        
        if task_info is None:
            return JsonResponse({
                'status': 'error',
                'message': f'Task {task_id} not found'
            }, status=404)
        
        return JsonResponse({
            'status': 'success',
            'task_info': task_info
        }, status=200)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@csrf_exempt
@require_POST
def force_reset_task(request, task_id):
    """
    Force reset task status (for swallowed tasks)
    POST /api/tasks/<str:task_id>/force_reset/
    
    Response example:
    {
        "status": "success",
        "message": "Task 001 forcefully reset to idle state"
    }
    
    curl example:
    curl -X POST http://localhost:8000/api/tasks/001/force_reset/
    """
    try:
        # Force stop task in task manager
        task_manager.stop_task(task_id)
        
        # Reset session status to idle
        numeric_id = int(task_id.lstrip('0') or '0')
        update_execute_agent_status_and_attempt(numeric_id, 0, 0)  # Set to idle status
        update_execute_agent_stage(numeric_id, "PLAN")  # Reset stage
        
        return JsonResponse({
            'status': 'success',
            'message': f'Task {task_id} forcefully reset to idle state'
        }, status=200)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@csrf_exempt
@require_GET
def timeout_monitor_status(request):
    """
    Get timeout monitor status
    GET /api/monitor/status/
    
    Response example:
    {
        "status": "success",
        "monitor_running": true,
        "check_interval": 60,
        "message": "Timeout monitor is running"
    }
    
    curl example:
    curl -X GET http://localhost:8000/api/monitor/status/
    """
    try:
        is_monitoring = timeout_monitor.is_monitoring()
        
        return JsonResponse({
            'status': 'success',
            'monitor_running': is_monitoring,
            'check_interval': timeout_monitor.check_interval,
            'message': 'Timeout monitor is running' if is_monitoring else 'Timeout monitor is not running'
        }, status=200)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@csrf_exempt
@require_POST
def restart_timeout_monitor(request):
    """
    Restart timeout monitor
    POST /api/monitor/restart/
    
    Response example:
    {
        "status": "success",
        "message": "Timeout monitor restarted successfully"
    }
    
    curl example:
    curl -X POST http://localhost:8000/api/monitor/restart/
    """
    try:
        # Stop existing monitor
        timeout_monitor.stop_monitoring()
        
        # Restart monitor
        timeout_monitor.start_monitoring()
        
        return JsonResponse({
            'status': 'success',
            'message': 'Timeout monitor restarted successfully'
        }, status=200)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@csrf_exempt
@require_GET
def get_api_pool_status(request):
    """
    Get API key pool status
    GET /api/pool/status/
    
    Response example:
    {
        "status": "success",
        "pool_status": {
            "pools": [
                {
                    "index": 0,
                    "name": "pool_1",
                    "base_url": "https://one-api.bltcy.top/v1",
                    "active_tasks": 2,
                    "max_concurrent": 3,
                    "utilization": "2/3",
                    "task_list": ["001", "002"]
                }
            ],
            "total_active_tasks": 5,
            "current_rotation_index": 1
        }
    }
    
    curl example:
    curl -X GET http://localhost:8000/api/pool/status/
    """
    try:
        pool_status = api_key_pool.get_pool_status()
        
        return JsonResponse({
            'status': 'success',
            'pool_status': pool_status
        }, status=200)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@csrf_exempt
@require_GET
def get_task_api_info(request, task_id):
    """
    Get API allocation info for specific task
    GET /api/tasks/<str:task_id>/api/
    
    Response example:
    {
        "status": "success",
        "api_info": {
            "allocated": true,
            "pool_index": 0,
            "pool_name": "pool_1",
            "base_url": "https://one-api.bltcy.top/v1",
            "pool_utilization": "2/3"
        }
    }
    
    curl example:
    curl -X GET http://localhost:8000/api/tasks/001/api/
    """
    try:
        api_info = api_key_pool.get_task_api_info(task_id)
        
        return JsonResponse({
            'status': 'success',
            'api_info': api_info
        }, status=200)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@csrf_exempt
@require_POST
def cleanup_api_allocations(request):
    """
    Clean up expired API allocations
    POST /api/pool/cleanup/
    
    Response example:
    {
        "status": "success",
        "cleaned_count": 3,
        "message": "Cleaned up 3 stale API allocations"
    }
    
    curl example:
    curl -X POST http://localhost:8000/api/pool/cleanup/
    """
    try:
        # Get current active task IDs
        active_task_ids = set(task_manager.tasks.keys())
        
        # Clean up expired allocations
        cleaned_count = api_key_pool.cleanup_stale_allocations(active_task_ids)
        
        return JsonResponse({
            'status': 'success',
            'cleaned_count': cleaned_count,
            'message': f'Cleaned up {cleaned_count} stale API allocations'
        }, status=200)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@csrf_exempt
@require_GET
def cleanup_sessions(request):
    """
    Clean up stale sessions and monitor session health
    GET /api/sessions/cleanup/
    """
    try:
        # Clean up stale sessions
        cleanup_result = cleanup_stale_sessions()
        
        # Monitor session health
        health_report = monitor_session_health()
        
        # Clean up task manager
        task_manager.cleanup_finished_tasks()
        
        return JsonResponse({
            'status': 'success',
            'cleanup_result': cleanup_result,
            'health_report': health_report,
            'message': 'Session cleanup completed'
        }, status=200)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@csrf_exempt
@require_GET
def debug_session_status(request, session_id):
    """
    Debug session status to help diagnose issues
    GET /api/sessions/<int:session_id>/debug/
    """
    try:
        formatted_id = f"{session_id:03d}"
        
        # Get session status
        session = get_session_by_id(session_id)
        
        # Get history
        history_file = os.path.join('./history', formatted_id, 'execute.json')
        history = []
        if os.path.exists(history_file):
            with open(history_file, 'r', encoding='utf-8') as f:
                history = json.load(f)
        
        # Get task manager status
        task_status = task_manager.get_task_status(formatted_id)
        
        # Analyze status
        analysis = {
            'session_exists': session is not None,
            'history_entries': len(history),
            'task_manager_status': task_status,
            'last_history_entry': history[-1] if history else None,
        }
        
        if session:
            execute_agent = session.get('execute_agent', {})
            analysis.update({
                'agent_status': execute_agent.get('status'),
                'agent_stage': execute_agent.get('stage'),
                'last_update': execute_agent.get('lastupdate'),
                'step_completion': execute_agent.get('step_completion'),
            })
        
        return JsonResponse({
            'status': 'success',
            'session_id': formatted_id,
            'session_data': session,
            'history': history,
            'analysis': analysis
        }, status=200)
        
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


async def execute_plan_async(api_key,base_url,goal, datalist, id='001'):  # New param id, default '001'
    try:
        manager = GenAgent(api_key, base_url, excutor=GLOBAL_EXECUTOR, tools_dir="./tools", id=id)
        print(f"GenAgent instantiated with ID {id}")
        
        # Execute task
        PLAN_results_dict = manager.execute_PLAN(goal, datalist)
        print(f"Plan task executed for ID {id}")
        
        return PLAN_results_dict
        
    except Exception as e:
        print(f"Error in execute_plan_async for ID {id}: {str(e)}")
        raise e


    
    
async def execute_analysis_async(api_key,base_url,goal, datalist, id='001'):  # New param id, default '001'


    agent = AnaAgent(api_key, base_url)
    print(f"Analysis instantiated with ID {id}")
    
    # Execute task
    interpretation = agent.interpret_plan(goal, datalist,id)
    print(interpretation)
    
    return interpretation

async def execute_chat_async(api_key,base_url,goal, datalist, id='001'):  # New param id, default '001'
    try:
        agent = ChatAgent(api_key, base_url)
        print(f"Chat instantiated with ID {id}")
        
        # Execute task
        interpretation = agent.interpret_plan(goal, id)
        print(f"Chat task completed for ID {id}")
        
        return interpretation
        
    except Exception as e:
        print(f"Error in execute_chat_async for ID {id}: {str(e)}")
        raise e


@csrf_exempt
async def run_plan(request):
    """
    Execute plan-related tasks
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            target_dialog = data.get('targetDialog')
            file_ids = data.get('dataPath', [])  # Now receives file ID list
            id = data.get('id', '001')

            print(f"Executing plan with ID: {id}")
            print(f"Received file IDs: {file_ids}")

            # Immediately update status to PLAN and thinking so frontend sees change
            update_execute_agent_stage(id, "PLAN")
            update_execute_agent_status_and_attempt(id, 1, 0)  # Set to thinking status immediately
            
            # Immediately create history entry, mark task start (if plan empty)
            create_initial_history_entry(id, target_dialog)

            # Get all file info
            file_info = load_file_info()
            
            # Convert file IDs to actual paths
            file_paths = []
            for file_id in file_ids:
                # Find matching file info
                matching_file = next(
                    (f for f in file_info if f['id'] == int(file_id)), 
                    None
                )
                if matching_file:
                    file_paths.append(matching_file['absolute_path'])
                else:
                    print(f"Warning: No file found for ID {file_id}")

            print(f"Converted to paths: {file_paths}")

            # Assign API key for PLAN task
            api_key, base_url = api_key_pool.allocate_api_key(f"{id}_plan")
            
            try:
                # Execute plan task using assigned API key and converted file paths
                interpretation = await execute_plan_async(
                    api_key, 
                    base_url, 
                    target_dialog, 
                    file_paths,  # Pass converted path list
                    id
                 )
            finally:
                # Release PLAN task API key
                api_key_pool.release_api_key(f"{id}_plan")
            interpretation_str = json.dumps(interpretation, indent=2)

            # Task complete, update status to idle
            update_execute_agent_status_and_attempt(id, 0, 0)
            
            # Update history
            update_history_with_result(id, interpretation)

            response = {
                'status': 'success', 
                'message': 'PLAN executed', 
                'interpretation': interpretation_str
            }
            return JsonResponse(response)

        except json.JSONDecodeError as e:
            print(f"Error parsing request data: {str(e)}")
            update_execute_agent_status_and_attempt(id, 2, 0)  # Set to error status
            return JsonResponse({
                'status': 'error',
                'message': f'Invalid JSON format: {str(e)}'
            }, status=400)
        except Exception as e:
            print(f"Error in execute_plan: {str(e)}")
            update_execute_agent_status_and_attempt(id, 2, 0)  # Set to error status
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=500)

    return JsonResponse({
        'status': 'error',
        'message': 'Invalid request method'
    }, status=405)


@csrf_exempt
async def run_analysis(request):
    """
    Execute analysis-related tasks
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            target_dialog = data.get('targetDialog')
            data_path = data.get('dataPath', [])
            id = data.get('id', '001')

            print("Executing analysis with ID:", id)
            
            # Immediately create analysis placeholder record
            create_analysis_placeholder(id, target_dialog)
            
            # Immediately update analysis agent status to thinking
            update_session(int(id.lstrip('0') or '0'), 'analysis_agent', 'status', 'thinking')
            
            # Assign API key for ANALYSIS task
            api_key, base_url = api_key_pool.allocate_api_key(f"{id}_analysis")
            
            try:
                # analysis agent has its own history storage (analysis.json)
                interpretation = await execute_analysis_async(api_key, base_url, target_dialog, data_path, id)
            finally:
                # Release ANALYSIS task API key
                api_key_pool.release_api_key(f"{id}_analysis")

            # Task complete, update status to idle
            update_session(int(id.lstrip('0') or '0'), 'analysis_agent', 'status', 'idle')

            response = {'status': 'success', 'message': 'Analysis executed', 'interpretation': interpretation}
            return JsonResponse(response)

        except Exception as e:
            print("Error in execute_analysis:", str(e))
            # Error occurred, update status to error and update placeholder record
            update_session(int(id.lstrip('0') or '0'), 'analysis_agent', 'status', 'error')
            update_analysis_placeholder_on_error(id, str(e))
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=405)


def create_chat_placeholder(id, asking):
    """
    Create chat placeholder record indicating chat in progress
    """
    try:
        formatted_id = str(id).zfill(3)
        history_dir = os.path.join('./history', formatted_id)
        os.makedirs(history_dir, exist_ok=True)
        
        chat_file_path = os.path.join(history_dir, 'chat.json')
        
        # Read existing records
        chat_history = []
        if os.path.exists(chat_file_path):
            with open(chat_file_path, 'r', encoding='utf-8') as file:
                chat_history = json.load(file)
        
        # Add placeholder record
        placeholder_entry = {
            "asking": asking,
            "response": "",  # Empty response indicates processing
            "timestamp": "",  # Empty timestamp indicates incomplete
            "session_id": formatted_id,
            "status": "processing"  # Add status identifier
        }
        chat_history.append(placeholder_entry)
        
        # Save placeholder record
        with open(chat_file_path, 'w', encoding='utf-8') as file:
            json.dump(chat_history, file, ensure_ascii=False, indent=4)
            
        logger.info(f"Created chat placeholder for session {formatted_id}")
        return True
    except Exception as e:
        logger.error(f"Error creating chat placeholder for session {id}: {str(e)}")
        return False

def update_chat_placeholder_on_error(id, error_message):
    """
    Update placeholder record when chat error occurs
    """
    try:
        formatted_id = str(id).zfill(3)
        history_dir = os.path.join('./history', formatted_id)
        chat_file_path = os.path.join(history_dir, 'chat.json')
        
        if os.path.exists(chat_file_path):
            with open(chat_file_path, 'r', encoding='utf-8') as file:
                chat_history = json.load(file)
            
            # Find last processing record and update
            for entry in reversed(chat_history):
                if entry.get('status') == 'processing':
                    entry['response'] = f"Error: {error_message}"
                    entry['timestamp'] = datetime.now().isoformat()
                    entry['status'] = 'error'
                    break
            
            with open(chat_file_path, 'w', encoding='utf-8') as file:
                json.dump(chat_history, file, ensure_ascii=False, indent=4)
                
        logger.info(f"Updated chat placeholder with error for session {formatted_id}")
    except Exception as e:
        logger.error(f"Error updating chat placeholder for session {id}: {str(e)}")

def create_report_placeholder(session_id):
    """
    Create report generation placeholder record
    """
    try:
        formatted_id = f"{session_id:03d}"
        history_dir = os.path.join('./history', formatted_id)
        os.makedirs(history_dir, exist_ok=True)
        
        execute_file_path = os.path.join(history_dir, 'execute.json')
        
        # Read existing execute.json
        execute_data = []
        if os.path.exists(execute_file_path):
            with open(execute_file_path, 'r', encoding='utf-8') as f:
                execute_data = json.load(f)
        
        # If data exists, add report placeholder to last entry
        if execute_data:
            execute_data[-1]["report_status"] = "generating"
            execute_data[-1]["report"] = ""  # Empty report indicates generating
        else:
            # If no existing data, create new entry
            execute_data.append({
                "asking": "Report generation",
                "plan": {"plan": []},
                "execute": {
                    "steps": [],
                    "status": "completed"
                },
                "report_status": "generating",
                "report": ""
            })
        
        # Save updated execute.json
        with open(execute_file_path, 'w', encoding='utf-8') as f:
            json.dump(execute_data, f, ensure_ascii=False, indent=4)
        
        logger.info(f"Created report placeholder for session {formatted_id}")
        return True
    except Exception as e:
        logger.error(f"Error creating report placeholder for session {session_id}: {str(e)}")
        return False

def update_report_placeholder_on_error(session_id, error_message):
    """
    Update placeholder record when report generation error occurs
    """
    try:
        formatted_id = f"{session_id:03d}"
        history_dir = os.path.join('./history', formatted_id)
        execute_file_path = os.path.join(history_dir, 'execute.json')
        
        if os.path.exists(execute_file_path):
            with open(execute_file_path, 'r', encoding='utf-8') as f:
                execute_data = json.load(f)
            
            # Find last generating record and update
            if execute_data and execute_data[-1].get('report_status') == 'generating':
                execute_data[-1]['report_status'] = 'error'
                execute_data[-1]['report'] = f"Report generation failed: {error_message}"
            
            with open(execute_file_path, 'w', encoding='utf-8') as f:
                json.dump(execute_data, f, ensure_ascii=False, indent=4)
                
        logger.info(f"Updated report placeholder with error for session {formatted_id}")
    except Exception as e:
        logger.error(f"Error updating report placeholder for session {session_id}: {str(e)}")

def create_analysis_placeholder(id, asking):
    """
    Create analysis placeholder record indicating analysis in progress
    """
    try:
        formatted_id = str(id).zfill(3)
        history_dir = os.path.join('./history', formatted_id)
        os.makedirs(history_dir, exist_ok=True)
        
        analysis_file_path = os.path.join(history_dir, 'analysis.json')
        
        # Read existing records
        analysis_history = []
        if os.path.exists(analysis_file_path):
            with open(analysis_file_path, 'r', encoding='utf-8') as file:
                analysis_history = json.load(file)
        
        # Add placeholder record
        placeholder_entry = {
            "asking": asking,
            "response": "",  # Empty response indicates processing
            "timestamp": "",  # Empty timestamp indicates incomplete
            "session_id": formatted_id,
            "status": "processing"  # Add status identifier
        }
        analysis_history.append(placeholder_entry)
        
        # Save placeholder record
        with open(analysis_file_path, 'w', encoding='utf-8') as file:
            json.dump(analysis_history, file, ensure_ascii=False, indent=4)
            
        logger.info(f"Created analysis placeholder for session {formatted_id}")
        return True
    except Exception as e:
        logger.error(f"Error creating analysis placeholder for session {id}: {str(e)}")
        return False

def update_analysis_placeholder_on_error(id, error_message):
    """
    Update placeholder record when analysis error occurs
    """
    try:
        formatted_id = str(id).zfill(3)
        history_dir = os.path.join('./history', formatted_id)
        analysis_file_path = os.path.join(history_dir, 'analysis.json')
        
        if os.path.exists(analysis_file_path):
            with open(analysis_file_path, 'r', encoding='utf-8') as file:
                analysis_history = json.load(file)
            
            # Find last processing record and update
            for entry in reversed(analysis_history):
                if entry.get('status') == 'processing':
                    entry['response'] = f"Error: {error_message}"
                    entry['timestamp'] = datetime.now().isoformat()
                    entry['status'] = 'error'
                    break
            
            with open(analysis_file_path, 'w', encoding='utf-8') as file:
                json.dump(analysis_history, file, ensure_ascii=False, indent=4)
                
        logger.info(f"Updated analysis placeholder with error for session {formatted_id}")
    except Exception as e:
        logger.error(f"Error updating analysis placeholder for session {id}: {str(e)}")

def cleanup_incomplete_tasks():
    """
    Clean up incomplete task status
    """
    try:
        logger.info("Starting cleanup of incomplete tasks...")
        
        # Clean up Chat placeholder records
        history_base_dir = './history'
        if os.path.exists(history_base_dir):
            for session_dir in os.listdir(history_base_dir):
                session_path = os.path.join(history_base_dir, session_dir)
                if os.path.isdir(session_path):
                    
                    # Clean up processing status in Chat history
                    chat_file_path = os.path.join(session_path, 'chat.json')
                    if os.path.exists(chat_file_path):
                        try:
                            with open(chat_file_path, 'r', encoding='utf-8') as f:
                                chat_history = json.load(f)
                            
                            updated = False
                            for entry in chat_history:
                                if entry.get('status') == 'processing':
                                    entry['response'] = "Response interrupted due to server shutdown"
                                    entry['timestamp'] = datetime.now().isoformat()
                                    entry['status'] = 'interrupted'
                                    updated = True
                            
                            if updated:
                                with open(chat_file_path, 'w', encoding='utf-8') as f:
                                    json.dump(chat_history, f, ensure_ascii=False, indent=4)
                                logger.info(f"Cleaned up incomplete chat tasks for session {session_dir}")
                        except Exception as e:
                            logger.error(f"Error cleaning up chat for session {session_dir}: {e}")
                    
                    # Clean up processing status in Analysis history
                    analysis_file_path = os.path.join(session_path, 'analysis.json')
                    if os.path.exists(analysis_file_path):
                        try:
                            with open(analysis_file_path, 'r', encoding='utf-8') as f:
                                analysis_history = json.load(f)
                            
                            updated = False
                            for entry in analysis_history:
                                if entry.get('status') == 'processing':
                                    entry['response'] = "Response interrupted due to server shutdown"
                                    entry['timestamp'] = datetime.now().isoformat()
                                    entry['status'] = 'interrupted'
                                    updated = True
                            
                            if updated:
                                with open(analysis_file_path, 'w', encoding='utf-8') as f:
                                    json.dump(analysis_history, f, ensure_ascii=False, indent=4)
                                logger.info(f"Cleaned up incomplete analysis tasks for session {session_dir}")
                        except Exception as e:
                            logger.error(f"Error cleaning up analysis for session {session_dir}: {e}")
                    
                    # Clean up Report generation status
                    execute_file_path = os.path.join(session_path, 'execute.json')
                    if os.path.exists(execute_file_path):
                        try:
                            with open(execute_file_path, 'r', encoding='utf-8') as f:
                                execute_data = json.load(f)
                            
                            updated = False
                            if execute_data:
                                for entry in execute_data:
                                    if entry.get('report_status') == 'generating':
                                        # Per your suggestion, delete incomplete report records
                                        if 'report' in entry:
                                            del entry['report']
                                        if 'report_status' in entry:
                                            del entry['report_status']
                                        updated = True
                            
                            if updated:
                                with open(execute_file_path, 'w', encoding='utf-8') as f:
                                    json.dump(execute_data, f, ensure_ascii=False, indent=4)
                                logger.info(f"Cleaned up incomplete report tasks for session {session_dir}")
                        except Exception as e:
                            logger.error(f"Error cleaning up report for session {session_dir}: {e}")
        
        logger.info("Cleanup of incomplete tasks completed")
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")

def signal_handler(signum, frame):
    """
    Signal handler, performs cleanup on SIGINT (Ctrl+C) or SIGTERM
    """
    logger.info(f"Received signal {signum}, starting cleanup...")
    cleanup_incomplete_tasks()
    sys.exit(0)

# Register signal handler
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# Register atexit handler as fallback
atexit.register(cleanup_incomplete_tasks)

@csrf_exempt
async def run_chat(request):
    """
    Execute chat-related tasks
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            target_dialog = data.get('targetDialog')
            data_path = data.get('dataPath', [])
            id = data.get('id', '001')

            print("Executing chat with ID:", id)
            
            # Immediately create chat placeholder record
            create_chat_placeholder(id, target_dialog)
            
            # Immediately update chat agent status to thinking
            update_session(int(id.lstrip('0') or '0'), 'chat_agent', 'status', 'thinking')
            
            # Assign API key for CHAT task
            api_key, base_url = api_key_pool.allocate_api_key(f"{id}_chat")
            
            try:
            # Create chat history (stored in chat.json, no need to create execute.json here)
                interpretation = await execute_chat_async(api_key, base_url, target_dialog, data_path, id)
            finally:
                # Release CHAT task API key
                api_key_pool.release_api_key(f"{id}_chat")

            # Task complete, update status to idle
            update_session(int(id.lstrip('0') or '0'), 'chat_agent', 'status', 'idle')

            response = {'status': 'success', 'message': 'Chat executed', 'interpretation': interpretation}
            return JsonResponse(response)

        except Exception as e:
            print("Error in execute_chat:", str(e))
            # Error occurred, update status to error and update placeholder record
            update_session(int(id.lstrip('0') or '0'), 'chat_agent', 'status', 'error')
            update_chat_placeholder_on_error(id, str(e))
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=405)

@csrf_exempt
def update_settings(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            global GLOBAL_API_KEY, GLOBAL_BASE_URL, GLOBAL_EXECUTOR
            print(GLOBAL_EXECUTOR)
            # Update global variables or environment
            GLOBAL_API_KEY = data.get('api_key', GLOBAL_API_KEY)
            GLOBAL_BASE_URL = data.get('base_url', GLOBAL_BASE_URL)
            GLOBAL_EXECUTOR = data.get('executor', GLOBAL_EXECUTOR)
            print(GLOBAL_EXECUTOR)
            # Save settings to .env file (overwrite mode to avoid unbounded file growth)
            try:
                env_content = f"API_KEY={GLOBAL_API_KEY}\nBASE_URL={GLOBAL_BASE_URL}\nEXECUTOR={str(GLOBAL_EXECUTOR).lower()}\n"
                with open('.env', 'w') as env_file:
                    env_file.write(env_content)
            except Exception as e:
                logger.warning(f"Failed to save settings to .env file: {e}")

            return JsonResponse({'status': 'success', 'message': 'Settings updated successfully'})

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    else:
        return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=405)
    
    
@csrf_exempt
def update_plan(request):
    print(request)
    if request.method == 'POST':
        try:
            # Print received raw data
            print(f"Raw body: {request.body}")

            data = json.loads(request.body)

            # If received a list instead of dict, wrap it
            if isinstance(data, list):
                id = request.GET.get('id', '001')  # Get id from URL param
                data = {
                    'id': id,
                    'plan': data
                }

            # Get and normalize ID format
            id = data.get('id')
            # Ensure id is string
            id = str(id)
            # Remove leading zeros to get pure number
            id = id.lstrip('0') or '1'  # If all zeros, default to '1'
            # Format as 3 digits
            id = id.zfill(3)
            
            plan = data.get('plan')

            if not id or not plan:
                return JsonResponse({'status': 'error', 'message': 'ID or plan data is missing'}, status=400)

            # Build save path
            plan_file_path = os.path.join(settings.BASE_DIR, 'output', f'{id}_PLAN.json')

            print(f"Saving plan to: {plan_file_path}")  # Debug info

            # Save execution history
            history_dir = os.path.join('./history', id)
            os.makedirs(history_dir, exist_ok=True)
            execute_file_path = os.path.join(history_dir, 'execute.json')

            # Read existing history or create new
            if os.path.exists(execute_file_path):
                with open(execute_file_path, 'r', encoding='utf-8') as f:
                    history = json.load(f)
                    # If last record's plan is string, try to parse it
                    if history and isinstance(history[-1]['plan'], str):
                        try:
                            history[-1]['plan'] = json.loads(history[-1]['plan'])
                        except json.JSONDecodeError:
                            print("Warning: Could not parse the last plan entry")
            else:
                history = []

            # Collect execution results
            execution_results = {
                "steps": [],
                "status": "completed"
            }

            # Create new history entry
            history_entry = {
                "asking": "Plan updated via API",  # Or get more specific description from request
                "plan": {'plan': plan},
                "execute": execution_results
            }

            # Add new record
            history.append(history_entry)

            # Save updated history
            with open(execute_file_path, 'w', encoding='utf-8') as f:
                json.dump(history, f, indent=4, ensure_ascii=False)

            # Write new plan to file
            with open(plan_file_path, 'w', encoding='utf-8') as file:
                json.dump({'plan': plan}, file, ensure_ascii=False, indent=2)

            return JsonResponse({'status': 'success', 'message': f'Plan {id}_PLAN.json saved/updated successfully'})

        except Exception as e:
            print(f"Error occurred while saving plan: {str(e)}")  # Output error to console
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    else:
        return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=405)



@csrf_exempt
def update_step(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            id = data.get('id')
            step_number = data.get('stepNumber')
            content = data.get('content')

            if not id or not step_number or not content:
                return JsonResponse({'status': 'error', 'message': 'ID, step number or content is missing'}, status=400)

            # Check if execution is paused
            session_status_path = os.path.join(settings.BASE_DIR, 'knowledge', 'session_status.json')
            if os.path.exists(session_status_path):
                with open(session_status_path, 'r', encoding='utf-8') as f:
                    sessions = json.load(f)
                
                # Convert id to integer (if it's a string with leading zeros)
                numeric_id = int(str(id).lstrip('0') or '0')
                
                # Find the session with matching id
                session = next((s for s in sessions if s.get('id') == numeric_id), None)
                
                if session:
                    # Check if execute_agent stage is PAUSED
                    execute_agent = session.get('execute_agent', {})
                    if execute_agent.get('stage') != "PAUSED":
                        return JsonResponse({
                            'status': 'error', 
                            'message': 'Cannot update step when execution is not paused'
                        }, status=403)
                else:
                    return JsonResponse({'status': 'error', 'message': f'Session with ID {id} not found'}, status=404)
            else:
                return JsonResponse({'status': 'error', 'message': 'Session status file not found'}, status=500)

            steps_dir = os.path.join(settings.BASE_DIR, 'output')
            step_file_path = os.path.join(steps_dir, f'{id}_Step_{step_number}.sh')

            with open(step_file_path, 'w', encoding='utf-8') as file:
                file.write(content.strip())
                
            # Also update corresponding DEBUG file
            debug_output_path = os.path.join(steps_dir, f'{id}_DEBUG_Output_{step_number}.json')
            if os.path.exists(debug_output_path):
                try:
                    with open(debug_output_path, 'r', encoding='utf-8') as f:
                        debug_data = json.load(f)
                        
                    # Update new shell commands to DEBUG file
                    shell_commands = [line.strip() for line in content.strip().split('\n') if line.strip()]
                    debug_data['shell'] = shell_commands
                    
                    with open(debug_output_path, 'w', encoding='utf-8') as f:
                        json.dump(debug_data, f, ensure_ascii=False, indent=4)
                        
                except Exception as e:
                    print(f"Error updating DEBUG file: {str(e)}")
            
            # Directly update history file
            formatted_id = str(id).zfill(3)  # Format as 3-digit ID
            history_dir = os.path.join('./history', formatted_id)
            execute_json_path = os.path.join(history_dir, 'execute.json')
            
            # Ensure history directory exists
            os.makedirs(history_dir, exist_ok=True)
            
            # Read current execute.json file
            execute_data = []
            if os.path.exists(execute_json_path):
                try:
                    with open(execute_json_path, 'r', encoding='utf-8') as f:
                        execute_data = json.load(f)
                except json.JSONDecodeError:
                    print(f"Invalid JSON format in {execute_json_path}")
                    execute_data = []
            
            # If data exists, update shell content for corresponding step in last record
            if execute_data:
                last_entry = execute_data[-1]
                if 'execute' in last_entry and 'steps' in last_entry['execute']:
                    steps = last_entry['execute']['steps']
                    step_num = int(step_number)
                    
                    # Find step with specified step_number
                    step_entry = None
                    for i, step in enumerate(steps):
                        if 'step_number' in step and step['step_number'] == step_num:
                            step_entry = step
                            break
                        # If step has no step_number field but index matches step_number
                        elif i == step_num:
                            step_entry = step
                            # Add step_number field for future identification
                            step['step_number'] = step_num
                            break
                    
                    # If no matching step found, create new step
                    if not step_entry:
                        # If step number exceeds array length, pad with empty objects first
                        while len(steps) <= step_num:
                            steps.append({})
                        
                        step_entry = {'step_number': step_num}
                        steps[step_num] = step_entry
                    
                    # Update shell content
                    step_entry['shell'] = content.strip()
                    
                    # If step has debug field, also update shell in debug
                    if 'debug' in step_entry:
                        shell_commands = [line.strip() for line in content.strip().split('\n') if line.strip()]
                        step_entry['debug']['shell'] = shell_commands
                    
                    # Save updated execute.json
                    with open(execute_json_path, 'w', encoding='utf-8') as f:
                        json.dump(execute_data, f, ensure_ascii=False, indent=4)

            return JsonResponse({'status': 'success', 'message': f'Step {step_number} for {id} saved/updated successfully'})

        except Exception as e:
            print(f"Error occurred while saving steps: {str(e)}")
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    else:
        return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=405)


# Get knowledge base entries from Task_Knowledge.json
def get_tools_files(request):
    """Read all knowledge base entries from Task_Knowledge.json"""
    json_file_path = os.path.join(settings.BASE_DIR, 'knowledge', 'Task_Konwledge.json')
    
    if os.path.exists(json_file_path):
        try:
            with open(json_file_path, 'r', encoding='utf-8') as f:
                knowledge_data = json.load(f)
            # Return entry list, each entry has source and page as identifier
            items = []
            for item in knowledge_data:
                source = item.get('metadata', {}).get('source', 'unknown')
                page = item.get('metadata', {}).get('page', 0)
                content_preview = item.get('content', '')[:100] + '...' if len(item.get('content', '')) > 100 else item.get('content', '')
                items.append({
                    'id': f"{source}_page{page}",
                    'source': source,
                    'page': page,
                    'content_preview': content_preview,
                    'content': item.get('content', '')
                })
            return JsonResponse({'files': items})
        except json.JSONDecodeError as e:
            logger.error(f"JSON Decode Error: {e}")
            return JsonResponse({'files': [], 'error': 'Invalid JSON format'})
    else:
        return JsonResponse({'files': []})

@csrf_exempt
def upload_tool_file(request):
    """Add new knowledge base entry to Task_Knowledge.json"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            content = data.get('content', '')
            source = data.get('source', 'custom')
            
            if not content:
                return JsonResponse({'status': 'error', 'message': 'Content is required'}, status=400)
            
            json_file_path = os.path.join(settings.BASE_DIR, 'knowledge', 'Task_Konwledge.json')
            
            # Read existing data
            knowledge_data = []
            if os.path.exists(json_file_path):
                with open(json_file_path, 'r', encoding='utf-8') as f:
                    knowledge_data = json.load(f)
            
            # Calculate new page number (max page + 1)
            max_page = 0
            for item in knowledge_data:
                page = item.get('metadata', {}).get('page', 0)
                if page > max_page:
                    max_page = page
            
            # Add new entry
            new_item = {
                'content': content,
                'metadata': {
                    'source': source,
                    'page': max_page + 1
                }
            }
            knowledge_data.append(new_item)
            
            # Save back to file
            with open(json_file_path, 'w', encoding='utf-8') as f:
                json.dump(knowledge_data, f, ensure_ascii=False, indent=4)
            
            return JsonResponse({
                'status': 'success', 
                'message': 'Knowledge entry added successfully',
                'item': {
                    'id': f"{source}_page{max_page + 1}",
                    'source': source,
                    'page': max_page + 1
                }
            })
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON data'}, status=400)
        except Exception as e:
            logger.error(f"Error adding knowledge entry: {e}")
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=400)

@csrf_exempt
def delete_tool_file(request):
    """Delete specified knowledge base entry from Task_Knowledge.json"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            # Support two delete modes: by id or by source+page
            item_id = data.get('file_name') or data.get('id')  # Compatible with old file_name param
            source = data.get('source')
            page = data.get('page')
            
            json_file_path = os.path.join(settings.BASE_DIR, 'knowledge', 'Task_Konwledge.json')
            
            if not os.path.exists(json_file_path):
                return JsonResponse({'status': 'error', 'message': 'Knowledge file not found'}, status=404)
            
            with open(json_file_path, 'r', encoding='utf-8') as f:
                knowledge_data = json.load(f)
            
            original_length = len(knowledge_data)
            
            # Parse source and page from id
            if item_id and '_page' in str(item_id):
                parts = str(item_id).rsplit('_page', 1)
                source = parts[0]
                page = int(parts[1])
            
            # Delete matching entry
            if source is not None and page is not None:
                knowledge_data = [
                    item for item in knowledge_data 
                    if not (item.get('metadata', {}).get('source') == source and 
                           item.get('metadata', {}).get('page') == int(page))
                ]
            
            if len(knowledge_data) == original_length:
                return JsonResponse({'status': 'error', 'message': 'Entry not found'}, status=404)
            
            # Save updated data
            with open(json_file_path, 'w', encoding='utf-8') as f:
                json.dump(knowledge_data, f, ensure_ascii=False, indent=4)
            
            return JsonResponse({'status': 'success', 'message': 'Knowledge entry deleted successfully'})
        
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON data'}, status=400)
        except Exception as e:
            logger.error(f"Error deleting knowledge entry: {e}")
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=400)



# Get files from knowledge folder
def get_doc_files(request):
#     doc_dir = os.path.join(settings.BASE_DIR, 'knowledge')
#     files = os.listdir(doc_dir) if os.path.exists(doc_dir) else []
#     print(files)
#     return JsonResponse({'files': files})
        # Locate JSON file path
    json_file_path = os.path.join(settings.BASE_DIR, 'knowledge', 'Plan_Knowledge.json')
    
    # Check if file exists and read its content
    if os.path.exists(json_file_path):
        with open(json_file_path, 'r', encoding='utf-8') as f:
            try:
                knowledge_data = json.load(f)  # Parse JSON file
            except json.JSONDecodeError as e:
                print(f"JSON Decode Error: {e}")
                return JsonResponse({'error': 'Invalid JSON format'}, status=400)
    else:
        print("File not found")
        return JsonResponse({'error': 'File not found'}, status=404)
    print(knowledge_data)
    # Return JSON data as response
    return JsonResponse({'files': knowledge_data})

@csrf_exempt
def update_doc_files(request):
    if request.method == 'POST':
        try:
            # Get data passed from request
            updated_data = json.loads(request.body)
            
            # Convert data to JSON format
            formatted_data = []
            for page, contents in updated_data.items():
                for content in contents:
                    formatted_data.append({
                        "content": content,
                        "metadata": {"source": "tools", "page": int(page)}
                    })

            # Locate JSON file path
            json_file_path = os.path.join(settings.BASE_DIR, 'knowledge', 'Plan_Knowledge.json')

            # Save updated data to JSON file
            with open(json_file_path, 'w', encoding='utf-8') as f:
                json.dump(formatted_data, f, ensure_ascii=False, indent=4)

            return JsonResponse({'status': 'success', 'message': 'Documents updated successfully.'})
        
        except json.JSONDecodeError as e:
            return JsonResponse({'status': 'error', 'message': f'Invalid JSON format: {e}'}, status=400)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'}, status=405)


@csrf_exempt
async def runagent(request):
    global GLOBAL_API_KEY, GLOBAL_BASE_URL

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            mode = data.get('mode')
            target_dialog = data.get('targetDialog')
            data_path = data.get('dataPath')
            id = data.get('id', '001')
            
            print("Received data:", target_dialog, mode, id)

            if mode == 'execute':
                print("a")
                interpretation = await execute_plan_async(GLOBAL_API_KEY, GLOBAL_BASE_URL, target_dialog, data_path, id)
                interpretation_str = json.dumps(interpretation, indent=2)
                
                response = {'status': 'success', 'message': 'PLAN executed', 'interpretation': interpretation_str}
                print(response)
            elif mode == 'analysis':
                interpretation = await execute_analysis_async(GLOBAL_API_KEY, GLOBAL_BASE_URL, target_dialog, data_path, id)
                response = {'status': 'success', 'message': 'Analysis executed', 'interpretation': interpretation}
                
            else:
                interpretation = await execute_chat_async(GLOBAL_API_KEY, GLOBAL_BASE_URL, target_dialog, data_path, id)
                response = {'status': 'success', 'message': 'Chat executed', 'interpretation': interpretation}
                print(response)

        except Exception as e:
            print("Error:", str(e))
            response = {'status': 'error', 'message': str(e)}

        # Return JsonResponse, ensure it is serializable dict
        return JsonResponse(response)
    else:
        return JsonResponse({'status': 'error', 'message': 'Invalid request method'})

@csrf_exempt
@require_GET
def get_execute_history(request, id):
    """
    API: Get execution history and execute_agent status for specific ID
    GET /api/execute_history/<str:id>/
curl -X GET http://129.226.112.200:8000/api/execute_history/005/
    Response example:
    {
        "status": "success",
        "history": [
            {
                "asking": "User request",
                "plan": {
                    "plan": [...]
                },
                "execute": {
                    "steps": [...],
                    "status": "completed"
                }
            }
        ],
        "execute_agent": {
            "step_completion": "100.00%",
            "current_step": 1,
            "total_steps": 1,
            "is_execute": false,
            "status": "idle",
            ...
        },
        "task_running": false
    }
    """
    try:
        # Format ID as 3 digits (e.g. '1' -> '001')
        formatted_id = str(id).zfill(3)
        history_file = os.path.join('./history', formatted_id, 'execute.json')
        
        # Check if task is running in task manager
        task_running = task_manager.get_task_status(formatted_id) == 'running'
        
        # Update execution status and history
        update_execute_agent_status(formatted_id)
        update_history_execute_json(formatted_id)
        
        # Read session status
        session_status_file = os.path.join(settings.BASE_DIR, 'knowledge', 'session_status.json')
        execute_agent_status = None
        
        if os.path.exists(session_status_file):
            with open(session_status_file, 'r', encoding='utf-8') as f:
                sessions = json.load(f)
                # Convert formatted_id to number (remove leading zeros)
                numeric_id = int(formatted_id)
                # Find corresponding session
                for session in sessions:
                    if session.get('id') == numeric_id:
                        execute_agent_status = session.get('execute_agent', {})
                        break

        # Read execution history
        history = []
        if os.path.exists(history_file):
            try:
                with open(history_file, 'r', encoding='utf-8') as f:
                    history = json.load(f)
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON format in history file: {str(e)}")
        
        # If task running but history empty, task just started
        if task_running and not history:
            # Try to create initial history (execution phase, should not create new entry)
            create_initial_history_entry(formatted_id, "Execute task in progress", is_execute_phase=True)
            # Re-read history
            if os.path.exists(history_file):
                try:
                    with open(history_file, 'r', encoding='utf-8') as f:
                        history = json.load(f)
                except json.JSONDecodeError:
                    pass

        # Improve status judgment logic
        display_status = "idle"
        if execute_agent_status:
            agent_status = execute_agent_status.get('status', 'idle')
            agent_stage = execute_agent_status.get('stage', 'PLAN')
            
            # If thinking status, show thinking
            if agent_status == 'thinking':
                display_status = "thinking"
            # If PLAN phase and has history, check last entry
            elif agent_stage == 'PLAN' and history:
                last_entry = history[-1]
                last_plan = last_entry.get('plan', {}).get('plan', [])
                last_execute_status = last_entry.get('execute', {}).get('status', '')
                
                # If plan empty and execute status running, show thinking
                if not last_plan and last_execute_status == 'running':
                    display_status = "thinking"
                elif last_plan and last_execute_status == 'completed':
                    display_status = "plan_completed"
            # Other statuses keep as-is
            else:
                display_status = agent_status

        return JsonResponse({
            'status': 'success',
            'history': history,
            'execute_agent': execute_agent_status,
            'task_running': task_running,  # Add task running status
            'session_id': formatted_id,
            'display_status': display_status  # Add display status suggestion
        })

    except Exception as e:
        logger.error(f"Error getting execute history for ID {id}: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)

@csrf_exempt
@require_GET
def get_task_status_view(request, session_id):
    """
    Get task status for specific session (including chat and report)
    GET /api/sessions/<int:session_id>/task_status/
    
    Response example:
    {
        "status": "success",
        "chat_processing": true,
        "report_generating": true,
        "last_chat_entry": {...},
        "report_status": "generating"
    }
    """
    try:
        formatted_id = f"{session_id:03d}"
        history_dir = os.path.join('./history', formatted_id)
        
        result = {
            "chat_processing": False,
            "report_generating": False,
            "analysis_processing": False,
            "last_chat_entry": None,
            "last_analysis_entry": None,
            "report_status": None
        }
        
        # Check Chat status
        chat_file_path = os.path.join(history_dir, 'chat.json')
        if os.path.exists(chat_file_path):
            try:
                with open(chat_file_path, 'r', encoding='utf-8') as f:
                    chat_history = json.load(f)
                if chat_history:
                    last_entry = chat_history[-1]
                    result["last_chat_entry"] = last_entry
                    if last_entry.get('status') == 'processing':
                        result["chat_processing"] = True
            except Exception as e:
                logger.error(f"Error reading chat history for session {formatted_id}: {e}")
        
        # Check Analysis status
        analysis_file_path = os.path.join(history_dir, 'analysis.json')
        if os.path.exists(analysis_file_path):
            try:
                with open(analysis_file_path, 'r', encoding='utf-8') as f:
                    analysis_history = json.load(f)
                if analysis_history:
                    last_entry = analysis_history[-1]
                    result["last_analysis_entry"] = last_entry
                    if last_entry.get('status') == 'processing':
                        result["analysis_processing"] = True
            except Exception as e:
                logger.error(f"Error reading analysis history for session {formatted_id}: {e}")
        
        # Check Report status
        execute_file_path = os.path.join(history_dir, 'execute.json')
        if os.path.exists(execute_file_path):
            try:
                with open(execute_file_path, 'r', encoding='utf-8') as f:
                    execute_data = json.load(f)
                if execute_data and execute_data[-1].get('report_status'):
                    report_status = execute_data[-1].get('report_status')
                    result["report_status"] = report_status
                    if report_status == 'generating':
                        result["report_generating"] = True
            except Exception as e:
                logger.error(f"Error reading execute history for session {formatted_id}: {e}")
        
        return JsonResponse({
            'status': 'success',
            **result
        }, status=200)
        
    except Exception as e:
        logger.error(f"Error getting task status for session {session_id}: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)

@csrf_exempt
@require_GET
def generate_report(request, session_id):
    """
    Generate a report for a specific session ID using ChatAgent
    GET /api/sessions/<int:session_id>/generate_report/
    
    Response example:
    {
        "status": "success",
        "report": "# Project 004 Report\n\n..."
    }
    curl -X GET http://localhost:8000/api/sessions/4/generate_report/
    curl example:
    curl -X GET http://129.226.112.200:8000/api/sessions/4/generate_report/
    """
    try:
        # Format session_id to 3 digits (e.g., "4" -> "004")
        formatted_id = f"{session_id:03d}"
        logger.info(f"Starting report generation for session {formatted_id}")
        
        # Immediately create report generation placeholder record
        create_report_placeholder(session_id)
        
        # Check if output directory exists
        output_dir = os.path.join('./output', formatted_id)
        if not os.path.exists(output_dir):
            logger.warning(f"Output directory not found for session {formatted_id}")
            update_report_placeholder_on_error(session_id, f'No output data found for session {session_id}')
            return JsonResponse({
                'status': 'error',
                'message': f'No output data found for session {session_id}. Please ensure the analysis has been completed.'
            }, status=404)
        
        get_session_content_index(formatted_id)
        
        # Assign API key for report generation
        api_key, base_url = api_key_pool.allocate_api_key(f"{formatted_id}_report")
        
        try:
            # Create ChatAgent instance with allocated credentials
            chat_agent = ChatAgent(
                    api_key=api_key,
                    base_url=base_url,
                Model='claude-opus-4-1-20250805-thinking'
            )
            
        # Generate the report
            report = chat_agent.generate_report(formatted_id)
        
            return JsonResponse({
                'status': 'success',
                'report': report
            }, status=200)
        finally:
                # Release report generation API key
                api_key_pool.release_api_key(f"{formatted_id}_report")
            
    except Exception as e:
        logger.error(f"Error generating report for session {session_id}: {str(e)}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        update_report_placeholder_on_error(session_id, str(e))
        return JsonResponse({
            'status': 'error',
            'message': f'Failed to generate report: {str(e)}'
        }, status=500)


@require_GET
def serve_output_file(request, file_path):
    """
    Serve files from the output directory for image visualization in reports.
    """
    # Security: Prevent directory traversal attacks
    if '..' in file_path or file_path.startswith('/'):
        raise Http404("Invalid file path")
    
    # Construct the full file path
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    full_path = os.path.join(base_dir, 'output', file_path)
    
    # Check if file exists
    if not os.path.exists(full_path) or not os.path.isfile(full_path):
        raise Http404("File not found")
    
    # Determine content type
    content_type, _ = mimetypes.guess_type(full_path)
    if content_type is None:
        content_type = 'application/octet-stream'
    
    # Only allow certain file types (images)
    allowed_types = ['image/png', 'image/jpeg', 'image/gif', 'image/svg+xml', 'image/webp']
    if content_type not in allowed_types:
        raise Http404("File type not allowed")
    
    return FileResponse(open(full_path, 'rb'), content_type=content_type)