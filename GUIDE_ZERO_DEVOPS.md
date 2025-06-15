# 🚀 Guide Zero-DevOps - ClickUp Agent

## 📋 Résumé
Votre ClickUp Agent est maintenant **100% automatisé**. Vous pouvez vous concentrer uniquement sur le développement !

## 🎯 URL de votre API
- **API Gateway**: https://api.axle-ia.com/
- **ClickUp Agent**: https://api.axle-ia.com/clickup-agent/
- **Health Check**: https://api.axle-ia.com/clickup-agent/health

## 🛠️ Commande Unique - `axle`

Tout se fait avec une seule commande : `axle`

### 📦 Déploiement (Zero-Downtime)
```bash
# Déployer votre code modifié
axle deploy

# En cas de problème, revenir en arrière
axle rollback
```

### 🔍 Monitoring
```bash
# Vérifier que tout fonctionne
axle status

# Test rapide de l'API
axle health

# Voir les logs récents
axle logs
```

### 🧹 Maintenance
```bash
# Sauvegarde manuelle
axle backup

# Nettoyer les anciens fichiers
axle clean

# Informations système
axle info
```

## 🤖 Automatisations Configurées

### ✅ Ce qui se fait automatiquement
- ✅ **Monitoring** : Vérifie l'API toutes les 5 minutes
- ✅ **Redémarrage auto** : Si l'API tombe, redémarrage automatique  
- ✅ **Sauvegardes** : Sauvegarde quotidienne à 2h du matin
- ✅ **Mises à jour** : Dependencies mises à jour chaque dimanche
- ✅ **SSL** : Renouvellement automatique des certificats
- ✅ **Logs** : Rotation et nettoyage automatique
- ✅ **Health checks** : Tests continus de l'API

### 🔄 Déploiement Automatique
Quand vous faites `axle deploy` :
1. 🗄️ Sauvegarde automatique de la version actuelle
2. 📥 Mise à jour du code (si Git configuré)
3. 📦 Installation des nouvelles dépendances
4. 🧪 Tests automatiques de l'API
5. 🔄 Redémarrage sans interruption de service
6. ✅ Validation que tout fonctionne
7. ⏪ Rollback automatique en cas d'erreur

## 🚨 Que faire en cas de problème ?

### API ne répond plus
```bash
axle health    # Diagnostic rapide
axle status    # État détaillé
axle deploy    # Redéploiement
```

### Erreurs dans les logs
```bash
axle logs      # Voir les erreurs récentes
```

### Problème majeur
```bash
axle rollback  # Revenir à la version précédente
```

## 🎯 Workflow Développeur

### Développement local
1. Modifiez votre code localement
2. Testez en local
3. Committez vos changements

### Déploiement production
```bash
# Une seule commande !
axle deploy
```

C'est tout ! Le système s'occupe de :
- Sauvegarder l'ancienne version
- Déployer la nouvelle
- Tester que ça marche
- Faire le rollback si problème

## 📧 Notifications (Optionnel)

Pour recevoir des alertes par email/Slack :
1. Éditer `/opt/clickup-agent/monitoring.sh`
2. Configurer `ALERT_EMAIL` ou webhook Slack
3. Les alertes se déclencheront automatiquement

## 🎉 Prêt pour la production !

Votre infrastructure est maintenant :
- 🔒 **Sécurisée** (SSL, firewall, utilisateur dédié)
- 🚀 **Performante** (Nginx, optimisations)  
- 🔄 **Automatisée** (déploiement, monitoring, sauvegardes)
- 📈 **Scalable** (structure multi-API prête)

**Concentrez-vous sur votre code, le DevOps est géré ! 🎯**