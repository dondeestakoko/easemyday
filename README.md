# easemyday
EASE MY DAY
 
I-	PRESENTATION DU PROJET
1-	Description du projet 
EASE MY DAY est un assistant personnel intelligent, conçu pour comprendre l’utilisateur, capturer ses intentions et organiser automatiquement son quotidien.
Il suffit d’exprimer quelque chose naturellement : Il faut que j’appelle ma mère demain, J’aimerais ranger le salon ce weekend, etc. Le système analyse alors, classe, transforme, priorise et planifie sans effort pour l’utilisateur. EASE MY DAY répond ainsi aux besoins suivants : 
•	La réduction de la charge mentale
•	La simplification du quotidien
•	La centralisation de l’information souvent dispersée
•	La suggestion proactive

2-	Fonctionnalités de EASE MY DAY
EASE MY DAY offre un ensemble de fonctionnalités conçues pour simplifier l’organisation des taches du quotidien et centralisées, ce grâce à sa compréhension du langage naturel et à sa structure multi-agents. Les fonctionnalités sont réparties en quatre grands blocs : interaction, classification, organisation et exécution :
•	Interaction intelligente avec l’utilisateur 
•	Classification et analyse de l’information
•	Organisation et structuration automatique
•	Suggestions intelligentes
•	Interface utilisateur (3 blocs)

3-	Caractéristiques du système
EASE MY DAY repose sur une architecture multi-agents, chacun spécialisé dans un rôle précis. Le système s'organise autour des éléments suivants :
•	Agent d’Orchestration dont le rôle est d’analyser et diriger le flux vers les bons agents.
•	Agent de Classification des Tâches dont le rôle est transformé l’intention en tâche structurée et priorisée
•	Agent Agenda dont le rôle est de convertir une intention en événement prêt à être planifié
•	Agent d’Écriture Agenda dont le rôle est d’exécuter les actions de planification (création, mise à jour, déplacement)
•	Agent Notes  dont le rôle est d’organiser les notes et détecter les actions cachées
•	Agent de Reconnaissance Vocale, il permet une interaction vocale fluide et naturelle

II-	ARCHITECTURE DU PROJET

 


III-	FONCTIONNALITES
Grâce à sa structure multi-agents et à l’utilisation du langage naturel, EASEMYDAY fluidifie l’organisation quotidienne et réduit l’effort cognitif de l’utilisateur.  Les fonctionnalités s’articulent autour de quatre piliers : comprendre, classifier, organiser et exécuter.
1-	L’interaction naturelle avec l’utilisateur
 Grâce à un chatbot conversationnel intelligent qui analyse la phrase, en extrait l’intention et déclenche automatiquement le traitement adéquat et  une interaction vocale permettant de dicter les instructions.
2-	Analyse et classification intelligente
Ce par une détection automatique du type de demande  qui permet d’identifier le type de requête (tache, évènement à planifier, note d’information ou rappel), l’extraction d’informations essentielles et enfin la structuration en éléments exploitables, processus par  lequel la demande est transformée en une donnée normalisée, prête à être intégrée dans l’agenda, la liste de tâches ou l’espace des notes.
3-	 Organisation automatique du quotidien
Par la gestion intelligente de l’agenda (proposer un créneau pertinent, éviter les conflits, réorganiser si un événement bloque la journée, etc.), la gestion optimisée des notes et des taches (to-do List).
4-	Exécution automatisée et cohérente
Grace à la Synchronisation avec Google Tasks (Le système peut lire, créer, modifier ou clôturer des tâches dans Google Tasks, garantissant une continuité entre l’application et l’écosystème existant de l’utilisateur) et la mise à jour en temps réel.

IV-	FLUX DE DONNEES 
Le parcours d’une donnée dans le système peut être représenté en cinq grandes étapes : entrée, analyse, classification, organisation, et exécution.
1-	Entrée de la donnée utilisateur
L’utilisateur peut interagir de deux manières :
•	A l’écrit (via le chatbot),
•	A l’oral (via l’agent de Reconnaissance Vocale qui convertit la voix en texte).
La donnée brute (phrase complète) est alors envoyée à l’Agent d’Orchestration.

