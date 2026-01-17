from flask import Blueprint, render_template
from logging_utility import logger

legal_blueprint = Blueprint("legal", __name__, url_prefix="/rechtliches")

# =====================================
# Legal Routes
# =====================================

# Route to retrieve the Impressum page
@legal_blueprint.route("/impressum", methods=["GET"])
def impressum():
    logger.info("GET request received for the Impressum page.")
    return render_template("imprint.jinja-html")

# Route to retrieve the AGB page
@legal_blueprint.route("/agb", methods=["GET"])
def agb():
    logger.info("GET request received for the AGB page.")
    return render_template("agb.jinja-html")

@legal_blueprint.route("/datenschutz", methods=["GET"])
def datenschutz():
    logger.info("GET request received for the Datenschutz page.")
    return render_template("privacy.jinja-html")
