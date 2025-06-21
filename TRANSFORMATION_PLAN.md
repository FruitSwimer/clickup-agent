# Plan de Transformation : clickup-agent → axle-agent-framework

## Vue d'ensemble

Ce document détaille le plan de transformation du projet `clickup-agent` en une librairie réutilisable `axle-agent-framework`. L'objectif est de créer une extension modulaire et non-intrusive de pydantic-ai qui ajoute des fonctionnalités optionnelles via un système de Mixins.

## 1. Architecture cible

### 1.1 Structure du projet

```
axle-agent-framework/
├── src/
│   └── axle_agent/
│       ├── __init__.py
│       ├── core/
│       │   ├── __init__.py
│       │   ├── mixins/
│       │   │   ├── __init__.py
│       │   │   ├── storage.py         # StorageMixin
│       │   │   ├── mcp_lifecycle.py  # MCPLifecycleMixin
│       │   │   ├── default_tools.py  # DefaultToolsMixin
│       │   │   ├── response.py       # ResponseExtractionMixin
│       │   │   └── metrics.py        # MetricsMixin
│       │   ├── agent.py              # AxleAgent (composition de tous les mixins)
│       │   ├── dependencies.py       # Base dependencies et protocols
│       │   └── tools.py             # Collection d'outils réutilisables
│       ├── storage/
│       │   ├── __init__.py
│       │   ├── base.py              # StorageProtocol
│       │   ├── backends/
│       │   │   ├── __init__.py
│       │   │   ├── mongodb.py       # MongoDB implementation
│       │   │   ├── postgresql.py    # PostgreSQL implementation
│       │   │   ├── redis.py         # Redis implementation
│       │   │   ├── memory.py        # In-memory storage
│       │   │   └── filesystem.py    # File-based storage
│       │   ├── serializers.py       # Message serialization
│       │   └── compression.py       # Optional compression
│       ├── mcp/
│       │   ├── __init__.py
│       │   ├── server.py            # FixedMCPServerStdio
│       │   ├── manager.py           # MCPServerManager
│       │   ├── health.py            # Health checks
│       │   └── discovery.py         # MCP server discovery
│       ├── api/
│       │   ├── __init__.py
│       │   ├── fastapi.py           # FastAPI integration helpers
│       │   ├── models.py            # Common Pydantic models
│       │   └── middleware.py        # Reusable middleware
│       ├── testing/
│       │   ├── __init__.py
│       │   ├── base.py              # AgentTestCase base class
│       │   ├── fixtures.py          # Pytest fixtures
│       │   ├── mocks.py             # Mock implementations
│       │   ├── factories.py         # Test data factories
│       │   └── benchmarks.py        # Performance testing tools
│       └── cli/
│           ├── __init__.py
│           ├── main.py              # CLI entry point
│           └── templates/           # Project templates
├── tests/
│   ├── unit/
│   │   ├── mixins/
│   │   │   ├── test_storage_mixin.py
│   │   │   ├── test_mcp_lifecycle_mixin.py
│   │   │   ├── test_default_tools_mixin.py
│   │   │   ├── test_response_mixin.py
│   │   │   └── test_metrics_mixin.py
│   │   ├── storage/
│   │   │   ├── test_mongodb_backend.py
│   │   │   ├── test_memory_backend.py
│   │   │   └── test_serializers.py
│   │   ├── mcp/
│   │   │   ├── test_fixed_mcp_server.py
│   │   │   ├── test_manager.py
│   │   │   └── test_health_checks.py
│   │   └── test_tools.py
│   ├── integration/
│   │   ├── test_mixin_composition.py
│   │   ├── test_storage_backends.py
│   │   ├── test_mcp_lifecycle.py
│   │   └── test_fastapi_integration.py
│   ├── e2e/
│   │   ├── test_full_agent_flow.py
│   │   ├── test_multi_agent_system.py
│   │   └── test_production_scenarios.py
│   └── benchmarks/
│       ├── test_performance.py
│       ├── test_memory_usage.py
│       └── test_scalability.py
├── examples/
│   ├── 01_basic_agent/
│   ├── 02_with_storage/
│   ├── 03_multiple_mixins/
│   ├── 04_custom_mixin/
│   ├── 05_production_agent/
│   ├── 06_fastapi_app/
│   └── 07_multi_agent/
├── docs/
│   ├── getting-started.md
│   ├── architecture.md
│   ├── mixins-guide.md
│   ├── storage-backends.md
│   ├── mcp-servers.md
│   ├── testing-guide.md
│   ├── migration-guide.md
│   └── api-reference/
├── .github/
│   └── workflows/
│       ├── tests.yml
│       ├── release.yml
│       ├── docs.yml
│       └── security.yml
├── pyproject.toml
├── Makefile
├── README.md
├── CHANGELOG.md
└── CONTRIBUTING.md
```

