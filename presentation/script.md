# Script de présentation TP5 - 15 minutes

Objectif : 5 minutes de slides, puis 10 minutes de démonstration. Le ton doit rester clair et
direct : expliquer le problème, montrer que la chaîne fonctionne, puis prouver l'intérêt de la
recherche sémantique avec l'interface.

## Avant de commencer

À lancer avant la soutenance :

```bash
source venv/bin/activate
docker compose up -d
tp5-log-search serve-api --host 127.0.0.1 --port 8000
tp5-log-search serve-web --port 8501
```

Ouvrir ensuite :

```text
Slides : presentation/index.html
Démo   : http://127.0.0.1:8501
API    : http://127.0.0.1:8000/docs
```

## Partie 1 - Slides, 5 minutes

### Slide 1 - Titre, 30 secondes

Bonjour, nous présentons notre TP5 : un moteur de recherche sémantique et analytique sur des logs
massifs. Le projet couvre toute la chaîne demandée : ingestion Big Data avec Spark, stockage dans
PostgreSQL avec pgvector, génération d'embeddings avec Sentence-Transformers, puis exposition par
FastAPI et Streamlit.

Transition : je commence par le problème que nous avons voulu résoudre.

### Slide 2 - Problème et objectif, 45 secondes

Les systèmes distribués produisent beaucoup de logs. Une recherche classique par mots-clés est utile,
mais elle reste limitée : deux logs peuvent parler du même incident avec des IP, ports ou utilisateurs différents. L'objectif est donc de ne pas chercher seulement les mots exacts, mais le sens du message.
Nous voulons retrouver les logs similaires, comparer cette approche aux mots-clés et analyser les erreurs récurrentes.

Transition : pour cela, il fallait d'abord un volume réaliste de données.

### Slide 3 - Données et architecture, 50 secondes

Nous avons utilisé le dataset OpenSSH de LogHub 2.0, avec 638 947 logs bruts, donc plus que le seuil de 500 000 entrées demandé. Les logs passent d'abord par Spark pour le nettoyage et la structuration.
Les sorties sont stockées en CSV et Parquet, puis chargées dans PostgreSQL. pgvector gère la partie
vectorielle, FastAPI expose les endpoints, et Streamlit sert d'interface de démonstration. La CLI rend
les étapes reproductibles.

Transition : je détaille maintenant le traitement technique.

### Slide 4 - Pipeline technique, 45 secondes

Cette slide résume les trois étapes techniques principales. D'abord, Spark parse les préfixes syslog,
nettoie les messages et fait la jointure avec les templates LogHub. Ensuite, la partie embeddings
calcule un vecteur pour chaque message normalisé distinct avec le modèle all-MiniLM-L6-v2, au lieu de
répéter le même calcul pour chaque occurrence brute. Enfin, pgvector stocke ces vecteurs dans
PostgreSQL et accélère la recherche avec un index HNSW. Le score affiché dans l'application est une
similarité : 1 moins la distance cosinus.

Transition : ce pipeline devient visible dans l'interface.

### Slide 5 - Interface de démonstration, 40 secondes

L'interface Streamlit permet de tester la recherche sémantique, la comparaison avec les mots-clés, les logs voisins, les analyses temporelles et les benchmarks. Ce screenshot montre une requête sur les échecs d'authentification SSH : les résultats remontent des logs proches même si les valeurs concrètes changent.

Transition : nous avons aussi vérifié que les exigences du sujet sont couvertes.

### Slide 6 - Résultats et validation, 45 secondes

Le projet couvre les cas pratiques demandés : trouver les logs similaires à une erreur critique,
identifier les groupes d'erreurs fréquentes, suivre leur évolution temporelle et comparer la recherche
sémantique avec la recherche par mots-clés. 
Côté technique, le pipeline a été exécuté sur les 638 947 logs, la base pgvector est indexée, l'API et l'interface fonctionnent, et les tests unitaires passent.
Nous avons ajouté des benchmarks de latence et un score proxy de cohérence top-k.

Transition : je vais maintenant montrer ces points dans la démo.

### Slide 7 - Scénario de démo, 35 secondes

La démonstration suit trois étapes. 
D'abord, je montre l'état du système avec les métriques globales.
Ensuite, je teste la recherche : sémantique, mots-clés et logs similaires. 
Enfin, je montre l'analyse :
erreurs fréquentes, timeline et benchmarks.

Transition : après la démo, je reviendrai à la conclusion.

### Slide 8 - Conclusion, 30 secondes

En résumé, le projet apporte une chaîne complète : Spark pour traiter le volume, PostgreSQL et
pgvector pour chercher efficacement, Sentence-Transformers pour capturer le sens, et une interface
web pour exploiter les résultats. Les perspectives sont d'ajouter des labels de pertinence, de tester
d'autres datasets LogHub et d'aller vers une recherche hybride qui combine mots-clés et vecteurs.

Transition vers la démo : maintenant je passe à l'application.

## Partie 2 - Démonstration, 10 minutes

### 0:00 à 1:00 - Démarrage et état global

À montrer :

- La page Streamlit `http://127.0.0.1:8501`.
- Les métriques en haut : nombre de logs, couverture, nombre d'événements, période.
- Expliquer que l'interface consomme l'API FastAPI et ne lit pas directement la base.

Phrase à dire :

