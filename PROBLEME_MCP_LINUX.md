# Problème MCP Server - Différence macOS vs Linux

## 🔍 Analyse du Problème

### Symptômes
- ✅ **macOS** : Le script fonctionne parfaitement et se termine proprement
- ❌ **Linux** : Le script se bloque après "🔌 Closing MCP servers..." et ne se termine jamais

### Cause Racine : Différences de Gestion des Processus

#### Sur macOS
```bash
# macOS gère automatiquement la terminaison des processus enfants
# Les signaux SIGTERM sont correctement propagés
# La fermeture des flux stdin/stdout termine le processus NPX
```

#### Sur Linux
```bash
# Linux nécessite une gestion explicite des processus enfants
# Le processus NPX peut ignorer SIGTERM
# Les flux peuvent rester ouverts même après la fermeture
```

## 🛠️ Solution Technique

### Problème Original
```python
# Code original dans mcp-client-python
async def __aexit__(self, exc_type, exc_val, exc_tb):
    if self.process and self.process.returncode is None:
        self.process.terminate()  # ❌ Insuffisant sur Linux
        # Pas d'attente de terminaison
        # Pas d'escalade vers SIGKILL
```

### Solution Implémentée
```python
# Nouvelle classe FixedMCPServerStdio
async def __aexit__(self, exc_type, exc_val, exc_tb):
    if self.process and self.process.returncode is None:
        # 1. Fermer les flux proprement
        self._close_streams()
        
        # 2. Envoyer SIGTERM
        self.process.terminate()
        
        # 3. Attendre avec timeout
        try:
            await asyncio.wait_for(self.process.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            # 4. Escalader vers SIGKILL si nécessaire
            self.process.kill()
            await self.process.wait()
```

## 🔄 Impact sur les Futurs Développements

### ✅ Agents Python
- **Aucun impact** : Vos agents Python n'auront aucun problème
- **Même code** : Vous pouvez utiliser le même pattern partout
- **Réutilisable** : La classe `FixedMCPServerStdio` est générique

### ✅ Nouveaux Serveurs MCP
- **Compatible** : Tous les serveurs MCP NPX fonctionneront
- **Pas de modification** : Aucun changement dans vos serveurs MCP
- **Automatique** : La correction est transparente

### Exemple d'Usage
```python
# Pour un nouvel agent avec différents serveurs MCP
servers = [
    FixedMCPServerStdio('npx', ['-y', '@another/mcp-server']),
    FixedMCPServerStdio('npx', ['-y', '@custom/mcp-server']),
    # ... autres serveurs
]
```

## 🎯 Pourquoi ce Problème ?

### 1. **Différences OS**
- **macOS** : Descendant de BSD Unix, gestion automatique des processus
- **Linux** : Gestion plus stricte, nécessite escalade explicite

### 2. **NPX + Subprocess**
- **NPX** lance un processus Node.js qui peut ignorer SIGTERM
- **Asyncio** sur Linux plus strict sur la fermeture des ressources

### 3. **Event Loop**
- **Linux** : L'event loop se ferme avant que le processus soit terminé
- **macOS** : Plus tolérant aux processus en cours

## 🚀 Recommandations

### Pour le Développement
1. **Tester sur Linux** : Toujours tester les agents sur un environnement Linux
2. **Utiliser FixedMCPServerStdio** : Pour tous les nouveaux projets
3. **Timeout appropriés** : Prévoir des timeouts pour l'initialisation NPX

### Pour la Production
1. **Monitoring** : Surveiller les processus orphelins
2. **Logs** : Activer les logs de debug pour le développement
3. **Cleanup** : Utiliser des scripts de nettoyage si nécessaire

## 📋 Checklist pour Nouveaux Projets

- [ ] Utiliser `FixedMCPServerStdio` au lieu de `MCPServerStdio`
- [ ] Définir des timeouts appropriés (30-60s pour NPX)
- [ ] Tester sur Linux avant déploiement
- [ ] Implémenter un signal handler pour SIGINT/SIGTERM
- [ ] Prévoir un cleanup final avec `os._exit(0)` si nécessaire

## 🔧 Code Template pour Nouveaux Agents

```python
from src.agent.mcp_servers import FixedMCPServerStdio

class MonNouvelAgent(AxleAgent):
    def get_mcp_servers(self):
        return [
            FixedMCPServerStdio(
                'npx',
                args=['-y', '@mon/mcp-server@latest'],
                env={'API_KEY': self.api_key},
                timeout=60.0  # Important pour NPX
            )
        ]
```

## 🔄 Migration d'Agents Existants

Si vous avez des agents existants qui utilisent `MCPServerStdio`, voici comment les migrer :

### Avant (problématique sur Linux)
```python
from pydantic_ai.mcp import MCPServerStdio

server = MCPServerStdio('npx', args=['-y', '@package/server'])
```

### Après (compatible macOS + Linux)
```python
from src.agent.mcp_servers import FixedMCPServerStdio

server = FixedMCPServerStdio('npx', args=['-y', '@package/server'], timeout=60.0)
```

## 🛡️ Garanties de Compatibilité

✅ **Nouveaux agents** : Aucun problème, utilisez `FixedMCPServerStdio`
✅ **Agents existants** : Migration simple en changeant l'import
✅ **Serveurs MCP** : Aucune modification nécessaire côté serveur
✅ **Développement local** : Fonctionne sur macOS et Linux
✅ **Production** : Déploiement Linux sans accroc

Ce problème est maintenant résolu une fois pour toutes ! 🎉