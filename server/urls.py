"""
URL configuration for Server project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from backend import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.index, name='index'),
    path('get_plan_data/', views.get_plan_data, name='get_plan_data'),
    path('get_step_data/', views.get_step_data, name='get_step_data'),
    path('get_all_ids/', views.get_all_ids, name='get_all_ids'),
    path('create_new_plan/', views.create_new_plan, name='create_new_plan'),
    path('delete_plan_and_steps/', views.delete_plan_and_steps, name='delete_plan_and_steps'),
    path('runagent/', views.runagent, name='runagent'),  
    path('update_settings/', views.update_settings, name='update_settings'),
    path('get_initial_settings/', views.get_initial_settings, name='get_initial_settings'),
    path('update_plan/', views.update_plan, name='update_plan'),
    path('update_step/', views.update_step, name='update_step'),
    path('execute_plan/', views.execute_plan, name='execute_plan'),
    path('stop_plan/', views.stop_plan, name='stop_plan'),
    path('stop_task/', views.stop_task, name='stop_task'),
    path('get_doc_files/', views.get_doc_files, name='get_doc_files'),
    path('update_doc_files/', views.update_doc_files, name='update_doc_files'),
    path('get_tools_files/', views.get_tools_files, name='get_tools_files'),
    path('upload_tool_file/', views.upload_tool_file, name='upload_tool_file'),
    path('delete_tool_file/', views.delete_tool_file, name='delete_tool_file'),
    path('upload_file/', views.upload_file, name='upload_file'),
    path('upload_file_from_google_drive/', views.upload_file_from_google_drive, name='upload_file_from_google_drive'),
    path('get_file_content/', views.get_file_content, name='get_file_content'),
    path('save_file_content/', views.save_file_content, name='save_file_content'),
    path('get_chat_history/<int:session_id>/', views.get_chat_history, name='get_chat_history'),
    path('run_plan/', views.run_plan, name='run_plan'),
    path('run_analysis/', views.run_analysis, name='run_analysis'),
    path('run_chat/', views.run_chat, name='run_chat'),

    # File info API routes
    path('api/files/', views.get_file_info, name='get_file_info'),
    path('api/files/update_description/', views.update_file_description, name='update_file_description'),
    # path('api/files/update_metadata/', views.update_file_metadata, name='update_file_metadata'),
        # API route for updating session title
    path('api/sessions/<int:session_id>/update_title/', views.update_session_title_view, name='update_session_title'),


    # Session management API routes
    path('api/sessions/create/', views.create_new_session, name='create_new_session'),
    path('api/sessions/<int:session_id>/', views.get_session_view, name='get_session'),
    path('api/sessions/<int:session_id>/update/', views.update_session_status_view, name='update_session_status'),
    
    # Session management API routes
    path('api/sessions/', views.get_session_list, name='get_session_list'),
    path('api/sessions/<int:session_id>/chat/', views.get_session_chat, name='get_session_chat'),
    path('api/sessions/<int:session_id>/execute/', views.get_session_execute, name='get_session_execute'),
    path('api/sessions/<int:session_id>/analysis/', views.get_session_analysis, name='get_session_analysis'),
    path('api/sessions/<int:session_id>/analysis_history/', views.get_session_analysis_history, name='get_session_analysis_history'),
    path('api/sessions/<int:session_id>/delete_session/', views.delete_session_files_view, name='delete_session_files'),
    # Execute step API route
    path('api/sessions/<int:session_id>/execute_step/<int:step_number>/', views.execute_step, name='execute_step'),
    path('api/execute_history/<str:id>/', views.get_execute_history, name='get_execute_history'),

    # New path for report generation
    path('api/sessions/<int:session_id>/generate_report/', views.generate_report, name='generate_report'),
    
    # Task status API
    path('api/sessions/<int:session_id>/task_status/', views.get_task_status_view, name='get_task_status_view'),
    
    # Task management and timeout control APIs
    path('api/tasks/status/', views.get_task_status, name='get_task_status'),
    path('api/tasks/check_timeout/', views.check_timeout_tasks, name='check_timeout_tasks'),
    path('api/tasks/<str:task_id>/info/', views.get_task_info, name='get_task_info'),
    path('api/tasks/<str:task_id>/force_reset/', views.force_reset_task, name='force_reset_task'),
    
    # Timeout monitor management APIs
    path('api/monitor/status/', views.timeout_monitor_status, name='timeout_monitor_status'),
    path('api/monitor/restart/', views.restart_timeout_monitor, name='restart_timeout_monitor'),
    
    # Session cleanup with timeout handling
    path('api/sessions/cleanup/', views.cleanup_sessions, name='cleanup_sessions'),
    
    # API key pool management APIs
    path('api/pool/status/', views.get_api_pool_status, name='get_api_pool_status'),
    path('api/pool/cleanup/', views.cleanup_api_allocations, name='cleanup_api_allocations'),
    path('api/tasks/<str:task_id>/api/', views.get_task_api_info, name='get_task_api_info'),
    
    # Output file serving (for images in reports)
    path('api/output/<path:file_path>', views.serve_output_file, name='serve_output_file'),
]

