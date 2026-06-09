# Installing uniprot-mcp-server

This is an MCP server for the UniProt protein knowledgebase.

## One-line install (zero-install via uvx)

```bash
uvx uniprot-mcp-server
```

This downloads and runs the server in an isolated environment. No prior `pip install` is required.

## MCP client configuration

Add the following to your MCP client configuration (for example, Claude Desktop's `claude_desktop_config.json` or a client's `.mcp.json`):

```json
{
  "mcpServers": {
    "uniprot": {
      "command": "uvx",
      "args": ["uniprot-mcp-server"]
    }
  }
}
```

## Package name

The PyPI distribution is `uniprot-mcp-server`. An unrelated package named `uniprot-mcp` (different author) also exists on PyPI; install `uniprot-mcp-server` to get this server.

## Optional environment variables

Neither is required for normal use:

- `UNIPROT_PIN_RELEASE` — pin responses to a specific UniProt release (for example, `2026_01`) for strict reproducibility.
- `UNIPROT_MCP_CACHE_DIR` — directory used by `uniprot_replay_from_cache` for offline replay of previously recorded responses.
