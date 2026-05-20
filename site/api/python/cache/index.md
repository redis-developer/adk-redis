# cache

## cache

Semantic caching for ADK agents using Redis.

### LLMResponseCache

```python
LLMResponseCache(provider: BaseCacheProvider, config: Optional[LLMResponseCacheConfig] = None)
```

Cache service for LLM responses.

This service caches LLM responses using semantic similarity matching. It can be configured to only cache first messages in a session to reduce API costs for common initial queries.

Initialize the LLM response cache.

Parameters:

| Name       | Type                               | Description                            | Default    |
| ---------- | ---------------------------------- | -------------------------------------- | ---------- |
| `provider` | `BaseCacheProvider`                | The cache provider to use for storage. | *required* |
| `config`   | `Optional[LLMResponseCacheConfig]` | Configuration for caching behavior.    | `None`     |

Source code in `src/adk_redis/cache/llm_cache.py`

```python
def __init__(
    self,
    provider: BaseCacheProvider,
    config: Optional[LLMResponseCacheConfig] = None,
):
  """Initialize the LLM response cache.

  Args:
      provider: The cache provider to use for storage.
      config: Configuration for caching behavior.
  """
  self._provider = provider
  self._config = config or LLMResponseCacheConfig()
  # Track pending prompts by session ID for after_model_callback
  self._pending_prompts: dict[str, str] = {}
```

#### before_model_callback

```python
before_model_callback(callback_context: CallbackContext, llm_request: LlmRequest) -> Optional[LlmResponse]
```

Check cache before making LLM call.

Parameters:

| Name               | Type              | Description                             | Default    |
| ------------------ | ----------------- | --------------------------------------- | ---------- |
| `callback_context` | `CallbackContext` | The callback context with session info. | *required* |
| `llm_request`      | `LlmRequest`      | The LLM request being made.             | *required* |

Returns:

| Type                    | Description                                              |
| ----------------------- | -------------------------------------------------------- |
| `Optional[LlmResponse]` | LlmResponse if cache hit, None to proceed with LLM call. |

Source code in `src/adk_redis/cache/llm_cache.py`

```python
async def before_model_callback(
    self,
    callback_context: CallbackContext,
    llm_request: LlmRequest,
) -> Optional[LlmResponse]:
  """Check cache before making LLM call.

  Args:
      callback_context: The callback context with session info.
      llm_request: The LLM request being made.

  Returns:
      LlmResponse if cache hit, None to proceed with LLM call.
  """
  if self._config.first_message_only and not self._is_first_message(
      callback_context
  ):
    logger.debug("Not first message, skipping cache check")
    return None

  prompt = self._extract_prompt(llm_request)
  if not prompt:
    logger.debug("No prompt found in request")
    return None

  cache_key = self._build_cache_key(prompt, callback_context)
  cache_entry = await self._provider.check(cache_key)

  if cache_entry:
    logger.info("Cache hit for prompt: %s", prompt[:50])
    return LlmResponse(
        content=types.Content(
            role="model",
            parts=[types.Part(text=cache_entry.response)],
        )
    )

  logger.debug("Cache miss for prompt: %s", prompt[:50])
  # Store prompt for after_model_callback
  session_key = self._get_session_key(callback_context)
  self._pending_prompts[session_key] = cache_key
  return None
```

#### after_model_callback

```python
after_model_callback(callback_context: CallbackContext, llm_response: LlmResponse) -> Optional[LlmResponse]
```

Store response in cache after LLM call.

Parameters:

| Name               | Type              | Description                             | Default    |
| ------------------ | ----------------- | --------------------------------------- | ---------- |
| `callback_context` | `CallbackContext` | The callback context with session info. | *required* |
| `llm_response`     | `LlmResponse`     | The LLM response to cache.              | *required* |

Returns:

| Type                    | Description                                 |
| ----------------------- | ------------------------------------------- |
| `Optional[LlmResponse]` | None to pass through the original response. |

Source code in `src/adk_redis/cache/llm_cache.py`

