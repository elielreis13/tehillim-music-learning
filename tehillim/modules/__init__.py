from flask import Blueprint

bp = Blueprint("modules", __name__)

from . import routes  # noqa: E402, F401
