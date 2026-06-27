import serverless_wsgi
from app import app

# serverless_wsgi translates API Gateway events into WSGI requests so Flask
# runs unmodified inside Lambda — no Lambda-specific code needed in app.py.
def handler(event, context):
    return serverless_wsgi.handle_request(app, event, context)
