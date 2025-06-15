#!/bin/bash

# Sauvegarde automatique ClickUp Agent
# Exécuté quotidiennement par cron

APP_NAME="clickup-agent"
APP_DIR="/opt/$APP_NAME"
BACKUP_DIR="/opt/backups/$APP_NAME"
LOG_FILE="/var/log/$APP_NAME/backup.log"

# Créer le backup
backup_name="auto-backup-$(date +%Y%m%d-%H%M%S)"
backup_path="$BACKUP_DIR/$backup_name"

echo "$(date): Début de la sauvegarde automatique" >> "$LOG_FILE"

mkdir -p "$backup_path"

# Sauvegarder l'application
cp -r "$APP_DIR" "$backup_path/app"

# Sauvegarder les configurations
cp "/etc/nginx/sites-available/$APP_NAME" "$backup_path/nginx.conf"
cp "/etc/systemd/system/$APP_NAME.service" "$backup_path/service.conf"

# Sauvegarder les logs (derniers 1000 lignes)
journalctl -u "$APP_NAME" --no-pager -n 1000 > "$backup_path/service.log"

# Garder seulement les 7 dernières sauvegardes automatiques
find "$BACKUP_DIR" -name "auto-backup-*" -type d -mtime +7 -exec rm -rf {} \;

echo "$(date): Sauvegarde créée: $backup_name" >> "$LOG_FILE"

# Optionnel: Envoyer vers un stockage cloud (à configurer selon vos besoins)
# gsutil cp -r "$backup_path" gs://your-backup-bucket/ 2>/dev/null || true