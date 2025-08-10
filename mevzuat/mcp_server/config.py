"""Configuration helpers for the MCP server."""

from __future__ import annotations

import os

import django


# Ensure Django is configured before accessing models
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mevzuat.settings")
if not django.apps.apps.ready:
    django.setup()
