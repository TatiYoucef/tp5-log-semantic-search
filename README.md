# TP5 - Recherche Semantique et Analytique sur Logs Massifs

Projet Big Data en Python pour ingerer, normaliser, vectoriser et interroger les logs OpenSSH de LogHub-2.0. Le dataset local contient 638 947 entrees brutes, un CSV structure et les templates d'evenements.

## Architecture

```text
data/raw/OpenSSH
   -> Spark preprocessing
   -> data/processed/*.csv + *.parquet
   -> PostgreSQL + pgvector
   -> FastAPI
   -> Streamlit
```

Technologies imposees et utilisees : Python, Apache Spark, PostgreSQL, pgvector, Sentence-Transformers. L'interface de demonstration repose sur FastAPI et Streamlit.

## Installation

```bash
./setup.sh
docker compose up -d
source venv/bin/activate
```

Le script utilise par defaut le venv du projet `./venv`; il ne cree pas de nouvel environnement. Installation manuelle equivalente :

```bash
source venv/bin/activate
python -m pip install -r requirements.txt
python -m pip install -e .
cp -n .env.example .env
```

## Pipeline complet

Execution rapide sur echantillon :

```bash
tp5-log-search run-pipeline --limit 10000
```

Execution complete sur les 638 947 logs :

```bash
tp5-log-search run-pipeline
```

Etapes separees :

```bash
tp5-log-search prepare-data
tp5-log-search init-db
tp5-log-search load-db
tp5-log-search embed
tp5-log-search index
tp5-log-search stats
tp5-log-search benchmark --query "failed password invalid user"
tp5-log-search compare-models --query "authentication failure"
```

La commande `embed` vectorise les messages normalises distincts avec `sentence-transformers/all-MiniLM-L6-v2` dans la table `message_embeddings`. Les logs massifs restent dans `log_entries` et sont relies aux vecteurs par `normalized_message`, ce qui evite de dupliquer le meme vecteur des milliers de fois.

La commande `benchmark` affiche les metriques de volume, taille disque, derniers temps de pipeline, latence de requete et qualite top-k. La qualite top-k est un score proxy base sur la similarite moyenne et la concentration des resultats autour des memes evenements/templates.

La commande `compare-models` compare `all-MiniLM-L6-v2`, `multi-qa-MiniLM-L6-cos-v1` et `all-mpnet-base-v2` sur les memes messages/templates normalises. Cette comparaison est faite en memoire afin de supporter aussi `all-mpnet-base-v2`, dont les vecteurs ont 768 dimensions alors que l'index pgvector de production utilise `vector(384)`.

## API et interface

Lancer l'API :

```bash
tp5-log-search serve-api --host 127.0.0.1 --port 8000
```

Lancer l'interface web :

```bash
tp5-log-search serve-web --port 8501
```

Endpoints principaux :

```text
GET  /health
GET  /stats
GET  /benchmark
POST /benchmark/query
POST /benchmark/models
POST /search/semantic
POST /search/keyword
POST /search/compare
GET  /logs/{id}/similar
GET  /analytics/frequent-errors
GET  /analytics/timeline
```

## Structure

```text
src/tp5_log_search/
  api.py             API FastAPI
  analytics.py       analyses recurrentes et temporelles
  benchmarks.py      metriques de performance et qualite top-k
  cli.py             commandes reproductibles
  config.py          configuration .env
  db.py              PostgreSQL, COPY, index pgvector
  embeddings.py      Sentence-Transformers
  search.py          recherche semantique et mots-cles
  spark_pipeline.py  preprocessing Spark
  text.py            parsing et normalisation OpenSSH
  web_app.py         interface Streamlit

sql/schema.sql       schema PostgreSQL + pgvector
reports/             rapport LaTeX
tests/               tests unitaires
```

## Rapport

Compiler le rapport technique :

```bash
tp5-log-search build-report
```

Le PDF attendu est `reports/rapport_tp5.pdf`.

## Tests

```bash
pytest
```

Les tests unitaires couvrent le parsing OpenSSH, la normalisation, la classification de niveau, la conversion pgvector et le parsing CLI. Les tests d'integration se valident via `run-pipeline --limit 10000`.
