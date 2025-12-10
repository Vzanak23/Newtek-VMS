from waitress import serve
from vms_web_server.wsgi import application

if __name__ == "__main__":
    serve(
        application,
        host="0.0.0.0",
        port=8000,
        threads=8,           # example extra config
        channel_timeout=60   # example extra config
    )
