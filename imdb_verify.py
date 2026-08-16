"""Abre o IMDB numa janela visível para a verificação humana do AWS WAF.

O navegador usa o mesmo perfil do scrapper, então os cookies obtidos aqui
valem para os cadastros seguintes. O backend precisa estar parado: o Chromium
tranca o diretório de perfil e só aceita um processo por vez.

    python imdb_verify.py [tconst]
"""

import sys

from playwright.sync_api import sync_playwright

from favorites.scrapper import BASE_URL, PROFILE_DIR, USER_AGENT

tconst = sys.argv[1] if len(sys.argv) > 1 else "tt0032138"
url = f"{BASE_URL}{tconst}/"

print(f"Perfil: {PROFILE_DIR}")
print(f"Abrindo {url}")

with sync_playwright() as pw:
    context = pw.chromium.launch_persistent_context(
        PROFILE_DIR,
        headless=False,
        locale="en-US",
        user_agent=USER_AGENT,
        viewport={"width": 1280, "height": 800},
    )
    page = context.pages[0] if context.pages else context.new_page()
    page.goto(url, wait_until="domcontentloaded", timeout=60000)

    print()
    print("Resolva a verificação na janela do navegador, se ela aparecer,")
    print("e aguarde a página do filme carregar. Depois volte aqui.")
    input("Pressione Enter para salvar a sessão e fechar... ")

    title = page.title()
    print(f"Título da página: {title}")
    if "human verification" in title.lower():
        print("A verificação ainda não passou — a sessão não foi validada.")
    else:
        print("Sessão validada e gravada no perfil.")

    context.close()
