from flask import Blueprint, request
from flask_restx import Namespace, Resource
from bs4 import BeautifulSoup
import requests

BASE_URL = "https://thepiratebay.party"

search_bp = Blueprint("search", __name__)
api = Namespace("search", description="Operações relacionadas a busca de torrents")


@api.route("/")
class TorrentSearch(Resource):
    @api.doc("search_torrents")
    @api.param("query", "Título do filme", required=True)
    @api.response(200, "Sucesso")
    @api.response(400, "Parâmetro query não fornecido")
    def get(self):
        """Busca torrents pelo título do filme"""
        query = request.args.get("query")
        if not query:
            return {"error": "Parâmetro query não fornecido"}, 400

        print(f"[SEARCH] Iniciando busca de torrents para: {query}")

        url = f"{BASE_URL}/search/{query}/0/99/0"
        print(f"[SEARCH] Requisitando: {url}")

        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        print(f"[SEARCH] Status HTTP: {response.status_code}")

        soup = BeautifulSoup(response.text, "html.parser")
        rows = soup.find_all("tr")
        print(f"[SEARCH] Linhas encontradas no HTML: {len(rows)}")

        results = []
        for row in rows:
            tds = row.find_all("td")
            if len(tds) < 7:
                continue
            title_tag = tds[1].find("a")
            if not title_tag:
                continue
            title = title_tag.get_text(strip=True)
            magnet_tag = tds[3].find("a", href=lambda x: x and x.startswith("magnet:"))
            magnet_link = magnet_tag["href"] if magnet_tag else None
            seeds = tds[5].get_text(strip=True)
            leechers = tds[6].get_text(strip=True)
            results.append({
                "title": title,
                "magnet": magnet_link,
                "seeds": int(seeds) if seeds.isdigit() else 0,
                "leechers": int(leechers) if leechers.isdigit() else 0,
            })

        print(f"[SEARCH] Resultados encontrados: {len(results)}")
        return results, 200


search_bp.api = api
