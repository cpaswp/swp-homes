"""Cloudflare Python Workers entrypoint for SWP-HOMES Django WSGI app."""
import os

from django.core.wsgi import get_wsgi_application
from workers import wsgi

# Root-level Django packages (config, core, accounting, leasing) are siblings
# of this entrypoint and therefore available in the Worker module tree.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

application = get_wsgi_application()
Default = wsgi.entrypoint(application)
