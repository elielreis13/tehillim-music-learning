from flask import Blueprint

bp = Blueprint("public", __name__, template_folder="../templates")

from . import routes