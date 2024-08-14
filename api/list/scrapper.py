from bs4 import BeautifulSoup
import requests

def get_movie_sm_plot(tconst):
    url = f"https://m.imdb.com/title/{tconst}/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "html.parser")
        plot_span = soup.find("span", {"data-testid": "plot-xs_to_m"})
        if plot_span:
            plot_text = plot_span.get_text()
            return plot_text if plot_text else "Plot not available"
    return "Plot not available"

def get_movie_quote(tconst):
    url = f"https://m.imdb.com/title/{tconst}/quotes/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "html.parser")
        content_divs = soup.find_all("div", {"class": "ipc-html-content-inner-div"})

        quotes = []
        for content_div in content_divs[:2]:  # Limita a captura às 2 primeiras divs
            ul_tag = content_div.find("ul")
            if ul_tag:
                quote_text = ul_tag.get_text(separator=" ", strip=True)
                quotes.append(quote_text)

        # Retorna todas as citações concatenadas ou uma mensagem padrão se nenhuma for encontrada
        return "\n\n".join(quotes) if quotes else "Quote not available"
    return "Quote not available"

def get_wikipedia_url(movie_title):
    base_url = f"https://en.wikipedia.org/wiki/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    movie_title_formatted = movie_title.replace(" ", "_")
    url = f"{base_url}{movie_title_formatted}"
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        return url 
    return "Wikipedia page not found"