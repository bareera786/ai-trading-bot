"""Shared helpers for route blueprints."""
from __future__ import annotations

from typing import Union

from flask import Response, current_app


def add_no_cache_headers(response: Response) -> Response:
    """Apply standard anti-cache headers to the provided response."""
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0, private, no-transform'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


def marketing_analytics_context() -> dict[str, Union[str, bool]]:
    config = current_app.config if current_app else {}
    enabled = bool(config.get('ENABLE_MARKETING_ANALYTICS'))
    script_src = (config.get('MARKETING_ANALYTICS_SRC') or '').strip()
    if not enabled or not script_src:
        return {'enabled': False}

    context: dict[str, Union[str, bool]] = {
        'enabled': True,
        'script_src': script_src,
    }

    domain = (config.get('MARKETING_ANALYTICS_DOMAIN') or '').strip()
    if domain:
        context['domain'] = domain

    api_host = (config.get('MARKETING_ANALYTICS_API_HOST') or '').strip()
    if api_host:
        context['api_host'] = api_host

    return context
