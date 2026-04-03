from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db import connection


@login_required
def portal_home(request):
    """Portal home - redirects based on user role."""
    return render(request, 'core/portal_home.html')


def health_check(_request):
    """
    Health check endpoint for load balancers and monitoring.
    Returns JSON with status of key services.
    """
    health_status = {
        'status': 'healthy',
        'database': False,
        'cache': False,
    }
    
    # Check database connection
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
        health_status['database'] = True
    except Exception:
        health_status['status'] = 'unhealthy'
    
    # Check cache/Redis connection
    try:
        from django.core.cache import cache
        cache.set('health_check', 'ok', 10)
        if cache.get('health_check') == 'ok':
            health_status['cache'] = True
    except Exception:
        pass  # Cache is optional, don't fail health check
    
    status_code = 200 if health_status['status'] == 'healthy' else 503
    return JsonResponse(health_status, status=status_code)
