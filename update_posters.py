"""
Migration script: add poster_url to favorites that are missing it.
Updates both Atlas and Local MongoDB collections.

Usage:
    python update_posters.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from config import get_mongo_collection
from favorites.scrapper import get_movie_poster

TCONSTS_WITHOUT_POSTER = [
    "tt0109830",  # Forrest Gump
    "tt30144839", # Uma Batalha Após a Outra
    "tt31193180", # Pecadores
    "tt33612209", # O Diabo Veste Prada 2
    "tt0118799",  # A Vida é Bela
    "tt0070460",  # Day for Night
    "tt0107211",  # Indecent Proposal
    "tt6725014",  # Scenes from a Marriage
    "tt0032143",  # The Women
    "tt0079753",  # The Prisoner of Zenda
    "tt0043014",  # Sunset Boulevard
    "tt0042192",  # All About Eve
    "tt0025316",  # It Happened One Night
    "tt0070903",  # The Way We Were
    "tt0074119",  # All the President's Men
    "tt0033467",  # Citizen Kane
    "tt0075686",  # Annie Hall
    "tt0060196",  # The Good, the Bad and the Ugly
    "tt7068946",  # The Accountant 2
    "tt20215234", # Conclave
    "tt0084805",  # Tootsie
    "tt0072684",  # Barry Lyndon
    "tt0035140",  # Now, Voyager
    "tt14230458", # Poor Things
    "tt3783958",  # La La Land
    "tt1517268",  # Barbie
    "tt1235841",  # Sidewalls
    "tt0087781",  # The Natural
    "tt0059903",  # What's New Pussycat
    "tt0110912",  # Pulp Fiction
    "tt0108052",  # Schindler's List
    "tt0068646",  # The Godfather
    "tt0111161",  # The Shawshank Redemption
    "tt0054130",  # La Notte
    "tt0042593",  # In a Lonely Place
    "tt0045810",  # Gentlemen Prefer Blondes
    "tt14961016", # I'm Still Here
    "tt0061735",  # Guess Who's Coming to Dinner
    "tt0061385",  # Barefoot in the Park
    "tt0079100",  # The Electric Horseman
    "tt0080474",  # Brubaker
    "tt0055184",  # The Misfits
    "tt0061722",  # The Graduate
    "tt0381061",  # Casino Royale
    "tt0091167",  # Hannah and Her Sisters
    "tt0080610",  # The Last Metro
    "tt6263850",  # Deadpool & Wolverine
    "tt0053125",  # North by Northwest
    "tt0053472",  # Breathless
    "tt0082370",  # The Woman Next Door
    "tt0059319",  # The Ipcress File
    "tt0055572",  # A Woman Is a Woman
]


def update_poster(tconst, collection_atlas, collection_local):
    print(f"[{tconst}] Scraping poster...")
    poster_url = get_movie_poster(tconst)
    if not poster_url:
        print(f"[{tconst}] No poster found — skipping")
        return False

    collection_atlas.update_one({"tconst": tconst}, {"$set": {"poster_url": poster_url}})
    if collection_local is not None:
        collection_local.update_one({"tconst": tconst}, {"$set": {"poster_url": poster_url}})
    print(f"[{tconst}] Updated: {poster_url[:80]}...")
    return True


def main():
    collection_atlas = get_mongo_collection("favoritelist", use_atlas=True)
    collection_local = get_mongo_collection("favoritelist", use_atlas=False)

    if collection_atlas is None:
        print("Cannot connect to Atlas — aborting")
        sys.exit(1)

    succeeded = []
    failed = []

    total = len(TCONSTS_WITHOUT_POSTER)
    for i, tconst in enumerate(TCONSTS_WITHOUT_POSTER, 1):
        print(f"\n[{i}/{total}] Processing {tconst}")
        ok = update_poster(tconst, collection_atlas, collection_local)
        if ok:
            succeeded.append(tconst)
        else:
            failed.append(tconst)

    print(f"\n=== Done ===")
    print(f"Updated:  {len(succeeded)}/{total}")
    print(f"Failed:   {len(failed)}/{total}")
    if failed:
        print("Failed tconsts:")
        for t in failed:
            print(f"  {t}")


if __name__ == "__main__":
    main()
