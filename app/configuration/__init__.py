from flask import Blueprint

bp = Blueprint('config', __name__)

from app.configuration import routes