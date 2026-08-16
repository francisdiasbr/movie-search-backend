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
    if not soup:
        return None

    plot_span = soup.find("span", {"data-testid": "plot-xs_to_m"})
    return plot_span.get_text() if plot_span else None


def get_movie_country(tconst):
    soup = fetch_soup(tconst)
    if not soup:
        return None

    details = soup.find("div", {"data-testid": "title-details-section"})
    origin = details.find("li", {"data-testid": "title-details-origin"}) if details else None
    inline_list = origin.find("ul", {"class": "ipc-inline-list"}) if origin else None
    link = inline_list.find("a") if inline_list else None
    return link.get_text(strip=True) if link else None


def get_movie_trivia(tconst):
    soup = fetch_soup(tconst, "trivia")
    if not soup:
        return None

    entries = [
        div.get_text(separator=" ", strip=True)
        for div in soup.find_all("div", {"class": "ipc-html-content-inner-div"})[:5]
    ]
    return "\n\n".join(entries) or None


def get_movie_quote(tconst):
    soup = fetch_soup(tconst, "quotes")
    if not soup:
        return None

    first = soup.find("div", {"class": "ipc-html-content-inner-div"})
    quote = first.find("ul") if first else None
    return quote.get_text(separator=" ", strip=True) if quote else None


def get_movie_plot_keywords(tconst):
    soup = fetch_soup(tconst, "keywords")
    if not soup:
        return None

    items = soup.find_all("li", {"data-testid": "list-summary-item"})
    return [item.find("a").get_text() for item in items if item.find("a")] or None


def _principal_credit(soup, index, tconst):
    """Returns the nth principal credit section: 0 director, 1 writers, 2 stars."""
    credits = soup.find_all("li", {"data-testid": "title-pc-principal-credit"})
    if len(credits) <= index:
        logger.warning(
            "Only %d credit sections on %s, expected at least %d",
            len(credits),
            tconst,
            index + 1,
        )
        return None
    return credits[index]


def get_director(tconst):
    soup = fetch_soup(tconst)
    if not soup:
        return None

    section = _principal_credit(soup, 0, tconst)
    link = section.find("a", {"class": "ipc-metadata-list-item__list-content-item--link"}) if section else None
    return link.get_text(strip=True) if link else None


def get_writers(tconst):
    soup = fetch_soup(tconst)
    if not soup:
        return None

    section = _principal_credit(soup, 1, tconst)
    if not section:
        return None

    links = section.find_all("a", {"class": "ipc-metadata-list-item__list-content-item--link"})
    return [link.get_text(strip=True) for link in links] or None


def get_movie_principal_stars(tconst):
    soup = fetch_soup(tconst)
    if not soup:
        return None

    section = _principal_credit(soup, 2, tconst)
    if not section:
        return None

    links = section.select(
        "ul.ipc-inline-list a.ipc-metadata-list-item__list-content-item--link"
    )
    if not links:
        logger.warning("No star links on %s", tconst)
        return None

    return [link.get_text(strip=True) for link in links]


def get_movie_genres(tconst):
    soup = fetch_soup(tconst)
    if not soup:
        return None

    interests = soup.find("div", {"data-testid": "interests"})
    if not interests:
        return None

    spans = interests.find_all("span", {"class": "ipc-chip__text"})
    return [span.get_text() for span in spans] or None


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
