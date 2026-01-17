from flask import Blueprint, render_template
from logging_utility import logger

other_blueprint = Blueprint("other", __name__)

# =====================================
# About Page Route
# =====================================

# Route to retrieve the "Über" (About) page
@other_blueprint.route("/ueber", methods=["GET"])
def about():
    logger.info("GET request received for the Über page.")
    return render_template("about.jinja-html")
