from flask import Blueprint

bp = Blueprint("api", __name__)

from . import content, progress, messages, recordings, teacher, tts, exercises, dev  # noqa
