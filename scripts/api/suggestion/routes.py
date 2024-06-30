from flask import Blueprint
from suggestion.controller import search_moviesuggestion

moviesuggestion_bp = Blueprint('moviesuggestion_bp', __name__)

@moviesuggestion_bp.route('/suggestion', methods=['GET'])
def search():
    return search_moviesuggestion()
