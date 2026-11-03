"""Cloudflare Python Workers entrypoint for the SWP-HOMES Django WSGI app."""
import os

from django.core.wsgi import get_wsgi_application
from workers import wsgi

# Cloudflare Worker secrets/vars must be configured in the Worker environment.
# Keep Django's standard settings module so local Django workflows remain intact.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

application = get_wsgi_application()
Default = wsgi.entrypoint(application)