### 1.2 Design des Mixins

#### StorageMixin
```python
from typing import Protocol, Optional, runtime_checkable
from pydantic_ai import Agent, RunContext
from pydantic_ai.agent import AgentRunResult

@runtime_checkable
class StorageProtocol(Protocol):
    """Protocol for storage backends"""
    async def save_run(self, session_id: str, result: AgentRunResult) -> None: ...
    async def get_history(self, session_id: str) -> list[dict]: ...
    async def clear_session(self, session_id: str) -> None: ...

class StorageMixin:
    """Adds automatic conversation persistence to agents"""
    
    def __init__(self, *args, storage: Optional[StorageProtocol] = None, **kwargs):
        super().__init__(*args, **kwargs)
        self._storage = storage
        self._auto_save = kwargs.pop('auto_save', True)
    
    async def run(self, prompt: str, *, context: RunContext, **kwargs) -> AgentRunResult:
        # Load history if storage is available
        message_history = kwargs.get('message_history', [])
        if self._storage and hasattr(context.deps, 'session_id'):
            stored_history = await self._storage.get_history(context.deps.session_id)
            message_history = stored_history + message_history
            kwargs['message_history'] = message_history
        
        # Run the agent
        result = await super().run(prompt, context=context, **kwargs)
        
        # Save if enabled
        if self._storage and self._auto_save and hasattr(context.deps, 'session_id'):
            await self._storage.save_run(context.deps.session_id, result)
        
        return result
```

#### MCPLifecycleMixin
```python
class MCPLifecycleMixin:
    """Automatically manages MCP server lifecycle"""
    
    def __init__(self, *args, mcp_timeout: float = 60.0, **kwargs):
        super().__init__(*args, **kwargs)
        self._mcp_timeout = mcp_timeout
        self._mcp_health_check = kwargs.pop('mcp_health_check', True)
    
    async def run(self, *args, **kwargs) -> AgentRunResult:
        # Start MCP servers with health checks
        async with self.run_mcp_servers(timeout=self._mcp_timeout) as servers:
            if self._mcp_health_check:
                await self._check_mcp_health(servers)
            
            return await super().run(*args, **kwargs)
    
    async def _check_mcp_health(self, servers):
        """Verify MCP servers are responsive"""
        # Implementation
```

#### DefaultToolsMixin
```python
class DefaultToolsMixin:
    """Adds configurable default tools to agents"""
    
    def __init__(self, *args, default_tools: Optional[list] = None, **kwargs):
        # Get existing tools
        tools = kwargs.get('tools', [])
        
        # Add default tools
        if default_tools is None:
            default_tools = ['datetime', 'user_info']
        
        tool_registry = {
            'datetime': get_current_datetime,
            'user_info': get_user_info,
            'calculator': calculator_tool,
            'web_search': web_search_tool,
        }
        
        for tool_name in default_tools:
            if tool_name in tool_registry:
                tools.append(tool_registry[tool_name])
        
        kwargs['tools'] = tools
        super().__init__(*args, **kwargs)
```