```python
async def after_model_callback(
    self,
    callback_context: CallbackContext,
    llm_response: LlmResponse,
) -> Optional[LlmResponse]:
  """Store response in cache after LLM call.

  Args:
      callback_context: The callback context with session info.
      llm_response: The LLM response to cache.

  Returns:
      None to pass through the original response.
  """
  session_key = self._get_session_key(callback_context)
  cache_key = self._pending_prompts.pop(session_key, None)

  if not cache_key:
    logger.debug("No pending prompt for session, skipping cache store")
    return None

  # Don't cache error responses
  if llm_response.error_message:
    logger.debug("Response has error, skipping cache store")
    return None

  # Don't cache function call responses
  if llm_response.content and llm_response.content.parts:
    for part in llm_response.content.parts:
      if hasattr(part, "function_call") and part.function_call:
        logger.debug("Response is function call, skipping cache store")
        return None

  response_text = self._extract_response_text(llm_response)
  if not response_text:
    logger.debug("No text in response, skipping cache store")
    return None

  await self._provider.store(cache_key, response_text)
  logger.info("Cached response for prompt: %s", cache_key[:50])
  return None
```

### LLMResponseCacheConfig

Bases: `BaseModel`

Configuration for LLM response caching.

Attributes:

| Name                 | Type   | Description                          |
| -------------------- | ------ | ------------------------------------ |
| `first_message_only` | `bool` | Only cache first message in session. |
| `include_app_name`   | `bool` | Include app name in cache key.       |
| `include_user_id`    | `bool` | Include user ID in cache key.        |
| `include_session_id` | `bool` | Include session ID in cache key.     |

### BaseCacheProvider

Bases: `ABC`

Abstract base class for cache providers.

#### check

```python
check(prompt: str, **kwargs: Any) -> Optional[CacheEntry]
```

Check if a semantically similar prompt exists in the cache.

Source code in `src/adk_redis/cache/_provider.py`

```python
@abstractmethod
async def check(self, prompt: str, **kwargs: Any) -> Optional[CacheEntry]:
  """Check if a semantically similar prompt exists in the cache."""
  pass
```

#### store

```python
store(prompt: str, response: str, metadata: Optional[dict[str, Any]] = None, **kwargs: Any) -> None
```

Store a prompt-response pair in the cache.

Source code in `src/adk_redis/cache/_provider.py`

```python
@abstractmethod
async def store(
    self,
    prompt: str,
    response: str,
    metadata: Optional[dict[str, Any]] = None,
    **kwargs: Any,
) -> None:
  """Store a prompt-response pair in the cache."""
  pass
```

#### clear

```python
clear(**kwargs: Any) -> None
```

Clear all entries from the cache.

Source code in `src/adk_redis/cache/_provider.py`

```python
@abstractmethod
async def clear(self, **kwargs: Any) -> None:
  """Clear all entries from the cache."""
  pass
```

#### close

```python
close() -> None
```

Close the cache provider and release resources.

Source code in `src/adk_redis/cache/_provider.py`

```python
@abstractmethod
async def close(self) -> None:
  """Close the cache provider and release resources."""
  pass
```

### CacheEntry

```python
CacheEntry(prompt: str, response: str, distance: Optional[float] = None, metadata: Optional[dict[str, Any]] = None)
```

Represents a cached entry.

### LangCacheProvider

```python
LangCacheProvider(config: LangCacheProviderConfig)
```

Bases: `BaseCacheProvider`

Cache provider using Redis LangCache (managed semantic cache service).

LangCache is a managed semantic caching service that handles embedding generation, storage, and retrieval. Unlike RedisVLCacheProvider, it does not require a local vectorizer — embeddings are handled server-side.

Requires redisvl>=0.11.1 with LangCache support.

Initialize the LangCache cache provider.

Parameters:

| Name     | Type                      | Description                               | Default    |
| -------- | ------------------------- | ----------------------------------------- | ---------- |
| `config` | `LangCacheProviderConfig` | Configuration for the LangCache provider. | *required* |

Raises:

| Type          | Description                          |
| ------------- | ------------------------------------ |
| `ImportError` | If redisvl>=0.11.1 is not installed. |

Source code in `src/adk_redis/cache/_provider.py`

```python
def __init__(self, config: LangCacheProviderConfig):
  """Initialize the LangCache cache provider.

  Args:
    config: Configuration for the LangCache provider.

  Raises:
    ImportError: If redisvl>=0.11.1 is not installed.
  """
  try:
    from redisvl.extensions.cache.llm import LangCacheSemanticCache
  except ImportError as e:
    raise ImportError(
        "redisvl>=0.11.1 with LangCache support is required for "
        "LangCacheProvider. Install it with: "
        "pip install 'adk-redis[langcache]'"
    ) from e

  self._config = config
  self._cache = LangCacheSemanticCache(
      name=config.name,
      server_url=config.server_url,
      cache_id=config.cache_id,
      api_key=config.api_key.get_secret_value(),
      ttl=config.ttl,
      use_exact_search=config.use_exact_search,
      use_semantic_search=config.use_semantic_search,
      distance_scale="redis",
  )
```

