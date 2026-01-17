import json
import os
import re
import time
from datetime import datetime, timedelta

from flask import render_template_string, request, jsonify, abort, session, Blueprint, send_file, render_template, redirect, url_for

from FlaskClass import csrf, app
from logging_utility import logger
from utility import get_settings, is_valid_json, get_product_by_id, sanitize_path, get_products, convert_markdown_to_html, get_coupons, get_coupon_by_id, generate_calendar, get_events, query_events, add_product, add_coupon, get_contact_requests, get_contact_by_id, get_event_by_id, get_orders, get_order_by_id

admin_blueprint = Blueprint("admin", __name__, url_prefix="/admin")

#===========================
# Authentication Functions
#===========================

# This function checks if the user is logged in before processing any request
@admin_blueprint.before_request
def check_login():
    if ("login" not in session) and (not request.base_url.endswith("login")):
        logger.warning("User not logged in, redirecting to login page")
        return redirect(url_for("admin.login"))

# This function handles the login process
@admin_blueprint.route("/login", methods=["GET", "POST"])
def login():
    logger.info("Login route accessed")
    if request.method == "GET":
        logger.info("Rendering login page")
        return render_template("admin/login.jinja-html")

    admin_password: dict = get_settings("admin-password")
    logger.debug(f"Admin password retrieved: {admin_password}")

    if request.form.get("password") != admin_password:
        error = "Passwort ungültig!"
        logger.warning("Invalid password attempt")
        return render_template("admin/login.jinja-html", error=error)

    session.permanent = True
    session["login"] = True
    session.modified = True
    logger.info("User logged in successfully")
    return redirect(url_for("admin.dashboard"))

# This function handles the logout process
@admin_blueprint.route("/logout", methods=["GET"])
def logout():
    logger.info("Logout route accessed")
    session.pop("login")
    logger.info("User logged out successfully")
    return redirect(url_for("home"))

#===========================
# Dashboard Functions
#===========================

# This function renders the admin dashboard
@admin_blueprint.route("/", methods=["GET"])
def dashboard():
    logger.info("Dashboard route accessed")
    today = datetime.today()
    events: list[dict] = query_events(year=today.year, month=today.month)

    month = int(request.args.get("month", today.month))
    year = int(request.args.get("year", today.year))

    calendar = generate_calendar(year, month)

    logger.debug(f"Rendering dashboard with calendar for {month}/{year}")
    return render_template("admin/admin.jinja-html", calendar=calendar, today=today, month=month, year=year, events=events)

#===========================
# Product Management Functions
#===========================

# This function renders the page with all products
@admin_blueprint.route("/produkte/alle", methods=["GET"])
def products():
    logger.info("Products route accessed")
    products: list[dict] = get_products()
    logger.debug(f"Retrieved {len(products)} products")
    return render_template("admin/all-products.jinja-html", products=products)

# This function handles viewing and editing a specific product
@admin_blueprint.route("/produkt/<string:product_id>", methods=["GET", "POST"])
def product(product_id: int):
    logger.info(f"Product route accessed for product ID: {product_id}")
    product: dict = get_product_by_id(product_id)
    if request.method == "GET":
        logger.info(f"GET request received for product with ID: {product_id}")
        if product is None:
            logger.warning(f"Product with ID {product_id} not found.")
        logger.info(f"Product retrieved: {product}")
        return render_template("admin/edit-product.jinja-html", product=product)

    thumbnail = request.files.get("thumbnail")
    if thumbnail:
        thumbnail_filename = sanitize_path(thumbnail.filename)
        thumbnail_path = os.path.join("uploads", "products", str(product_id), thumbnail_filename)
        thumbnail.save(thumbnail_path)
        thumbnail_url = f"products/{product_id}/{thumbnail_filename}"
    else:
        thumbnail_url = product.get("thumbnail", "")

    product_data = {
        "id": str(product_id),
        "name": request.form.get("name", ""),
        "price": float(request.form.get("price", 0)),
        "thumbnail": thumbnail_url,
        "amount": int(request.form.get("amount", 0)),
        "images": request.form.getlist("images[]"),
        "featured": "featured" in request.form,
        "new_price": float(0 if request.form.get("new_price", 0) == "" else request.form.get("new_price", 0)),
        "raw_description": request.form.get("content", ""),
        "description": convert_markdown_to_html(request.form.get("content", "")),
        "categories": request.form.getlist("categories"),
        "tax": float(request.form.get("tax", 0)),
        "availability": "Auf Lager", 
        "keyword": request.form.get("keyword", "") 
    }

    products: list[dict] = get_products()
    for prod in products:
        if prod.get("id") == str(product_id):
            prod.update(product_data)
            break

    with open("data/products.json", "w", encoding="utf-8") as f:
        json.dump(products, f, indent=4, ensure_ascii=False)
    
    get_product_by_id.cache_clear()
    logger.info(f"Product with ID {product_id} updated successfully")
    return redirect(url_for("admin.products"))