#### ResponseExtractionMixin
```python
class ResponseExtractionMixin:
    """Provides convenient methods to extract responses"""
    
    def get_text_response(self, result: AgentRunResult) -> Optional[str]:
        """Extract the last text response from the agent"""
        for message in reversed(result.all_messages()):
            if isinstance(message, ModelResponse):
                for part in message.parts:
                    if isinstance(part, TextPart):
                        return part.content
        return None
    
    def get_tool_calls(self, result: AgentRunResult) -> list[ToolCall]:
        """Extract all tool calls from the result"""
        # Implementation
```

#### MetricsMixin
```python
from dataclasses import dataclass
from datetime import datetime
import time

@dataclass
class AgentMetrics:
    start_time: datetime
    end_time: datetime
    duration_ms: float
    token_count: int
    tool_calls: int
    errors: list[str]

class MetricsMixin:
    """Collects metrics about agent runs"""
    
    def __init__(self, *args, collect_metrics: bool = False, **kwargs):
        super().__init__(*args, **kwargs)
        self._collect_metrics = collect_metrics
        self._metrics_history: list[AgentMetrics] = []
    
    async def run(self, *args, **kwargs) -> AgentRunResult:
        if not self._collect_metrics:
            return await super().run(*args, **kwargs)
        
        start = time.time()
        errors = []
        
        try:
            result = await super().run(*args, **kwargs)
            
            metrics = AgentMetrics(
                start_time=datetime.fromtimestamp(start),
                end_time=datetime.now(),
                duration_ms=(time.time() - start) * 1000,
                token_count=result.usage.total_tokens if result.usage else 0,
                tool_calls=len([m for m in result.all_messages() if isinstance(m, ToolCall)]),
                errors=errors
            )
            
            self._metrics_history.append(metrics)
            return result
            
        except Exception as e:
            errors.append(str(e))
            raise
```

### 1.3 Composition et utilisation

```python
from pydantic_ai import Agent
from axle_agent import (
    StorageMixin, MCPLifecycleMixin, DefaultToolsMixin,
    ResponseExtractionMixin, MetricsMixin, AxleAgent
)
from axle_agent.storage.backends import MongoDBStorage

# 1. Agent Pydantic-AI vanilla (aucun changement)
vanilla_agent = Agent(
    model='gpt-4',
    system_prompt='You are a helpful assistant'
)

# 2. Agent avec storage seulement
class AgentWithStorage(StorageMixin, Agent):
    pass

agent = AgentWithStorage(
    model='gpt-4',
    storage=MongoDBStorage(uri='mongodb://localhost:27017')
)

# 3. Agent avec plusieurs mixins
class CustomAgent(StorageMixin, MCPLifecycleMixin, DefaultToolsMixin, Agent):
    pass

agent = CustomAgent(
    model='gpt-4',
    storage=MongoDBStorage(),
    default_tools=['datetime', 'calculator'],
    mcp_servers=[MyMCPServer()]
)

# 4. Utiliser AxleAgent (tous les mixins pré-configurés)
agent = AxleAgent(
    agent_id='my-agent',
    model='gpt-4',
    storage=MongoDBStorage(),
    enable_metrics=True
)

# 5. Création dynamique avec helper
from axle_agent import compose_agent

agent = compose_agent(
    Agent,
    mixins=['storage', 'mcp_lifecycle'],
    storage=MongoDBStorage(),
    model='gpt-4'
)
```

## 2. Plan d'implémentation

### Phase 1 : Core Foundation (Semaines 1-2)

#### Semaine 1
- [ ] Setup du nouveau repository `axle-agent-framework`
- [ ] Configuration pyproject.toml avec dependencies optionnelles
- [ ] Extraction et refactoring de `StorageMixin`
- [ ] Extraction et refactoring de `MCPLifecycleMixin`
- [ ] Création du `StorageProtocol`
- [ ] Tests unitaires pour les deux mixins principaux

#### Semaine 2
- [ ] Implémentation de `DefaultToolsMixin`
- [ ] Implémentation de `ResponseExtractionMixin`
- [ ] Implémentation de `MetricsMixin`
- [ ] Création de la classe `AxleAgent` composée
- [ ] Tests d'intégration pour la composition des mixins
- [ ] Documentation de base avec docstrings

