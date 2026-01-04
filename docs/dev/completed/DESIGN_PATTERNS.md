# Design Patterns in Bookmark Tools

This document explains the design patterns used in the bookmark management tools.

## Factory Pattern: LLM Client Creation

### Problem

We have multiple versions of LLM clients supporting different providers (Perplexity, OpenAI, Anthropic) and extraction formats (HTML, Markdown).

The code was using conditional imports and if/else logic to choose between them, which was:
- ❌ Repetitive (same logic in multiple places)
- ❌ Hard to maintain (changes needed in multiple locations)
- ❌ Not extensible (adding new providers requires changes everywhere)
- ❌ Violates DRY (Don't Repeat Yourself) principle

### Solution: Factory Pattern

The **Factory Pattern** provides a single point of creation for objects with a common interface.

```
┌─────────────────────────────┐
│      LLMClientFactory       │
│  (creates LLMService)       │
└──────────┬──────────────────┘
           │
           │
           ▼
┌──────────────────────┐
│      LLMService      │ (Unified Interface)
└──────────┬───────────┘
           │
           │ (Composition)
           ▼
┌──────────────────────┐  ┌──────────────────────┐
│     LLMProvider      │  │   ContentExtractor   │
│ (Specific API Logic) │  │  (HTML or Markdown)  │
└──────────────────────┘  └──────────────────────┘
```

### Implementation

#### 1. Provider and Extractor Protocols

We use Python Protocols to define clear interfaces for the components used by the factory.

```python
class LLMProvider(Protocol):
    """Interface for LLM API providers."""
    def call_api(self, system_prompt: str, user_prompt: str) -> dict[str, Any]: ...
    def estimate_cost(self, tokens: int) -> float: ...
    def get_default_model(self) -> str: ...

class ContentExtractor(Protocol):
    """Interface for content extraction strategies."""
    def extract(self, url: str) -> dict[str, str]: ...
```

**Benefits:**
- ✅ Type safety with static type checkers
- ✅ Clear contract for all implementations
- ✅ Composition-based architecture

#### 2. Factory Class

The `LLMClientFactory` encapsulates the logic to assemble a complete `LLMService` with the right provider and extractor.

```python
class LLMClientFactory:
    """Factory for creating LLM clients (LLMService instances)."""
    
    @staticmethod
    def create_client(
        provider: str = "perplexity",
        content_format: str = "markdown",
        api_key: Optional[str] = None
    ) -> LLMService:
        """Assembles and returns an LLMService instance."""
        # Logic to choose LLMProvider implementation
        # Logic to choose ContentExtractor implementation
        # Return assembled LLMService
```

**Benefits:**
- ✅ Single point of creation
- ✅ Encapsulates assembly logic
- ✅ Easy to extend with new providers
- ✅ Lazy imports (only import what's needed)

#### 3. Usage in Application

**After (with Factory):**
```python
# Single line, used everywhere
from bookmarks.services import LLMClientFactory
client = LLMClientFactory.create_client(provider="openai", content_format="markdown")
```

### Benefits Achieved

1. **DRY (Don't Repeat Yourself)**
   - Creation logic in one place
   - Changes only needed in factory

2. **Open/Closed Principle**
   - Open for extension (add new providers like Gemini or local LLMs)
   - Closed for modification (existing code stays simple)

3. **Single Responsibility**
   - Factory handles creation/assembly
   - Service handles orchestration
   - Providers handle specific API communication
   - Extractors handle specific content formats

4. **Easier Testing**
   - Can mock the factory or inject mock providers/extractors
   - Isolated unit tests for each component

## Alternative Patterns Considered

### 1. Strategy Pattern

**When to use:** When you need to switch algorithms at runtime.

**Why not used here:** 
- The content extraction format is often fixed at the start of a process.
- However, the `LLMService` *uses* the strategy pattern internally by being composed with a `ContentExtractor`.

### 2. Abstract Factory Pattern

**When to use:** When you need families of related objects.

**Why not used here:**
- We don't have enough product variety to justify an abstract factory yet.
- Simple Factory around composition is sufficient.

## Summary

The **Factory Pattern** combined with **Protocols** was the right choice because:

✅ **Simple** - Easy to understand and maintain  
✅ **Flexible** - Easy to swap providers or extraction formats  
✅ **Clean** - Eliminates code duplication  
✅ **Type-safe** - Works well with Python's type system  
✅ **Testable** - Easy to mock and test  

The implementation in `llm_client_factory.py` provides a clean, maintainable solution for managing the complexity of diverse LLM integrations while keeping the application code simple and focused on bookmark management.
