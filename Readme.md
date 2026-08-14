# 📦 OCP DataFlow — Pipeline ETL de collecte de données agricoles & financières

Ce projet regroupe **6 collectors** chargés de récupérer automatiquement des données provenant de sources publiques (API, fichiers, config internes) : marchés financiers, production agricole, indices alimentaires, prix des matières premières, actualités et résultats financiers d'OCP. Les données sont ensuite **transformées**, **validées** (Pandera) et 
**chargées** dans un schéma en étoile PostgreSQL.

---

## 📁 Structure du projet

```
.
├── src/
│   ├── config/
│   │   ├── config.py                  # Clés API / tokens (via .env)
│   │   ├── auth.py                    # TokenManager — authentification Cognito (FAO)
│   │   ├── settings.py                # URLs et dossiers de sortie
│   │   ├── db_config.py               # Création de l'engine SQLAlchemy
│   │   └── ocp_financials.json        # Données trimestrielles OCP (source manuelle)
│   │
│   ├── etl/
│   │   ├── extract/
│   │   │   ├── extract_base.py        # Classe abstraite BaseCollector
│   │   │   ├── alpha_vantage_collector.py
│   │   │   ├── fao_collector.py
│   │   │   ├── ffpi_collector.py
│   │   │   ├── world_bank_collector.py
│   │   │   ├── news_collector.py
│   │   │   ├── ocp_financials.py
│   │   │   ├── state.py               # Suivi du dernier run réussi (last_success)
│   │   │   └── etl_state.json         # État persistant (par source)
│   │   │
│   │   ├── transform/
│   │   │   ├── io_utils.py
│   │   │   ├── transform_alpha.py
│   │   │   ├── transform_fao.py
│   │   │   ├── transform_ffpi.py
│   │   │   ├── transform_worldbank.py
│   │   │   ├── transform_news.py
│   │   │   └── transform_ocp.py
│   │   │
│   │   ├── load/
│   │   │   ├── db_writer.py           # upsert() générique (SQLAlchemy)
│   │   │   ├── load_dimensions.py
│   │   │   ├── load_facts.py
│   │   │   └── generate_dim_date.py
│   │   │
│   │   ├── quality_checks.py          # Schémas Pandera par table
│   │   └── main.py                    # Orchestration collect -> transform -> validate -> load
│   │
│   ├── logger_config.py               # Configuration du logging
│   └── run_etl.py                     # Point d'entrée (exécuté par le Dockerfile)
│
├── database/
│   └── schema.sql                     # Schéma PostgreSQL (schéma ocp_dataflow)
│
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .env.example                       # Modèle des variables d'environnement requises
├── .dockerignore
├── .gitignore
└── data/raw/...                       # Données collectées (générées à l'exécution)
```

> ⚠️ Tout le code applicatif vit sous `src/` et s'importe en tant que **paquet Python** (`from src.xxx import ...`), aussi bien en local qu'en Docker. C'est ce point précis qui a changé récemment (voir Changelog) — veillez à ne pas réintroduire d'imports « plats » type `from logger_config import ...`.

---

## 🧱 1. `BaseCollector` — la classe de base

Toutes les collectors héritent de `BaseCollector` (`src/etl/extract/extract_base.py`, classe abstraite `abc`).

**Constructeur** — initialise les attributs communs :

| Attribut      | Rôle                                                |
|---------------|------------------------------------------------------|
| `base_url`    | URL de base utilisée pour les requêtes               |
| `output_dir`  | Dossier où seront sauvegardées les données            |
| `logger`      | Logger dédié au collector (voir section logging)      |
| `timeout`     | Timeout HTTP (défaut : 15s)                           |
| `max_retries` | Nombre de tentatives en cas d'échec (défaut : 3)      |

**Méthodes principales :**

- **`_request_with_retry(url=None, **kwargs)`**
  Envoie une requête HTTP via `requests`, avec retry automatique sur erreurs serveur/réseau (backoff exponentiel `2**attempt`), et **sans retry** sur les erreurs client 4xx (401/403/404 — réessayer ne changerait rien). Retourne `Response` ou `None`.

