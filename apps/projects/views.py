from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.core.decorators import staff_required

from .forms import ProjectForm, TaskForm
from .models import Project, Task


@login_required
def project_list(request):
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
        'current_status': status,
    }
    return render(request, 'projects/project_list.html', context)


@login_required
def project_detail(request, pk):
    project = get_object_or_404(Project, pk=pk)
    tasks = project.tasks.select_related('assigned_to').all()
    documents = project.documents.all()

    context = {
        'project': project,
        'tasks': tasks,
        'documents': documents,
    }
    return render(request, 'projects/project_detail.html', context)


@staff_required
def project_create(request):
    if request.method == 'POST':
        form = ProjectForm(request.POST)
        if form.is_valid():
            project = form.save()
            messages.success(request, f'Project "{project.name}" created.')
            return redirect('projects:project_detail', pk=project.pk)
    else:
        form = ProjectForm()
    return render(request, 'projects/project_form.html', {'form': form, 'action': 'Create'})


@staff_required
def project_update(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if request.method == 'POST':
        form = ProjectForm(request.POST, instance=project)
        if form.is_valid():
            form.save()
            messages.success(request, f'Project "{project.name}" updated.')
            return redirect('projects:project_detail', pk=project.pk)
    else:
        form = ProjectForm(instance=project)
    return render(request, 'projects/project_form.html', {'form': form, 'project': project, 'action': 'Edit'})


@staff_required
def project_delete(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if request.method == 'POST':
        name = project.name
        project.delete()
        messages.success(request, f'Project "{name}" deleted.')
        return redirect('projects:project_list')
    return render(request, 'projects/project_confirm_delete.html', {'project': project})


# ── Task CRUD ─────────────────────────────────────────────────────────────────

@login_required
def task_list(request):
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
    task = get_object_or_404(Task.objects.select_related('project', 'assigned_to'), pk=pk)
    return render(request, 'projects/task_detail.html', {'task': task})


@staff_required
def task_create(request, project_pk):
    project = get_object_or_404(Project, pk=project_pk)
    if request.method == 'POST':
        form = TaskForm(request.POST)
        if form.is_valid():
            task = form.save(commit=False)
            task.project = project
            task.save()
            messages.success(request, f'Task "{task.title}" added.')
            return redirect('projects:project_detail', pk=project.pk)
    else:
        form = TaskForm()
    return render(request, 'projects/task_form.html', {'form': form, 'project': project, 'action': 'Add'})


@staff_required
def task_update(request, pk):
    task = get_object_or_404(Task, pk=pk)
    if request.method == 'POST':
        form = TaskForm(request.POST, instance=task)
        if form.is_valid():
            form.save()
            messages.success(request, f'Task "{task.title}" updated.')
            return redirect('projects:project_detail', pk=task.project.pk)
    else:
        form = TaskForm(instance=task)
    return render(request, 'projects/task_form.html', {'form': form, 'task': task, 'project': task.project, 'action': 'Edit'})


@staff_required
@require_POST
def task_delete(request, pk):
    task = get_object_or_404(Task, pk=pk)
    project_pk = task.project.pk
    task.delete()
    messages.success(request, f'Task "{task.title}" deleted.')
    return redirect('projects:project_detail', pk=project_pk)
