  Structure du projet

  axle-agents/
  ├── src/
  │   ├── __init__.py
  │   ├── config/
  │   │   ├── __init__.py
  │   │   └── database.py
  │   ├── models/
  │   │   ├── __init__.py
  │   │   └── messages.py
  │   ├── repositories/
  │   │   ├── __init__.py
  │   │   ├── base.py
  │   │   └── messages.py
  │   ├── services/
  │   │   ├── __init__.py
  │   │   └── message_service.py
  │   └── utils/
  │       ├── __init__.py
  │       └── message_transformer.py
  ├── example_usage.py
  ├── requirements.txt
  └── .env.example

  Détail de chaque fichier et classe

  1. Configuration (src/config/database.py)

  DatabaseSettings : Configuration de la base de données
  - Utilise pydantic_settings pour charger les variables d'environnement
  - Définit les paramètres MongoDB (URL, nom de base, noms des collections)
  - Charge automatiquement depuis .env

  DatabaseConnection : Singleton pour gérer la connexion MongoDB
  - Utilise Motor (driver async de PyMongo)
  - Méthodes connect() et disconnect() pour gérer le cycle de vie
  - Propriétés pour accéder aux collections

  2. Modèles (src/models/messages.py)

  MessageRole : Enum des rôles possibles dans une conversation
  - USER, ASSISTANT, SYSTEM, TOOL

  SimpleMessage : Message simplifié pour la lecture facile
  - role: Rôle du message
  - content: Contenu textuel

  TokenUsage et TokenUsageDetails : Tracking de l'utilisation des tokens
  - Compteurs de tokens (request, response, total)
  - Détails additionnels (tokens cachés, audio, etc.)

  AgentSession : Session de conversation complète
  - session_id: Identifiant unique
  - agent_id: ID de l'agent
  - messages: Liste des messages simplifiés
  - model: Modèle utilisé (GPT-4, etc.)
  - token_usage: Statistiques d'utilisation
  - metadata: Données supplémentaires

  RawMessage : Message brut de pydantic-ai
  - session_id: Référence à la session
  - message_index: Position dans la conversation
  - message_data: Données JSON complètes du message
  - timestamp: Horodatage

  3. Repositories (src/repositories/)

  BaseRepository<T> (base.py) : Classe générique pour les opérations CRUD
  - Méthodes async : create, find_one, find_many, update_one, delete_one
  - Gère la sérialisation/désérialisation Pydantic
  - Réutilisable pour tout modèle Pydantic

  RawMessageRepository (messages.py) : Gestion des messages bruts
  - create_for_session(): Crée plusieurs messages pour une session
  - find_by_session_id(): Récupère tous les messages d'une session
  - append_to_session(): Ajoute des messages à une session existante

  AgentSessionRepository (messages.py) : Gestion des sessions
  - create_session(): Crée une nouvelle session
  - update_session(): Met à jour une session
  - find_by_agent_id(): Trouve les sessions d'un agent
  - find_recent_sessions(): Sessions récentes

  4. Services (src/services/message_service.py)

  MessageService : Service principal (couche métier)
  - save_agent_run(): Sauvegarde un AgentRunResult complet
    - Stocke les messages bruts dans une collection
    - Crée une session simplifiée dans l'autre collection
    - Agrège les statistiques de tokens
  - append_to_session(): Ajoute des messages à une session existante
  - get_session(): Récupère une session par ID
  - get_raw_messages(): Récupère les messages bruts
  - get_sessions_by_agent(): Liste les sessions d'un agent

  5. Utilitaires (src/utils/message_transformer.py)

  MessageTransformer : Transforme les données pydantic-ai
  - extract_simple_message(): Convertit un message brut en SimpleMessage
  - transform_messages(): Transforme une liste de messages
  - extract_model_info(): Extrait le nom du modèle utilisé
  - aggregate_token_usage(): Calcule le total des tokens utilisés

  6. Fichiers de configuration

  requirements.txt : Dépendances Python
  - pydantic, pydantic-ai, motor, python-dotenv

  .env.example : Template des variables d'environnement
  - Configuration MongoDB (URL, noms des collections)

  example_usage.py : Exemple d'utilisation
  - Montre comment sauvegarder un run d'agent
  - Comment ajouter des messages à une session
  - Comment récupérer et afficher les données

  Flux de données

  1. Agent Run → AgentRunResult avec tous les messages
  2. MessageService reçoit le résultat
  3. RawMessageRepository stocke les messages JSON bruts
  4. MessageTransformer convertit en format simplifié
  5. AgentSessionRepository stocke la session simplifiée
  6. Deux collections MongoDB :
    - raw_messages : Messages complets pour l'audit/debug
    - agent_sessions : Sessions simplifiées pour l'affichage

  Cette architecture suit les bonnes pratiques :
  - Séparation des responsabilités : Modèles, Repositories, Services
  - Async/await : Performances optimales avec Motor
  - Type safety : Pydantic pour la validation
  - Flexibilité : Deux vues des données selon les besoins