#### check

```python
check(prompt: str, **kwargs: Any) -> Optional[CacheEntry]
```

Check for a semantically similar prompt in LangCache.

Parameters:

| Name       | Type  | Description                                              | Default    |
| ---------- | ----- | -------------------------------------------------------- | ---------- |
| `prompt`   | `str` | The prompt to check.                                     | *required* |
| `**kwargs` | `Any` | Additional keyword arguments (e.g., distance_threshold). | `{}`       |

Returns:

| Type                   | Description                                           |
| ---------------------- | ----------------------------------------------------- |
| `Optional[CacheEntry]` | A CacheEntry if a cache hit is found, None otherwise. |

Source code in `src/adk_redis/cache/_provider.py`

```python
async def check(self, prompt: str, **kwargs: Any) -> Optional[CacheEntry]:
  """Check for a semantically similar prompt in LangCache.

  Args:
    prompt: The prompt to check.
    **kwargs: Additional keyword arguments (e.g., distance_threshold).

  Returns:
    A CacheEntry if a cache hit is found, None otherwise.
  """
  distance_threshold = kwargs.get(
      "distance_threshold", self._config.distance_threshold
  )
  acheck_kwargs: dict[str, Any] = {"prompt": prompt}
  if distance_threshold is not None:
    acheck_kwargs["distance_threshold"] = distance_threshold
  result = await self._cache.acheck(**acheck_kwargs)
  if result:
    logger.debug("LangCache hit for prompt: %s", prompt[:50])
    return CacheEntry(
        prompt=prompt,
        response=result[0]["response"],
        distance=result[0].get("vector_distance"),
        metadata=result[0].get("metadata"),
    )
  logger.debug("LangCache miss for prompt: %s", prompt[:50])
  return None
```

#### store

```python
store(prompt: str, response: str, metadata: Optional[dict[str, Any]] = None, **kwargs: Any) -> None
```

Store a prompt-response pair in LangCache.

Parameters:

| Name       | Type                       | Description                                     | Default    |
| ---------- | -------------------------- | ----------------------------------------------- | ---------- |
| `prompt`   | `str`                      | The prompt text.                                | *required* |
| `response` | `str`                      | The response text.                              | *required* |
| `metadata` | `Optional[dict[str, Any]]` | Optional metadata to store alongside the entry. | `None`     |
| `**kwargs` | `Any`                      | Additional keyword arguments (e.g., ttl).       | `{}`       |

Source code in `src/adk_redis/cache/_provider.py`

```python
async def store(
    self,
    prompt: str,
    response: str,
    metadata: Optional[dict[str, Any]] = None,
    **kwargs: Any,
) -> None:
  """Store a prompt-response pair in LangCache.

  Args:
    prompt: The prompt text.
    response: The response text.
    metadata: Optional metadata to store alongside the entry.
    **kwargs: Additional keyword arguments (e.g., ttl).
  """
  astore_kwargs: dict[str, Any] = {
      "prompt": prompt,
      "response": response,
      "metadata": metadata,
  }
  # Only override TTL when an explicit, non-None value is provided.
  ttl = kwargs.get("ttl")
  if ttl is not None:
    astore_kwargs["ttl"] = ttl
  await self._cache.astore(**astore_kwargs)
  logger.debug("LangCache stored response for prompt: %s", prompt[:50])
```

#### clear

```python
clear(**kwargs: Any) -> None
```

Clear all entries from the LangCache.

Source code in `src/adk_redis/cache/_provider.py`

```python
async def clear(self, **kwargs: Any) -> None:
  """Clear all entries from the LangCache."""
  await self._cache.aclear()
  logger.info("LangCache cleared")
```

#### close

```python
close() -> None
```

Close the LangCache provider and release resources.

Source code in `src/adk_redis/cache/_provider.py`

```python
async def close(self) -> None:
  """Close the LangCache provider and release resources."""
  await self._cache.adisconnect()
  logger.debug("LangCache provider closed")
```

### LangCacheProviderConfig

Bases: `BaseModel`

Configuration for LangCache (managed semantic cache) provider.

LangCache is a managed semantic caching service provided by Redis. It requires a cache_id and api_key from the LangCache service.

### RedisVLCacheProvider

```python
RedisVLCacheProvider(config: RedisVLCacheProviderConfig, vectorizer: Any)
```

Bases: `BaseCacheProvider`

