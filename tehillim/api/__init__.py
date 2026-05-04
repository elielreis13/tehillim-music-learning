from flask import Blueprint, jsonify

bp = Blueprint("api", __name__)

from . import routes  # noqa: E402, F401


@bp.errorhandler(Exception)
def handle_api_error(exc):
    """Garante que o blueprint /api sempre retorne JSON em vez de HTML."""
    import traceback
    traceback.print_exc()
    return jsonify({"error": str(exc)}), 500
