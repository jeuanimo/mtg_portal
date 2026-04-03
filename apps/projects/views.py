from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from .models import Project, Task


@login_required
def project_list(request):
    """List projects."""
    if request.user.is_staff_user:
        projects = Project.objects.select_related('organization', 'project_manager').all()
    else:
        projects = Project.objects.filter(
            Q(team_members=request.user) |
            Q(organization__contacts__user=request.user)
        ).distinct()
    
    status = request.GET.get('status')
    if status:
        projects = projects.filter(status=status)
    
    context = {
        'projects': projects,
        'status_choices': Project.Status.choices,
    }
    return render(request, 'projects/project_list.html', context)


@login_required
def project_detail(request, pk):
    """Project detail view."""
    project = get_object_or_404(Project, pk=pk)
    tasks = project.tasks.select_related('assigned_to').all()
    documents = project.documents.all()
    
    context = {
        'project': project,
        'tasks': tasks,
        'documents': documents,
    }
    return render(request, 'projects/project_detail.html', context)


@login_required
def task_list(request):
    """List tasks assigned to user."""
    if request.user.is_staff_user:
        tasks = Task.objects.select_related('project', 'assigned_to').all()
    else:
        tasks = Task.objects.filter(assigned_to=request.user)
    
    status = request.GET.get('status')
    if status:
        tasks = tasks.filter(status=status)
    
    context = {
        'tasks': tasks,
        'status_choices': Task.Status.choices,
    }
    return render(request, 'projects/task_list.html', context)


@login_required
def task_detail(request, pk):
    """Task detail view."""
    task = get_object_or_404(Task.objects.select_related('project', 'assigned_to'), pk=pk)
    return render(request, 'projects/task_detail.html', {'task': task})
