from django.http import JsonResponse
from django.views.decorators.http import require_GET


@require_GET
def healthz(request):
    """
    Liveness check for uptime monitoring: answers as long as the app is running.
    It deliberately doesn't touch the database, so monitoring it every few minutes
    doesn't keep the (free, auto-suspending) Postgres database awake.
    """
    response = JsonResponse({'status': 'ok'})
    response['Cache-Control'] = 'no-store'
    return response
