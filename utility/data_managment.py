import json
import re
from functools import lru_cache

from logging_utility import logger

# =====================================
# Products Functions
# =====================================

# Get products from the products.json file
@lru_cache(maxsize=30720)
def get_products() -> list | None:
    try:
        with open("data/products.json", "r", encoding="utf-8") as file:
            products: list = json.load(file)
        logger.info("Products loaded successfully.")
        return products
    except FileNotFoundError:
        logger.critical("products.json file not found.")
        return None
    except json.JSONDecodeError:
        logger.critical("Invalid JSON in products.json.")
        return None


# Query products based on search criteria
def query_products(query: str = None, category: str = None, sort_by=None, ascending=True) -> list | None:
    try:
        products: list[dict] | None = get_products()
        
        # Filter by query (name or keyword)
        if query is not None:
            if query.strip() == "":
                query = ".*"
            pattern = re.compile(query, re.IGNORECASE)
            products = [
                product for product in products 
                if (pattern.search(product.get("id", "")) or pattern.search(product.get("name", "")) or pattern.search(product.get("keyword", "")))
            ]
        
        # Filter by category
        if category is not None:
            products = [
                product for product in products if (category in product.get("categories", []))
            ]
        
        # Sort products by given field
        if sort_by:
            products = sorted(products, key=lambda x: x.get(sort_by, None), reverse=not ascending)
        
        logger.info("Products queried successfully.")
        return products if products else []

    except Exception as e:
        logger.error(f"Error querying products: {e}")
        return []


# Get product by its ID
@lru_cache(maxsize=30720)
def get_product_by_id(_id: str) -> dict | None:
    try:
        products: list[dict] | None = get_products()
        result = [product for product in products if (str(_id) == (product.get("id")))]
        product = result[0] if result else None
        logger.info(f"Product with ID {_id} retrieved.")
        return product
    except Exception as e:
        logger.error(f"Error retrieving product by ID {_id}: {e}")
        return None


# Delete product from the products.json file
def delete_product_json(product_id: str):
    try:
        products: list[dict] = get_products()
        
        # Remove the product with the given ID
        products_new = [product for product in products if product.get("id") != str(product_id)]

        # Save the updated list back to the file
        with open("data/products.json", "w", encoding="utf-8") as f:
            json.dump(products_new, f, indent=4, ensure_ascii=False)    
        
        logger.info(f"Product with ID {product_id} deleted successfully.")

        # Clear cached data for products
        get_product_by_id.cache_clear()
        get_products.cache_clear()
    
    except FileNotFoundError:
        logger.critical("products.json file not found.")
    except json.JSONDecodeError:
        logger.critical("Invalid JSON in products.json.")
    except Exception as e:
        logger.error(f"Error deleting product with ID {product_id}: {e}")


def add_product(product_data: dict):
    try:
        products: list[dict] = get_products()
        products.append(product_data)

        with open("data/products.json", "w", encoding="utf-8") as f:
            json.dump(products, f, indent=4, ensure_ascii=False)
        
        logger.info(f"Product added successfully | Product ID: {product_data.get('id')}")
        
        # Clear cached data for products
        get_product_by_id.cache_clear()
        get_products.cache_clear()
    except FileNotFoundError:
        logger.critical("products.json file not found.")
    except json.JSONDecodeError:
        logger.critical("Invalid JSON in products.json.")
    except Exception as e:
        logger.error(f"Error adding product: {e}")


# Modify product by its ID
def modify_product(product_id: str, updated_data: dict):
    try:
        products: list[dict] = get_products()
        product = get_product_by_id(product_id)
        if product:
            product.update(updated_data)
            with open("data/products.json", "w", encoding="utf-8") as f:
                json.dump(products, f, indent=4, ensure_ascii=False)
            logger.info(f"Product with ID {product_id} updated successfully.")
            # Clear cached data for products
            get_product_by_id.cache_clear()
            get_products.cache_clear()
        else:
            logger.error(f"Product with ID {product_id} not found.")
    except FileNotFoundError:
        logger.critical("products.json file not found.")
    except json.JSONDecodeError:
        logger.critical("Invalid JSON in products.json.")
    except Exception as e:
        logger.error(f"Error updating product with ID {product_id}: {e}")


# =====================================
# Coupons Functions
# =====================================

# Get coupons from the coupons.json file
@lru_cache(maxsize=30720)
def get_coupons(type: str = "") -> dict | None:
    try:
        with open("data/coupons.json", "r", encoding="utf-8") as file:
            data: dict = json.load(file)
        logger.info("Coupons loaded successfully.")
    except FileNotFoundError:
        logger.critical("coupons.json file not found.")
        return None
    except json.JSONDecodeError:
        logger.critical("Invalid JSON in coupons.json.")
        return None

    if type != "":
        return data.get(type, None)
    else:
        return data


# Get coupon by its ID
@lru_cache(maxsize=30720)
def get_coupon_by_id(_id: str) -> dict | None:
    try:
        coupons: list[dict] | None = get_coupons()
        result = [coupon for coupon in coupons if str(_id) == coupon.get("id")]
        coupon = result[0] if result else None
        logger.info(f"Coupon with ID {_id} retrieved.")
        return coupon
    except Exception as e:
        logger.error(f"Error retrieving coupon by ID {_id}: {e}")
        return None