Cache provider using RedisVL's SemanticCache.

Initialize the RedisVL cache provider.

Source code in `src/adk_redis/cache/_provider.py`

```python
def __init__(self, config: RedisVLCacheProviderConfig, vectorizer: Any):
  """Initialize the RedisVL cache provider."""
  try:
    from redisvl.extensions.cache.llm import SemanticCache
  except ImportError as e:
    raise ImportError(
        "redisvl is required for RedisVLCacheProvider. "
        "Install it with: pip install redisvl>=0.18.2"
    ) from e

  self._config = config
  self._vectorizer = vectorizer
  self._cache = SemanticCache(
      name=config.name,
      redis_url=config.redis_url,
      ttl=config.ttl,
      distance_threshold=config.distance_threshold,
      vectorizer=vectorizer,
      overwrite=True,  # Overwrite existing index if schema doesn't match
  )
```

#### check

```python
check(prompt: str, **kwargs: Any) -> Optional[CacheEntry]
```

Check for a semantically similar prompt in the cache.

Source code in `src/adk_redis/cache/_provider.py`

```python
async def check(self, prompt: str, **kwargs: Any) -> Optional[CacheEntry]:
  """Check for a semantically similar prompt in the cache."""
  result = await asyncio.to_thread(self._cache.check, prompt=prompt)
  if result:
    logger.debug("Cache hit for prompt: %s", prompt[:50])
    return CacheEntry(
        prompt=prompt,
        response=result[0]["response"],
        distance=result[0].get("vector_distance"),
    )
  logger.debug("Cache miss for prompt: %s", prompt[:50])
  return None
```

#### store

```python
store(prompt: str, response: str, metadata: Optional[dict[str, Any]] = None, **kwargs: Any) -> None
```

Store a prompt-response pair in the cache.

Source code in `src/adk_redis/cache/_provider.py`

```python
async def store(
    self,
    prompt: str,
    response: str,
    metadata: Optional[dict[str, Any]] = None,
    **kwargs: Any,
) -> None:
  """Store a prompt-response pair in the cache."""
  await asyncio.to_thread(self._cache.store, prompt=prompt, response=response)
  logger.debug("Stored response for prompt: %s", prompt[:50])
```

#### clear

```python
clear(**kwargs: Any) -> None
```

Clear all entries from the cache.

Source code in `src/adk_redis/cache/_provider.py`

```python
async def clear(self, **kwargs: Any) -> None:
  """Clear all entries from the cache."""
  await asyncio.to_thread(self._cache.clear)
  logger.info("Cache cleared")
```

#### close

```python
close() -> None
```

Close the cache provider and release resources.

Source code in `src/adk_redis/cache/_provider.py`

```python
async def close(self) -> None:
  """Close the cache provider and release resources."""
  if hasattr(self._cache, "_index") and hasattr(self._cache._index, "client"):
    await asyncio.to_thread(self._cache._index.client.close)
  logger.debug("RedisVL cache provider closed")
```

### RedisVLCacheProviderConfig

Bases: `BaseModel`

Configuration for RedisVL cache provider.

### ToolCache

```python
ToolCache(provider: BaseCacheProvider, config: Optional[ToolCacheConfig] = None)
```

Cache service for tool call results.

This service caches tool results using semantic similarity matching on the tool name and arguments. It can be configured to only cache specific tools.

Initialize the tool cache.

Parameters:

| Name       | Type                        | Description                            | Default    |
| ---------- | --------------------------- | -------------------------------------- | ---------- |
| `provider` | `BaseCacheProvider`         | The cache provider to use for storage. | *required* |
| `config`   | `Optional[ToolCacheConfig]` | Configuration for caching behavior.    | `None`     |

Source code in `src/adk_redis/cache/tool_cache.py`

```python
def __init__(
    self,
    provider: BaseCacheProvider,
    config: Optional[ToolCacheConfig] = None,
):
  """Initialize the tool cache.

  Args:
      provider: The cache provider to use for storage.
      config: Configuration for caching behavior.
  """
  self._provider = provider
  self._config = config or ToolCacheConfig()
  # Track pending tool calls by session key for after_tool_callback
  self._pending_calls: dict[str, str] = {}
```

#### before_tool_callback

```python
before_tool_callback(tool: BaseTool, args: Dict[str, Any], tool_context: ToolContext) -> Optional[Dict[str, Any]]
```

Check cache before executing tool.

Parameters:

