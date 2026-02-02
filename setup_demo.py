#!/usr/bin/env python
"""Setup demo data for the status page."""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from status.models import SiteSettings, Service

# Create site settings
settings = SiteSettings.get_settings()
settings.company_name = "Acme Inc"
settings.save()
print(f"Created site settings: {settings.company_name}")

# Create sample services
services_data = [
    ("Website", "Main website and landing pages", "operational", 1),
    ("API", "REST API endpoints", "operational", 2),
    ("Database", "Primary database cluster", "operational", 3),
    ("Email", "Transactional email service", "operational", 4),
    ("CDN", "Content delivery network", "operational", 5),
]

for name, desc, status, order in services_data:
    service, created = Service.objects.get_or_create(
        name=name,
        defaults={"description": desc, "status": status, "order": order}
    )
    if created:
        print(f"Created service: {name}")
    else:
        print(f"Service already exists: {name}")

print("\nDemo data setup complete!")
print("Visit http://localhost:8000 to see the status page")
print("Visit http://localhost:8000/admin to manage (admin/admin)")
