# Entry point for the web app (minimal stub)

def create_app():
    """Return a very small WSGI-like app function for testing."""
    def app():
        return "Columbus Traffic Predictor App"
    return app

if __name__ == "__main__":
    print(create_app()())