| Name           | Type             | Description                         | Default    |
| -------------- | ---------------- | ----------------------------------- | ---------- |
| `tool`         | `BaseTool`       | The tool being called.              | *required* |
| `args`         | `Dict[str, Any]` | The arguments for the tool call.    | *required* |
| `tool_context` | `ToolContext`    | The tool context with session info. | *required* |

Returns:

| Type                       | Description                                                |
| -------------------------- | ---------------------------------------------------------- |
| `Optional[Dict[str, Any]]` | Dict if cache hit (skips tool execution), None to proceed. |

Source code in `src/adk_redis/cache/tool_cache.py`

```python
async def before_tool_callback(
    self,
    tool: BaseTool,
    args: Dict[str, Any],
    tool_context: ToolContext,
) -> Optional[Dict[str, Any]]:
  """Check cache before executing tool.

  Args:
      tool: The tool being called.
      args: The arguments for the tool call.
      tool_context: The tool context with session info.

  Returns:
      Dict if cache hit (skips tool execution), None to proceed.
  """
  tool_name = tool.name
  if not self._should_cache_tool(tool_name):
    logger.debug("Tool %s not in cache list, skipping", tool_name)
    return None

  cache_key = self._build_cache_key(tool_name, args, tool_context)
  cache_entry = await self._provider.check(cache_key)

  if cache_entry:
    logger.info("Cache hit for tool: %s", tool_name)
    try:
      return json.loads(cache_entry.response)  # type: ignore[no-any-return]
    except (json.JSONDecodeError, TypeError):
      return {"result": cache_entry.response}

  logger.debug("Cache miss for tool: %s", tool_name)
  # Store cache key for after_tool_callback
  session_key = self._get_session_key(tool_context)
  self._pending_calls[session_key] = cache_key
  return None
```

#### after_tool_callback

```python
after_tool_callback(tool: BaseTool, args: Dict[str, Any], tool_context: ToolContext, tool_response: Dict[str, Any]) -> Optional[Dict[str, Any]]
```

Store tool result in cache after execution.

Parameters:

| Name            | Type             | Description                           | Default    |
| --------------- | ---------------- | ------------------------------------- | ---------- |
| `tool`          | `BaseTool`       | The tool that was called.             | *required* |
| `args`          | `Dict[str, Any]` | The arguments used for the tool call. | *required* |
| `tool_context`  | `ToolContext`    | The tool context with session info.   | *required* |
| `tool_response` | `Dict[str, Any]` | The result from the tool execution.   | *required* |

Returns:

| Type                       | Description                                 |
| -------------------------- | ------------------------------------------- |
| `Optional[Dict[str, Any]]` | None to pass through the original response. |

Source code in `src/adk_redis/cache/tool_cache.py`

```python
async def after_tool_callback(
    self,
    tool: BaseTool,
    args: Dict[str, Any],
    tool_context: ToolContext,
    tool_response: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
  """Store tool result in cache after execution.

  Args:
      tool: The tool that was called.
      args: The arguments used for the tool call.
      tool_context: The tool context with session info.
      tool_response: The result from the tool execution.

  Returns:
      None to pass through the original response.
  """
  session_key = self._get_session_key(tool_context)
  cache_key = self._pending_calls.pop(session_key, None)

  if not cache_key:
    logger.debug("No pending cache key for tool, skipping store")
    return None

  # Serialize the tool response
  try:
    response_str = json.dumps(tool_response, default=str)
  except (TypeError, ValueError):
    response_str = str(tool_response)

  await self._provider.store(cache_key, response_str)
  logger.info("Cached result for tool: %s", tool.name)
  return None
```

### ToolCacheConfig

Bases: `BaseModel`

Configuration for tool result caching.

Attributes:

| Name                 | Type                 | Description                                             |
| -------------------- | -------------------- | ------------------------------------------------------- |
| `tool_names`         | `Optional[Set[str]]` | Set of tool names to cache. None means cache all tools. |
| `include_app_name`   | `bool`               | Include app name in cache key.                          |
| `include_user_id`    | `bool`               | Include user ID in cache key.                           |
| `include_session_id` | `bool`               | Include session ID in cache key.                        |

### create_llm_cache_callbacks

```python
create_llm_cache_callbacks(cache: LLMResponseCache) -> Tuple[BeforeModelCallback, AfterModelCallback]
```

Create callback functions for LLM response caching.

This factory function wraps the LLMResponseCache methods into standalone callback functions compatible with ADK's Agent constructor.

Parameters:

| Name    | Type               | Description                           | Default    |
| ------- | ------------------ | ------------------------------------- | ---------- |
| `cache` | `LLMResponseCache` | The LLMResponseCache instance to use. | *required* |

