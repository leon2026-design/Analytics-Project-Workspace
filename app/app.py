"""Application factory for the Dash dashboard."""

from .dash_app import app as dash_app


def create_app():
    """Return the configured Dash application."""
    return dash_app