### Phase 2 : Storage System (Semaines 3-4)

#### Semaine 3
- [ ] Implémentation du backend MongoDB (migration depuis code existant)
- [ ] Implémentation du backend In-Memory
- [ ] Implémentation du backend Filesystem
- [ ] Système de serialization/deserialization
- [ ] Tests unitaires pour chaque backend

#### Semaine 4
- [ ] Implémentation backends PostgreSQL et Redis
- [ ] Support de la compression (gzip, zstd)
- [ ] Support du chiffrement (optionnel)
- [ ] Outils de migration depuis l'ancien format
- [ ] Tests de performance et benchmarks

### Phase 3 : MCP Enhancements (Semaine 5)

- [ ] Amélioration de `FixedMCPServerStdio` avec meilleur support cross-platform
- [ ] Implémentation de `MCPServerManager` pour gérer plusieurs serveurs
- [ ] Système de health checks pour les serveurs MCP
- [ ] Retry logic et circuit breaker
- [ ] Monitoring des ressources (CPU, mémoire)
- [ ] Tests cross-platform (Linux, macOS, Windows)

### Phase 4 : Testing Framework (Semaine 6)

- [ ] Création de `AgentTestCase` base class
- [ ] Fixtures pytest réutilisables
- [ ] Mock implementations pour tous les composants
- [ ] Test data factories
- [ ] Benchmarking tools
- [ ] Documentation du testing framework

### Phase 5 : Developer Experience (Semaine 7)

- [ ] CLI avec commandes : `axle-agent new`, `axle-agent test`, etc.
- [ ] Templates de projets (minimal, avec storage, production-ready)
- [ ] Générateur de code pour custom mixins
- [ ] VS Code snippets et extension
- [ ] Exemples complets avec README

### Phase 6 : Documentation & Release (Semaine 8)

- [ ] Documentation complète avec MkDocs
- [ ] Guide de migration depuis clickup-agent
- [ ] Tutoriels step-by-step
- [ ] API reference auto-générée
- [ ] Setup CI/CD avec GitHub Actions
- [ ] Publication sur PyPI

## 3. Testing Strategy

### 3.1 Structure des tests

```python
# tests/unit/mixins/test_storage_mixin.py
import pytest
from unittest.mock import Mock, AsyncMock
from axle_agent.core.mixins import StorageMixin
from pydantic_ai import Agent

class TestStorageMixin:
    @pytest.fixture
    def mock_storage(self):
        storage = Mock()
        storage.save_run = AsyncMock()
        storage.get_history = AsyncMock(return_value=[])
        return storage
    
    @pytest.mark.asyncio
    async def test_saves_run_when_storage_provided(self, mock_storage):
        class TestAgent(StorageMixin, Agent):
            pass
        
        agent = TestAgent(model='test', storage=mock_storage)
        result = await agent.run('test prompt', context=...)
        
        mock_storage.save_run.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_works_without_storage(self):
        class TestAgent(StorageMixin, Agent):
            pass
        
        agent = TestAgent(model='test', storage=None)
        # Should not raise
        result = await agent.run('test prompt', context=...)
    
    @pytest.mark.asyncio
    async def test_loads_history_from_storage(self, mock_storage):
        mock_storage.get_history.return_value = [
            {'role': 'user', 'content': 'previous message'}
        ]
        
        class TestAgent(StorageMixin, Agent):
            pass
        
        agent = TestAgent(model='test', storage=mock_storage)
        result = await agent.run('test prompt', context=...)
        
        mock_storage.get_history.assert_called_once()
```

### 3.2 Tests d'intégration

