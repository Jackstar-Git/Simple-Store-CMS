import base64
import io
import os
import shutil
import time
import zipfile
from datetime import date, datetime

import psutil
from flask import request, jsonify, abort, session, Blueprint, send_file, url_for, redirect, make_response
from flask_wtf.csrf import validate_csrf

from FlaskClass import app, csrf
from logging_utility import logger
from utility import sanitize_path, generate_captcha, convert_markdown_to_html, query_events, create_invoice_pdf, get_product_by_id, get_settings, get_coupon_by_id, get_products, get_coupons, get_events, add_contact_request, add_event, get_order_by_id, delete_product_json, delete_coupon_json, delete_order_json, delete_event_json

internal_blueprint = Blueprint("internal", __name__, template_folder="./templates")

# =====================================
# File Handling Routes
# =====================================

# This function serves files from the uploads directory
@internal_blueprint.route("/uploads/<path:filename>", methods=["GET"])
def uploads(filename):
    logger.info(f"GET request received for serving file from uploads | Filename: {filename}")
    try:
        return send_file(os.path.join(app.root_path, "uploads", filename))
    except Exception as e:
        logger.error(f"Error serving file from uploads | Filename: {filename} | Error: {str(e)}")
        abort(404)  # Not found

# This function serves files from the plugins directory
@internal_blueprint.route("/plugins/<path:filename>", methods=["GET"])
def plugins(filename):
    logger.info(f"GET request received for serving file from plugins | Filename: {filename}")
    try:
        return send_file(os.path.join(app.root_path, "plugins", filename))
    except Exception as e:
        logger.error(f"Error serving file from plugins | Filename: {filename} | Error: {str(e)}")
        abort(404)  # Not found

