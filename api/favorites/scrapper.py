from bs4 import BeautifulSoup
import requests

BASE_URL = "https://m.imdb.com/title/"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}


def fetch_soup(tconst, path=""):
    url = f"{BASE_URL}{tconst}/{path}"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        return BeautifulSoup(response.text, "html.parser")
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


def get_movie_poster(tconst):
    soup = fetch_soup(tconst)
    if soup:
        poster_div = soup.find("div", {"class": "ipc-poster"})
        if poster_div:
            poster_img = poster_div.find("img", {"class": "ipc-image"})
            if poster_img:
                return poster_img["src"] if poster_img else "Poster not available"
    return "Poster not available"


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
        trivia = [content_div.get_text(separator=" ", strip=True) for content_div in content_divs[:5]]
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
        keywords = [item.find("a").get_text() for item in keywords_list if item.find("a")]
        return keywords if keywords else ["Keywords not available"]
    return ["Error retrieving keywords"]


def get_director(tconst):
    soup = fetch_soup(tconst)
    if soup:
        director_section = soup.find_all("li", {"data-testid": "title-pc-principal-credit"})[0]
        if director_section:
            director_link = director_section.find("a", {"class": "ipc-metadata-list-item__list-content-item--link"})
            if director_link:
                return director_link.get_text(strip=True)
    return "Director not available"


def get_writers(tconst):
    soup = fetch_soup(tconst)
    if soup:
        writers_section = soup.find_all("li", {"data-testid": "title-pc-principal-credit"})[1]
        if writers_section:
            writers_links = writers_section.find_all("a", {"class": "ipc-metadata-list-item__list-content-item--link"})
            writers = [link.get_text(strip=True) for link in writers_links]
            return writers if writers else ["Writers not available"]
    return ["Error retrieving writers"]


def get_movie_genres(tconst):
    soup = fetch_soup(tconst)
    if soup:
        genres_div = soup.find("div", {"data-testid": "interests"})
        if genres_div:
            genre_spans = genres_div.find_all("span", {"class": "ipc-chip__text"})
            genres = [span.get_text() for span in genre_spans]
            return genres if genres else ["Genres not available"]
    return ["Error retrieving genres"]


def get_movie_stars(tconst):
    soup = fetch_soup(tconst)
    if soup:
        stars_section = soup.find("li", {"class": "ipc-metadata-list-item--link", "data-testid": "title-pc-principal-credit"})
        if stars_section:
            stars_links = stars_section.find_all("a", {"class": "ipc-metadata-list-item__list-content-item--link"})
            stars = [link.get_text(strip=True) for link in stars_links]
            return stars if stars else ["Stars not available"]
    return ["Error retrieving stars"]

