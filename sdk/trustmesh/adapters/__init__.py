"""Framework adapters for TrustMeshWatcher.

Each adapter is an *optional* integration and imports its framework lazily, so
the core `trustmesh` package stays dependency-free. Import the one you need
explicitly, e.g.::

    from trustmesh.adapters.langchain import TrustMeshCallbackHandler
"""