# Delete coupon from the coupons.json file
def delete_coupon_json(coupon_id: str):
    try:
        coupons = get_coupons()

        # Remove the coupon with the given ID
        coupons_new = [coupon for coupon in coupons if coupon.get("id") != str(coupon_id)]

        # Save the updated list back to the file
        with open("data/coupons.json", "w", encoding="utf-8") as f:
            json.dump(coupons_new, f, indent=4, ensure_ascii=False)    
        
        logger.info(f"Coupon with ID {coupon_id} deleted successfully.")

        # Clear cached data for coupons
        get_coupon_by_id.cache_clear()
        get_coupons.cache_clear()
    
    except FileNotFoundError:
        logger.critical("coupons.json file not found.")
    except json.JSONDecodeError:
        logger.critical("Invalid JSON in coupons.json.")
    except Exception as e:
        logger.error(f"Error deleting coupon with ID {coupon_id}: {e}")


def add_coupon(coupon_data: dict):
    try:
        coupons: list[dict] = get_coupons()
        coupons.append(coupon_data)

        with open("data/coupons.json", "w", encoding="utf-8") as f:
            json.dump(coupons, f, indent=4, ensure_ascii=False)
        
        logger.info(f"Coupon added successfully | Coupon ID: {coupon_data.get('id')}")
        
        # Clear cached data for coupons
        get_coupon_by_id.cache_clear()
        get_coupons.cache_clear()
    except FileNotFoundError:
        logger.critical("coupons.json file not found.")
    except json.JSONDecodeError:
        logger.critical("Invalid JSON in coupons.json.")
    except Exception as e:
        logger.error(f"Error adding coupon: {e}")


# Modify coupon by its ID
def modify_coupon(coupon_id: str, updated_data: dict):
    try:
        coupons: list[dict] = get_coupons()
        coupon = get_coupon_by_id(coupon_id)
        if coupon:
            coupon.update(updated_data)
            with open("data/coupons.json", "w", encoding="utf-8") as f:
                json.dump(coupons, f, indent=4, ensure_ascii=False)
            logger.info(f"Coupon with ID {coupon_id} updated successfully.")
            # Clear cached data for coupons
            get_coupon_by_id.cache_clear()
            get_coupons.cache_clear()
        else:
            logger.error(f"Coupon with ID {coupon_id} not found.")
    except FileNotFoundError:
        logger.critical("coupons.json file not found.")
    except json.JSONDecodeError:
        logger.critical("Invalid JSON in coupons.json.")
    except Exception as e:
        logger.error(f"Error updating coupon with ID {coupon_id}: {e}")


# =====================================
# Settings Functions
# =====================================

# Get settings from the settings.json file
@lru_cache(maxsize=30720)
def get_settings(type: str = "") -> dict | None:
    try:
        with open("data/settings.json", "r", encoding="utf-8") as file:
            data: dict = json.load(file)
        logger.info("Settings loaded successfully.")
    except FileNotFoundError:
        logger.critical("settings.json file not found.")
        return None
    except json.JSONDecodeError:
        logger.critical("Invalid JSON in settings.json.")
        return None

    if type != "":
        return data.get(type, None)
    else:
        return data


# =====================================
# Contact Functions
# =====================================

# Get contact requests from the contacts.json file
@lru_cache(maxsize=30720)
def get_contact_requests(type: str = "") -> dict | None:
    try:
        with open("data/contact.json", "r", encoding="utf-8") as file:
            data: dict = json.load(file)
        logger.info("Contact requests loaded successfully.")
    except FileNotFoundError:
        logger.critical("contacts.json file not found.")
        return None
    except json.JSONDecodeError:
        logger.critical("Invalid JSON in contacts.json.")
        return None

    if type != "":
        return data.get(type, None)
    else:
        return data


# Get coupon by its ID
@lru_cache(maxsize=30720)
def get_contact_by_id(_id: str) -> dict | None:
    try:
        contact_requests: list[dict] | None = get_contact_requests()
        result = [request for request in contact_requests if str(_id) == request.get("id")]
        request = result[0] if result else None
        logger.info(f"Coupon with ID {_id} retrieved.")
        return request
    except Exception as e:
        logger.error(f"Error retrieving coupon by ID {_id}: {e}")
        return None


# Delete coupon from the coupons.json file
def delete_request_json(request_id: str):
    try:
        contact_requests = get_contact_requests()

        # Remove the coupon with the given ID
        coupons_new = [request for request in contact_requests if request.get("id") != str(request_id)]

        # Save the updated list back to the file
        with open("data/coupons.json", "w", encoding="utf-8") as f:
            json.dump(coupons_new, f, indent=4, ensure_ascii=False)    
        
        logger.info(f"Contact Request with ID {request_id} deleted successfully.")

        # Clear cached data for coupons
        get_contact_requests.cache_clear()
        get_contact_by_id.cache_clear()
    
    except FileNotFoundError:
        logger.critical("contacts.json file not found.")
    except json.JSONDecodeError:
        logger.critical("Invalid JSON in contacts.json.")
    except Exception as e:
        logger.error(f"Error deleting coupon with ID {request_id}: {e}")