Nous sommes sur l'interface Streamlit. En haut, on voit que la base contient les logs traités, que les
messages normalisés sont couverts par les embeddings, et que l'on peut explorer le dataset sans
manipuler SQL directement. L'application appelle l'API FastAPI, ce qui sépare bien la logique backend
de l'interface.

### 1:00 à 3:00 - Recherche sémantique

Onglet : `Recherche`

Requête :

```text
failed password for invalid user
```

Paramètres conseillés :

```text
Niveau : ALL ou ERROR
Résultats : 20
```

À montrer :

- Lancer la recherche.
- Lire les colonnes `level`, `event_id`, `similarity` et `raw_message`.
- Expliquer que les résultats peuvent changer dans les valeurs, mais garder le même sens.

Phrase à dire :

Ici, je cherche une idée : un échec de mot de passe pour un utilisateur invalide. La base ne compare
pas seulement les mots de la requête. Elle transforme la requête en vecteur, puis cherche les messages
normalisés les plus proches dans pgvector. Le score affiché est une similarité dérivée de la distance
cosinus.

### 3:00 à 4:30 - Comparaison avec les mots-clés

Onglet : `Comparaison`

Requête :

```text
brute force ssh authentication failure
```

À montrer :

- Lancer la comparaison.
- Comparer la colonne de gauche `Sémantique` et la colonne de droite `Mots-clés`.
- Dire quand les mots-clés restent utiles.

Phrase à dire :

La recherche par mots-clés reste très utile pour une IP, un identifiant exact ou une chaîne précise.
Mais sur une requête plus générale, comme une tentative de brute force SSH, la recherche sémantique
peut retrouver des messages proches même quand les mots exacts ne sont pas tous présents. C'est
l'intérêt principal du modèle d'embeddings.

### 4:30 à 5:45 - Logs similaires

Onglet : `Logs similaires`

À faire :

- Saisir la requête `wrong password` dans `Recherche texte`.
- Cliquer sur `Rechercher des logs`.
- Sélectionner une ligne dans le tableau `Résultats de recherche`.
- Montrer le panneau `Log de départ`.
- Cliquer sur `Chercher les similarités`.
- Montrer le tableau `Logs voisins`.

Phrase à dire :

Cette étape part d'une requête simple, par exemple "wrong password". L'application affiche d'abord
des logs trouvés par recherche sémantique. Ensuite, je sélectionne explicitement une ligne du tableau :
ce log devient le log de départ. On voit son ID, son niveau, son événement, son score et son message
complet. Puis on lance la recherche de similarités pour afficher les logs voisins. C'est utile pour
regrouper des occurrences d'un même problème ou retrouver des variantes du même événement dans le
dataset.

### 5:45 à 7:15 - Analytique : erreurs fréquentes et timeline

Onglet : `Analytique`

À montrer :

- À gauche : groupes récurrents, idéalement filtrer sur `ERROR` si le graphique est trop large.
- À droite : timeline avec la requête suivante.

```text
failed password invalid user
```

Phrase à dire :

La partie analytique répond au besoin opérationnel : au lieu de lire les logs ligne par ligne, on
observe les groupes d'erreurs les plus fréquents. Ensuite, avec la timeline, on peut suivre l'évolution
d'une famille d'erreurs dans le temps. Cela aide à détecter des pics, par exemple une période avec
beaucoup d'échecs d'authentification.

### 7:15 à 9:40 - Benchmark des modèles

Onglet : `Benchmarks`

Requête :

```text
failed password invalid user
```

À montrer :

- Garder les trois modèles sélectionnés.
- Cliquer sur `Benchmarker les modèles`.
- Lire le tableau comparatif : dimension, latence, cohérence top-k et similarité moyenne.
- Montrer les deux graphiques : cohérence et latence.
- Ouvrir `Top résultats par modèle` si le temps le permet.

Phrase à dire :

Dans cet onglet, on benchmarke les trois modèles en même temps sur la même requête. Le modèle de
production est MiniLM en 384 dimensions, adapté à l'index pgvector actuel. MPNet a une dimension plus
grande, donc cette comparaison se fait en mémoire. On compare la latence, la dimension, la similarité
moyenne et la cohérence top-k. La cohérence n'est pas une précision supervisée : c'est un score proxy
qui combine similarité moyenne et concentration autour du même événement. L'objectif est de montrer
le compromis entre qualité et coût.

### 9:40 à 10:00 - Fermeture de la démo

Phrase à dire :

La démonstration montre donc la chaîne complète : données traitées, recherche sémantique, baseline
par mots-clés, analyse temporelle et benchmarks. On peut revenir au slide de conclusion.

## Questions probables

### Pourquoi ne pas vectoriser les 638 947 lignes ?

Parce que beaucoup de lignes partagent le même template ou le même message normalisé. Vectoriser les
messages distincts réduit le coût de calcul et de stockage, tout en conservant toutes les occurrences
dans la table `log_entries`.

### Pourquoi pgvector ?

pgvector permet de garder la recherche vectorielle dans PostgreSQL, avec les métadonnées relationnelles
et un index HNSW. Cela évite d'ajouter un moteur vectoriel séparé pour ce TP.

### Quelle est la limite de la comparaison de modèles ?

Le dataset ne fournit pas de labels de pertinence par requête. La cohérence top-k est donc un indicateur
proxy, pas une mesure supervisée définitive.

### Que faire si la démo prend du retard ?

Priorité : montrer `Recherche`, `Comparaison`, puis `Analytique`. Les benchmarks peuvent être résumés
à partir des métriques déjà visibles si le temps est court.