# This function handles creating a new product
@admin_blueprint.route("/produkte/erstellen/", methods=["GET", "POST"])
def create_product():
    logger.info("Create product route accessed")
    if request.method == "GET":
        logger.info("Rendering create product page")
        return render_template("admin/add-product.jinja-html")

    product_id: str = request.form.get("id", None)
    if product_id is None:
        session["error"] = "Produkt-ID fehlt!"
        session.modified = True
        logger.warning("Product ID missing")
        return render_template("admin/add-product.jinja-html")

    if get_product_by_id(product_id):
        session["error"] = "Produkt mit dieser ID existiert bereits!"
        session.modified = True
        logger.warning(f"Product with ID {product_id} already exists")
        return render_template("admin/add-product.jinja-html")

    thumbnail = request.files.get("thumbnail")
    if thumbnail:
        thumbnail_filename = sanitize_path(thumbnail.filename)
        thumbnail_path = os.path.join("uploads", "products", str(product_id))
        os.mkdir(thumbnail_path)
        thumbnail.save(os.path.join(thumbnail_path, thumbnail_filename))
        thumbnail_url = f"products/{product_id}/{thumbnail_filename}"

    product_data = {
        "id": str(product_id),
        "name": request.form.get("name", ""),
        "price": float(request.form.get("price", 0)),
        "thumbnail": thumbnail_url,
        "amount": int(request.form.get("amount", 0)),
        "images": request.form.getlist("images"),
        "featured": "featured" in request.form,
        "new_price": float(0 if request.form.get("new_price", 0) == "" else request.form.get("new_price", 0)),
        "raw_description": request.form.get("content", ""),
        "description": convert_markdown_to_html(request.form.get("content", "")),
        "categories": request.form.getlist("categories"),
        "tax": float(request.form.get("tax", 0)),
        "availability": "Auf Lager", 
        "keyword": request.form.get("keyword", "") 
    }

    try:
        add_product(product_data)
        logger.info(f"Product with ID {product_id} created successfully")
    except Exception as e:
        logger.error(f"Failed to add product | Error: {str(e)}")
        abort(500)  # Internal Server Error

    return redirect(url_for("admin.products"))

#===========================
# Category Management Functions
#===========================