def add_contact_request(contact_entry: dict):
    try:
        contact_requests: list[dict] = get_contact_requests()
        contact_requests.append(contact_entry)

        with open("data/contact.json", "w", encoding="utf-8") as file:
            json.dump(contact_requests, file, indent=4, ensure_ascii=False)
        
        logger.info(f"Contact entry added successfully | Entry: {contact_entry}")
        
        # Clear cached data for contact requests
        get_contact_by_id.cache_clear()
        get_contact_requests.cache_clear()
    except FileNotFoundError:
        logger.critical("contact.json file not found.")
    except json.JSONDecodeError:
        logger.critical("Invalid JSON in contact.json.")
    except Exception as e:
        logger.error(f"Error adding contact entry: {e}")


# Modify contact request by its ID
def modify_contact_request(request_id: str, updated_data: dict):
    try:
        contact_requests: list[dict] = get_contact_requests()
        request = get_contact_by_id(request_id)
        if request:
            request.update(updated_data)
            with open("data/contact.json", "w", encoding="utf-8") as f:
                json.dump(contact_requests, f, indent=4, ensure_ascii=False)
            logger.info(f"Contact request with ID {request_id} updated successfully.")
            # Clear cached data for contact requests
            get_contact_by_id.cache_clear()
            get_contact_requests.cache_clear()
        else:
            logger.error(f"Contact request with ID {request_id} not found.")
    except FileNotFoundError:
        logger.critical("contacts.json file not found.")
    except json.JSONDecodeError:
        logger.critical("Invalid JSON in contacts.json.")
    except Exception as e:
        logger.error(f"Error updating contact request with ID {request_id}: {e}")


# =====================================
# Orders Functions
# =====================================

# Get orders from the orders.json file
@lru_cache(maxsize=30720)
def get_orders() -> list | None:
    try:
        with open("data/orders.json", "r", encoding="utf-8") as file:
            orders: list = json.load(file)
        logger.info("Orders loaded successfully.")
        return orders
    except FileNotFoundError:
        logger.critical("orders.json file not found.")
        return None
    except json.JSONDecodeError:
        logger.critical("Invalid JSON in orders.json.")
        return None

# Get order by its ID
@lru_cache(maxsize=30720)
def get_order_by_id(_id: str) -> dict | None:
    try:
        orders: list[dict] | None = get_orders()
        result = [order for order in orders if str(_id) == order.get("id")]
        order = result[0] if result else None
        logger.info(f"Order with ID {_id} retrieved.")
        return order
    except Exception as e:
        logger.error(f"Error retrieving order by ID {_id}: {e}")
        return None

# Delete order from the orders.json file
def delete_order_json(order_id: str):
    try:
        orders: list[dict] = get_orders()
        
        # Remove the order with the given ID
        orders_new = [order for order in orders if order.get("id") != str(order_id)]

        # Save the updated list back to the file
        with open("data/orders.json", "w", encoding="utf-8") as f:
            json.dump(orders_new, f, indent=4, ensure_ascii=False)    
        
        logger.info(f"Order with ID {order_id} deleted successfully.")

        # Clear cached data for orders
        get_order_by_id.cache_clear()
        get_orders.cache_clear()
    
    except FileNotFoundError:
        logger.critical("orders.json file not found.")
    except json.JSONDecodeError:
        logger.critical("Invalid JSON in orders.json.")
    except Exception as e:
        logger.error(f"Error deleting order with ID {order_id}: {e}")

# Add order to the orders.json file
def add_order(order_data: dict):
    try:
        orders: list[dict] = get_orders()
        orders.append(order_data)

        with open("data/orders.json", "w", encoding="utf-8") as f:
            json.dump(orders, f, indent=4, ensure_ascii=False)
        
        logger.info(f"Order added successfully | Order ID: {order_data.get('id')}")
        
        # Clear cached data for orders
        get_order_by_id.cache_clear()
        get_orders.cache_clear()
    except FileNotFoundError:
        logger.critical("orders.json file not found.")
    except json.JSONDecodeError:
        logger.critical("Invalid JSON in orders.json.")
    except Exception as e:
        logger.error(f"Error adding order: {e}")


# Modify order by its ID
def modify_order(order_id: str, updated_data: dict):
    try:
        orders: list[dict] = get_orders()
        order = get_order_by_id(order_id)
        if order:
            order.update(updated_data)
            with open("data/orders.json", "w", encoding="utf-8") as f:
                json.dump(orders, f, indent=4, ensure_ascii=False)
            logger.info(f"Order with ID {order_id} updated successfully.")
            # Clear cached data for orders
            get_order_by_id.cache_clear()
            get_orders.cache_clear()
        else:
            logger.error(f"Order with ID {order_id} not found.")
    except FileNotFoundError:
        logger.critical("orders.json file not found.")
    except json.JSONDecodeError:
        logger.critical("Invalid JSON in orders.json.")
    except Exception as e:
        logger.error(f"Error updating order with ID {order_id}: {e}")


