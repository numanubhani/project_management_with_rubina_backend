from django.contrib import admin
from .models import User, Workspace, Project, ProjectFile, Comment, ProjectUpdate

admin.site.register(User)
admin.site.register(Workspace)
admin.site.register(Project)
admin.site.register(ProjectFile)
admin.site.register(Comment)
admin.site.register(ProjectUpdate)

