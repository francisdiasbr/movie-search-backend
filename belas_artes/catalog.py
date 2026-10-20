"""Belas Artes à la Carte catalog, read from the JSON its own site loads.

The site (www.belasartesalacarte.com.br) is a SPA: it asks the core API where
the storage is, then downloads one public JSON with every title, view
(section) and person. No login, no key and no HTML to scrape. The JSON is
versioned, so it is only downloaded again when the version changes.
"""

import logging
import threading

import requests

from config import HTTP_TIMEOUT

logger = logging.getLogger(__name__)

CORE_API_URL = "https://prd-core-alacarte.futuraproducoes.com.br/api/v1/version"


class CatalogUnavailable(Exception):
    """The site's API or storage did not answer."""


_lock = threading.Lock()
_catalog = {"version": None, "data": None}


def _get_json(url):
    try:
        response = requests.get(url, timeout=HTTP_TIMEOUT)
        response.raise_for_status()
        return response.json()
    except (requests.RequestException, ValueError) as e:
        raise CatalogUnavailable(f"Belas Artes request to {url} failed: {e}") from e


def load_catalog():
    """The whole catalog, downloaded again only when its version changes."""
    storage_url = _get_json(CORE_API_URL)["app"]["url"]
    manifest = _get_json(f"{storage_url}/api/prepare/version.json.gz")

    with _lock:
        if _catalog["version"] != manifest["version"]:
            _catalog["data"] = _get_json(f"{storage_url}/{manifest['path']}")
            _catalog["version"] = manifest["version"]
            logger.info(
                "Belas Artes catalog %s: %d titles",
                manifest["version"],
                len(_catalog["data"]["titles"]),
            )
        return _catalog["data"]


def view_titles(catalog, slug):
    """Titles of the view `slug`, in the site's order and without repeats.

    A view is a page of the site (e.g. "adicionados-recentemente"); its GRID
    lists hold the title ids, the BANNERS lists only hold the header image.
    None when the view does not exist.
    """
    view = next((v for v in catalog["views"].values() if v["slug"] == slug), None)
    if view is None:
        return None

    ids = [
        title_id
        for lst in view["lists"]
        if lst["type"] == "GRID"
        for title_id in lst["items"]
    ]
    titles = catalog["titles"]
    return [titles[str(i)] for i in dict.fromkeys(ids) if str(i) in titles]
