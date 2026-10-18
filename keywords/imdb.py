"""Movies that carry a keyword on IMDB, through IMDB's own GraphQL API.

It is the API behind imdb.com's advanced title search. It needs no session,
no key and is not behind the AWS WAF that blocks the scraper; only the
`x-imdb-client-name` header is required, without it the answer is 403.
"""

import logging
import re
import unicodedata

import requests

from config import HTTP_TIMEOUT

logger = logging.getLogger(__name__)

GRAPHQL_URL = "https://api.graphql.imdb.com/"
HEADERS = {
    "Content-Type": "application/json",
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
    ),
    "x-imdb-client-name": "imdb-web-next-localized",
    "x-imdb-user-country": "US",
    "x-imdb-user-language": "en-US",
}

SEARCH_QUERY = """
query MoviesByKeyword($keyword: String!, $first: Int!) {
  advancedTitleSearch(
    first: $first
    constraints: {
      keywordConstraint: { anyKeywords: [$keyword] }
      titleTypeConstraint: { anyTitleTypeIds: ["movie"] }
    }
    sort: { sortBy: POPULARITY, sortOrder: ASC }
  ) {
    edges {
      node {
        title {
          id
          titleText { text }
          originalTitleText { text }
          releaseYear { year }
          plot { plotText { plainText } }
          titleGenres { genres { genre { text } } }
        }
      }
    }
  }
}
"""


class IMDBSearchError(Exception):
    """IMDB's API did not answer the keyword search."""


def keyword_slug(keyword):
    """IMDB keyword id: lowercase ASCII words joined by hyphens.

    "French New Wave" -> "french-new-wave". Any other form returns nothing.
    """
    text = unicodedata.normalize("NFKD", str(keyword or ""))
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def search_movies_by_keyword(keyword, first=15):
    """Up to `first` movies tagged with `keyword`, most popular first.

    Each movie is a dict with tconst, title, original_title, year,
    description and genres.
    """
    slug = keyword_slug(keyword)
    if not slug:
        return []

    try:
        response = requests.post(
            GRAPHQL_URL,
            json={
                "query": SEARCH_QUERY,
                "variables": {"keyword": slug, "first": first},
            },
            headers=HEADERS,
            timeout=HTTP_TIMEOUT,
        )
        response.raise_for_status()
        body = response.json()
    except (requests.RequestException, ValueError) as e:
        raise IMDBSearchError(f"keyword search failed for {slug!r}: {e}") from e

    if body.get("errors"):
        raise IMDBSearchError(f"keyword search failed for {slug!r}: {body['errors']}")

    edges = body.get("data", {}).get("advancedTitleSearch", {}).get("edges") or []
    movies = [_movie(edge["node"]["title"]) for edge in edges]
    logger.info("IMDB keyword %r: %d movies", slug, len(movies))
    return movies


def _text(node, *keys):
    for key in keys:
        node = (node or {}).get(key)
    return node


def _movie(title):
    return {
        "tconst": title["id"],
        "title": _text(title, "titleText", "text") or "",
        "original_title": _text(title, "originalTitleText", "text")
        or _text(title, "titleText", "text")
        or "",
        "year": _text(title, "releaseYear", "year"),
        "description": _text(title, "plot", "plotText", "plainText") or "",
        "genres": [
            genre["genre"]["text"]
            for genre in _text(title, "titleGenres", "genres") or []
        ],
    }
