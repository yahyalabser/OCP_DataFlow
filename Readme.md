# 📦 Data Collectors — Pipeline de collecte de données agricoles & financières

Ce projet regroupe **6 collectors** chargés de récupérer automatiquement des données provenant de sources publiques (API, fichiers, config internes) : marchés financiers, production agricole, indices alimentaires, prix des matières premières, actualités et résultats financiers d'OCP.

---

## 📁 Structure du projet

```
.
├── collectors/
│   ├── base_collector.py          # Classe abstraite commune à tous les collectors
│   ├── alpha_vantage_collector.py # Marchés financiers (actions)
│   ├── fao_collector.py           # Production agricole (FAOSTAT)
│   ├── ffpi_collector.py          # FAO Food Price Index
│   ├── world_bank_collector.py    # Prix des matières premières (World Bank)
│   ├── news_collector.py          # Actualités (NewsAPI)
│   └── ocp_financials.py          # Résultats financiers OCP (config locale)
│
├── config/
│   ├── config.py                  # Clés API / tokens (via .env)
│   ├── auth.py                    # Logique d'authentification (à détailler)
│   ├── settings.py                # URLs et dossiers de sortie
│   └── ocp_financials.json        # Données trimestrielles OCP (source manuelle)
│
├── logger_config.py               # Configuration du logging
├── run_collectors.py              # Script principal d'exécution
├── requirements.txt
├── Dockerfile                      # Image Docker pour exécution isolée
├── .env.example                    # Modèle des variables d'environnement requises
└── data/raw/...                   # Données collectées (générées à l'exécution)
```

---

## 🧱 1. `BaseCollector` — la classe de base

Toutes les collectors héritent de `BaseCollector` (classe abstraite, module `abc`).

**Constructeur** — initialise les attributs communs :

| Attribut      | Rôle                                                |
|---------------|------------------------------------------------------|
| `base_url`    | URL de base utilisée pour les requêtes               |
| `output_dir`  | Dossier où seront sauvegardées les données            |
| `logger`      | Logger dédié au collector (voir section logging)      |
| `timeout`     | Timeout HTTP (défaut : 15s)                           |
| `max_retries` | Nombre de tentatives en cas d'échec (défaut : 3)      |

**Méthodes :**

