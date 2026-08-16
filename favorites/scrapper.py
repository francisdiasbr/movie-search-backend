from bs4 import BeautifulSoup
import atexit
import logging
import os
import queue
import random
import requests
import threading
import time
from playwright.sync_api import sync_playwright

logger = logging.getLogger(__name__)

BASE_URL = "https://www.imdb.com/title/"

# Chromium profile reused across runs. It holds the IMDB cookies, including the
# AWS WAF token from the manual verification (see imdb_verify.py).
PROFILE_DIR = os.path.expanduser("~/.cache/movie-search/imdb-profile")
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"

# The only knob worth flipping by hand: IMDB_HEADLESS=0 shows the browser while
# debugging a scraper.
HEADLESS = os.getenv("IMDB_HEADLESS", "1") != "0"

# Minimum gap between two page loads, plus jitter.
MIN_INTERVAL = 1.5

# How long a soup stays cached. Covers a whole favorite_movie with room to
# spare and expires on its own.
CACHE_TTL = 600

# WAF challenges are usually transient, so a page is retried before being given
# up on.
WAF_ATTEMPTS = 3
WAF_RETRY_DELAY = 3

_cache = {}
_cache_lock = threading.Lock()

# Every page load goes through a single thread that owns Playwright: the sync
# API cannot be used from a thread other than the one that created it, and
# Chromium locks the profile directory, so it cannot be opened in parallel.
_jobs = queue.Queue()
_worker = None
_worker_lock = threading.Lock()


def _browser_loop():
    pw = sync_playwright().start()
    context = pw.chromium.launch_persistent_context(
        PROFILE_DIR,
        headless=HEADLESS,
        locale="en-US",
        user_agent=USER_AGENT,
        viewport={"width": 1280, "height": 800},
    )
    last_request = 0.0
    try:
        while True:
            job = _jobs.get()
            if job is None:
                break
            url, box, done = job
            try:
                wait = MIN_INTERVAL - (time.monotonic() - last_request)
                if wait > 0:
                    time.sleep(wait + random.uniform(0, 0.5))
                page = context.new_page()
                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=30000)
                    page.wait_for_selector(
                        "[data-testid='hero__pageTitle'], [data-testid='title-details-section'], h1",
                        timeout=15000,
                    )
                    box["html"] = page.content()
                finally:
                    last_request = time.monotonic()
                    page.close()
            except Exception as e:
                box["error"] = e
            finally:
                done.set()
    finally:
        try:
            context.close()
        finally:
            pw.stop()


def _ensure_worker():
    global _worker
    with _worker_lock:
        if _worker is None or not _worker.is_alive():
            os.makedirs(PROFILE_DIR, exist_ok=True)
            _worker = threading.Thread(target=_browser_loop, daemon=True)
            _worker.start()
            atexit.register(_shutdown)


def _shutdown():
    _jobs.put(None)


def _load_html(url):
    _ensure_worker()
    box, done = {}, threading.Event()
    _jobs.put((url, box, done))
    done.wait(90)
    if "error" in box:
        raise box["error"]
    return box.get("html")


def _is_waf_challenge(soup):
    title = soup.title.string if soup.title else ""
    return "human verification" in (title or "").lower()


def clear_soup_cache():
    with _cache_lock:
        _cache.clear()


def fetch_soup(tconst, path=""):
    url = f"{BASE_URL}{tconst}/{path}"
    key = (tconst, path)
    now = time.monotonic()

    with _cache_lock:
        hit = _cache.get(key)
        if hit and now - hit[0] < CACHE_TTL:
            return hit[1]

    for attempt in range(1, WAF_ATTEMPTS + 1):
        try:
            html = _load_html(url)
            if html is None:
                logger.warning("Timed out waiting for %s", url)
                return None

            soup = BeautifulSoup(html, "html.parser")
            if _is_waf_challenge(soup):
                # The challenge is usually transient: the WAF token in the
                # profile stays valid and a retry goes through.
                if attempt < WAF_ATTEMPTS:
                    logger.warning(
                        "WAF challenge on %s, retrying (%d/%d)", url, attempt, WAF_ATTEMPTS
                    )
                    time.sleep(WAF_RETRY_DELAY * attempt)
                    continue
                logger.error(
                    "%s blocked by IMDB's AWS WAF after %d attempts. "
                    "Run 'python imdb_verify.py' to renew the session.",
                    url,
                    WAF_ATTEMPTS,
                )
                return None

            logger.info("Loaded %s", url)
            with _cache_lock:
                _cache[key] = (time.monotonic(), soup)
            return soup
        except Exception as e:
            logger.error("Could not load %s: %s", url, e)
            return None


def get_wikipedia_url(movie_title):
    url = f"https://en.wikipedia.org/wiki/{movie_title.replace(' ', '_')}"
    try:
        response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=10)
    except requests.RequestException as e:
        logger.warning("Could not reach Wikipedia for %s: %s", movie_title, e)
        return None

    return url if response.status_code == 200 else None


def get_movie_sm_plot(tconst):
    soup = fetch_soup(tconst)
    if soup:
        plot_span = soup.find("span", {"data-testid": "plot-xs_to_m"})
        if plot_span:
            plot_text = plot_span.get_text()
            return plot_text if plot_text else "Plot not available"
    return "Plot not available"


def get_movie_country(tconst):
    soup = fetch_soup(tconst)
    if soup:
        country_div = soup.find("div", {"data-testid": "title-details-section"})
        if country_div:
            origin_li = country_div.find("li", {"data-testid": "title-details-origin"})
            if origin_li:
                ul_inline_list = origin_li.find("ul", {"class": "ipc-inline-list"})
                if ul_inline_list:
                    country_link = ul_inline_list.find("a")
                    if country_link:
                        return country_link.get_text(strip=True)
            return "Country not available"
    return "Country not available"


