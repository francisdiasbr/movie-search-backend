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

# Perfil do Chromium reaproveitado entre execuções. Guarda os cookies do IMDB,
# incluindo o token do AWS WAF obtido na verificação manual (ver imdb_verify.py).
PROFILE_DIR = os.getenv(
    "IMDB_PROFILE_DIR", os.path.expanduser("~/.cache/movie-search/imdb-profile")
)
HEADLESS = os.getenv("IMDB_HEADLESS", "1") != "0"
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"

# Intervalo mínimo entre dois carregamentos de página, com jitter.
MIN_INTERVAL = float(os.getenv("IMDB_MIN_INTERVAL", "1.5"))

# Tempo de vida da soup em cache. Cobre com folga um favorite_movie inteiro e
# expira sozinho, evitando servir página velha em cadastros posteriores.
CACHE_TTL = float(os.getenv("IMDB_CACHE_TTL", "600"))

# WAF challenges are usually transient, so a page is retried before being given
# up on. Once every attempt is challenged the session is likely really stale,
# and the cooldown makes the remaining scrapers of the same request fail fast
# instead of hitting the captcha one by one.
WAF_ATTEMPTS = int(os.getenv("IMDB_WAF_ATTEMPTS", "3"))
WAF_RETRY_DELAY = float(os.getenv("IMDB_WAF_RETRY_DELAY", "3"))
WAF_COOLDOWN = float(os.getenv("IMDB_WAF_COOLDOWN", "300"))

_cache = {}
_cache_lock = threading.Lock()
_blocked_until = 0.0

# Toda navegação passa por uma única thread dona do Playwright: a API síncrona
# não pode ser usada de outra thread além da que a criou, e o Chromium tranca o
# diretório de perfil, então não dá para abrir o mesmo perfil em paralelo.
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
    global _blocked_until
    with _cache_lock:
        _cache.clear()
        _blocked_until = 0.0


def fetch_soup(tconst, path=""):
    global _blocked_until
    url = f"{BASE_URL}{tconst}/{path}"
    key = (tconst, path)
    now = time.monotonic()

    with _cache_lock:
        hit = _cache.get(key)
        if hit and now - hit[0] < CACHE_TTL:
            return hit[1]
        if now < _blocked_until:
            return None

    for attempt in range(1, WAF_ATTEMPTS + 1):
        try:
            html = _load_html(url)
            if html is None:
                logger.warning("Timed out waiting for %s", url)
                return None

            soup = BeautifulSoup(html, "html.parser")
            if _is_waf_challenge(soup):
                # The challenge is usually transient: the WAF token in the
                # profile stays valid and a retry goes through. Only give up -
                # and open the cooldown - once every attempt was challenged.
                if attempt < WAF_ATTEMPTS:
                    logger.warning(
                        "WAF challenge on %s, retrying (%d/%d)", url, attempt, WAF_ATTEMPTS
                    )
                    time.sleep(WAF_RETRY_DELAY * attempt)
                    continue
                with _cache_lock:
                    _blocked_until = time.monotonic() + WAF_COOLDOWN
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
    base_url = "https://en.wikipedia.org/wiki/"
    movie_title_formatted = movie_title.replace(" ", "_")
    url = f"{base_url}{movie_title_formatted}"
    response = requests.get(url, headers=HEADERS)

    if response.status_code == 200:
        return url
    return "Wikipedia page not found"


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
    if soup:
        try:
            print("Soup fetched successfully.")

            # Encontrar todas as seções de créditos principais
            credit_sections = soup.find_all(
                "li", {"data-testid": "title-pc-principal-credit"}
            )
            print(f"Found {len(credit_sections)} credit sections")

            # Procurar pela seção específica de Stars (geralmente é a terceira seção)
            if len(credit_sections) >= 3:
                stars_section = credit_sections[2]  # índice 2 é o terceiro elemento

                # Encontrar todos os links dos atores dentro da ul específica
                star_links = stars_section.select(
                    "ul.ipc-inline-list a.ipc-metadata-list-item__list-content-item--link"
                )
                if star_links:
                    # Extrair os nomes das estrelas
                    stars = [link.get_text(strip=True) for link in star_links]
                    return stars if stars else ["Stars not available"]
                else:
                    print("No star links found in the section")
            else:
                print(
                    f"Not enough credit sections found (expected 3, got {len(credit_sections)})"
                )

        except Exception as e:
            print(f"Error extracting stars: {e}")
            print(f"Error type: {type(e)}")
            import traceback

            print(traceback.format_exc())
    else:
        print("Failed to fetch soup.")
        return None


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
        print(soup.prettify()[:1000])
    else:
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
                print(f"[SCRAPPER] poster via data-testid={testid}: {img['src'][:60]}")
                return img["src"]

    # 2. overlay com aria-label contendo "poster" ou "pôster"
    for overlay in soup.find_all("a", class_="ipc-lockup-overlay"):
        label = (overlay.get("aria-label") or "").lower()
        if "poster" in label or "pôster" in label:
            parent = overlay.find_parent()
            if parent:
                img = parent.find("img", class_="ipc-image")
                if img and img.get("src"):
                    print(f"[SCRAPPER] poster via aria-label: {img['src'][:60]}")
                    return img["src"]

    # 3. primeira ipc-image dentro de ipc-poster
    poster_div = soup.find(class_="ipc-poster")
    if poster_div:
        img = poster_div.find("img", class_="ipc-image")
        if img and img.get("src"):
            print(f"[SCRAPPER] poster via ipc-poster: {img['src'][:60]}")
            return img["src"]

    print(f"[SCRAPPER] poster não encontrado para {tconst}")
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
