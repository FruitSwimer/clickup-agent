#!/bin/bash

# Monitoring avancé ClickUp Agent
# Vérifie l'état et envoie des alertes si nécessaire

APP_NAME="clickup-agent"
LOG_FILE="/var/log/$APP_NAME/monitoring.log"
ALERT_EMAIL="admin@axle-ia.com"  # À mettre à jour

# Fonction d'alerte
send_alert() {
    local subject="$1"
    local message="$2"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    # Log l'alerte
    echo "[$timestamp] ALERT: $subject - $message" >> "$LOG_FILE"
    
    # Optionnel: Envoyer email (nécessite mailutils)
    # echo "$message" | mail -s "$subject" "$ALERT_EMAIL" 2>/dev/null || true
    
    # Optionnel: Webhook Slack/Discord
    # curl -X POST -H 'Content-type: application/json' \
    #     --data '{"text":"🚨 '$subject': '$message'"}' \
    #     YOUR_SLACK_WEBHOOK_URL 2>/dev/null || true
}

# Vérifier le service
check_service() {
    if ! systemctl is-active --quiet "$APP_NAME"; then
        send_alert "Service Down" "Le service $APP_NAME est arrêté"
        
        # Tentative de redémarrage automatique
        systemctl start "$APP_NAME"
        sleep 10
        
        if systemctl is-active --quiet "$APP_NAME"; then
            send_alert "Service Recovered" "Le service $APP_NAME a été redémarré avec succès"
        else
            send_alert "Service Critical" "Impossible de redémarrer le service $APP_NAME"
        fi
    fi
}

# Vérifier l'API
check_api() {
    if ! curl -f -s "https://api.axle-ia.com/clickup-agent/health" > /dev/null; then
        send_alert "API Down" "L'API ClickUp Agent ne répond pas"
        
        # Redémarrer Nginx et le service
        systemctl reload nginx
        systemctl restart "$APP_NAME"
        
        sleep 15
        
        if curl -f -s "https://api.axle-ia.com/clickup-agent/health" > /dev/null; then
            send_alert "API Recovered" "L'API ClickUp Agent est de nouveau accessible"
        else
            send_alert "API Critical" "L'API ClickUp Agent reste inaccessible après redémarrage"
        fi
    fi
}

# Vérifier l'utilisation des ressources
check_resources() {
    # Vérifier la RAM
    memory_usage=$(free | grep Mem | awk '{printf("%.0f", $3/$2 * 100.0)}')
    if [ "$memory_usage" -gt 90 ]; then
        send_alert "High Memory Usage" "Utilisation RAM: ${memory_usage}%"
    fi
    
    # Vérifier l'espace disque
    disk_usage=$(df /opt | tail -1 | awk '{print $5}' | sed 's/%//')
    if [ "$disk_usage" -gt 90 ]; then
        send_alert "High Disk Usage" "Utilisation disque: ${disk_usage}%"
    fi
    
    # Vérifier les logs d'erreur récents
    error_count=$(journalctl -u "$APP_NAME" --since "5 minutes ago" | grep -i error | wc -l)
    if [ "$error_count" -gt 10 ]; then
        send_alert "High Error Rate" "$error_count erreurs dans les 5 dernières minutes"
    fi
}

# Vérifier le certificat SSL
check_ssl() {
    expiry_date=$(echo | openssl s_client -servername api.axle-ia.com -connect api.axle-ia.com:443 2>/dev/null | openssl x509 -noout -dates | grep "notAfter" | cut -d= -f2)
    expiry_timestamp=$(date -d "$expiry_date" +%s)
    current_timestamp=$(date +%s)
    days_until_expiry=$(( (expiry_timestamp - current_timestamp) / 86400 ))
    
    if [ "$days_until_expiry" -lt 30 ]; then
        send_alert "SSL Certificate Expiring" "Le certificat SSL expire dans $days_until_expiry jours"
    fi
}

# Exécuter toutes les vérifications
echo "$(date): Début du monitoring" >> "$LOG_FILE"

check_service
check_api
check_resources
check_ssl

echo "$(date): Monitoring terminé" >> "$LOG_FILE"