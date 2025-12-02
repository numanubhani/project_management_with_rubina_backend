from rest_framework import permissions
from .models import UserRole


class IsAdmin(permissions.BasePermission):
    """Only allow admin users"""
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role == UserRole.ADMIN


class IsClient(permissions.BasePermission):
    """Only allow client users"""
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role == UserRole.CLIENT


class IsProjectOwner(permissions.BasePermission):
    """Only allow project owner (client) or admin"""
    def has_object_permission(self, request, view, obj):
        if request.user.role == UserRole.ADMIN:
            return True
        return obj.client == request.user

