import os
import threading
import requests
from datetime import datetime
import time

from dotenv import load_dotenv
from flask import render_template, url_for, make_response, request, jsonify, session, send_from_directory, Response
from flask_wtf.csrf import generate_csrf, CSRFError
from waitress import serve

from FlaskClass import app
from logging_utility import logger
from routes import blueprints
from utility import query_products, get_settings, format_number

load_dotenv()
logger.debug("Environment variables have been loaded successfully.")

# Registering blueprints and logging
for route in blueprints:
    app.register_blueprint(route)
    logger.debug(f"Registered blueprint: {route.name}")


@app.template_filter("custom_format")
def custom_format(value):
    if isinstance(value, (int, float)):
        return format_number(value, app._format)
    return value

@app.before_request
def request_handler():
    request.query_params = dict(request.args)
    if app.maintenance and not request.path.startswith("/admin") and not request.path.startswith("/static") and not request.path.startswith("/uploads") and not session.get("login"):
        logger.warning("Maintenance mode is enabled.")
        response = Response(render_template("maintenance.jinja-html"), status=503)
        response.headers["Retry-After"] = "3600"  # Optional: Retry after 1 hour
        return response

@app.context_processor
def utility_processor():
    methods: dict = {
        "query_params": request.query_params, 
        "session": session,
        "query_products": query_products, 
        "get_settings": get_settings, 
        "generate_token": generate_csrf
    }
    return methods

@app.route("/")
def home():
    logger.info("Home page accessed.")
    return render_template('index.jinja-html')

@app.route('/sitemap.xml')
def sitemap():
    logger.info("Sitemap requested.")
    pages = []
    lastmod = datetime.now().date().isoformat()
    for rule in app.url_map.iter_rules():
        if rule.rule.startswith('/admin') or rule.rule.startswith('/api'):
            continue
        if "GET" in rule.methods and "filename" not in rule.arguments:
            if len(rule.arguments) == 0:
                url = url_for(rule.endpoint)
            else:
                url = rule.empty()
            pages.append({"loc": url, "lastmod": lastmod})
    
    response = make_response(render_template('sitemap.xml', pages=pages))
    response.headers["Content-Type"] = "application/xml"
    logger.info("Sitemap generated with %d pages.", len(pages))
    return response

@app.route("/robots.txt")
def robots():
    return send_from_directory("./", "robots.txt")


@app.errorhandler(405)
def method_not_allowed(error):
    logger.warning(f"405 Method Not Allowed: {request.path}; {error}")
    return jsonify({"error": str(error), "code": 405})

@app.errorhandler(404)
def page_not_found(error):
    logger.warning(f"A page was not found: {request.path}; {error}")
    return render_template("404.jinja-html")

@app.errorhandler(403)
def access_denied(error):
    logger.warning(f"403 Access Denied: {request.path}; {error}")
    return render_template("403.jinja-html")

@app.errorhandler(CSRFError)
def handle_csrf_error(e):
    if 'missing' in str(e):
        logger.warning("CSRF token is missing.")
        response = jsonify({'error': 'Missing CSRF token'})
        response.status_code = 400
    else:
        logger.warning("Invalid CSRF token.")
        response = jsonify({'error': 'Invalid CSRF token'})
        response.status_code = 403
    
    return response

@app.errorhandler(Exception)
def handle_general_errors(e):
    logger.critical(f"An unexpected error occurred: {str(e)}", exc_info=True)

def stay_alive():
    def send_request(server_url):
        while True:
            try:
                response = requests.get(f"{server_url}/")
                logger.info(f"Stay alive request sent. Status code: {response.status_code}")
            except Exception as e:
                logger.error(f"Error in stay alive request: {str(e)}")
            time.sleep(100)  # Sleep for  100 seconds

    server_url = "https://birdie-club.onrender.com"
    thread = threading.Thread(target=send_request, args=(server_url,))
    thread.daemon = True
    thread.start()

if __name__ == '__main__':
    os.chdir(os.path.dirname(__file__))
    logger.info("*" * 50)
    logger.info("Application Server started!")
    stay_alive()
    serve(app, port=8080, threads=64, url_scheme="https")
    #app.run(host="localhost", port=8080, debug=True)