# This function handles viewing and updating product categories
@admin_blueprint.route("/produkte/kategorien", methods=["GET", "POST"])
def categories():
    logger.info("Categories route accessed")
    if request.method == "GET":
        categories: list[str] = get_settings("categories")
        logger.debug(f"Retrieved categories: {categories}")
        return render_template("admin/categories.jinja-html", categories=categories)

    categories: list = request.form.getlist("category")
    settings: dict = get_settings()
    settings["categories"] = categories

    get_settings.cache_clear()
    with open("data/settings.json", "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=4, ensure_ascii=False)
    
    logger.info("Categories updated successfully")
    return redirect(url_for("admin.categories"))

#===========================
# Media Management Functions
#===========================

# This function renders the media library
@admin_blueprint.route("/medien/alle", methods=["GET"])
def library():
    logger.info("Media library route accessed")
    return render_template("admin/media-library.jinja-html")

#===========================
# Coupon Management Functions
#===========================

# This function renders the page with all coupons
@admin_blueprint.route("/coupons/alle", methods=["GET"])
def coupons():
    logger.info("Coupons route accessed")
    coupons: list[dict] = get_coupons()
    logger.debug(f"Retrieved {len(coupons)} coupons")
    return render_template("admin/all-coupons.jinja-html", coupons=coupons)

# This function handles viewing and editing a specific coupon
@admin_blueprint.route("/coupon/<string:coupon_id>", methods=["GET", "POST"])
def coupon(coupon_id: int):
    logger.info(f"Coupon route accessed for coupon ID: {coupon_id}")
    coupon: dict = get_coupon_by_id(coupon_id)
    if request.method == "GET":
        logger.info(f"GET request received for coupon with ID: {coupon_id}")
        if coupon is None:
            logger.warning(f"Coupon with ID {coupon_id} not found.")
        logger.info(f"Coupon retrieved: {coupon}")
        return render_template("admin/edit-coupon.jinja-html", coupon=coupon)

    coupon_data = {
        "id": str(coupon_id),
        "type": request.form.get("type", ""),
        "value": float(request.form.get("value", 0)),
        "uses_remaining": (
            None if "uses_remaining" in request.form 
            else int(request.form.get("uses_remaining", 0)) or None
        ),
        "valid_till": (
            None if "unlimited_validity" in request.form 
            else str(request.form.get("valid_till", "")) or None
        )
    }

    coupons: list[dict] = get_coupons()
    for coup in coupons:
        if coup.get("id") == str(coupon_id):
            coup.update(coupon_data)
            break

    with open("data/coupons.json", "w", encoding="utf-8") as f:
        json.dump(coupons, f, indent=4, ensure_ascii=False)
    
    get_coupon_by_id.cache_clear()
    logger.info(f"Coupon with ID {coupon_id} updated successfully")
    return redirect(url_for("admin.coupons"))

# This function handles creating a new coupon
@admin_blueprint.route("/coupons/erstellen", methods=["GET", "POST"])
def create_coupon():
    logger.info("Create coupon route accessed")
    if request.method == "GET":
        logger.info("Rendering create coupon page")
        return render_template("admin/add-coupon.jinja-html")

    coupon_id: str = request.form.get("id", None)
    if coupon_id is None:
        session["error"] = "Coupon-ID fehlt!"
        session.modified = True
        logger.warning("Coupon ID missing")
        return render_template("admin/add-coupon.jinja-html")

    if get_coupon_by_id(coupon_id):
        session["error"] = "Coupon mit dieser ID existiert bereits!"
        session.modified = True
        logger.warning(f"Coupon with ID {coupon_id} already exists")
        return render_template("admin/add-coupon.jinja-html")

    coupon_data = {
        "id": str(coupon_id),
        "type": request.form.get("type", ""),
        "value": float(request.form.get("value", 0)),
        "uses_remaining": (
            None if "uses_remaining" in request.form 
            else int(request.form.get("uses_remaining", 0)) or None
        ),
        "valid_till": (
            None if "unlimited_validity" in request.form 
            else str(request.form.get("valid_till", "")) or None
        )
    }

    try:
        add_coupon(coupon_data)
        logger.info(f"Coupon with ID {coupon_id} created successfully")
    except Exception as e:
        logger.error(f"Failed to add coupon | Error: {str(e)}")
        abort(500)  # Internal Server Error

    return redirect(url_for("admin.coupons"))


#===========================
# Contact & Orders Functions
#===========================
@admin_blueprint.route("/anfragen/kontakt", methods=["GET"])
def contact_requests():
    logger.info("Contact requests route accessed")
    requests: list[dict] = get_contact_requests()
    logger.debug(f"Retrieved {len(requests)} contact requests")
    return render_template("admin/contact-requests.jinja-html", requests=requests)

@admin_blueprint.route('/kontakt/<string:id>', methods=['GET', 'POST'])
def view_contact_request(id):
    contact = get_contact_by_id(id)
    if not contact:
        return "Contact request not found", 404

    if request.method == 'POST':
        contact['status'] = request.form['status']
        contact['notiz'] = request.form['notiz']
        
        contacts = get_contact_requests()
        for item in contacts:
            if item['id'] == id:
                item.update(contact)
                break

        with open("data/contact.json", "w", encoding="utf-8") as f:
            json.dump(contacts, f, indent=4, ensure_ascii=False)
        
        get_contact_by_id.cache_clear()
        return redirect(url_for('admin.view_contact_request', id=id))

    return render_template('admin/edit-contact-request.jinja-html', contact=contact)

@admin_blueprint.route('/bestellung/<string:id>', methods=['GET', 'POST'])
def view_order(id):
    order = get_order_by_id(id)
    if not order:
        return "Order not found", 404

    if request.method == 'POST':
        order['status'] = request.form['status']
        order['notiz'] = request.form['notiz']
        
        orders = get_orders()
        for item in orders:
            if item['id'] == id:
                item.update(order)
                break

        with open("data/orders.json", "w", encoding="utf-8") as f:
            json.dump(orders, f, indent=4, ensure_ascii=False)
        
        get_order_by_id.cache_clear()
        return redirect(url_for('admin.view_order', id=id))

    return render_template('admin/edit-order.jinja-html', order=order)

@admin_blueprint.route("/anfragen/bestellungen", methods=["GET"])
def orders():
    logger.info("Orders route accessed")
    orders: list[dict] = get_orders()
    logger.debug(f"Retrieved {len(orders)} orders")
    return render_template("admin/orders.jinja-html", orders=orders)

#===========================
# Appearance Settings Functions
#===========================

# This function handles viewing and updating general appearance settings
@admin_blueprint.route("/aussehen/allgemein", methods=["GET", "POST"])
@csrf.exempt
def general_appearance():
    if request.method == "POST":
        logger.info("General appearance settings updated")

        with open("static/css/root.css", "r") as file:
            css_content = file.read()

        for key, value in request.form.items():
            pattern = rf"--{key}:\s*[^;]+;"
            
            replacement = f"--{key}: {value};"
            if re.search(pattern, css_content):
                css_content = re.sub(pattern, replacement, css_content)
            else:
                css_content += f"\n{replacement}"

        with open("static/css/root.css", "w") as file:
            file.write(css_content)

        return redirect(url_for("admin.general_appearance"))
    
    logger.info("General appearance route accessed")
    with open("static/css/root.css") as file:
        content: str = file.read()
    
    root_styles = {}
    root_regex = r"--([a-zA-Z0-9-]+)\s*:\s*([^;]+);"
    matches = re.findall(root_regex, content)
    for match in matches:
        root_styles[f"{str(match[0])}"] = str(match[1]).strip()

    logger.debug("Rendering general appearance settings page")
    return render_template("admin/appearance.jinja-html", styles=root_styles)

@admin_blueprint.route("/aussehen/templates", methods=["GET", "POST"])
def template_appearance():
    logger.info("Edit Templates route accessed")
    return render_template("admin/edit-templates.jinja-html")

@admin_blueprint.route("/aussehen/templates/bearbeiten/<path:template>", methods=["GET", "POST"])
def template_appearance_edit(template):
    logger.info("Edit Templates route accessed")
    template_path = os.path.join(app.root_path, "templates", f"{template}")
    
    if request.method == "POST":
        new_content = request.form.get("template_content", "")
        with open(template_path, "w", encoding="utf-8") as file:
            file.write(new_content)

            template = app.jinja_env.get_template(sanitize_path(template))
            template.environment.cache.clear()
        logger.info("Template file saved successfully")
        return redirect(url_for("admin.template_appearance_edit", template=template))
    
    with open(template_path, "r", encoding="utf-8") as file:
        template_content = str(file.read())
    
    # Escape the template content to prevent breaking the page
    template_content = template_content.replace("<", "&lt;").replace(">", "&gt;")
    
    return render_template("admin/edit-template.jinja-html", template_content=template_content)

@admin_blueprint.route("/aussehen/static", methods=["GET", "POST"])
def change_static_files():
    logger.info("Edit Static route accessed")
    return render_template("admin/edit-static.jinja-html")

@admin_blueprint.route("/aussehen/static/bearbeiten/<path:file>", methods=["GET", "POST"])
def change_static_files_edit(file):
    logger.info("Edit Templates route accessed")
    file_path = os.path.join(app.root_path, "static", f"{file}")
    
    if request.method == "POST":
        new_content = request.form.get("template_content", "")
        with open(file_path, "w", encoding="utf-8") as file:
            file.write(new_content)

        logger.info("Static file saved successfully")
        return redirect(url_for("admin.template_appearance_edit", template=file))
    
    with open(file_path, "r", encoding="utf-8") as file:
        file_content = str(file.read())
    
    file_content = file_content.replace("<", "&lt;").replace(">", "&gt;")
    
    return render_template("admin/edit-template.jinja-html", template_content=file_content)

#===========================
# General Settings Functions
#===========================

# This function handles viewing and updating general settings
@admin_blueprint.route("/einstellungen/allgemein", methods=["GET", "POST"])
def general_settings():
    logger.info("General settings route accessed")
    settings: dict = get_settings()
    if request.method == "GET":
        logger.debug("Rendering general settings page")
        return render_template("admin/general-settings.jinja-html", settings=settings)

    settings_data = {
        "url": request.form.get("url", ""),
        "format": request.form.get("zahlenformat", ""),
        "admin-password": request.form.get("admin_password", "")
    }

    settings_import = request.files.get("settings_import")
    product_import = request.files.get("product_import")
    coupon_import = request.files.get("coupon_import")
    events_import = request.files.get("events_import")
    contacts_import = request.files.get("contacts_import")

    if product_import:
        if is_valid_json(product_import.stream):
            product_import.save("data/products.json")
            get_product_by_id.cache_clear()
            get_products.cache_clear()

    if coupon_import:
        if is_valid_json(coupon_import.stream):
            coupon_import.save("data/coupons.json")
            get_coupon_by_id.cache_clear()
            get_coupons.cache_clear()
    
    if events_import:
        if is_valid_json(events_import.stream):
            contacts_import.save("data/events.json")
            get_events.cache_clear()
            get_event_by_id.cache_clear()

    if contacts_import:
        if is_valid_json(contacts_import.stream):
            contacts_import.save("data/contacts.json")
            get_contact_requests.cache_clear()
            get_contact_by_id.cache_clear()

    if settings_import:
        if is_valid_json(settings_import.stream):
            settings_import.save("data/settings.json")
    else:
        settings.update(settings_data)

        with open("data/settings.json", "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=4, ensure_ascii=False)
            
        app._format = settings.get("format", "#.##0,00")

    get_settings.cache_clear()

    logger.info("General settings updated successfully")
    return redirect(url_for("admin.general_settings"))

#===========================
# Server Settings Functions
#===========================

# This function handles viewing and updating server settings
@admin_blueprint.route("/einstellungen/server", methods=["GET", "POST"])
def server_settings():
    logger.info("Server settings route accessed")
    settings: dict = get_settings()
    with open("robots.txt", "r") as file:
        robots: str = file.read()

    if request.method == "GET":
        logger.debug("Rendering server settings page")
        return render_template("admin/server-settings.jinja-html", settings=settings, robots=robots)

    config_data = {
        "MAX_CONTENT_LENGTH": int(request.form.get("max_content_length", 0)),
        "PERMANENT_SESSION_LIFETIME": int(request.form.get("permanent_session_lifetime", 0)),
        "SESSION_COOKIE_NAME": request.form.get("session_cookie_name", ""),
        "maintenance": "maintenance" in request.form
    }

    with open("robots.txt", "w") as file:
        file.write(request.form.get("robots_txt", "").replace("\r", ""))

    settings["server_config"].update(config_data)    

    with open("data/settings.json", "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=4, ensure_ascii=False)

    app.update_config(config_data)
    app.maintenance = config_data.get("maintenance", False)
    
    get_settings.cache_clear()
    logger.info("Server settings updated successfully")
    return redirect(url_for("admin.server_settings"))

#===========================
# Log Viewing Functions
#===========================

# This function renders the server logs
@admin_blueprint.route("/einstellungen/logs", methods=["GET"])
def server_logs():
    logger.info("Server logs route accessed")
    with open("logs/app.log", "r", encoding="utf-8") as file:
        lines = file.readlines()
    
    clean_lines = lines[-50::-1]
    logger.info("Rendering server logs page")
    return render_template("admin/see-logs.jinja-html", logs=clean_lines)




