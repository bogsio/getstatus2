from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta
from django.db.models import Q

from .models import SiteSettings, Service, Incident, IncidentUpdate
from .forms import IncidentForm, IncidentUpdateForm, ServiceStatusForm


# Map incident impact to service status color
IMPACT_TO_STATUS = {
    'none': 'operational',
    'minor': 'degraded',
    'major': 'partial',
    'critical': 'major',
}


def get_service_history(service, hours=24):
    """Get hourly status history for a service based on incidents."""
    now = timezone.now().replace(minute=0, second=0, microsecond=0)
    start_time = now - timedelta(hours=hours-1)  # -1 to include current hour
    history = []

    # Get incidents affecting this service in the time range
    incidents = Incident.objects.filter(
        services=service,
        created_at__lte=timezone.now()  # Use actual now for active incidents
    ).filter(
        Q(resolved_at__isnull=True) | Q(resolved_at__gte=start_time)
    )

    # Build incident lookup by hour (higher impact takes precedence)
    incident_by_hour = {}
    impact_priority = {'critical': 4, 'major': 3, 'minor': 2, 'none': 1}

    for incident in incidents:
        incident_start = incident.created_at.replace(minute=0, second=0, microsecond=0)
        incident_end = incident.resolved_at.replace(minute=0, second=0, microsecond=0) if incident.resolved_at else now

        current = incident_start
        while current <= incident_end:
            if start_time <= current <= now:
                current_priority = impact_priority.get(incident.impact, 0)
                existing = incident_by_hour.get(current)
                existing_priority = impact_priority.get(existing['impact'], 0) if existing else 0

                if current_priority > existing_priority:
                    incident_by_hour[current] = {
                        'title': incident.title,
                        'impact': incident.impact,
                        'status': IMPACT_TO_STATUS.get(incident.impact, 'degraded'),
                    }
            current += timedelta(hours=1)

    # Build the 24-hour timeline (including current hour)
    for i in range(hours-1, -1, -1):  # from 23 hours ago to now (hour 0)
        hour = now - timedelta(hours=i)
        incident_data = incident_by_hour.get(hour)

        if incident_data:
            history.append({
                'hour': hour,
                'status': incident_data['status'],
                'incident': incident_data['title'],
            })
        else:
            history.append({
                'hour': hour,
                'status': 'operational',
                'incident': '',
            })

    return history


def index(request):
    settings = SiteSettings.get_settings()
    services = Service.objects.all()

    # Add history to each service
    services_with_history = []
    for service in services:
        services_with_history.append({
            'service': service,
            'history': get_service_history(service),
        })

    # Active incidents (not resolved)
    active_incidents = Incident.objects.exclude(status='resolved').prefetch_related('updates', 'services')

    # All resolved incidents (ordered by most recent first)
    resolved_incidents = Incident.objects.filter(
        status='resolved'
    ).order_by('-resolved_at').prefetch_related('updates', 'services')

    # Calculate overall status
    if services.filter(status='major').exists():
        overall_status = 'major'
        overall_message = 'Major System Outage'
    elif services.filter(status='partial').exists():
        overall_status = 'partial'
        overall_message = 'Partial System Outage'
    elif services.filter(status='degraded').exists():
        overall_status = 'degraded'
        overall_message = 'Degraded Performance'
    elif services.filter(status='maintenance').exists():
        overall_status = 'maintenance'
        overall_message = 'Scheduled Maintenance'
    else:
        overall_status = 'operational'
        overall_message = 'All Systems Operational'

    context = {
        'settings': settings,
        'services': services_with_history,
        'active_incidents': active_incidents,
        'resolved_incidents': resolved_incidents,
        'overall_status': overall_status,
        'overall_message': overall_message,
    }
    return render(request, 'status/index.html', context)


# Dashboard views

def dashboard_login(request):
    if request.user.is_authenticated:
        return redirect('status:dashboard')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect('status:dashboard')
        else:
            messages.error(request, 'Invalid username or password.')

    return render(request, 'status/dashboard/login.html')


def dashboard_logout(request):
    logout(request)
    return redirect('status:dashboard_login')


@login_required(login_url='status:dashboard_login')
def dashboard(request):
    settings = SiteSettings.get_settings()
    services = Service.objects.all()
    active_incidents = Incident.objects.exclude(status='resolved').prefetch_related('updates', 'services')
    recent_incidents = Incident.objects.filter(status='resolved').order_by('-resolved_at')[:5]

    context = {
        'settings': settings,
        'services': services,
        'active_incidents': active_incidents,
        'recent_incidents': recent_incidents,
    }
    return render(request, 'status/dashboard/index.html', context)


@login_required(login_url='status:dashboard_login')
def dashboard_incident_create(request):
    if request.method == 'POST':
        form = IncidentForm(request.POST)
        if form.is_valid():
            incident = form.save()

            # Create initial update
            IncidentUpdate.objects.create(
                incident=incident,
                status=incident.status,
                message=f"Incident created: {incident.title}"
            )

            # Update service statuses based on impact
            impact_to_status = {
                'none': 'operational',
                'minor': 'degraded',
                'major': 'partial',
                'critical': 'major',
            }
            new_status = impact_to_status.get(incident.impact, 'degraded')
            for service in incident.services.all():
                service.status = new_status
                service.save()

            messages.success(request, f'Incident "{incident.title}" created successfully.')
            return redirect('status:dashboard')
    else:
        form = IncidentForm()

    return render(request, 'status/dashboard/incident_form.html', {
        'form': form,
        'title': 'Create Incident',
        'submit_text': 'Create Incident',
    })


@login_required(login_url='status:dashboard_login')
def dashboard_incident_detail(request, pk):
    incident = get_object_or_404(Incident, pk=pk)
    update_form = IncidentUpdateForm()

    if request.method == 'POST':
        update_form = IncidentUpdateForm(request.POST)
        if update_form.is_valid():
            update = update_form.save(commit=False)
            update.incident = incident
            update.save()

            # Update incident status
            incident.status = update.status
            if update.status == 'resolved':
                incident.resolved_at = timezone.now()
                # Reset affected services to operational
                for service in incident.services.all():
                    service.status = 'operational'
                    service.save()
            incident.save()

            messages.success(request, 'Incident updated successfully.')
            return redirect('status:dashboard_incident_detail', pk=pk)

    context = {
        'incident': incident,
        'update_form': update_form,
    }
    return render(request, 'status/dashboard/incident_detail.html', context)


@login_required(login_url='status:dashboard_login')
def dashboard_service_status(request, pk):
    service = get_object_or_404(Service, pk=pk)

    if request.method == 'POST':
        form = ServiceStatusForm(request.POST, instance=service)
        if form.is_valid():
            form.save()
            messages.success(request, f'Status for "{service.name}" updated.')
            return redirect('status:dashboard')

    return redirect('status:dashboard')
