from flask import Blueprint

bp = Blueprint("teacher", __name__)

from . import routes  # noqa