- **`_request_with_retry(url=None, **kwargs)`**
  Envoie une requête HTTP via `requests`, avec gestion des erreurs (`Timeout`, `HTTPError`, `RequestException`) et un mécanisme de **retry automatique** (jusqu'à `max_retries` tentatives, avec backoff exponentiel `2**attempt` entre chaque essai).
  → Retourne l'objet `Response` en cas de succès, `None` en cas d'échec définitif.

- **`_safe_json(response)`**
  Convertit une réponse HTTP en JSON de façon sécurisée :
  - `dict` → si le JSON est un objet
  - `list` → si le JSON est un tableau
  - `None` → si le contenu n'est pas un JSON valide

- **`collect()`** et **`save()`** — méthodes abstraites, à implémenter dans chaque sous-classe.

---

## 🪵 2. Logging — `get_logger()`

Le module `logging` (standard Python) remplace `print()` pour un suivi structuré de l'exécution : les logs peuvent être filtrés par niveau, écrits dans un fichier et affichés dans le terminal simultanément.

**Niveaux (du moins au plus critique) :**

| Niveau     | Description                        | Exemple d'usage                          |
|------------|-------------------------------------|-------------------------------------------|
| `DEBUG`    | Détails internes                    | Valeurs de variables, pour le développeur |
| `INFO`     | Fonctionnement normal                | Étapes importantes de l'exécution        |
| `WARNING`  | Comportement inhabituel non bloquant | Le programme continue                    |
| `ERROR`    | Une opération a échoué               | Requête échouée, JSON invalide           |
| `CRITICAL` | Erreur grave, bloquante              | Le programme ne peut plus continuer      |

`get_logger(name)` :
- crée le dossier `logs/` s'il n'existe pas ;
- configure un logger avec un handler **fichier** (`logs/{name}.log`) et un handler **console** ;
- évite les doublons de handlers si la fonction est appelée plusieurs fois pour le même nom.

---

## 🤖 3. Les collectors

### 3.1 `AlphaVantageCollector` — Marchés financiers

Récupère les prix boursiers quotidiens via l'API [Alpha Vantage](https://www.alphavantage.co/).

- **Symboles suivis** : `MOS`, `NTR`, `CF`, `ICL`, `YARIY` (acteurs du secteur des engrais/phosphates)
- **Fonction API utilisée** : `TIME_SERIES_DAILY` (prix Open/High/Low/Close/Volume quotidiens, format `compact` = 100 derniers jours)

**Fonctionnement :**
1. `collect()` boucle sur chaque symbole et appelle `collect_symbol(symbol)`.
2. `collect_symbol()` construit les paramètres (`function`, `symbol`, `outputsize`, `apikey`), envoie la requête via `_request_with_retry()`, puis vérifie la présence de clés d'erreur (`Note`, `Information`, `Error Message`) dans la réponse — Alpha Vantage renvoie ces clés en cas de dépassement de quota ou d'erreur, même avec un code HTTP 200.
3. Si les données sont valides, `save()` est appelée ; sinon le symbole est ignoré.
4. **`time.sleep(12)` entre chaque symbole** : le plan gratuit d'Alpha Vantage limite les requêtes à **5 par minute**, soit une requête toutes les 12 secondes — ce délai évite de dépasser le quota.

**Sauvegarde (`save()`) :**
- `data/raw/alpha_vantage/{symbol}_{AAAA-MM-JJ}.json` → archive datée (historique)
- `data/raw/alpha_vantage/{symbol}_latest.json` → copie toujours écrasée, pratique pour que les étapes suivantes du pipeline lisent toujours la donnée la plus récente sans se soucier de la date

**Autres paramètres Alpha Vantage disponibles** (non utilisés ici mais utiles à connaître) :

| Paramètre   | Description                          |
|-------------|----------------------------------------|
| `function`  | Type de données demandé (voir ci-dessous) |
| `symbol`    | Symbole boursier (`AAPL`, `TSLA`...)  |
| `interval`  | Intervalle pour l'intraday (`5min`...) |
| `outputsize`| `compact` (100 pts) ou `full`         |
| `datatype`  | `json` ou `csv`                      |
| `apikey`    | Clé d'API                            |

Fonctions notables : `TIME_SERIES_INTRADAY`, `TIME_SERIES_WEEKLY`, `TIME_SERIES_MONTHLY`, `FX_DAILY` (forex), `DIGITAL_CURRENCY_DAILY` (crypto), indicateurs techniques (`RSI`, `MACD`, `SMA`), données macro (inflation, PIB, chômage).

#### 📡 L'API en détail

[Alpha Vantage](https://www.alphavantage.co/) est une API REST gratuite (avec offre payante) qui donne accès à des données de marché en JSON ou CSV. C'est une API **sans authentification OAuth** : une simple clé (`apikey`) suffit, passée en paramètre de requête (query string), pas en en-tête.

- **Authentification** : clé API gratuite obtenue par simple inscription sur le site.
- **Limites du plan gratuit** : 25 requêtes/jour et 5 requêtes/minute — d'où le `sleep(12)` entre chaque symbole dans le code.
- **Format de requête** : `GET https://www.alphavantage.co/query?function=...&symbol=...&apikey=...`
- **Particularité importante** : Alpha Vantage renvoie toujours un code HTTP `200`, même en cas d'erreur ou de quota dépassé — l'erreur est indiquée **dans le corps JSON** via les clés `"Note"`, `"Information"` ou `"Error Message"`. C'est pourquoi le collector doit explicitement vérifier ces clés (`_request_with_retry()` seul ne suffit pas à détecter ce type d'échec).

#### 📦 Données retournées (exemple `TIME_SERIES_DAILY`)

```json
{
  "Meta Data": {
    "1. Information": "Daily Prices (open, high, low, close) and Volumes",
    "2. Symbol": "MOS",
    "3. Last Refreshed": "2026-07-21",
    "4. Output Size": "Compact",
    "5. Time Zone": "US/Eastern"
  },
  "Time Series (Daily)": {
    "2026-07-21": {
      "1. open": "28.50",
      "2. high": "29.10",
      "3. low": "28.20",
      "4. close": "28.95",
      "5. volume": "3456789"
    },
    "2026-07-20": {
      "1. open": "28.10",
      "2. high": "28.60",
      "3. low": "27.90",
      "4. close": "28.40",
      "5. volume": "2987654"
    }
  }
}
```

- `Meta Data` : informations sur la requête (symbole, date de dernière mise à jour, fuseau horaire).
- `Time Series (Daily)` : dictionnaire dont chaque clé est une date (`AAAA-MM-JJ`) et chaque valeur un objet OHLCV (Open/High/Low/Close/Volume) pour ce jour-là. En mode `compact`, environ 100 dernières séances sont renvoyées.

---

### 3.2 `FAOCollector` — Production agricole (FAOSTAT)

Récupère les données de production agricole via l'API [FAOSTAT](https://www.fao.org/faostat/) (dataset **QCL** — Crops and livestock products).

- **Zones suivies** : Maroc, Brésil, Inde, Chine, USA, Canada, France, Argentine
- **Cultures suivies** : Blé, Maïs, Riz, Soja, Orge, Colza, Tournesol
- **Période** : 2020 à 2024
- **Élément** : code `2510` (quantité produite)

**Fonctionnement :**
- Triple boucle imbriquée (zone × culture × année), soit `8 × 7 × 5 = 280` requêtes.
- Pour chaque combinaison, envoi d'une requête avec `area`, `item`, `element`, `year` en paramètres et un token Bearer en en-tête.
- `time.sleep(1)` entre chaque requête pour ménager l'API.
- Toutes les données valides sont accumulées dans une liste unique, puis sauvegardées en une seule fois à la fin.

**Sauvegarde :** `data/raw/fao/crop_production.json` (liste consolidée de tous les enregistrements).

#### 📡 L'API en détail

[FAOSTAT](https://www.fao.org/faostat/) est la base de données statistiques officielle de l'**Organisation des Nations Unies pour l'alimentation et l'agriculture**. Son API REST (`faostatservices.fao.org/api/v1`) donne accès à des dizaines de domaines statistiques (production, commerce, sécurité alimentaire, prix, émissions...), chacun identifié par un code (ex. `QCL` = *Crops and Livestock products*).

- **Authentification** : token Bearer (en-tête `Authorization: Bearer <token>`), obtenu via **AWS Cognito** — voir `config/auth.py` (section 4) pour le détail du mécanisme de génération/rafraîchissement du token.
- **Système de dimensions/filtres** : chaque domaine se filtre par plusieurs dimensions — `area` (zone géographique), `item` (produit), `element` (type de mesure : production, superficie récoltée, rendement...), `year`. Chaque dimension a ses propres codes numériques internes (ex. zone Maroc = `143`, Blé = `15`).
- **Élément `2510`** utilisé ici correspond au code de mesure **"Production"** (quantité produite, en tonnes) — à ne pas confondre avec les codes d'affichage utilisés dans l'interface web, qui diffèrent des codes de filtre de l'API.
- **Limitation** : l'API ne renvoie qu'une combinaison de filtres à la fois pour ce type d'appel, d'où la triple boucle du collector plutôt qu'une requête unique groupée.

#### 📦 Données retournées (exemple)

```json
{
  "data": [
    {
      "Area Code": 143,
      "Area": "Morocco",
      "Item Code": 15,
      "Item": "Wheat",
      "Element Code": 2510,
      "Element": "Production",
      "Year": 2023,
      "Year Code": 2023,
      "Unit": "t",
      "Value": 3400000,
      "Flag": "A",
      "Flag Description": "Official figure"
    }
  ]
}
```

- La clé `"data"` contient une **liste d'enregistrements**, un par combinaison zone/produit/année ayant une valeur disponible (une combinaison sans donnée renvoie une liste vide).
- `Value` : la quantité produite, dans l'unité indiquée par `Unit` (tonnes ici).
- `Flag` : qualifie la fiabilité/origine de la donnée (`A` = donnée officielle, `E` = estimation, etc.).

---

### 3.3 `FFPICollector` — FAO Food Price Index

Télécharge le fichier CSV de l'**indice FAO des prix alimentaires** (FFPI), publié mensuellement.

**Fonctionnement :**
- Requête simple (pas de paramètres), timeout étendu à 30s (fichier volumineux).
- Vérification basique de l'intégrité de la réponse (`len(content) >= 100`) avant sauvegarde, pour éviter d'écraser les données avec une réponse vide ou corrompue.

**Sauvegarde :**
- `data/raw/ffpi/ffpi_{AAAA-MM}.csv` → une copie par mois (historique des publications)
- `data/raw/ffpi/ffpi_latest.csv` → copie toujours à jour

#### 📡 La source en détail

Ce n'est pas une API à proprement parler mais un **fichier CSV statique** publié mensuellement par la FAO, à une URL fixe. Le **FFPI** (FAO Food Price Index) mesure l'évolution mensuelle des prix internationaux d'un panier de matières premières alimentaires, base 100 sur la période 2014-2016.

- **Pas de clé API ni de paramètres** : simple téléchargement HTTP du fichier le plus récent.
- **Fréquence de mise à jour** : mensuelle (généralement début de mois pour le mois précédent).
- **Sous-indices** : l'indice global agrège 5 sous-indices sectoriels (céréales, huiles végétales, produits laitiers, viande, sucre), chacun pondéré par sa part dans le commerce international 2014-2016.

#### 📦 Données retournées (structure du CSV)

| Date       | Food Price Index | Meat | Dairy | Cereals | Oils | Sugar |
|------------|-------------------|------|-------|---------|------|-------|
| 2026-06    | 121.4             | 118.2| 125.6 | 119.8   | 130.1| 108.3 |
| 2026-07    | 122.9             | 119.0| 126.9 | 121.0   | 131.5| 109.0 |

- Chaque ligne = un mois, chaque colonne = l'indice global ou l'un des 5 sous-indices sectoriels.
- Toutes les valeurs sont des **indices** (base 100 sur 2014-2016), pas des prix absolus en devise.

---

### 3.4 `WorldBankCollector` — Prix des matières premières

Télécharge le fichier Excel officiel de la Banque Mondiale (**CMO Historical Data**) contenant l'historique mensuel des prix des matières premières (métaux, énergie, agriculture...).

**Fonctionnement :** requête simple, timeout de 30s, sauvegarde directe du contenu binaire.

**Sauvegarde :** `data/raw/world_bank/commodity_prices.xlsx` (écrasé à chaque exécution).

#### 📡 La source en détail

Comme pour FFPI, il ne s'agit pas d'une API interrogeable avec paramètres mais d'un **fichier Excel statique** (`CMO-Historical-Data-Monthly.xlsx`) publié mensuellement par la Banque Mondiale dans le cadre de son rapport **Commodity Markets Outlook (CMO)**.

- **Pas d'authentification, pas de paramètres** : téléchargement direct du fichier.
- **Contenu** : historique mensuel des prix (souvent depuis 1960) pour des dizaines de matières premières classées par catégorie — énergie (pétrole, gaz, charbon), métaux (or, cuivre, aluminium...), agriculture (blé, maïs, soja, **phosphates**, engrais...), et d'autres.
- **Fréquence de mise à jour** : mensuelle.

#### 📦 Données retournées (structure du fichier Excel)

Le fichier contient plusieurs feuilles, notamment :

| Feuille                | Contenu                                                |
|-------------------------|---------------------------------------------------------|
| `Monthly Prices`        | Prix mensuels bruts par matière première (une colonne par produit, une ligne par mois) |
| `Monthly Indices`       | Indices de prix (base 100) par catégorie                |
| `Description`           | Métadonnées : unité, devise, source de chaque série     |

Exemple simplifié de `Monthly Prices` :

| Date      | Crude oil, average ($/bbl) | Wheat, US HRW ($/mt) | Phosphate rock ($/mt) | DAP ($/mt) |
|-----------|------------------------------|------------------------|--------------------------|------------|
| 2026M06   | 78.4                          | 268.5                  | 165.2                    | 612.0      |
| 2026M07   | 79.1                          | 271.0                  | 168.0                    | 615.5      |

- Chaque colonne correspond à une matière première précise, avec son unité de prix (`$/bbl`, `$/mt`...) indiquée dans l'en-tête.
- Les phosphates et engrais (`Phosphate rock`, `DAP`, `TSP`, `Urea`...) sont particulièrement pertinents pour le suivi du secteur OCP.

---

### 3.5 `NewsCollector` — Actualités (NewsAPI)

Récupère les articles récents liés à OCP et au secteur des engrais/phosphates via [NewsAPI](https://newsapi.org/).

- **Mots-clés suivis** : `"OCP Group"`, `"OCP SA"`, `phosphate`, `fertilizer`, `agriculture`

**Fonctionnement :**
1. `collect_keyword(keyword, days_back)` construit une fenêtre de recherche (minimum 2 jours en arrière, contrainte du plan gratuit NewsAPI) et interroge l'API (tri par date de publication, langue anglaise).
2. Vérifie le statut de la réponse (`status == "error"`) avant d'extraire les articles.
3. `time.sleep(1)` entre chaque mot-clé.
4. Les résultats sont regroupés dans un dictionnaire `{mot_clé: [articles]}`.

**Sauvegarde :** `data/raw/news/news_{AAAA-MM-JJ_HHMMSS}.json` (un fichier horodaté par exécution, pas de fichier `latest` ici car chaque run capture une fenêtre temporelle différente).

#### 📡 L'API en détail

[NewsAPI](https://newsapi.org/) est un agrégateur qui indexe des dizaines de milliers de sources d'actualités (journaux, blogs, sites spécialisés) et expose une recherche par mots-clés via une API REST.

- **Authentification** : clé API (`apiKey`) passée en paramètre de requête.
- **Endpoint utilisé** : `/v2/everything` — recherche plein texte sur tous les articles indexés (par opposition à `/v2/top-headlines` qui ne couvre que la une).
- **Limites du plan gratuit** : recherche limitée aux **articles vieux d'au maximum un mois**, et surtout — contrainte visible dans le code — **impossible d'interroger les dernières 24h** (d'où `safe_days_back = max(days_back, 2)`, qui force une fenêtre d'au moins 2 jours en arrière).
- **Paramètres principaux** : `q` (mot-clé/expression, les guillemets forcent une recherche exacte comme `"OCP Group"`), `from`/`to` (fenêtre de dates), `language`, `sortBy` (`relevancy`, `popularity`, `publishedAt`), `pageSize` (max 100 en gratuit).

#### 📦 Données retournées (exemple)

```json
{
  "status": "ok",
  "totalResults": 37,
  "articles": [
    {
      "source": { "id": "reuters", "name": "Reuters" },
      "author": "Jane Doe",
      "title": "OCP Group announces new fertilizer plant investment",
      "description": "Morocco's OCP Group said it will invest...",
      "url": "https://www.reuters.com/...",
      "urlToImage": "https://www.reuters.com/.../image.jpg",
      "publishedAt": "2026-07-20T08:15:00Z",
      "content": "Morocco's OCP Group said on Monday it will invest... [+1500 chars]"
    }
  ]
}
```

- `status` : `"ok"` ou `"error"` (le collector vérifie ce champ avant de continuer).
- `totalResults` : nombre total d'articles correspondants (peut dépasser `pageSize`, dans ce cas seule la première page est renvoyée).
- `articles` : liste des articles, chacun avec sa source, son titre, sa description, son URL, sa date de publication et un extrait de contenu (`content` est souvent tronqué à ~200 caractères en plan gratuit, avec un indicateur `[+N chars]`).

---

### 3.6 `OCPFinancialsCollector` — Résultats financiers OCP

Contrairement aux autres collectors, celui-ci ne fait **aucune requête HTTP** : il lit et valide un fichier de configuration local (`config/ocp_financials.json`) alimenté manuellement à partir des communiqués officiels d'OCP Group (les résultats financiers ne sont pas disponibles via une API publique).

**Champs requis par trimestre :** `quarter`, `revenue`, `ebitda`, `net_income`, `published_at`

**Fonctionnement (`collect()`) :**
1. `_load_config()` charge et parse le JSON, vérifie que c'est bien une liste.
2. `_validate_entry()` vérifie pour chaque entrée :
   - présence de tous les champs requis (non vides) ;
   - `revenue` et `ebitda` sont des nombres **positifs** ;
   - `net_income` est bien un nombre (les pertes trimestrielles, négatives, sont acceptées).
3. Les doublons de trimestre sont ignorés (`seen_quarters`).
4. Si `ebitda_margin` est absent, il est **calculé automatiquement** : `ebitda / revenue` (arrondi à 4 décimales).
5. Un champ `source` par défaut (`"OCP Group communiqué"`) est ajouté si absent.

**Sauvegarde :** `data/raw/ocp_financials/ocp_financials.json` (liste des trimestres validés).

#### 📡 La source en détail

Il n'existe **pas d'API publique** pour les résultats financiers d'OCP Group (entreprise non cotée en bourse en actions ordinaires accessibles au grand public de la même façon qu'une société cotée classique, et ne publiant pas de flux de données structuré). Les chiffres proviennent donc des **communiqués de presse officiels** publiés trimestriellement par OCP Group, saisis manuellement dans `config/ocp_financials.json`. Ce collector joue un rôle de **validation et de nettoyage** plutôt que de collecte réseau.

#### 📦 Données retournées / attendues (format `config/ocp_financials.json` en entrée, identique en sortie après validation)

```json
[
  {
    "quarter": "Q2-2026",
    "revenue": 26800000000,
    "ebitda": 11000000000,
    "ebitda_margin": 0.4104,
    "net_income": 5600000000,
    "published_at": "2026-07-25",
    "source": "OCP Group communiqué"
  }
]
```

| Champ           | Type / Unité                    | Description                                              |
|------------------|----------------------------------|------------------------------------------------------------|
| `quarter`        | `string` (`"QX-AAAA"`)          | Trimestre concerné                                        |
| `revenue`        | `number` (MAD, ≥ 0)             | Chiffre d'affaires du trimestre                           |
| `ebitda`         | `number` (MAD, ≥ 0)             | Excédent brut d'exploitation                              |
| `ebitda_margin`  | `float` (calculé si absent)     | `ebitda / revenue`, arrondi à 4 décimales                 |
| `net_income`     | `number` (MAD, peut être négatif)| Résultat net (une perte trimestrielle est acceptée)       |
| `published_at`   | `string` (`AAAA-MM-JJ`)         | Date de publication du communiqué                         |
| `source`         | `string`                        | Ajouté automatiquement si absent (`"OCP Group communiqué"`) |

---

## ⚙️ 4. Configuration

### `config/settings.py`
Centralise les URLs des sources et les dossiers de sortie pour chaque collector.

### `config/config.py`
Charge les clés API / tokens depuis un fichier `.env` (via `python-dotenv`) :

| Variable            | Utilisée par         |
|---------------------|----------------------|
| `API_KEY_NEWS`       | `NewsCollector`      |
| `API_KEY_alpha`      | `AlphaVantageCollector` |
| `FAO_USERNAME`       | `FAOCollector` (via `TokenManager` dans `auth.py`) |
| `FAO_PASSWORD`       | `FAOCollector` (via `TokenManager` dans `auth.py`) |

### `config/auth.py`

Contient la classe `TokenManager`, qui gère l'authentification auprès de **FAOSTAT via AWS Cognito** (le service d'authentification managé d'AWS). C'est ce token qui est ensuite utilisé en en-tête `Authorization: Bearer <token>` par `FAOCollector` (voir section 3.2).

```python
import boto3, time

COGNITO_CLIENT_ID = "2csltsigao85ivhp6ojp1aic7o"
COGNITO_REGION = "eu-west-1"

class TokenManager:
   def __init__(self, username: str, password: str):
      self.username = username
      self.password = password
      self.client = boto3.client("cognito-idp", region_name=COGNITO_REGION)
      self._token = None
      self._expires_at = 0

   def get_token(self) -> str:
      if self._token is None or time.time() > self._expires_at - 60:
         self._refresh()
      return self._token

   def _refresh(self):
      response = self.client.initiate_auth(
         ClientId=COGNITO_CLIENT_ID,
         AuthFlow="USER_PASSWORD_AUTH",
         AuthParameters={
            "USERNAME": self.username,
            "PASSWORD": self.password,
         },
      )
      auth_result = response["AuthenticationResult"]
      self._token = auth_result["AccessToken"]
      self._expires_at = time.time() + auth_result["ExpiresIn"]
```

**Fonctionnement :**
- `boto3` (SDK AWS officiel pour Python) est utilisé pour dialoguer avec **Amazon Cognito**, service géré par la FAO pour authentifier les utilisateurs de son API.
- **`get_token()`** est le point d'entrée utilisé par les collectors : il renvoie un token valide, et ne déclenche un rafraîchissement (`_refresh()`) que si aucun token n'a encore été récupéré ou s'il expire dans moins de 60 secondes (marge de sécurité).
- **`_refresh()`** utilise le flux d'authentification `USER_PASSWORD_AUTH` de Cognito : identifiants (`FAO_USERNAME`/`FAO_PASSWORD`) envoyés à Cognito, qui renvoie en retour un `AccessToken` (le vrai jeton à utiliser) et sa durée de validité (`ExpiresIn`, en secondes).
- Ce mécanisme évite de générer un nouveau token à **chaque** requête (ce qui serait lent et inutile) : le même token est réutilisé pendant toute sa durée de vie, et n'est renouvelé qu'une fois arrivé (presque) à expiration — important ici vu le grand nombre de requêtes envoyées par `FAOCollector` (jusqu'à 280).
- `COGNITO_CLIENT_ID` est l'identifiant de l'application cliente enregistrée côté FAO/Cognito (public, ce n'est pas un secret à proprement parler — contrairement au couple `FAO_USERNAME`/`FAO_PASSWORD`).

Un fichier **`.env.example`** est fourni à la racine du projet comme modèle :

```dotenv
API_KEY_alpha=
API_KEY_NEWS=
FAO_USERNAME=
FAO_PASSWORD=
```

📌 **À faire** : copier ce fichier en `.env` (`cp .env.example .env`) et renseigner les valeurs avant de lancer les collectors concernés :

```bash
cp .env.example .env
```

⚠️ Le fichier `.env` (contenant les vraies clés et identifiants) ne doit **jamais** être commité — pense à l'ajouter dans `.gitignore` s'il n'y est pas déjà.

### `config/ocp_financials.json`
Fichier de données manuelles (voir `OCPFinancialsCollector`) — à mettre à jour à chaque publication trimestrielle d'OCP.

---

## 🚀 5. Exécution — `run_collectors.py`

Script principal qui instancie et exécute les collectors les uns après les autres, en isolant les erreurs (un échec sur un collector n'interrompt pas les autres) :

```python
collectors = [
   NewsCollector(),
   AlphaVantageCollector(),
   WorldBankCollector(),
   FAOCollector(),
   FFPICollector(),
   OCPFinancialsCollector()
]
```

Pour chaque collector : log de démarrage → `collect()` → succès/échec enregistré → log récapitulatif final (`results["success"]` / `results["failed"]`).

> 💡 Les **6 collectors sont actifs** dans la liste — le pipeline complet (marchés financiers, prix des matières premières, production agricole, indice alimentaire, actualités et résultats OCP) est exécuté à chaque lancement de `run_collectors.py`. Pense à bien renseigner toutes les variables du `.env` (`API_KEY_alpha`, `API_KEY_NEWS`, `FAO_USERNAME`, `FAO_PASSWORD`) avant de lancer le script, sous peine de voir `AlphaVantageCollector`, `NewsCollector` et `FAOCollector` échouer faute d'authentification.

---

## 📥 Installation

```bash
pip install -r requirements.txt
```

Dépendances : `boto3`, `python-dotenv` (`dotenv`), `requests`

---

## ▶️ Lancer le pipeline

```bash
python run_collectors.py
```

Les données collectées sont sauvegardées sous `data/raw/<source>/` et les logs sous `logs/<nom_du_collector>.log`.

---

## 🐳 6. Exécution avec Docker

Un `Dockerfile` est fourni pour exécuter le pipeline dans un environnement isolé et reproductible.

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "run_collectors.py"]
```

**Fonctionnement :**
- Image de base **`python:3.11-slim`** : version allégée de Python 3.11, sans les paquets superflus, pour une image finale plus légère.
- Les dépendances (`requirements.txt`) sont copiées et installées **avant** le reste du code : Docker met cette étape en cache, donc si seul le code change (pas `requirements.txt`), le `pip install` n'est pas relancé au prochain build → builds plus rapides.
- `--no-cache-dir` évite de stocker le cache pip dans l'image, réduisant sa taille.
- Tout le reste du projet est ensuite copié dans `/app`.
- Au démarrage du conteneur, `run_collectors.py` est exécuté automatiquement (`CMD`).

### Construire l'image

```bash
docker build -t collectors .
```

### Lancer le conteneur

Les clés API doivent être transmises au conteneur — soit via un fichier `.env`, soit variable par variable :

```bash
docker run --rm --env-file .env collectors
```

ou :

```bash
docker run --rm \
  -e API_KEY_alpha=xxx \
  -e API_KEY_NEWS=xxx \
  -e FAO_USERNAME=xxx \
  -e FAO_PASSWORD=xxx \
  collectors
```

### Conserver les données et les logs en dehors du conteneur

Par défaut, `data/` et `logs/` sont créés **à l'intérieur** du conteneur et sont donc perdus quand celui-ci est supprimé (`--rm`). Pour les conserver sur la machine hôte, monter des volumes :

```bash
docker run --rm --env-file .env \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  collectors
```

### Fichier `.dockerignore`

```ignore
.env
data/
logs/
.git/
__pycache__/
```

Ce fichier évite de copier dans l'image Docker des éléments sensibles ou inutiles lors du `COPY . .` :
- `.env` → clés API réelles, ne doit jamais se retrouver dans une image (surtout si celle-ci est ensuite publiée sur un registre) ;
- `data/` et `logs/` → générés à l'exécution, inutiles (et potentiellement volumineux) dans l'image de base ;
- `.git/` → historique Git, alourdit l'image sans utilité à l'exécution ;
- `__pycache__/` → fichiers `.pyc` compilés, régénérés automatiquement, à exclure de toute image ou dépôt.