```python
# tests/integration/test_mixin_composition.py
@pytest.mark.integration
class TestMixinComposition:
    @pytest.mark.asyncio
    async def test_multiple_mixins_work_together(self, mongodb_fixture):
        class MyAgent(StorageMixin, MCPLifecycleMixin, MetricsMixin, Agent):
            pass
        
        agent = MyAgent(
            model='gpt-4',
            storage=MongoDBStorage(mongodb_fixture.uri),
            collect_metrics=True,
            mcp_servers=[TestMCPServer()]
        )
        
        result = await agent.run('test', context=...)
        
        # Verify all mixins functioned
        assert agent._metrics_history  # Metrics collected
        # Check storage has data
        # Verify MCP servers were used
```

### 3.3 Tests de performance

```python
# tests/benchmarks/test_performance.py
import pytest
from axle_agent.testing import benchmark_agent

@pytest.mark.benchmark
def test_mixin_overhead(benchmark):
    """Test overhead of mixins vs vanilla agent"""
    vanilla = Agent(model='gpt-4')
    with_mixins = AxleAgent(model='gpt-4')
    
    vanilla_time = benchmark(vanilla.run, 'test prompt')
    mixin_time = benchmark(with_mixins.run, 'test prompt')
    
    # Overhead should be minimal (< 5%)
    assert mixin_time < vanilla_time * 1.05
```

### 3.4 Property-based testing

```python
# tests/unit/test_storage_serialization.py
from hypothesis import given, strategies as st
from axle_agent.storage.serializers import MessageSerializer

class TestSerialization:
    @given(st.text(), st.integers(), st.lists(st.text()))
    def test_serialization_roundtrip(self, content, tokens, tags):
        original = {
            'content': content,
            'tokens': tokens,
            'tags': tags
        }
        
        serialized = MessageSerializer.serialize(original)
        deserialized = MessageSerializer.deserialize(serialized)
        
        assert deserialized == original
```

## 4. CI/CD Pipeline

### 4.1 GitHub Actions Workflow

```yaml
# .github/workflows/tests.yml
name: Tests

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: |
          pip install ruff mypy
          ruff check .
          mypy src/

  test:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
        python-version: ['3.9', '3.10', '3.11', '3.12']
    
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: ${{ matrix.python-version }}
      
      - name: Install dependencies
        run: |
          pip install -e ".[test]"
      
      - name: Run unit tests
        run: pytest tests/unit -v --cov=axle_agent
      
      - name: Run integration tests
        run: |
          docker-compose -f tests/docker-compose.yml up -d
          pytest tests/integration -v
          docker-compose -f tests/docker-compose.yml down

  benchmark:
    runs-on: ubuntu-latest
    if: github.event_name == 'push'
    steps:
      - uses: actions/checkout@v3
      - run: |
          pip install -e ".[test,benchmark]"
          pytest tests/benchmarks --benchmark-only
```

### 4.2 Release workflow

```yaml
# .github/workflows/release.yml
name: Release

on:
  push:
    tags:
      - 'v*'

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Build and publish
        run: |
          pip install build twine
          python -m build
          twine upload dist/*
        env:
          TWINE_USERNAME: __token__
          TWINE_PASSWORD: ${{ secrets.PYPI_API_TOKEN }}
```

## 5. Documentation

### 5.1 Structure de la documentation

```
docs/
├── index.md                 # Landing page
├── getting-started/
│   ├── installation.md     # Installation guide
│   ├── quickstart.md       # 5-minute tutorial
│   └── concepts.md         # Core concepts
├── guides/
│   ├── mixins.md          # Using mixins
│   ├── storage.md         # Storage backends
│   ├── mcp-servers.md     # MCP integration
│   ├── testing.md         # Testing agents
│   └── production.md      # Production deployment
├── api-reference/
│   ├── mixins.md
│   ├── storage.md
│   ├── mcp.md
│   └── testing.md
├── examples/
│   └── ... (linked from examples/)
└── migration/
    ├── from-clickup-agent.md
    └── from-vanilla-pydantic-ai.md
```

### 5.2 Documentation automatique

