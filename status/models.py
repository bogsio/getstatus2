from django.db import models


class SiteSettings(models.Model):
    """Singleton model for site-wide settings."""
    company_name = models.CharField(max_length=100, default="Your Company")
    company_url = models.URLField(blank=True, default="")
    logo = models.ImageField(upload_to='logo/', blank=True, null=True)

    class Meta:
        verbose_name = "Site Settings"
        verbose_name_plural = "Site Settings"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get_settings(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return "Site Settings"


class Service(models.Model):
    """A service/component to monitor."""
    STATUS_CHOICES = [
        ('operational', 'Operational'),
        ('degraded', 'Degraded Performance'),
        ('partial', 'Partial Outage'),
        ('major', 'Major Outage'),
        ('maintenance', 'Under Maintenance'),
    ]

    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='operational')
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'name']

    def __str__(self):
        return self.name


class Incident(models.Model):
    """An incident affecting one or more services."""
    STATUS_CHOICES = [
        ('investigating', 'Investigating'),
        ('identified', 'Identified'),
        ('monitoring', 'Monitoring'),
        ('resolved', 'Resolved'),
    ]

    IMPACT_CHOICES = [
        ('none', 'None'),
        ('minor', 'Minor'),
        ('major', 'Major'),
        ('critical', 'Critical'),
    ]

    title = models.CharField(max_length=200)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='investigating')
    impact = models.CharField(max_length=20, choices=IMPACT_CHOICES, default='minor')
    services = models.ManyToManyField(Service, related_name='incidents', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class IncidentUpdate(models.Model):
    """An update to an incident."""
    incident = models.ForeignKey(Incident, on_delete=models.CASCADE, related_name='updates')
    status = models.CharField(max_length=20, choices=Incident.STATUS_CHOICES)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.incident.title} - {self.status}"


class StatusHistory(models.Model):
    """Hourly status snapshots for services."""
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='status_history')
    status = models.CharField(max_length=20, choices=Service.STATUS_CHOICES)
    incident = models.ForeignKey(Incident, on_delete=models.SET_NULL, null=True, blank=True, related_name='status_history')
    recorded_at = models.DateTimeField()

    class Meta:
        ordering = ['-recorded_at']
        unique_together = ['service', 'recorded_at']

    def __str__(self):
        return f"{self.service.name} - {self.status} @ {self.recorded_at}"