Returns:

| Type                                             | Description                                                         |
| ------------------------------------------------ | ------------------------------------------------------------------- |
| `Tuple[BeforeModelCallback, AfterModelCallback]` | A tuple of (before_model_callback, after_model_callback) functions. |

Example

```python
llm_cache = LLMResponseCache(provider=provider)
before_cb, after_cb = create_llm_cache_callbacks(llm_cache)

agent = Agent(
    name="my_agent",
    before_model_callback=before_cb,
    after_model_callback=after_cb,
)
```

Source code in `src/adk_redis/cache/callbacks.py`

````python
def create_llm_cache_callbacks(
    cache: LLMResponseCache,
) -> Tuple[BeforeModelCallback, AfterModelCallback]:
  """Create callback functions for LLM response caching.

  This factory function wraps the LLMResponseCache methods into standalone
  callback functions compatible with ADK's Agent constructor.

  Args:
      cache: The LLMResponseCache instance to use.

  Returns:
      A tuple of (before_model_callback, after_model_callback) functions.

  Example:
      ```python
      llm_cache = LLMResponseCache(provider=provider)
      before_cb, after_cb = create_llm_cache_callbacks(llm_cache)

      agent = Agent(
          name="my_agent",
          before_model_callback=before_cb,
          after_model_callback=after_cb,
      )
      ```
  """

  async def before_model_callback(
      callback_context: CallbackContext,
      llm_request: LlmRequest,
  ) -> Optional[LlmResponse]:
    return await cache.before_model_callback(callback_context, llm_request)  # type: ignore[return-value,no-any-return]

  async def after_model_callback(
      callback_context: CallbackContext,
      llm_response: LlmResponse,
  ) -> Optional[LlmResponse]:
    return await cache.after_model_callback(callback_context, llm_response)  # type: ignore[return-value,no-any-return]

  return before_model_callback, after_model_callback  # type: ignore[return-value]
````

### create_tool_cache_callbacks

```python
create_tool_cache_callbacks(cache: ToolCache) -> Tuple[BeforeToolCallback, AfterToolCallback]
```

Create callback functions for tool result caching.

This factory function wraps the ToolCache methods into standalone callback functions compatible with ADK's Agent constructor.

Parameters:

| Name    | Type        | Description                    | Default    |
| ------- | ----------- | ------------------------------ | ---------- |
| `cache` | `ToolCache` | The ToolCache instance to use. | *required* |

Returns:

| Type                                           | Description                                                       |
| ---------------------------------------------- | ----------------------------------------------------------------- |
| `Tuple[BeforeToolCallback, AfterToolCallback]` | A tuple of (before_tool_callback, after_tool_callback) functions. |

Example

```python
tool_cache = ToolCache(provider=provider)
before_cb, after_cb = create_tool_cache_callbacks(tool_cache)

agent = Agent(
    name="my_agent",
    before_tool_callback=before_cb,
    after_tool_callback=after_cb,
)
```

Source code in `src/adk_redis/cache/callbacks.py`

````python
def create_tool_cache_callbacks(
    cache: ToolCache,
) -> Tuple[BeforeToolCallback, AfterToolCallback]:
  """Create callback functions for tool result caching.

  This factory function wraps the ToolCache methods into standalone
  callback functions compatible with ADK's Agent constructor.

  Args:
      cache: The ToolCache instance to use.

  Returns:
      A tuple of (before_tool_callback, after_tool_callback) functions.

  Example:
      ```python
      tool_cache = ToolCache(provider=provider)
      before_cb, after_cb = create_tool_cache_callbacks(tool_cache)

      agent = Agent(
          name="my_agent",
          before_tool_callback=before_cb,
          after_tool_callback=after_cb,
      )
      ```
  """

  async def before_tool_callback(
      tool: BaseTool,
      args: Dict[str, Any],
      tool_context: ToolContext,
  ) -> Optional[Dict[str, Any]]:
    return await cache.before_tool_callback(tool, args, tool_context)  # type: ignore[return-value]

  async def after_tool_callback(
      tool: BaseTool,
      args: Dict[str, Any],
      tool_context: ToolContext,
      tool_response: Dict[str, Any],
  ) -> Optional[Dict[str, Any]]:
    return await cache.after_tool_callback(  # type: ignore[return-value]
        tool, args, tool_context, tool_response
    )

  return before_tool_callback, after_tool_callback  # type: ignore[return-value]
````
