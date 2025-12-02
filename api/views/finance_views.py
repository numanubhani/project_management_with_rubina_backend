from rest_framework.decorators import api_view
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema

from ..models import Project, ProjectStatus, PaymentStatus, UserRole
from ..views.project_views import project_to_response


@extend_schema(
    tags=['Finance']
)
@api_view(['GET'])
def get_finance_history(request):
    """Get financial history (completed/paid projects)"""
    query = Project.objects.filter(workspace=request.user.workspace)
    
    if request.user.role == UserRole.CLIENT:
        query = query.filter(client=request.user)
    
    projects = query.filter(
        status=ProjectStatus.COMPLETED
    ) | query.filter(
        payment_status__in=[PaymentStatus.PENDING_APPROVAL, PaymentStatus.PAID]
    )
    
    return Response([project_to_response(p, request.user) for p in projects])


@extend_schema(
    tags=['Finance']
)
@api_view(['GET'])
def get_finance_stats(request):
    """Get financial statistics"""
    query = Project.objects.filter(workspace=request.user.workspace)
    
    if request.user.role == UserRole.CLIENT:
        query = query.filter(client=request.user)
    
    projects = query.filter(
        status=ProjectStatus.COMPLETED
    ) | query.filter(
        payment_status__in=[PaymentStatus.PENDING_APPROVAL, PaymentStatus.PAID]
    )
    
    total_amount = sum(p.amount for p in projects if p.payment_status == PaymentStatus.PAID)
    pending_amount = sum(
        p.amount for p in projects
        if p.payment_status == PaymentStatus.PENDING_APPROVAL or
        (p.status == ProjectStatus.COMPLETED and p.payment_status == PaymentStatus.UNPAID)
    )
    
    return Response({
        'total_amount': total_amount,
        'pending_amount': pending_amount,
        'projects_count': len(projects)
    })

