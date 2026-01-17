from datetime import date, datetime

from flask import request, session, Blueprint, url_for, redirect, render_template
from utility import get_product_by_id, get_coupon_by_id, delete_coupon_json, get_orders, add_order

checkout_blueprint = Blueprint("checkout", __name__, template_folder="./templates", root_path="/")


@checkout_blueprint.route("/cart/", methods=["GET"])
def cart():
    return render_template("cart.jinja-html")


@checkout_blueprint.route("/checkout/", methods=["GET", "POST"])
def checkout():
    if not session.get("cart"):
        return redirect(url_for("checkout.cart"), code=302)

    if request.method == "GET":
        return render_template("checkout.jinja-html")

    form_data = {
        "type": request.form.get("type"),
        "name": request.form.get("name"),
        "email": request.form.get("email"),
        "tel": request.form.get("tel"),
        "address": request.form.get("address"),
        "country": request.form.get("country"),
        "city": request.form.get("city"),
        "zip_code": request.form.get("zip_code"),
        "captcha_text": request.form.get("captcha-text"),
    }

    items = []
    cart: dict = session.get("cart", {})
    discount: dict = session.get("discount", {})

    for product_id, quantity in cart.items():
        product: dict = get_product_by_id(str(product_id))
        price: float|None = product.get("new_price", None)
        if price is None or price <= 0:
            price: float = product.get("price", 0)
        product_data = {
            "name": product.get("name", ""),
            "quantity": quantity,
            "unit_price": price,
            "tax_rate": product.get("tax", 20) / 100,
            "total": price * quantity,
        }
        items.append(product_data)

    subtotal = sum(item["total"] for item in items)
    tax = sum(item["total"]/(item["tax_rate"]+1) * item["tax_rate"] for item in items)

    old_total: float = subtotal
    discount_amount: float = 0

    if discount:
        discount_value = discount.get("value", 0)
        if discount.get("type", "absolute") == "absolute":
            subtotal = max(subtotal - discount_value, 0)
            tax = max(tax - discount_value, 0)
        else:
            discount_factor = (100 - discount_value) / 100
            subtotal *= discount_factor
            tax *= discount_factor

        discount_amount: float = old_total-subtotal

    coupon_id = str(session.get("discount", {}).get("id", None))

    coupon = get_coupon_by_id(coupon_id)
    if coupon:
        valid_till = coupon.get("valid_till")
        uses_remaining = coupon.get("uses_remaining")

        if valid_till and datetime.strptime(valid_till, "%Y-%m-%d") < datetime.today():
            delete_coupon_json(coupon_id)
        elif uses_remaining is not None:
            coupon["uses_remaining"] -= 1
            if coupon["uses_remaining"] <= 0:
                delete_coupon_json(coupon_id)

    # Generate a new order ID
    orders = get_orders()
    new_order_id = f"{1700000000 + len(orders) + 1}"

    # Create order data
    order_data = {
        "id": new_order_id,
        "email": form_data["email"],
        "name": form_data["name"],
        "type": form_data["type"],
        "tel": form_data["tel"],
        "address": form_data["address"],
        "country": form_data["country"],
        "city": form_data["city"],
        "zip_code": form_data["zip_code"],
        "items": items,
        "total_price": subtotal,
        "old_total": old_total,
        "total_tax": tax,
        "date": date.today().strftime('%d.%m.%Y'),
        "status": "offen",
        "notiz": "",
        "discount": discount_amount
    }

    # Add the order to orders.json
    add_order(order_data)

    try:
        session.pop("cart")
        session.pop("cart_sums")
        session.pop("discount")
        session.modified = True
    except KeyError:
        pass

    return render_template("checkout_done.jinja-html")