# This function handles file and directory downloads
@internal_blueprint.route("/download/<path:filepath>", methods=["GET"])
def download(filepath):
    logger.info(f"GET request received for download | Path: {filepath}")
    if not session.get("login", False):
        logger.warning("Unauthorized download attempt")
        return abort(403)

    if not os.path.exists(filepath):
        logger.error(f"File or directory not found | Path: {filepath}")
        abort(404, description="File or directory not found.")

    if os.path.isfile(filepath):
        logger.info(f"Serving file | Path: {filepath}")
        return send_file(filepath, as_attachment=True)

    elif os.path.isdir(filepath):
        logger.info(f"Creating zip for directory | Path: {filepath}")
        memory_file = io.BytesIO()
        with zipfile.ZipFile(memory_file, "w", zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(filepath):
                for file in files:
                    file_path = os.path.join(root, file)
                    zipf.write(file_path, os.path.relpath(file_path, filepath))
        
        memory_file.seek(0)
        zip_filename = os.path.basename(filepath) + ".zip"
        return send_file(memory_file, as_attachment=True, download_name=zip_filename, mimetype="application/zip")

    else:
        logger.error(f"Invalid path provided | Path: {filepath}")
        abort(400, description="Invalid path provided.")

# =====================================
# API Routes
# =====================================

#===========================
# Contact API Routes
#===========================

# This function handles contact requests
@internal_blueprint.route("/api/send-contact-request", methods=["POST"])
def send_contact_request():
    logger.info("POST request received for sending contact request")
    email = request.form["email"]
    name = request.form["name"]
    subject = request.form["subject"]
    message = request.form["message"]
    captcha_test = request.form["captcha-text"]

    if captcha_test != session.get("captcha"):
        session["error"] = "Ungültiges Captcha!"
        session.modified = True
        logger.warning("Invalid captcha attempt")
        return redirect("/#contact-section")

    logger.info(f"Received contact request | Name: {name} | Email: {email} | Subject: {subject}")
    today = date.today().strftime("%d.%m.%Y")

    contact_entry = {
        "id": str(int(time.time())),  # Generate ID based on current timestamp
        "email": email,
        "name": name,
        "subject": subject,
        "message": message,
        "date": today
    }

    try:
        add_contact_request(contact_entry)
        logger.info(f"Contact entry added successfully | Entry: {contact_entry}")
    except Exception as e:
        logger.error(f"Failed to add contact entry | Error: {str(e)}")
        abort(500)  # Internal Server Error

    return redirect(f"{url_for('home')}#contact-section")

#===========================
# Cart API Routes
#===========================

# This function handles adding items to the cart
@internal_blueprint.route("/api/update-cart", methods=["POST"])
def add_to_cart():
    logger.info("POST request received for updating cart")
    data: dict | None = request.get_json()
    if data is None:
        logger.warning("Received empty JSON data for update-cart")
        return abort(400)

    product_id: str = str(data.get("product_id", ""))
    quantity: int = int(data.get("quantity", 0))
    
    logger.info(f"Adding to cart | Product ID: {product_id} | Quantity: {quantity}")

    if not product_id:
        logger.warning("Product ID is missing in the cart update request")
        return abort(400)

    cart: dict = session.get("cart", {})
    
    if product_id in cart:
        old_quantity: int = cart.get(product_id)
        
        if (old_quantity + quantity <= 0) or (quantity == 0):
            logger.info(f"Removing product from cart | Product ID: {product_id}")
            cart.pop(product_id)
        else:
            logger.info(f"Updating quantity for product in cart | Product ID: {product_id} | Old Quantity: {old_quantity} | New Quantity: {old_quantity + quantity}")
            cart.update({str(product_id): old_quantity + quantity})
    else:
        logger.info(f"Adding new product to cart | Product ID: {product_id} | Quantity: {quantity}")
        cart.update({str(product_id): quantity})
    
    session.permanent = True
    session.update({"cart": cart})
    session.modified = True
    logger.info(f"Cart updated successfully | Cart: {cart}")

    return {"success": "ok"}

# This function calculates the cart totals
@internal_blueprint.route("/api/calculate-cart", methods=["GET"])
def calculate_cart():
    logger.info("GET request received for calculating cart")
    csrf_token = request.headers.get("X-CSRF-Token")

    try:
        validate_csrf(csrf_token)
    except Exception as e:
        logger.error(f"CSRF validation failed | Error: {str(e)}")
        return str(e), 403
    
    cart: dict  = session.get("cart", {})
    discount: dict = session.get("discount", {})
    products = get_products()

    total: float = 0
    tax: float = 0
    discount_amount: float = 0

    items = [
        {
            "price": product.get("new_price") if product.get("new_price", 0) > 0 else product.get("price", 0.0),
            "tax_rate": product.get("tax", 0.0) / 100,
            "quantity": quantity,
            "total": (product.get("new_price") if product.get("new_price", 0) > 0 else product.get("price", 0.0)) * quantity
        }
        for product_id, quantity in cart.items()
        if (product := get_product_by_id(str(product_id)))
    ]          

    total = sum(item["total"] for item in items)
    tax = sum((item["total"] / (1 + item["tax_rate"])) * item["tax_rate"] for item in items)
    

    old_total: float = total

    if discount:
        discount_value = discount.get("value", 0)
        if discount.get("type", "absolute") == "absolute":
            total = max(total - discount_value, 0)
            tax = max(tax - discount_value, 0)
        else:
            discount_factor = (100 - discount_value) / 100
            total *= discount_factor
            tax *= discount_factor
        
        discount_amount: float = old_total-total

    session["cart_sums"] = {"total": total, "tax": tax, "total_discount": discount_amount, "old_total": old_total}
    session.modified = True
    logger.info(f"Cart calculated successfully | Total: {total} | Tax: {tax} | Discount: {discount_amount}")
    return {"total": total, "tax": tax, "total_discount": discount_amount, "old_total": old_total}

# This function checks the validity of a discount code
@internal_blueprint.route("/api/check-discount", methods=["POST"])
def check_discount():
    logger.info("POST request received for checking discount")
    csrf_token = request.headers.get("X-CSRF-Token")

    try:
        validate_csrf(csrf_token)
    except Exception as e:
        logger.error(f"CSRF validation failed | Error: {str(e)}")
        return str(e), 403
    

    data: dict | None = request.get_json()
    if data is None:
        logger.warning("Received empty JSON data for check-discount")
        return abort(400)

    discount_id: str = data.get("code", "")
    active_discount: dict = session.get("discount", {})

    if active_discount:
        logger.warning("Attempt to apply multiple discount codes")
        return {"error": "Es kann nur 1 Code aufeinmal eingelöst werden!"}, 404

    if not discount_id:
        logger.warning("Code ID is missing in the check discount request")
        return abort(400)

    coupon = get_coupon_by_id(str(discount_id))

    if coupon is None:
        logger.warning(f"Coupon does not exist | Coupon ID: {discount_id}")
        return {"error": "Coupon existiert nicht!"}, 404
    
    remaining = coupon.get("uses_remaining", 0)
    valid_till = coupon.get("valid_till", None)

    if (remaining is not None and remaining <= 0) or (valid_till is not None and (not datetime.strptime(valid_till, "%y-%m-%d") < datetime.today())):
        logger.warning(f"Coupon is invalid or expired | Coupon ID: {discount_id}")
        return {"error": "Coupon ist ungültig oder abgelaufen!"}, 404
    
    session.permanent = True
    session["discount"] = coupon
    session.modified = True
    logger.info(f"Discount applied successfully | Coupon: {coupon}")

    return {"id": discount_id, "type": coupon.get("type"), "value": coupon.get("value", 0)}, 200

# This function removes the active discount code
@internal_blueprint.route("/api/remove-discount", methods=["POST"])
def remove_discount():
    logger.info("POST request received for removing discount")
    csrf_token = request.headers.get("X-CSRF-Token")

    try:
        validate_csrf(csrf_token)
    except Exception as e:
        logger.error(f"CSRF validation failed | Error: {str(e)}")
        return str(e), 403
    
    active_discount: dict = session.get("discount", {})

    if not active_discount:
        logger.warning("No active discount code to remove")
        return {"error": "Es ist aktuell kein Code aktiv!"}, 404

    session.permanent = True
    session["discount"] = {}
    session.modified = True
    logger.info("Discount removed successfully")

    return {"success": "ok"}

#===========================
# Captcha API Routes
#===========================

# This function generates a captcha image
@internal_blueprint.route("/api/generate-captcha", methods=["POST"])
def captcha():
    logger.info("POST request received for generating captcha")
    captcha_image = generate_captcha()

    img_byte_arr = io.BytesIO()
    captcha_image[0].save(img_byte_arr, format="PNG")
    img_byte_arr.seek(0)

    base64_image = base64.b64encode(img_byte_arr.getvalue()).decode("utf-8")
    base64_image_data = f"data:image/png;base64,{base64_image}"

    session["captcha"] = captcha_image[1]
    session.modified = True
    logger.info("Captcha generated successfully")

    return jsonify({"captcha": base64_image_data})

#===========================
# Media API Routes
#===========================

# This function handles file uploads
@internal_blueprint.route("/api/files/upload", methods=["POST"])
@csrf.exempt
def upload_file():
    logger.info("POST request received for file upload")
    if not session.get("login", False):
        logger.warning("Unauthorized file upload attempt")
        return abort(403)

    directory = request.args.get("dir", "").lstrip("/")
    root = request.args.get("root", "uploads").lstrip("/")

    if "files[]" not in request.files:
        logger.warning("No files part in the request")
        return abort(400, description="No files part in the request")
    
    files = request.files.getlist("files[]")
    
    if not files:
        logger.warning("No selected files")
        return abort(400, description="No selected files")
    
    for file in files:
        filename = sanitize_path(file.filename)
        name, ext = os.path.splitext(filename)
        full_file_location = sanitize_path(os.path.join(root, directory, f"{name}{ext}"))

        counter = 1
        while os.path.exists(full_file_location):
            filename = f"{name}_{counter}{ext}"
            full_file_location = sanitize_path(os.path.join(root, directory, filename))
            counter += 1
        
        file.save(full_file_location)
        logger.info(f"File uploaded successfully | Path: {full_file_location}")

    return jsonify({"status": "Files uploaded successfully"}), 200

# This function handles file deletions
@internal_blueprint.route("/api/files/delete", methods=["DELETE"])
@csrf.exempt
def delete_media():
    logger.info("DELETE request received for file deletion")
    if not session.get("login", False):
        logger.warning("Unauthorized file deletion attempt")
        return abort(403)
    
    request_data: dict = request.get_json()
    path: str | None = request_data.get("path", None)
    files = request_data.get("files", [])
    root = request_data.get("root", "uploads").lstrip("/")

    if path is None or not files:
        logger.warning("Invalid file deletion request")
        return abort(400)
    else:
        path = path.replace("\\", "/").lstrip("/")

    errors = []

    for file in files:
        clean_path = sanitize_path(os.path.join(root, path, file))
        try:
            if os.path.isdir(clean_path):
                shutil.rmtree(clean_path)
            else:
                os.remove(clean_path)
        except FileNotFoundError:
            errors.append(f"File or directory not found: {clean_path}")
        except PermissionError:
            errors.append(f"Permission denied: {clean_path}")
        except Exception as e:
            errors.append(f"Error processing {clean_path}: {str(e)}")

    if errors:
        logger.warning(f"Errors occurred during file deletion | Errors: {errors}")
        return jsonify({"status": "Partial success", "errors": errors}), 207
    logger.info("Files deleted successfully")
    return jsonify({"status": "Files deleted successfully"}), 200

# This function handles renaming files and directories
@internal_blueprint.route("/api/files/rename", methods=["POST"])
@csrf.exempt
def rename_path():
    logger.info("POST request received for renaming path")
    if not session.get("login", False):
        logger.warning("Unauthorized file rename attempt")
        return abort(403)
    
    request_data: dict = request.get_json()

    path: str | None = request_data.get("path", None)
    file_name: str | None = request_data.get("name", None)
    new_name: str | None = request_data.get("new_name", None)
    root = request_data.get("root", "uploads").lstrip("/")

    if path is None or new_name is None or file_name is None:
        logger.warning("Invalid file rename request")
        return abort(400)
    else:
        path = path.replace("\\", "/").lstrip("/")
        file_name = file_name.replace("\\", "/").lstrip("/")
        new_name = new_name.replace("\\", "/").lstrip("/")

    clean_path = sanitize_path(os.path.join(root, path, file_name))
    new_clean_name = sanitize_path(os.path.join(root, path, new_name))

    error = None

    try:
        os.rename(clean_path, new_clean_name)
    except FileExistsError:
        error = f"A path with this name already exists: {new_clean_name}"
    except PermissionError:
        error  = f"Permission denied: {clean_path}"
    except OSError as e:
        error  = f"The operating system could not process the following path: {clean_path} - {str(e)}"
    except Exception as e:
        error = f"An error occured while trying to process the request: {str(e)}"

    if error is not None:
        logger.error(f"Error renaming path | Error: {error}")
        return jsonify({"error": error}), 409
    logger.info(f"Path renamed successfully | Old Path: {clean_path} | New Path: {new_clean_name}")
    return jsonify({"status": "Path renamed successfully"}), 200

# This function handles copying files and directories
@internal_blueprint.route("/api/files/copy", methods=["POST"])
@csrf.exempt
def copy_path():
    logger.info("POST request received for copying path")
    if not session.get("login", False):
        logger.warning("Unauthorized file copy attempt")
        return abort(403)

    request_data: dict = request.get_json()

    path: str | None = request_data.get("path", None)
    file_name: str | None = request_data.get("file_name", None)
    new_name: str | None = request_data.get("new_name", None)
    root = request_data.get("root", "uploads").lstrip("/")

    if path is None or new_name is None or file_name is None:
        logger.warning("Invalid file copy request")
        return abort(400)
    else:
        path = path.replace("\\", "/").lstrip("/")
        file_name = file_name.replace("\\", "/").lstrip("/")
        new_name = new_name.replace("\\", "/").lstrip("/")

    clean_path = sanitize_path(os.path.join(root, path, file_name))
    new_clean_name = sanitize_path(os.path.join(root, path, new_name))

    error = None

    try:
        if os.path.isdir(clean_path):
            shutil.copytree(clean_path, new_clean_name)
        else:
            shutil.copyfile(clean_path, new_clean_name)
    except FileExistsError:
        error = f"A path with this name already exists: {new_clean_name}"
    except PermissionError:
        error  = f"Permission denied: {clean_path}"
    except OSError as e:
        error  = f"The operating system could not process the following path: {clean_path} - {str(e)}"
    except Exception as e:
        error = f"An error occured while trying to process the request: {str(e)}"

    if error is not None:
        logger.error(f"Error copying path | Error: {error}")
        return jsonify({"error": error}), 409
    logger.info(f"Path copied successfully | Old Path: {clean_path} | New Path: {new_clean_name}")
    return jsonify({"status": "Path copied successfully"}), 200

# This function retrieves all media files in a directory
@internal_blueprint.route("/api/files/get_all", methods=["POST"])
@csrf.exempt
def get_all_media():
    logger.info("POST request received for getting all media")
    if not session.get("login", False):
        logger.warning("Unauthorized get all media attempt")
        return abort(403)

    path = request.args.get("path", "").lstrip("/")
    request_data: dict = request.get_json()
    root = request_data.get("root", "uploads").lstrip("/")

    # Custom mapping of file types to extensions
    CUSTOM_FILE_MAPPING = {
        "image": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff"],
        "video": [".mp4", ".mov", ".avi", ".mkv", ".flv", ".wmv"],
        "audio": [".mp3", ".wav", ".aac", ".flac", ".ogg"],
        "archive": [".zip", ".tar", ".rar", ".gz"],
        "document": [".pdf", ".docx", ".txt", ".pptx", ".xlsx"],
    }

    files = []
    full_path = sanitize_path(os.path.join(root, path))
    
    try:
        upload_directory = os.listdir(full_path)
    except FileNotFoundError:
        return {"error": "Directory not found"}

    for item in upload_directory:
        item_path = os.path.join(full_path, item)

        if os.path.isdir(item_path):
            file_type = "folder"
            size = len(os.listdir(item_path))
        else:
            _, ext = os.path.splitext(item)
            ext = ext.lower()
            file_type = "other"
            for category, extensions in CUSTOM_FILE_MAPPING.items():
                if ext in extensions:
                    file_type = category
                    break
            size = round(os.path.getsize(item_path) / 1024)

        last_modified_time = time.strftime("%d-%m-%Y %H:%M", time.localtime(os.path.getmtime(item_path)))

        files.append({
            "name": item,
            "type": file_type,
            "size": size,
            "last_modified": last_modified_time
        })

    return jsonify(files)

# This function handles folder creation
@internal_blueprint.route("/api/files/create_folder", methods=["POST"])
@csrf.exempt
def create_folder():
    logger.info("POST request received for folder creation")
    if not session.get("login", False):
        logger.warning("Unauthorized folder creation attempt")
        return abort(403)

    request_data: dict = request.get_json()
    path: str | None = request_data.get("path", None)
    folder_name: str | None = request_data.get("folder_name", None)
    root = request_data.get("root", "uploads").lstrip("/")

    if path is None or folder_name is None:
        logger.warning("Invalid folder creation request")
        return abort(400)
    else:
        path = path.replace("\\", "/").lstrip("/")
        folder_name = folder_name.replace("\\", "/").lstrip("/")

    full_folder_location = sanitize_path(os.path.join(root, path, folder_name))

    try:
        os.makedirs(full_folder_location, exist_ok=False)
    except FileExistsError:
        error = f"A folder with this name already exists: {full_folder_location}"
        logger.error(f"Error creating folder | Error: {error}")
        return jsonify({"error": error}), 409
    except PermissionError:
        error = f"Permission denied: {full_folder_location}"
        logger.error(f"Error creating folder | Error: {error}")
        return jsonify({"error": error}), 403
    except OSError as e:
        error = f"The operating system could not process the following path: {full_folder_location} - {str(e)}"
        logger.error(f"Error creating folder | Error: {error}")
        return jsonify({"error": error}), 500
    except Exception as e:
        error = f"An error occurred while trying to process the request: {str(e)}"
        logger.error(f"Error creating folder | Error: {error}")
        return jsonify({"error": error}), 500

    logger.info(f"Folder created successfully | Path: {full_folder_location}")
    return jsonify({"status": "Folder created successfully"}), 200

# This function deletes a product
@internal_blueprint.route("/api/delete-product")
@csrf.exempt
def delete_product():
    logger.info("GET request received for deleting product")
    if not session.get("login", False):
        logger.warning("Unauthorized delete product attempt")
        return abort(403)

    product_id: str|None = request.args.get("id", None)

    if product_id is None:
        logger.warning("No product provided for deletion")
        return {"error": "No product provided"}, 405
    
    delete_product_json(product_id)
    logger.info(f"Product deleted successfully | Product ID: {product_id}")
    return redirect(url_for("admin.products"))

# This function deletes a coupon
@internal_blueprint.route("/api/delete-coupon")
@csrf.exempt
def delete_coupon():
    logger.info("GET request received for deleting coupon")
    if not session.get("login", False):
        logger.warning("Unauthorized delete coupon attempt")
        return abort(403)

    coupons_id: str|None = request.args.get("id", None)

    if coupons_id is None:
        logger.warning("No coupon provided for deletion")
        return {"error": "No product provided"}, 405
    
    delete_coupon_json(coupons_id)
    logger.info(f"Coupon deleted successfully | Coupon ID: {coupons_id}")
    return redirect(url_for("admin.coupons"))

# This function deletes an order
@internal_blueprint.route("/api/delete-order")
@csrf.exempt
def delete_order():
    logger.info("GET request received for deleting order")
    if not session.get("login", False):
        logger.warning("Unauthorized delete order attempt")
        return abort(403)

    order_id: str|None = request.args.get("id", None)

    if order_id is None:
        logger.warning("No order provided for deletion")
        return {"error": "No order provided"}, 405
    
    delete_order_json(order_id)
    logger.info(f"Order deleted successfully | Order ID: {order_id}")
    return redirect(url_for("admin.orders"))

# This function converts markdown to HTML
@internal_blueprint.route("/api/markdown-to-html/", methods=["POST"])
@csrf.exempt
def markdown_to_html():
    logger.info("POST request received for converting markdown to HTML")
    if not session.get("login", False):
        logger.warning("Unauthorized markdown to HTML conversion attempt")
        return abort(403)
    return convert_markdown_to_html(request.json.get("data", ""))

# This function clears the cache
@internal_blueprint.route("/api/clear-cache/", methods=["POST"])
def clear_cache():
    logger.info("POST request received for clearing cache")
    if not session.get("login", False):
        logger.warning("Unauthorized cache clear attempt")
        return abort(403)
    
    get_products.cache_clear()
    get_product_by_id.cache_clear()
    get_settings.cache_clear()
    get_coupon_by_id.cache_clear()
    get_coupons.cache_clear()

    logger.info("Cache cleared successfully")
    return jsonify({"sucess": "Cache cleared sucessfully!"})

# This function retrieves system information
@internal_blueprint.route("/api/get-system-info/", methods=["GET"])
def get_system_info():
    logger.info("GET request received for getting system info")
    if not session.get("login", False):
        logger.warning("Unauthorized system info request attempt")
        return abort(403)
    
    memory_info = psutil.virtual_memory()
    ram_usage = {
        "total": round(memory_info.total / (1024 ** 3), 2),
        "used": round(memory_info.used / (1024 ** 3), 2),
        "percentage": memory_info.percent
    }

    disk_info = psutil.disk_usage("/")
    disk_usage = {
        "total": round(disk_info.total / (1024 ** 3), 2),
        "used": round(disk_info.used / (1024 ** 3), 2),
        "percentage": disk_info.percent
    }

    cpu_usage = {
        "percentage": psutil.cpu_percent(interval=1)
    }

    response = {
        "ram_usage": ram_usage,
        "disk_usage": disk_usage,
        "cpu_usage": cpu_usage
    }

    logger.info("System info retrieved successfully")
    return jsonify(response)

# =====================================
# Event Handling Routes
# =====================================

# This function retrieves events
@internal_blueprint.route("/api/get-events/", methods=["GET"])
def get_events_route():
    logger.info("GET request received for getting events")
    if not session.get("login", False):
        logger.warning("Unauthorized get events attempt")
        return abort(403)
    
    year = request.args.get("year", type=int, default=None)
    month = request.args.get("month", type=int, default=None)
    day = request.args.get("day", type=int, default=None)

    events: list[dict] = query_events(day=day, month=month, year=year)
    
    logger.info("Events retrieved successfully")
    return jsonify(events)

# This function adds events
@internal_blueprint.route("/api/add-events/", methods=["POST"])
def add_events():
    logger.info("POST request received for adding events")
    if not session.get("login", False):
        logger.warning("Unauthorized add events attempt")
        return abort(403)

    data = request.get_json()
    if not data:
        logger.warning("No data provided for adding events")
        return jsonify({"error": "No data provided"}), 400

    required_fields = {"year", "month", "day", "name", "description"}
    if not required_fields.issubset(data):
        logger.warning(f"Missing required fields for adding events: {required_fields - set(data.keys())}")
        return jsonify({"error": f"Missing required fields: {required_fields - set(data.keys())}"}), 400

    try:
        year = int(data["year"])
        month = int(data["month"])
        day = int(data["day"])
    except ValueError:
        logger.warning("Year, month, and day must be integers for adding events")
        return jsonify({"error": "Year, month, and day must be integers"}), 400

    if not (1 <= month <= 12 and 1 <= day <= 31):
        logger.warning("Invalid month or day for adding events")
        return jsonify({"error": "Invalid month or day"}), 400

    name = data["name"]
    description = data["description"]

    events = get_events()

    existing_ids = {event["id"] for event in events}
    new_id = str(max(map(int, existing_ids), default=0) + 1)

    new_event = {
        "id": new_id,
        "year": year,
        "month": month,
        "day": day,
        "name": name,
        "description": description,
    }

    try:
        add_event(new_event)
        logger.info(f"Event added successfully: {new_event}")
    except Exception as e:
        logger.error(f"Failed to add event | Error: {str(e)}")
        abort(500)  # Internal Server Error

    return jsonify({"message": "Event added successfully", "event": new_event}), 201

# This function deletes an event
@internal_blueprint.route("/api/delete-event")
@csrf.exempt
def delete_event():
    logger.info("GET request received for deleting event")
    if not session.get("login", False):
        logger.warning("Unauthorized delete event attempt")
        return abort(403)

    event_id: str|None = request.args.get("id", None)

    if event_id is None:
        logger.warning("No event provided for deletion")
        return {"error": "No event provided"}, 405
    
    delete_event_json(event_id)
    logger.info(f"Event deleted successfully: {event_id}")
    return redirect(url_for("admin.dashboard")+"#calendarMonthYear")

# This function retrieves logs
@internal_blueprint.route("/api/get-logs", methods=["POST"])
def get_logs():
    logger.info("POST request received for getting logs")
    if not session.get("login", False):
        logger.warning("Unauthorized get logs attempt")
        return abort(403)
    
    data = request.get_json()
    
    if not data:
        logger.warning("No data provided for getting logs")
        return jsonify({"error": "No data provided"}), 400

    severity: str = data.get("severityFilter", "ALL").upper()
    num_of_items: int = int(data.get("itemsFilter", 500)) * (-1)
    sorting: str = data.get("sortingFilter", "ASC")

    with open("logs/app.log", "r", encoding="utf-8") as file:
        lines = file.readlines()

    if severity != "ALL": 
        filtered_lines = [line for line in lines if severity in line]
    else:
        filtered_lines = [line for line in lines if "DEBUG" not in line]

    clean_lines = filtered_lines[num_of_items:]

    if sorting == "DESC":
        clean_lines = list(reversed(clean_lines)) 

    logger.info("Logs retrieved successfully")
    return jsonify({
        "logs": clean_lines
    })

# This function creates an invoice for an order
@internal_blueprint.route("/api/create-invoice/<order_id>", methods=["GET"])
@csrf.exempt
def create_invoice(order_id):
    logger.info(f"GET request received for creating invoice | Order ID: {order_id}")
    if not session.get("login", False):
        logger.warning("Unauthorized create invoice attempt")
        return abort(403)

    order = get_order_by_id(order_id)
    if not order:
        logger.warning(f"Order not found | Order ID: {order_id}")
        return abort(404, description="Order not found.")

    pdf_buffer = create_invoice_pdf(order)
    response = make_response(pdf_buffer.getvalue())
    response.headers["Content-Disposition"] = f"attachment; filename=invoice_{order_id}.pdf"
    response.mimetype = "application/pdf"

    logger.info(f"Invoice created successfully | Order ID: {order_id}")
    return response


