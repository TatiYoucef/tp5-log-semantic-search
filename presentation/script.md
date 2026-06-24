# Script de presentation

## Slide 1 - Titre
Bonjour, nous presentons notre projet TP5 : un moteur de recherche semantique et analytique sur des logs massifs. L'objectif est de montrer une chaine complete Big Data, depuis l'ingestion des logs jusqu'a la recherche semantique, l'analyse et la demonstration web.

## Slide 2 - Problematique
Les logs generes par les systemes distribues sont nombreux et difficiles a exploiter uniquement avec des mots-cles. Deux messages peuvent decrire le meme probleme avec des formulations differentes. Notre objectif est donc de construire un systeme capable de retrouver des logs similaires par leur sens, puis d'analyser les erreurs recurrentes.

## Slide 3 - Objectifs
Le sujet impose Python, Spark, PostgreSQL avec pgvector et Sentence-Transformers. Notre solution couvre ces exigences avec un pipeline de pretraitement Spark, une base vectorielle indexee, une API, une interface Streamlit et un rapport technique. Nous avons aussi ajoute des benchmarks et une comparaison de modeles.

## Slide 4 - Dataset
Nous avons utilise le dataset OpenSSH de LogHub 2.0. Il contient 638 947 logs bruts, donc plus que le seuil demande de 500 000 entrees. Le dataset fournit aussi des fichiers structures avec des identifiants d'evenements et des templates, ce qui est tres utile pour normaliser les messages.

## Slide 5 - Architecture
L'architecture suit une chaine batch classique : logs OpenSSH, pretraitement Spark, export CSV et Parquet, chargement dans PostgreSQL avec pgvector, exposition par FastAPI, puis interface Streamlit. Cette separation rend le projet reproductible et plus facile a tester.

## Slide 6 - Pretraitement Spark
Spark lit les logs bruts, extrait les champs syslog comme la date, l'hote, le service et le PID, puis joint ces informations avec le CSV structure de LogHub. Le resultat est sauvegarde en CSV pour PostgreSQL et en Parquet partitionne par niveau de severite.

## Slide 7 - Base de donnees
La base contient les logs nettoyes, les templates d'evenements, les embeddings et les traces d'execution du pipeline. L'index principal est un index HNSW pgvector sur la colonne embedding, avec une distance cosinus.

## Slide 8 - Vectorisation
Nous ne stockons pas un vecteur par ligne brute. Nous stockons un vecteur par message normalise distinct, souvent base sur le template LogHub. Les 638 947 lignes restent conservees dans log_entries et sont reliees au vecteur par normalized_message. Cela reduit fortement le cout de calcul sans perdre les occurrences originales.

## Slide 9 - Recherche semantique
Ici, une requete comme "failed password for invalid user" retourne des logs pertinents meme si les valeurs variables changent, comme les utilisateurs, les adresses IP ou les ports. La similarite affichee vient de la distance cosinus entre le vecteur de la requete et les vecteurs indexes.

## Slide 10 - Comparaison avec mots-cles
La comparaison montre la difference entre recherche semantique et recherche lexicale. La recherche par mots-cles reste utile pour une IP ou un identifiant exact, mais la recherche semantique est plus adaptee pour retrouver des messages proches par le sens.

## Slide 11 - Analytique
L'onglet analytique identifie les groupes d'erreurs frequentes et permet de suivre leur evolution temporelle. Cela repond aux cas pratiques demandes : identifier les groupes d'erreurs et analyser leur evolution dans le temps.

## Slide 12 - Benchmarks
Nous avons ajoute des metriques de benchmark : nombre d'embeddings, tailles disque, latence de recherche semantique, latence de recherche par mots-cles et coherence top-k. La coherence top-k est un indicateur proxy qui combine similarite moyenne et concentration autour du meme evenement.

## Slide 13 - Comparaison de modeles
Nous comparons trois modeles : all-MiniLM-L6-v2, multi-qa-MiniLM-L6-cos-v1 et all-mpnet-base-v2. La comparaison est faite en memoire parce que MPNet produit des vecteurs de dimension 768, alors que l'index de production utilise vector(384). On compare donc dimension, latence, coherence et similarite moyenne.

## Slide 14 - Validation
La solution couvre les cas pratiques imposes : retrouver des logs similaires a une erreur critique, identifier des groupes d'erreurs frequentes, analyser l'evolution temporelle et comparer avec une recherche par mots-cles. Le pipeline complet a ete execute sur 638 947 logs et les tests unitaires passent.

## Slide 15 - Conclusion
En conclusion, le projet fournit une chaine complete et modulaire : Spark pour le batch, PostgreSQL et pgvector pour la recherche vectorielle, Sentence-Transformers pour les embeddings, FastAPI pour l'API et Streamlit pour la demonstration. Les perspectives seraient d'ajouter une evaluation annotee, de tester d'autres datasets LogHub et de construire une recherche hybride lexical-vectorielle.
