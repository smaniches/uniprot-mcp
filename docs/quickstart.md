# Quickstart

## Install

```bash
# From PyPI (distribution name is uniprot-mcp-server,
# the installed console script is uniprot-mcp):
pip install uniprot-mcp-server
# or in an isolated environment:
uvx --from uniprot-mcp-server uniprot-mcp

# From source:
git clone https://github.com/smaniches/uniprot-mcp.git
cd uniprot-mcp
pip install -e .
```

## Verify it works

```bash
uniprot-mcp --self-test
```

Expected output:

```
[tools] registered: 38/38
[live] P04637 -> TP53 OK
[PASS]
```

The self-test makes one live UniProt call (`/uniprotkb/P04637`) and
asserts the gene is `TP53`. No API key required.

## Hook it up to Claude Desktop

Edit `claude_desktop_config.json` (the location depends on your OS;
on Windows it lives under `%APPDATA%\Claude\`):

```json
{
  "mcpServers": {
    "uniprot": {
      "command": "uniprot-mcp"
    }
  }
}
```

Restart Claude Desktop. Type `/mcp` in any conversation; you should
see the 41 tools listed.

For **strict release pinning** (any drift raises an error):

```json
{
  "mcpServers": {
    "uniprot": {
      "command": "uniprot-mcp",
      "args": ["--pin-release=2026_01"]
    }
  }
}
```

For the **local provenance cache** (replay any past answer offline):

```json
{
  "mcpServers": {
    "uniprot": {
      "command": "uniprot-mcp",
      "env": {
        "UNIPROT_MCP_CACHE_DIR": "/path/to/your/cache"
      }
    }
  }
}
```

## Hook it up to Claude Code (CLI)

```bash
claude mcp add uniprot -- uniprot-mcp
```

## First useful question

Once configured, ask Claude something like:

> What does UniProt say about TP53? Resolve any PDB structures.

Claude will call `uniprot_get_entry("P04637")` followed by
`uniprot_resolve_pdb("P04637")` and present the entry summary plus a
structured table of PDB structures (id + method + resolution + chain
coverage). Every response carries the provenance footer at the bottom
— the line beginning `_Source: UniProt release …_` — that you can use
later to verify the answer.

## A workflow that's hard without `uniprot-mcp`

> For human TP53, give me: (a) the canonical entry summary, (b) a
> drug-target dossier, (c) a list of every disease association with
> OMIM IDs, (d) the AlphaFold pLDDT confidence summary, (e) every
> ClinVar pathogenic variant.

That's five tool calls — `uniprot_get_entry`,
`uniprot_target_dossier`, `uniprot_get_disease_associations`,
`uniprot_get_alphafold_confidence`, `uniprot_resolve_clinvar` — and
the agent assembles the answer with provenance footers on every
section. See [recipes](recipes/clinical-variant-interpretation.md)
for worked examples.

## Where to go next

- **Full tool reference** → [Tools](tools.md)
- **Verification deep-dive** → [Provenance & verification](provenance-guide.md)
- **Recipe: variant interpretation** → [Clinical variant interpretation](recipes/clinical-variant-interpretation.md)
- **Threat model and operational policy** → [Threat model](THREAT_MODEL.md), [Incident policy](INCIDENT_POLICY.md)
