from app.app import create_app

def test_app_callable():
    app = create_app()
    assert callable(app)
    assert app() == "Columbus Traffic Predictor App"
