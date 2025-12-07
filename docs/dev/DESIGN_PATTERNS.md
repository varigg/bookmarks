# Design Patterns in Bookmark Tools

This document explains the design patterns used in the bookmark management tools.

## Factory Pattern: Perplexity Client Creation

### Problem

We have two different implementations of Perplexity clients:
1. **Direct API Client** (`perplexity_client.py`) - Uses REST API directly
2. **MCP Client** (`perplexity_mcp_client.py`) - Uses Model Context Protocol

Both clients provide the same interface:
- `generate_description(url: str) -> dict[str, str]`
- `get_usage_stats() -> dict[str, any]`

The code was using conditional imports and if/else logic to choose between them, which was:
- ❌ Repetitive (same logic in multiple places)
- ❌ Hard to maintain (changes needed in multiple locations)
- ❌ Not extensible (adding new client types requires changes everywhere)
- ❌ Violates DRY (Don't Repeat Yourself) principle

### Solution: Factory Pattern

The **Factory Pattern** provides a single point of creation for objects with a common interface.

```
┌─────────────────────────────┐
│  PerplexityClientFactory    │
│  (creates clients)          │
└──────────┬──────────────────┘
           │
           ├─────────────────────────┐
           │                         │
           ▼                         ▼
┌──────────────────────┐  ┌──────────────────────┐
│  PerplexityClient    │  │ PerplexityMCPClient  │
│  (Direct API)        │  │ (MCP Protocol)       │
└──────────────────────┘  └──────────────────────┘
           │                         │
           └─────────┬───────────────┘
                     │
                     ▼
        PerplexityClientProtocol
        (common interface)
```

### Implementation

#### 1. Protocol Definition (Interface)

```python
class PerplexityClientProtocol(Protocol):
    """Defines the interface all clients must implement."""
    
    def generate_description(self, url: str) -> dict[str, str]:
        ...
    
    def get_usage_stats(self) -> dict[str, any]:
        ...
```

**Benefits:**
- ✅ Type safety with static type checkers
- ✅ Clear contract for all implementations
- ✅ Documentation of expected interface

#### 2. Factory Class

```python
class PerplexityClientFactory:
    """Factory for creating Perplexity clients."""
    
    @staticmethod
    def create_client(
        use_mcp: bool = False,
        api_key: Optional[str] = None
    ) -> PerplexityClientProtocol:
        """Create appropriate client based on parameters."""
        if use_mcp:
            from perplexity_mcp_client import PerplexityMCPClient
            return PerplexityMCPClient(api_key=api_key)
        else:
            from perplexity_client import PerplexityClient
            return PerplexityClient(api_key=api_key)
    
    @staticmethod
    def get_client_type_name(use_mcp: bool) -> str:
        """Get human-readable client type name."""
        return "Perplexity MCP" if use_mcp else "Perplexity API"
```

**Benefits:**
- ✅ Single point of creation
- ✅ Encapsulates conditional logic
- ✅ Easy to extend with new client types
- ✅ Lazy imports (only import what's needed)

#### 3. Usage in Application

**Before (without Factory):**
```python
# Repeated in multiple places
if use_mcp:
    from perplexity_mcp_client import PerplexityMCPClient
    client = PerplexityMCPClient()
else:
    from perplexity_client import PerplexityClient
    client = PerplexityClient()
```

**After (with Factory):**
```python
# Single line, used everywhere
from perplexity_factory import PerplexityClientFactory
client = PerplexityClientFactory.create_client(use_mcp=use_mcp)
```

### Benefits Achieved

1. **DRY (Don't Repeat Yourself)**
   - Creation logic in one place
   - Changes only needed in factory

2. **Open/Closed Principle**
   - Open for extension (add new client types)
   - Closed for modification (existing code unchanged)

3. **Single Responsibility**
   - Factory handles creation
   - Clients handle their specific logic
   - Application code handles business logic

4. **Easier Testing**
   - Can mock the factory
   - Can inject test clients
   - Isolated unit tests

5. **Better Error Messages**
   - Centralized error handling
   - Consistent messaging via `get_client_type_name()`

## Alternative Patterns Considered

### 1. Strategy Pattern

**When to use:** When you need to switch algorithms at runtime.

**Why not used here:** 
- We don't switch clients during runtime
- Client is chosen once at startup
- Factory is simpler for this use case

### 2. Abstract Factory Pattern

**When to use:** When you need families of related objects.

**Why not used here:**
- We only have one product (Perplexity client)
- No need for multiple related objects
- Simple Factory is sufficient

### 3. Builder Pattern

**When to use:** When object construction is complex with many optional parameters.

**Why not used here:**
- Client construction is simple
- Only one optional parameter (api_key)
- Factory handles this easily

### 4. Dependency Injection

**When to use:** In larger applications with complex dependencies.

**Why not used here:**
- Script-based tool, not a large application
- No DI container needed
- Factory provides sufficient decoupling

## Extending the Pattern

### Adding a New Client Type

To add a new client (e.g., Copilot):

1. **Create the client class:**
   ```python
   # copilot_client.py
   class CopilotClient:
       def generate_description(self, url: str) -> dict[str, str]:
           # Implementation
           ...
       
       def get_usage_stats(self) -> dict[str, any]:
           # Implementation
           ...
   ```

2. **Update the factory:**
   ```python
   class PerplexityClientFactory:
       @staticmethod
       def create_client(
           provider: str = 'perplexity',
           use_mcp: bool = False,
           api_key: Optional[str] = None
       ):
           if provider == 'copilot':
               from copilot_client import CopilotClient
               return CopilotClient(api_key=api_key)
           elif provider == 'perplexity':
               # Existing logic
               ...
   ```

3. **No changes needed in application code!**
   ```python
   # Still works the same way
   client = factory.create_client(provider='copilot')
   ```

## Best Practices

### 1. Use Protocols for Type Safety

```python
from typing import Protocol

class ClientProtocol(Protocol):
    def method(self) -> ReturnType: ...
```

**Benefits:**
- Static type checking
- IDE autocomplete
- Clear interface documentation

### 2. Lazy Imports in Factory

```python
def create_client(self, use_mcp: bool):
    if use_mcp:
        from module import MCPClient  # Import only when needed
        return MCPClient()
```

**Benefits:**
- Faster startup (don't import unused modules)
- Avoid import errors for unused clients
- Better dependency management

### 3. Provide Helper Methods

```python
@staticmethod
def get_client_type_name(use_mcp: bool) -> str:
    return "MCP" if use_mcp else "API"
```

**Benefits:**
- Consistent naming across application
- Easier to change display names
- Better error messages

## Summary

The **Factory Pattern** was the right choice because:

✅ **Simple** - Easy to understand and maintain  
✅ **Flexible** - Easy to add new client types  
✅ **Clean** - Eliminates code duplication  
✅ **Type-safe** - Works well with Python's type system  
✅ **Testable** - Easy to mock and test  

The implementation in `perplexity_factory.py` provides a clean, maintainable solution for managing multiple Perplexity client implementations while keeping the application code simple and focused on business logic.
