from django.contrib import admin
from .models import Project, Task, ProjectDocument


class TaskInline(admin.TabularInline):
    model = Task
    extra = 0


class ProjectDocumentInline(admin.TabularInline):
    model = ProjectDocument
    extra = 0


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'organization', 'status', 'project_manager', 'start_date', 'target_end_date']
    list_filter = ['status', 'created_at']
    search_fields = ['name', 'organization__name']
    filter_horizontal = ['team_members']
    inlines = [TaskInline, ProjectDocumentInline]


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ['title', 'project', 'status', 'priority', 'assigned_to', 'due_date']
    list_filter = ['status', 'priority', 'project']
    search_fields = ['title', 'description']
