# Failure Modes

Things that look like bugs but are intentional. Read this before "fixing"
any of them.

## Memory tool parameter names are part of the contract

The ADK `FunctionTool` wrappers under `tools/memory/` look like trivial
glue around the memory service. They are not. The LLM picks tools by
parameter name; renaming a parameter (even from `query` to `q`) silently
breaks tool selection. If you must rename, update the tool wrapper, the
service method, and any prompt fragments together.

## Sessions and memory go through Agent Memory Server, not Redis directly

Both `RedisSessionMemoryService` and `RedisLongTermMemoryService`
talk to Agent Memory Server, not raw Redis. Reaching into Redis from
either service bypasses dedup, summarization, embedding, and the
working-to-long-term promotion pipeline. Stay on the AMS client.

## Search tools are independent on purpose

Vector, hybrid, range, BM25 text, and SQL search tools live as five
separate classes rather than one polymorphic tool with a `mode=`
parameter. The LLM is much better at selecting between narrow tools than
at choosing the right value for a `mode` argument. Do not consolidate.

## `epsilon` is not on `RedisVectorQueryConfig`

`EPSILON` is a `VECTOR_RANGE`-only attribute. Emitting it inside a KNN
bracket makes Redis reject the query. `RedisVectorQueryConfig` therefore
does not accept the field; only `RedisRangeQueryConfig` does. If a user
PR adds it back to the KNN config, push back and point at the regression
tests in `tests/tools/test_vector_search.py::TestRedisVectorQueryConfigEpsilonRemoval`.

## Import semantic cache from `redisvl.extensions.cache.llm`

The `redisvl.extensions.llmcache` path still works but emits a
`DeprecationWarning`. The cache provider imports from
`redisvl.extensions.cache.llm` (`cache/_provider.py`). Do not revert
to the old path; the regression test in
`tests/cache/test_provider.py` asserts no `DeprecationWarning` fires.

## No MCP wrapper helpers

There are no custom MCP wrapper helpers in this package. For both the
RedisVL MCP server (`rvl mcp`) and Agent Memory Server's MCP endpoint,
users wire ADK's native `McpToolset` with `StdioConnectionParams` /
`SseConnectionParams` / `StreamableHTTPConnectionParams` directly. This
keeps the MCP wiring story aligned with every other ADK catalog
integration. Do not introduce `create_redisvl_mcp_toolset` or
`create_memory_mcp_toolset` wrappers.

## Two cache providers exist on purpose

`RedisVLCacheProvider` (self-hosted RedisVL semantic cache) and
`LangCacheProvider` (managed Redis LangCache) are both first-class. Do
not "simplify" by removing one. Customers pick by deployment model.

## No inline imports

`AGENTS.md` forbids inline (in-function) imports. Moving an import inside
a function to "speed up startup" or "avoid optional deps" is the wrong
fix; use `autodoc_mock_imports` for docs and an `extras_require` group
for runtime optionality.

## No em dashes; restructure sentences

`AGENTS.md` also forbids em dashes (—) and double hyphens (--) in prose.
This applies to docstrings (which become reference docs) and to
user-facing prose in `docs/`. Restructure the sentence; do not add a
typographic shortcut.

## 2-space indent and Google-style docstrings

The project uses 2-space indent and Google-style docstrings. PEP 8's
4-space convention is intentionally not followed for this repo;
`make format` enforces the local style.

## Coverage gate failures are not flakes

If CI reports coverage below the project bar, do not retry. The failure
is real. Either add a test or delete the unreachable branch.

## Sphinx warnings are errors

`sphinx-build -W` is the published build mode. Suppressing a warning to
"make CI green" hides broken cross-references that later become 404s on
the published docs site.

## A mismatched attached index misses silently, it does not raise

With `create_index=False` the cache provider attaches to an index it did
not create, and RedisVL validates nothing about it. A wrong or absent
index `name` raises `RedisSearchError` on the first `check()`, but a wrong
vector dimension, key prefix, storage type, or distance metric is silent:
entries are written, every lookup misses, and the cache adds latency
while saving nothing. Do not "fix" this by adding an `FT.INFO` probe to
the provider. That command is exactly what the credential is denied, and
probing would defeat the feature. Verify the index out of band instead.
`tests/integration/test_sql_and_cache_end_to_end.py` pins both shapes.

## The cache swallows backend failures on purpose

`LLMResponseCache` and `ToolCache` catch every exception from
`provider.check()` and `provider.store()` and fall through to the model or
the tool. This is deliberate: ADK awaits callbacks with no `try`/`except`
and outside its own model-error handling, so a raised exception ends the
invocation with no events emitted, discarding a response the caller
already paid for. Do not narrow these to specific exception types to
"surface real errors"; a cache is an optimization and must not be able to
break an agent turn. Developers who want the exception set
`ignore_errors=False` on `LLMResponseCacheConfig` or `ToolCacheConfig`.
Construction errors are never absorbed. `tests/cache/test_fail_open.py`
pins both paths.

## `overwrite` defaults to False, so a drifted schema raises

`RedisVLCacheProvider` once hardcoded `overwrite=True`, which dropped and
recreated the index on every construction. It now reuses an existing
index, matching RedisVL's own default, so a config that no longer matches
the index in Redis raises at construction where it previously appeared to
succeed. That is the intended report, not a regression: the old default
hid the real problem, leaving entries embedded by a previous model in the
keyspace, unindexed. Set `overwrite=True` to rebuild deliberately.
