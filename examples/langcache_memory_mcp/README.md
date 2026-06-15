# Langcache Memory over MCP

An ADK agent whose long-term memory is served by the **langcache
memory-dataplane MCP server** ("Redis Agent Memory" managed plane).

This is the managed-plane counterpart to
[`examples/fitness_coach_mcp`](../fitness_coach_mcp), which connects to the
open-source Agent Memory Server. Both expose the *same* memory tool surface over
MCP; the differences are transport and tenancy:

| | fitness_coach_mcp | langcache_memory_mcp |
| --- | --- | --- |
| Server | Agent Memory Server (OSS) | langcache memory-dataplane (managed) |
| Transport | SSE (`/sse`) | streamable HTTP (`/v1/stores/{storeId}/mcp`) |
| Tenancy | namespaces | per-store, Bearer-token scoped |

## Configuration

| Env var | Meaning |
| --- | --- |
| `LANGCACHE_MCP_URL` | Full endpoint incl. store path, e.g. `https://<host>/v1/stores/<store>/mcp` |
| `LANGCACHE_MCP_TOKEN` | The store's Bearer token (omit for an auth-disabled local server) |
| `GOOGLE_API_KEY` | Gemini key for the agent model |

## Run

```bash
export LANGCACHE_MCP_URL="http://localhost:9100/v1/stores/test-store/mcp"
export LANGCACHE_MCP_TOKEN="<store-token>"   # optional for local
adk web langcache_memory
```

## Interop test

`tests/integration/test_langcache_mcp_end_to_end.py` verifies that ADK's
`McpToolset` discovers the langcache tool surface and that a
create → get → search round trip works over MCP. It is gated on
`LANGCACHE_MCP_URL`.

A local langcache MCP server (in-memory, no Redis/codegen needed) can be run
from the langcache repo via `go run ./memory-dataplane/cmd/mcpstub` (serves
`/v1/stores/{storeId}/mcp` on port 9100).
