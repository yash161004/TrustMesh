"""trustmesh — a thin, tamper-evident audit layer for AI-agent conversations.

Public API::

    from trustmesh import TrustMeshWatcher, AuditedTurn

See sdk/README.md for the design rationale and honest scope.
"""
from .watcher import AuditedTurn, TrustMeshWatcher

__all__ = ["TrustMeshWatcher", "AuditedTurn"]
__version__ = "0.1.0"
