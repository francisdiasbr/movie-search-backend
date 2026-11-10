"""Movies that carry a keyword on IMDB, through IMDB's own GraphQL API.

It is the API behind imdb.com's advanced title search. It needs no session,
no key and is not behind the AWS WAF that blocks the scraper; only the
`x-imdb-client-name` header is required, without it the answer is 403.
"""

import logging
import re
import unicodedata

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

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
DIRECTOR_QUERY = """
query Director($name: String!) {
  mainSearch(first: 5, options: { searchTerm: $name, type: NAME }) {
    edges { node { entity { ... on Name { id nameText { text } } } } }
  }
}
"""

DIRECTED_QUERY = """
query Directed($id: ID!) {
  name(id: $id) {
    credits(first: 250, filter: { categories: ["director"], titleType: "movie" }) {
      edges {
        node {
          title {
            id
            titleText { text }
            originalTitleText { text }
            releaseYear { year }
            plot { plotText { plainText } }
            titleGenres { genres { genre { text } } }
            ratingsSummary { voteCount }
          }
        }
      }
    }
  }
}
"""
# Parallel rating searches sometimes fail to resolve the host on the first
# burst; retrying the connection is enough.
_session = requests.Session()
_session.mount(
    "https://", HTTPAdapter(max_retries=Retry(connect=3, backoff_factor=0.5))
)

RATING_QUERY = """
query RatingByTitle($term: String!, $start: Date!, $end: Date!) {
  advancedTitleSearch(
    first: 5
    constraints: {
      titleTextConstraint: { searchTerm: $term }
      releaseDateConstraint: { releaseDateRange: { start: $start, end: $end } }
      titleTypeConstraint: { anyTitleTypeIds: ["movie", "tvMovie", "tvMiniSeries"] }
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
          ratingsSummary { aggregateRating }
        }
      }
    }
  }
}
"""

IMAGES_QUERY = """
query TitleImages($id: ID!) {
  title(id: $id) {
    images(first: 50) {
      edges { node { url width height type } }
    }
  }
}
"""

LOCALIZED_TITLE_QUERY = """
query LocalizedTitle($id: ID!) {
  title(id: $id) {
    titleText { text }
    originalTitleText { text }
  }
}
"""
# The API localizes `titleText` by these headers; the default ones (US) give
# the English title the scraper already stores.
BRAZIL_HEADERS = {
    **HEADERS,
    "x-imdb-user-country": "BR",
    "x-imdb-user-language": "pt-BR",
}

SERIES_QUERY = """
query Series($id: ID!) {
  title(id: $id) {
    id
    titleType { id }
    titleText { text }
    originalTitleText { text }
    releaseYear { year endYear }
    plot { plotText { plainText } }
    titleGenres { genres { genre { text } } }
    primaryImage { url }
    ratingsSummary { aggregateRating }
    episodes {
      seasons { number }
      episodes(first: 1) { total }
    }
    principalCredits(filter: { categories: ["creator", "cast"] }) {
      category { id }
      credits { name { nameText { text } } }
    }
  }
}
"""
SERIES_TYPES = ("tvSeries", "tvMiniSeries")
# IMDB resizes posters on the fly from the URL; the list needs small ones.
POSTER_WIDTH = 400

# Stills at least this much wider than tall work as a banner.
BACKDROP_MIN_RATIO = 1.4
# IMDB resizes on the fly from the URL; the originals can be 5000px wide.
BACKDROP_WIDTH = 1600


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

    edges = _search(
        SEARCH_QUERY,
        {"keyword": slug, "first": first},
        f"keyword search for {slug!r}",
    )
    movies = [_movie(edge["node"]["title"]) for edge in edges]
    logger.info("IMDB keyword %r: %d movies", slug, len(movies))
    return movies


def search_movies_by_director(name, first=15):
    """Up to `first` movies directed by the person called `name`, the most
    voted on IMDB first.

    IMDB's name search is fuzzy, so only a person whose name is the same once
    accents, punctuation and case are dropped counts. Returns [] when nobody
    has that name or they directed no movie.
    """
    wanted = _normalize(name)
    if not wanted:
        return []

    body = _post(DIRECTOR_QUERY, {"name": name.strip()}, f"name search for {name!r}")
    edges = _text(body, "data", "mainSearch", "edges") or []
    person = next(
        (
            edge["node"]["entity"]
            for edge in edges
            if _normalize(_text(edge["node"]["entity"], "nameText", "text")) == wanted
        ),
        None,
    )
    if not person:
        return []

    body = _post(DIRECTED_QUERY, {"id": person["id"]}, f"movies directed by {name!r}")
    edges = _text(body, "data", "name", "credits", "edges") or []
    titles = sorted(
        (edge["node"]["title"] for edge in edges),
        key=lambda t: -(_text(t, "ratingsSummary", "voteCount") or 0),
    )
    movies = [_movie(title) for title in titles[:first]]
    logger.info("IMDB director %r (%s): %d movies", name, person["id"], len(movies))
    return movies