```python
# docs/conf.py pour Sphinx/MkDocs
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx.ext.viewcode',
    'sphinx_autodoc_typehints',
    'myst_parser',
]

# Auto-generate API docs from docstrings
autodoc_default_options = {
    'members': True,
    'member-order': 'bysource',
    'special-members': '__init__',
    'undoc-members': True,
    'exclude-members': '__weakref__'
}
```

## 6. Exemples

### 6.1 Structure des exemples

Chaque exemple suit cette structure :
```
examples/XX_example_name/
├── README.md           # Description et instructions
├── requirements.txt    # Dependencies spécifiques
├── src/
│   └── agent.py       # Code de l'agent
├── tests/
│   └── test_agent.py  # Tests de l'exemple
└── Dockerfile         # Si applicable
```

### 6.2 Progression des exemples

1. **01_basic_agent** : Agent minimal sans mixins
2. **02_with_storage** : Ajout de persistence MongoDB
3. **03_multiple_mixins** : Composition de plusieurs mixins
4. **04_custom_mixin** : Création d'un mixin personnalisé
5. **05_production_agent** : Agent complet avec monitoring, storage, MCP
6. **06_fastapi_app** : Intégration dans une API REST
7. **07_multi_agent** : Système multi-agents collaboratifs

## 7. Compatibilité et Versioning

### 7.1 Politique de compatibilité

- **Python** : Support 3.9+ (pour les type hints modernes)
- **pydantic-ai** : Support des 3 dernières versions majeures
- **Dependencies** : Toutes optionnelles sauf pydantic-ai
- **Breaking changes** : Seulement dans les versions majeures

### 7.2 Gestion des versions

```python
# src/axle_agent/__init__.py
__version__ = '1.0.0'

# Semantic versioning
# MAJOR.MINOR.PATCH
# - MAJOR: Breaking changes
# - MINOR: New features (backwards compatible)
# - PATCH: Bug fixes

# Feature flags pour la rétrocompatibilité
from axle_agent.compat import features

features.enable('experimental_mcp_v2')
features.disable('legacy_storage_format')
```

## 8. Performance et optimisation

### 8.1 Objectifs de performance

- Overhead des mixins < 5% vs pydantic-ai vanilla
- Storage async avec batching pour haute performance
- MCP server pooling pour réutilisation
- Lazy loading des dépendances optionnelles

### 8.2 Optimisations prévues

```python
# Lazy imports pour les backends
def get_mongodb_storage():
    from axle_agent.storage.backends.mongodb import MongoDBStorage
    return MongoDBStorage

# Connection pooling
class StoragePool:
    def __init__(self, backend_class, pool_size=10):
        self._pool = []
        self._backend_class = backend_class
    
    async def acquire(self):
        # Return connection from pool
        pass
```

## 9. Sécurité

### 9.1 Bonnes pratiques

- Pas de credentials dans le code
- Support des variables d'environnement
- Validation des inputs avec Pydantic
- Sanitization des données stockées
- Encryption at rest optionnelle

### 9.2 Scanning de sécurité

```yaml
# .github/workflows/security.yml
- name: Security scan
  run: |
    pip install bandit safety
    bandit -r src/
    safety check
```

## 10. Métriques de succès

### 10.1 Objectifs techniques

- ✅ 90%+ code coverage
- ✅ < 5% performance overhead
- ✅ Support Python 3.9-3.12
- ✅ Support Linux/macOS/Windows
- ✅ 100% backwards compatible avec pydantic-ai

### 10.2 Objectifs d'adoption

- Documentation complète avec exemples
- Migration facile depuis clickup-agent
- API intuitive et pythonique
- Communauté active (issues, PRs)
- Utilisable en production dès v1.0

## Prochaines étapes

1. **Validation** : Revoir ce plan avec l'équipe
2. **Setup** : Créer le repository et la structure de base
3. **Prototype** : Implémenter StorageMixin et MCPLifecycleMixin
4. **Feedback** : Tester avec clickup-agent migré
5. **Itération** : Affiner basé sur les retours
6. **Release** : Publier v0.1.0 en alpha

---

Ce plan sera mis à jour régulièrement pendant le développement.