def get_movie_trivia(tconst):
    soup = fetch_soup(tconst, "trivia")
    if soup:
        content_divs = soup.find_all("div", {"class": "ipc-html-content-inner-div"})
        trivia = [
            content_div.get_text(separator=" ", strip=True)
            for content_div in content_divs[:5]
        ]
        return "\n\n".join(trivia) if trivia else "Trivia not available"
    return "Trivia not available"


def get_movie_quote(tconst):
    soup = fetch_soup(tconst, "quotes")
    if soup:
        content_divs = soup.find_all("div", {"class": "ipc-html-content-inner-div"})
        quotes = []
        for content_div in content_divs[:1]:
            ul_tag = content_div.find("ul")
            if ul_tag:
                quote_text = ul_tag.get_text(separator=" ", strip=True)
                quotes.append(quote_text)
        return "\n\n".join(quotes) if quotes else "Quote not available"
    return "Quote not available"


def get_movie_plot_keywords(tconst):
    soup = fetch_soup(tconst, "keywords")
    if soup:
        keywords_list = soup.find_all("li", {"data-testid": "list-summary-item"})
        keywords = [
            item.find("a").get_text() for item in keywords_list if item.find("a")
        ]
        return keywords if keywords else ["Keywords not available"]
    return ["Error retrieving keywords"]


def get_director(tconst):
    soup = fetch_soup(tconst)
    if soup:
        director_section = soup.find_all(
            "li", {"data-testid": "title-pc-principal-credit"}
        )[0]
        if director_section:
            director_link = director_section.find(
                "a", {"class": "ipc-metadata-list-item__list-content-item--link"}
            )
            if director_link:
                return director_link.get_text(strip=True)
    return "Director not available"


def get_writers(tconst):
    soup = fetch_soup(tconst)
    if soup:
        writers_section = soup.find_all(
            "li", {"data-testid": "title-pc-principal-credit"}
        )[1]
        if writers_section:
            writers_links = writers_section.find_all(
                "a", {"class": "ipc-metadata-list-item__list-content-item--link"}
            )
            writers = [link.get_text(strip=True) for link in writers_links]
            return writers if writers else ["Writers not available"]
    return ["Error retrieving writers"]


def get_movie_principal_stars(tconst):
    soup = fetch_soup(tconst)
    if not soup:
        return None

    # Stars are the third principal credit, after director and writers.
    credits = soup.find_all("li", {"data-testid": "title-pc-principal-credit"})
    if len(credits) < 3:
        logger.warning("Only %d credit sections on %s, expected 3", len(credits), tconst)
        return None

    links = credits[2].select(
        "ul.ipc-inline-list a.ipc-metadata-list-item__list-content-item--link"
    )
    if not links:
        logger.warning("No star links on %s", tconst)
        return None

    return [link.get_text(strip=True) for link in links]


def get_movie_genres(tconst):
    soup = fetch_soup(tconst)
    if soup:
        genres_div = soup.find("div", {"data-testid": "interests"})
        if genres_div:
            genre_spans = genres_div.find_all("span", {"class": "ipc-chip__text"})
            genres = [span.get_text() for span in genre_spans]
            return genres if genres else ["Genres not available"]
    return ["Error retrieving genres"]


def get_movie_title(tconst):
    soup = fetch_soup(tconst)
    if soup:
        h1 = soup.find("h1", {"data-testid": "hero__pageTitle"})
        if h1:
            span = h1.find("span", {"data-testid": "hero__primary-text"})
            if span:
                return span.get_text(strip=True)
            return h1.get_text(strip=True)
        logger.warning("No title heading on %s", tconst)
    return None


def get_movie_poster(tconst):
    soup = fetch_soup(tconst)
    if not soup:
        return None

    # 1. data-testid no container do hero poster
    for testid in ("hero-media__poster", "hero__poster"):
        container = soup.find(attrs={"data-testid": testid})
        if container:
            img = container.find("img")
            if img and img.get("src"):
                logger.debug("Poster of %s via data-testid=%s", tconst, testid)
                return img["src"]

    # 2. overlay com aria-label contendo "poster" ou "pôster"
    for overlay in soup.find_all("a", class_="ipc-lockup-overlay"):
        label = (overlay.get("aria-label") or "").lower()
        if "poster" in label or "pôster" in label:
            parent = overlay.find_parent()
            if parent:
                img = parent.find("img", class_="ipc-image")
                if img and img.get("src"):
                    logger.debug("Poster of %s via aria-label", tconst)
                    return img["src"]

    # 3. primeira ipc-image dentro de ipc-poster
    poster_div = soup.find(class_="ipc-poster")
    if poster_div:
        img = poster_div.find("img", class_="ipc-image")
        if img and img.get("src"):
            logger.debug("Poster of %s via ipc-poster", tconst)
            return img["src"]

    logger.warning("No poster found for %s", tconst)
    return None


def get_movie_year(tconst):
    soup = fetch_soup(tconst)
    if soup:
        h1 = soup.find("h1", {"data-testid": "hero__pageTitle"})
        if h1:
            ul = h1.find_next("ul", {"class": "ipc-inline-list"})
            if ul:
                li = ul.find("li", {"class": "ipc-inline-list__item"})
                if li:
                    year_text = li.get_text(strip=True)
                    try:
                        return int(year_text)
                    except ValueError:
                        return year_text
    return None