def find_rating(title, year):
    """IMDB rating and tconst of the movie called `title` released in `year`.

    IMDB's search is fuzzy, so only a candidate whose title is the same once
    accents, punctuation and case are dropped counts; the closest year wins
    (catalogs often disagree with IMDB by one year). Returns
    `{"tconst", "rating"}`, or None when nothing matches.
    """
    wanted = _normalize(title)
    if not wanted or not year:
        return None

    edges = _search(
        RATING_QUERY,
        {"term": title.strip(), "start": f"{year - 1}-01-01", "end": f"{year + 1}-12-31"},
        f"rating search for {title!r} ({year})",
    )
    candidates = [
        edge["node"]["title"]
        for edge in edges
        if wanted
        in (
            _normalize(_text(edge["node"]["title"], "titleText", "text")),
            _normalize(_text(edge["node"]["title"], "originalTitleText", "text")),
        )
    ]
    if not candidates:
        return None

    best = min(
        candidates,
        key=lambda t: abs((_text(t, "releaseYear", "year") or 0) - year),
    )
    return {
        "tconst": best["id"],
        "rating": _text(best, "ratingsSummary", "aggregateRating"),
    }


def find_backdrop(tconst):
    """URL of the widest landscape still of `tconst`, for a banner.

    Only `still_frame` images count: posters and DVD covers are portrait and
    publicity photos are often collages. None when the movie has no
    landscape still.
    """
    body = _post(IMAGES_QUERY, {"id": tconst}, f"images of {tconst}")
    edges = _text(body, "data", "title", "images", "edges") or []
    stills = [
        edge["node"]
        for edge in edges
        if edge["node"].get("type") == "still_frame"
        and edge["node"].get("width")
        and edge["node"].get("height")
        and edge["node"]["width"] / edge["node"]["height"] >= BACKDROP_MIN_RATIO
    ]
    if not stills:
        return None

    url = max(stills, key=lambda node: node["width"])["url"]
    return url.replace("._V1_.", f"._V1_UX{BACKDROP_WIDTH}_.")


def find_brazilian_title(tconst):
    """Title of `tconst` as released in Brazil ("The Party" -> "Um Convidado
    Bem Trapalhão"). None when IMDB has no Brazilian title, in which case it
    answers the original one."""
    body = _post(
        LOCALIZED_TITLE_QUERY,
        {"id": tconst},
        f"Brazilian title of {tconst}",
        headers=BRAZIL_HEADERS,
    )
    title = _text(body, "data", "title")
    localized = _text(title, "titleText", "text")
    original = _text(title, "originalTitleText", "text")
    if not localized or localized == original:
        return None
    return localized


def find_series(tconst):
    """The TV series `tconst` as IMDB describes it, for the series list.

    None when IMDB has no such title. A title that exists but is not a
    series (a movie, an episode) comes back with `is_series` False so the
    caller can refuse it with a clear message.
    """
    body = _post(SERIES_QUERY, {"id": tconst}, f"series {tconst}")
    title = _text(body, "data", "title")
    if not title:
        return None

    credits = {
        _text(group, "category", "id"): [
            _text(credit, "name", "nameText", "text")
            for credit in group.get("credits") or []
        ]
        for group in title.get("principalCredits") or []
    }
    poster = _text(title, "primaryImage", "url") or ""
    return {
        "tconst": title["id"],
        "is_series": _text(title, "titleType", "id") in SERIES_TYPES,
        "primaryTitle": _text(title, "titleText", "text") or "",
        "originalTitle": _text(title, "originalTitleText", "text") or "",
        "startYear": _text(title, "releaseYear", "year"),
        "endYear": _text(title, "releaseYear", "endYear"),
        "plot": _text(title, "plot", "plotText", "plainText") or "",
        "genres": [
            genre["genre"]["text"]
            for genre in _text(title, "titleGenres", "genres") or []
        ],
        "poster_url": poster.replace("._V1_.", f"._V1_UX{POSTER_WIDTH}_."),
        "imdb_rating": _text(title, "ratingsSummary", "aggregateRating"),
        "seasons": len(_text(title, "episodes", "seasons") or []),
        "episodes": _text(title, "episodes", "episodes", "total") or 0,
        "creators": credits.get("creator", []),
        "stars": credits.get("cast", []),
    }


def _search(query, variables, what):
    """Edges of an advancedTitleSearch; IMDBSearchError when IMDB fails."""
    body = _post(query, variables, what)
    return body.get("data", {}).get("advancedTitleSearch", {}).get("edges") or []


def _post(query, variables, what, headers=HEADERS):
    """Body of a GraphQL answer; IMDBSearchError when IMDB fails."""
    try:
        response = _session.post(
            GRAPHQL_URL,
            json={"query": query, "variables": variables},
            headers=headers,
            timeout=HTTP_TIMEOUT,
        )
        response.raise_for_status()
        body = response.json()
    except (requests.RequestException, ValueError) as e:
        raise IMDBSearchError(f"{what} failed: {e}") from e

    if body.get("errors"):
        raise IMDBSearchError(f"{what} failed: {body['errors']}")

    return body


def _normalize(title):
    """"The Cook, the Thief, His Wife &Her Lover" -> "thecookthethiefhiswifeherlover"."""
    text = unicodedata.normalize("NFKD", str(title or ""))
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", "", text.lower())


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
