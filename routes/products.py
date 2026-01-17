from flask import abort, Blueprint, render_template
from utility import get_product_by_id
from logging_utility import logger

product_blueprint = Blueprint("products", __name__, url_prefix="")

# =====================================
# Product Routes
# =====================================

# Route to retrieve all products
@product_blueprint.route("/produkte", methods=["GET"])
def products():
    logger.info("GET request received for all products.")
    return render_template("products.jinja-html")

# Route to retrieve a single product by ID
@product_blueprint.route("/produkt/<string:product_id>", methods=["GET"])
def product(product_id: int):
    logger.info(f"GET request received for product with ID: {product_id}")
    
    # Fetch product by ID
    product: dict = get_product_by_id(product_id)
    
    if product is None:
        logger.warning(f"Product with ID {product_id} not found.")
        abort(404)  # Product not found
    
    logger.info(f"Product retrieved: {product}")
    return render_template("product.jinja-html", product=product)
