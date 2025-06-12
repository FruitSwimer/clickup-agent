# AXLE Agents - Déploiement

## Prérequis

- Google Cloud CLI (`gcloud`) installé et configuré
- Accès au projet GCP `axle-agents`
- Python 3.11+
- MongoDB

## Structure du projet

```
axle-agents/
├── app.py              # Application FastAPI principale
├── main.py             # Script de test local
├── requirements.txt    # Dépendances Python
├── deploy.sh          # Script de déploiement
├── src/               # Code source
│   ├── agent/         # Logique de l'agent ClickUp
│   ├── config/        # Configuration database
│   ├── models/        # Modèles Pydantic
│   ├── repositories/  # Couche d'accès aux données
│   ├── services/      # Logique métier
│   └── utils/         # Utilitaires
└── .env.example       # Exemple de configuration

```

## Configuration

1. Créer un fichier `.env` basé sur `.env.example`:
```bash
cp .env.example .env
# Éditer .env avec vos valeurs
```

2. Pour différents environnements, créer `.env.dev`, `.env.staging`, `.env.production`

## Déploiement

### Déploiement automatique

```bash
# Déploiement en production
./deploy.sh production

# Déploiement en développement
./deploy.sh dev

# Déploiement en staging
./deploy.sh staging
```

### Commandes utiles

```bash
# Connexion SSH au serveur
gcloud compute ssh --zone "europe-west2-c" "instance-20250514-144835" --project "axle-agents"

# Voir les logs de l'application
gcloud compute ssh --zone "europe-west2-c" "instance-20250514-144835" --project "axle-agents" --command "sudo journalctl -u axle-agents.service -f"

# Redémarrer le service
gcloud compute ssh --zone "europe-west2-c" "instance-20250514-144835" --project "axle-agents" --command "sudo systemctl restart axle-agents.service"

# Vérifier le statut
gcloud compute ssh --zone "europe-west2-c" "instance-20250514-144835" --project "axle-agents" --command "sudo systemctl status axle-agents.service"
```

## API Endpoints

- `GET /health` - Vérification de santé
- `POST /chat` - Envoyer un message à l'agent ClickUp

### Exemple d'utilisation

```bash
# Health check
curl http://[EXTERNAL_IP]:8000/health

# Chat avec l'agent
curl -X POST http://[EXTERNAL_IP]:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "user_input": "get workspace hierarchy",
    "user_id": "12345"
  }'
```

## Monitoring

Le script de déploiement:
- Crée des sauvegardes automatiques
- Configure systemd pour le redémarrage automatique
- Configure le pare-feu GCP
- Effectue des tests de santé

## Rollback

En cas de problème, restaurer depuis la sauvegarde:
```bash
gcloud compute ssh --zone "europe-west2-c" "instance-20250514-144835" --project "axle-agents" --command "
  # Lister les sauvegardes
  ls -la /home/\$(whoami)/backups/
  
  # Restaurer une sauvegarde (remplacer TIMESTAMP)
  sudo systemctl stop axle-agents.service
  rm -rf /home/\$(whoami)/axle-agents
  cp -r /home/\$(whoami)/backups/axle-agents_TIMESTAMP/axle-agents /home/\$(whoami)/
  sudo systemctl start axle-agents.service
"
```