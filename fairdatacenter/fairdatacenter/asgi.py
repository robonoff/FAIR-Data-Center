"""
ASGI config for fairdatacenter project.
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fairdatacenter.settings')

application = get_asgi_application()
