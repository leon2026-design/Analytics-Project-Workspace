from app.app import create_app


def test_create_app_returns_dash_application():
    app = create_app()
    assert app.server is not None
