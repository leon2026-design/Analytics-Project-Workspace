"""Run the traffic prediction dashboard."""

from app.app import create_app


def main():
    app = create_app()
    app.run(debug=True, host="127.0.0.1", port=8050)


if __name__ == "__main__":
    main()
