import csv
import sys
import os

# Adiciona o diretório pai ao path para importar config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import get_mongo_collection


def import_watchlist_from_csv(csv_path):
    """Importa a watchlist do CSV para o MongoDB"""
    collection = get_mongo_collection("recommendations")
    
    # Limpa a collection antes de importar
    print("Limpando collection existente...")
    result = collection.delete_many({})
    print(f"Removidos {result.deleted_count} documentos existentes")
    
    movies_imported = 0
    
    try:
        with open(csv_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            
            for row in reader:
                # Prepara o documento para inserir
                movie_doc = {
                    "position": int(row.get("Position", 0)),
                    "tconst": row.get("Const", ""),
                    "title": row.get("Title", ""),
                    "original_title": row.get("Original Title", ""),
                    "year": row.get("Year", ""),
                    "director": row.get("Directors", ""),
                    "genres": row.get("Genres", ""),
                    "imdb_rating": row.get("IMDb Rating", ""),
                    "runtime": row.get("Runtime (mins)", ""),
                    "num_votes": row.get("Num Votes", ""),
                    "release_date": row.get("Release Date", ""),
                    "url": row.get("URL", ""),
                    "title_type": row.get("Title Type", ""),
                    "your_rating": row.get("Your Rating", ""),
                    "date_rated": row.get("Date Rated", ""),
                }
                
                # Remove campos vazios
                movie_doc = {k: v for k, v in movie_doc.items() if v}
                
                # Insere no MongoDB
                collection.insert_one(movie_doc)
                movies_imported += 1
                
                if movies_imported % 10 == 0:
                    print(f"Importados {movies_imported} filmes...")
        
        print(f"\n✅ Importação concluída! Total: {movies_imported} filmes")
        return movies_imported
        
    except FileNotFoundError:
        print(f"❌ Erro: Arquivo não encontrado: {csv_path}")
        return 0
    except Exception as e:
        print(f"❌ Erro ao importar: {e}")
        return 0


if __name__ == "__main__":
    # Caminho do CSV na pasta Downloads
    csv_path = os.path.expanduser("~/Downloads/1b366b7b-3ac7-4168-b389-3c836fb608ae.csv")
    
    if len(sys.argv) > 1:
        csv_path = sys.argv[1]
    
    print(f"Importando watchlist de: {csv_path}\n")
    import_watchlist_from_csv(csv_path)

