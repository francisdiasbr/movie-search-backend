## Como utilizar

### instale o ambiente local (uma vez)
python3 -m venv venv

### ative o ambiente local 
source venv/bin/activate
source venv/bin/deactivate

### instale os requerimentos
pip install -r requirements.txt

### run
clear; python ingest_title_basics.py
clear; python ingest_title_ratings.py
clear; python ingest_title_crew.py
clear; python ingest_title principals.py
clear; python ingest_name_basics.py