from django.urls import path
from .views import (
    # Auth
    login, register_workspace,
    # Users
    get_users, create_user, get_current_user_info, update_profile,
    # Projects
    get_projects, get_project, create_project, get_dashboard_stats,
    update_project_status, upload_delivery, add_comment, add_project_update,
    mark_payment_cleared, approve_payment, get_unread_updates,
    # Workspaces
    get_current_workspace, get_workspace, update_workspace,
    get_workspace_stats, export_workspace_data,
    # Files
    download_file,
    # Finance
    get_finance_history, get_finance_stats,
)

urlpatterns = [
    # Authentication
    path('auth/login', login, name='login'),
    path('auth/register', register_workspace, name='register'),
    
    # Users
    path('users/', get_users, name='get_users'),
    path('users/create', create_user, name='create_user'),
    path('users/me', get_current_user_info, name='get_current_user'),
    path('users/me/update', update_profile, name='update_profile'),
    
    # Projects
    path('projects/', get_projects, name='get_projects'),
    path('projects/', create_project, name='create_project'),
    path('projects/dashboard/stats', get_dashboard_stats, name='dashboard_stats'),
    path('projects/<str:project_id>', get_project, name='get_project'),
    path('projects/<str:project_id>/status', update_project_status, name='update_status'),
    path('projects/<str:project_id>/delivery', upload_delivery, name='upload_delivery'),
    path('projects/<str:project_id>/comments', add_comment, name='add_comment'),
    path('projects/<str:project_id>/updates', add_project_update, name='add_update'),
    path('projects/<str:project_id>/payment/clear', mark_payment_cleared, name='clear_payment'),
    path('projects/<str:project_id>/payment/approve', approve_payment, name='approve_payment'),
    path('projects/<str:project_id>/updates/unread', get_unread_updates, name='unread_updates'),
    
    # Workspaces
    path('workspaces/me', get_current_workspace, name='get_current_workspace'),
    path('workspaces/me/update', update_workspace, name='update_workspace'),
    path('workspaces/me/stats', get_workspace_stats, name='workspace_stats'),
    path('workspaces/me/export', export_workspace_data, name='export_workspace'),
    path('workspaces/<str:workspace_id>', get_workspace, name='get_workspace'),
    
    # Files
    path('files/<str:project_id>/<str:category>/<str:filename>', download_file, name='download_file'),
    
    # Finance
    path('finance/history', get_finance_history, name='finance_history'),
    path('finance/stats', get_finance_stats, name='finance_stats'),
]