2-	Analyse et extraction
L’Agent analyse la structure linguistique du message et en extrait les premiers éléments sémantiques, il identifie le sens global et redirige la donnée vers l’agent approprié. Ensuite une analyse est faite est les éléments pertinents sont repérés (types d’action, échéance, contexte, durée, etc.)

3-	Classification intelligente
•	Classification des taches : si la requête correspond à une action à réaliser, l’agent structure la tâche selon  la priorité, la durée estimée, le niveau d’urgence, la catégorie.
•	La gestion des notes : si la demande concerne une information à conserver, la note est analysée, résumée, classée dans un dossier logique.
•	La préparation de l’agenda : si la requête implique une planification, l’agent identifie la date, le créneau possible, la durée ; le type d’évènement.

4-	Agrégation et décision
Les informations issues des différents agents sont harmonisées, le système détermine ensuite l’action finale (planifier, créer une tache, transformer une note, proposer une suggestion, etc.)
5-	Validation et exécution 
Une fois validée, l’action est inscrite dans  l’agenda interne, Google Tasks ou l’espace note. Grâce à l’Agent mémoire, les décisions passées sont utilisées pour :
•	Améliorer  la qualité des suggestions
•	Adapter la priorisation
•	Affiner l’interprétation des requêtes futures


V-	TECHNOLOGIES UTILISEES
EASE MY DAY s’appuie sur un ensemble de technologies modernes couvrant l’IA, les interfaces web, les API cloud et la gestion des données.
Composant	Description
Python	Langage principal pour les agents, la logique métier et l’interface.
Groq + LLaMA 3.x	Compréhension du langage, extraction d’intentions, génération JSON.
Whisper-large-v3	Transcription vocale → texte pour les commandes audio.
Google Calendar API	Lecture/écriture d’événements, détection de conflits.
Google Tasks API	Création, modification et gestion des tâches.
OAuth 2.0	Authentification sécurisée aux services Google.
Streamlit	Interface web : chatbot, agenda, notes, microphone.
JSON local	Stockage interne des notes, tâches extraites, tokens OAuth.
Dotenv	Gestion des variables sensibles (clé Groq).




L’architecture multi-agents en Python, chaque agent est un script indépendant :
Agent	Fichier	Rôle
Agent d’Orchestration	agent_extract.py	Analyse NLP et extraction
Agent de Classification	intégré dans LLM	Détection tâche / note / agenda
Agent Agenda	google_agenda_agent.py, agent_write_agenda.py	Lecture/écriture Google Calendar
Agent Tâches	agent_task.py	Gestion Google Tasks
Agent Notes	notes_agent.py	Gestion notes JSON
Agent Mémoire	partie intégrée dans agent_record.py	Persistance des items LLM
Agent TTS / STT	via Whisper dans app.py	Reconnaissance vocale

VI-	CONTRAINTES
Le fonctionnement de EASE MY DAY s’appuie sur plusieurs contraintes techniques et organisationnelles qui conditionnent la qualité du système :
•	Dépendance à une connexion internet pour interroger Groq et les API Google.
•	Gestion rigoureuse des fichiers JSON pour éviter les doublons et garantir la cohérence des données.
•	Limites et quotas imposés par les API (Groq, Google Calendar, Google Tasks).
•	Nécessité de sécuriser les jetons OAuth 2.0 et de gérer leur rafraîchissement automatique.
•	Transcription vocale limitée à de courtes séquences pour assurer un traitement rapide.
•	Exigence de performance : temps de réponse court et synchronisation fluide entre agents.
•	Protection obligatoire des clés sensibles (clé Groq, tokens Google) via .env et stockage sécurisé.
VII-	KPI
Plusieurs indicateurs permettent d’évaluer l’efficacité et la fiabilité de EASE MY DAY :
•	Taux de classification correcte des requêtes (tâche, note, événement).
•	Taux de réussite de création d’événements dans Google Calendar (sans conflit).
•	Temps moyen de réponse entre l’entrée utilisateur et l’exécution finale.
•	Taux de transcription correcte des instructions vocales via Whisper.
•	Niveau d’engagement (nombre de requêtes par session).
•	Taux de refus des éléments proposés (mesure de pertinence du système)