- **`_safe_json(response, context="")`**
  Parse la réponse en JSON de façon sécurisée, retourne `None` si invalide (avec log d'erreur contextualisé).

- **`_save_json` / `_save_bytes` / `_save_dated_and_latest`**
  Sauvegarde des données en JSON ou binaire, avec double écriture (copie datée + copie `_latest` toujours écrasée) pour les sources qui en ont besoin.

- **`collect()`** et **`save()`** — méthodes abstraites, implémentées dans chaque sous-classe.

---

## 🪵 2. Logging — `get_logger()`

`src/logger_config.py` configure un logger par source (`get_logger(name)`) :
- crée `logs/` si besoin ;
- handler **fichier tournant** (`RotatingFileHandler`, 5 Mo, 3 backups) + handler **console** ;
- évite les doublons de handlers si appelé plusieurs fois pour le même nom.

| Niveau     | Description                        | Exemple d'usage                          |
|------------|-------------------------------------|--------------------------------------------|
| `DEBUG`    | Détails internes                    | Valeurs de variables, pour le développeur  |
| `INFO`     | Fonctionnement normal                | Étapes importantes de l'exécution         |
| `WARNING`  | Comportement inhabituel non bloquant | Le programme continue                     |
| `ERROR`    | Une opération a échoué               | Requête échouée, JSON invalide            |
| `CRITICAL` | Erreur grave, bloquante              | Le programme ne peut plus continuer       |

---

## 🤖 3. Les collectors (`src/etl/extract/`)

### 3.1 `AlphaVantageCollector` — Marchés financiers
API [Alpha Vantage](https://www.alphavantage.co/), `TIME_SERIES_DAILY`, symboles `MOS`, `NTR`, `CF`, `ICL`, `YARIY`. Plan gratuit : 5 req/min → `sleep(12)` entre symboles. Erreurs de quota renvoyées en HTTP 200 (clés `Note`/`Information`/`Error Message` vérifiées explicitement).
Sauvegarde : `data/raw/alpha_vantage/{symbol}_{date}.json` + `{symbol}_latest.json`.

### 3.2 `FAOCollector` — Production agricole (FAOSTAT)
API [FAOSTAT](https://www.fao.org/faostat/) (dataset `QCL`), authentification Bearer via AWS Cognito (`TokenManager`, voir §4). Triple boucle zone × culture × année (8×7×5 = 280 requêtes), `sleep(1)` entre requêtes.
Sauvegarde : `data/raw/fao/crop_production.json`.

### 3.3 `FFPICollector` — FAO Food Price Index
Téléchargement CSV mensuel statique. Détection **dynamique** du début des données (recherche de la première valeur de date valide en colonne A), pour ne pas dépendre d'un `skiprows` en dur si la mise en page FAO change.
Sauvegarde : `data/raw/ffpi/ffpi_{AAAA-MM}.csv` + `ffpi_latest.csv`.

### 3.4 `WorldBankCollector` — Prix des matières premières
Fichier Excel statique (`CMO-Historical-Data-Monthly.xlsx`), validation du contenu (taille + lecture Excel effective) avant d'écraser `latest`.
Sauvegarde : `data/raw/world_bank/commodity_prices_{date}.xlsx` + `commodity_prices_latest.xlsx`.

### 3.5 `NewsCollector` — Actualités (NewsAPI)
Endpoint `/v2/everything`, mots-clés OCP/phosphate/fertilizer/agriculture/concurrents. Fenêtre de recherche adaptative via `state.py` (`get_last_success`/`set_last_success`) — repart du dernier run réussi, plafonnée à 30 jours (contrainte du plan gratuit NewsAPI : pas d'accès aux dernières 24h, `floor=2`).
Sauvegarde : `data/raw/news/news_{date_heure}.json` (pas de `latest` figé, chaque run capture une fenêtre temporelle différente — mais `transform_news.py` lit `news_latest.json`, donc `_save_dated_and_latest` s'applique bien ici aussi).

### 3.6 `OCPFinancialsCollector` — Résultats financiers OCP
Pas de requête HTTP : lit/valide `src/config/ocp_financials.json` (saisie manuelle depuis les communiqués officiels). Vérifie champs requis, positivité de `revenue`/`ebitda`, calcule `ebitda_margin` si absent, déduplique par trimestre.
Sauvegarde : `data/raw/ocp_financials/ocp_financials.json`.

---

## 🔄 4. Transformation (`src/etl/transform/`)

Chaque source a son module `transform_xxx.py` avec deux fonctions : `clean()` (nettoyage/typage) et `transform()` (mise en forme dimensionnelle), orchestrées par `run()`.

- **`transform_alpha.py`** : construit `DimCompany` (avec `company_name`/`sector` = `"Unknown"`, protégés en base — voir §6) et `FactStockPrices`.
- **`transform_fao.py`** : extrait `DimCountry`, `DimCrop`, `DimElement` et `FactCropProduction`.
- **`transform_ffpi.py`** : localise dynamiquement le début des données, type les colonnes, retourne `FactFoodPriceIndex`.
- **`transform_worldbank.py`** : détecte dynamiquement la ligne de début (motif `YYYYMxx`), passe en format long (`melt`), extrait `DimCommodity`/`FactCommodityPrices`.
- **`transform_news.py`** : nettoie le HTML/entités des textes (`_clean_text`), accès défensif aux champs de chaque article (`article.get(...)`, avec repli sur `"Unknown"` si `source` est absent/malformé), construit `FactNews`, `BridgeArticleKeyword`, `DimNewsSource`, `DimKeyword`.
- **`transform_ocp.py`** : type les montants, déduplique par `quarter_label` (garde la dernière entrée).

---

## ✅ 5. Validation — `quality_checks.py` (Pandera)

Chaque table de sortie (dimension ou fait) a un schéma Pandera dédié dans `SCHEMAS` (`src/etl/quality_checks.py`), avec typage, contraintes (`Check.ge(0)`, `in_range`...) et unicité, alignés sur `database/schema.sql`. `main.py` valide table par table : une table en échec est exclue **sans bloquer** les autres tables de la même source.

---

## 🗄️ 6. Chargement (`src/etl/load/`)

- **`db_writer.py`** : `upsert(engine, df, table_name, unique_cols, protected_cols=None)` — `INSERT ... ON CONFLICT DO UPDATE` générique via SQLAlchemy, avec colonnes « protégées » (jamais écrasées lors d'un conflit, ex. `company_name`/`sector` saisis manuellement).
- **`load_dimensions.py`** : charge toutes les dimensions, dont `DimDate` (générée dynamiquement par `generate_dim_date.py`, de 1960 à aujourd'hui + 5 ans).
- **`load_facts.py`** : charge les tables de faits dans un **ordre explicite** (liste, pas un dict) — `FactNews` **avant** `BridgeArticleKeyword`, car cette dernière référence `FactNews.url` par contrainte FK.

`main.py` appelle `load_dimensions()` avant `load_facts()`, ce qui protège toutes les FK vers les dimensions.

---

## ⚙️ 7. Configuration

### `src/config/settings.py`
Centralise les URLs des sources et les dossiers de sortie pour chaque collector.

### `src/config/config.py`
Charge les clés API/tokens depuis `.env` (via `python-dotenv`), avec validation **différée** (erreur levée seulement au premier usage réel d'une variable manquante) :

| Variable            | Utilisée par         |
|---------------------|-----------------------|
| `API_KEY_NEWS`       | `NewsCollector`       |
| `API_KEY_alpha`      | `AlphaVantageCollector` |
| `FAO_USERNAME` / `FAO_PASSWORD` | `FAOCollector` (via `TokenManager`) |
| `COGNITO_CLIENT_ID`  | `TokenManager`        |
| `POSTGRES_USER/PASSWORD/DB/HOST/PORT` | `db_config.py` |

### `src/config/auth.py` — `TokenManager`
Authentification FAOSTAT via **AWS Cognito** (`boto3`, flux `USER_PASSWORD_AUTH`). Le token est mis en cache et rafraîchi automatiquement dès qu'il expire dans moins de 60 secondes — évite de regénérer un token à chacune des 280 requêtes de `FAOCollector`. En cas d'échec Cognito (`ClientError`, `BotoCoreError`, `KeyError`), une `RuntimeError` explicite est levée.

### `src/config/db_config.py`
Crée l'engine SQLAlchemy (`postgresql+psycopg2`) au premier appel réel (pas à l'import), avec `search_path=ocp_dataflow`.

### `src/config/ocp_financials.json`
Données manuelles OCP — à mettre à jour à chaque publication trimestrielle.

Un fichier **`.env.example`** est fourni comme modèle :

```dotenv
API_KEY_alpha=
API_KEY_NEWS=
FAO_USERNAME=
FAO_PASSWORD=
COGNITO_CLIENT_ID=
POSTGRES_USER=
POSTGRES_PASSWORD=
POSTGRES_DB=
POSTGRES_HOST=
POSTGRES_PORT=
```

📌 **À faire** : `cp .env.example .env` puis renseigner les vraies valeurs avant de lancer le pipeline.

⚠️ Le fichier `.env` ne doit **jamais** être commité (déjà exclu via `.gitignore`/`.dockerignore`).

---

## 🚀 8. Exécution — `src/run_etl.py`

Point d'entrée qui appelle `run_pipeline()` (`src/etl/main.py`), lequel exécute pour chaque source, dans l'ordre :

```
collect() → transform.run() → validate() par table → (à la fin) load_dimensions() → load_facts()
```

Chaque étape est isolée : un échec sur une source (ou une table) n'interrompt pas les autres. Le processus se termine avec un code de sortie **1** si au moins une source a échoué (`sys.exit(1)` dans `run_etl.py`), utile pour la supervision CI/CD ou cron.

### Lancer en local

```bash
pip install -r requirements.txt
python -m src.run_etl
```

> Le module doit être lancé avec `-m` depuis la racine du repo, pour que les imports `from src.xxx import ...` se résolvent correctement.

Les données sont sauvegardées sous `data/raw/<source>/` et les logs sous `logs/<nom_du_collector>.log`.

---

## 🐳 9. Exécution avec Docker

```dockerfile
FROM python:3.11.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --default-timeout=120 --retries 10 -r requirements.txt

COPY src/ ./src/

RUN useradd --create-home --uid 1000 etluser \
    && chown -R etluser:etluser /app
USER etluser

CMD ["python", "-m", "src.run_etl"]
```

- **`COPY src/ ./src/`** (et non `COPY src/ .`) : préserve la structure du paquet `src/` dans l'image, indispensable pour que `from src.xxx import ...` fonctionne.
- **`CMD ["python", "-m", "src.run_etl"]`** : exécution en tant que module, cohérente avec l'exécution locale.
- Image `python:3.11.9-slim`, dépendances installées avant copie du code (cache Docker), utilisateur non-root (`etluser`).

### Construire l'image

```bash
docker build -t ocp-dataflow .
```

### Lancer avec Docker Compose (recommandé — inclut Postgres)

```bash
docker compose up --build
```

`docker-compose.yml` orchestre `postgres` (avec healthcheck, init via `database/schema.sql`) et `etl` (démarre seulement une fois Postgres prêt). Volumes montés :

```yaml
    volumes:
      - ./logs:/app/logs
      - ./data:/app/data
```

> Le volume `./data:/app/data` est **indispensable** : sans lui, toutes les données brutes collectées (`data/raw/*`) sont perdues à chaque destruction du conteneur `etl` (`restart: "no"`).

### Lancer le conteneur seul (sans compose)

```bash
docker run --rm --env-file .env \
  -e POSTGRES_HOST=<host_postgres_accessible> \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  ocp-dataflow
```

### Persistance de l'état incrémental (`etl_state.json`)

`NewsCollector` s'appuie sur `src/etl/extract/etl_state.json` (via `state.py`) pour ne récupérer que les news depuis le dernier run réussi. Ce fichier vit **sous `data`-like logique mais physiquement sous `src/etl/extract/`** — pensez à le monter explicitement si vous voulez qu'il survive à la destruction du conteneur :

```yaml
      - ./src/etl/extract/etl_state.json:/app/src/etl/extract/etl_state.json
```

Sans ce montage (ou une migration vers une table Postgres dédiée), chaque run Docker repart avec `last_success = None` et retombe sur la fenêtre max (30 jours) — ce qui fonctionne mais annule l'intérêt de la logique incrémentale.

### `.dockerignore`

```
.env
.env.*
.git
__pycache__/
*.pyc
.venv/
venv/
logs/
```

`etl_state.json` n'est **plus** exclu ici (contrairement à une version précédente) : il doit pouvoir être copié dans l'image au build, quitte à être ensuite écrasé par un volume monté en exécution.

---

## ✅ 10. Changelog — Corrections et ajouts récents

### Imports — uniformisation `src.xxx`
Le projet mélangeait deux styles d'import (`from logger_config import ...` et `from src.config... import ...`), rendant le pipeline **inexécutable** aussi bien en local qu'en Docker selon la configuration. Tous les modules utilisent désormais `from src.xxx import ...` de façon cohérente, et le `Dockerfile`/`CMD` ont été adaptés en conséquence (`COPY src/ ./src/`, `python -m src.run_etl`).

### `extract_base.py`
- **Pas de retry inutile sur les erreurs client (4xx)** : `_request_with_retry()` distingue erreurs serveur/réseau (retryables, backoff exponentiel) des erreurs client (401/403/404, non retryables).

### `transform_ffpi.py`
- Détection **dynamique** du début des données (recherche de la première date valide en colonne A), au lieu d'un `skiprows=4` en dur — aligné sur l'approche déjà utilisée dans `transform_worldbank.py`.

### `transform_news.py`
- Accès défensif aux champs `source`/`url`/`publishedAt` de chaque article (`.get()` avec replis), pour éviter qu'un article malformé ne fasse échouer tout le run.

### `load_facts.py`
- `FACT_KEYS` passé d'un `dict` à une liste de tuples **explicitement ordonnée et commentée**, pour documenter la dépendance FK implicite (`FactNews` avant `BridgeArticleKeyword`).

### `docker-compose.yml`
- Ajout du volume `./data:/app/data` pour éviter la perte des données brutes collectées entre deux runs du conteneur `etl`.

### Fichiers manquants ajoutés à la racine du projet
| Fichier | Rôle |
|---------|------|
| `.env.example` | Modèle des variables d'environnement requises |
| `Dockerfile` | Image Docker pour exécution isolée du pipeline |
| `.dockerignore` | Exclusion de `.env`, `logs/`, `.git/`, `__pycache__/` du build Docker |

---

## 📥 Installation rapide

```bash
git clone <repo>
cd ocp-dataflow
cp .env.example .env   # puis renseigner les valeurs
pip install -r requirements.txt
python -m src.run_etl
```

Ou via Docker Compose (recommandé) :

```bash
cp .env.example .env
docker compose up --build
```