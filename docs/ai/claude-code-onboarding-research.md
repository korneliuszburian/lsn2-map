# Claude Code Onboarding Research — 2nd Opinion Report

**Project:** lsn2-map — North America Generator Deployment Mapping Pipeline
**Date:** 2026-05-07
**Author:** Claude Code audit (research-only, no changes made)

---

## 1. Executive Summary

This is a greenfield GIS/data-engineering project: no code, no git repo, no Claude Code configuration. The project will geocode ~1200 generator deployments across US/CA/MX from Excel input, producing enriched exports for Power BI / Mapbox / QGIS.

**Verdict: GO for bootstrap.** The project is a clean slate with well-defined requirements (from `one_hit_prompt_pipeline.txt`). Claude Code configuration should be established before any pipeline code is written. The recommended approach is project-scoped plugins + project-scoped MCP + a comprehensive CLAUDE.md.

Key decisions needed before Phase 2 (bootstrap):
1. Initialize git repo and push to GitHub (required for `github` plugin)
2. Install Python 3.11+ and `pyright-langserver` (required for `pyright-lsp`)
3. Decide whether to adopt Superpowers methodology or keep lightweight with `feature-dev`
4. Decide on MCP servers for this project (likely none needed beyond plugin-provided)

---

## 2. Source Verification Table

| # | Source | URL | Status | Date Verified | Key Findings |
|---|--------|-----|--------|---------------|--------------|
| 1 | Plugin Discovery | https://code.claude.com/docs/en/discover-plugins | Accessible | 2026-05-07 | Official marketplace: `claude-plugins-official`. 11 LSP plugins, 12+ integration plugins, 4 workflow plugins, 2 output-style plugins. Install: `/plugin install <name>@claude-plugins-official`. |
| 2 | Official Plugin Repo | https://github.com/anthropics/claude-plugins-official | Accessible | 2026-05-07 | 18.7k stars. Contains `/plugins` (Anthropic-authored) and `/external_plugins` (third-party). |
| 3 | Plugin Examples in Claude Code | https://github.com/anthropics/claude-code/tree/main/plugins | Accessible | 2026-05-07 | 13 example plugins with full source: code-review, commit-commands, feature-dev, frontend-design, hookify, plugin-dev, pr-review-toolkit, security-guidance, etc. |
| 4 | Best Practices | https://code.claude.com/docs/en/best-practices | Accessible | 2026-05-07 | CLAUDE.md hierarchy, skills, subagents, hooks, plugins, MCP servers. |
| 5 | .claude Directory | https://code.claude.com/docs/en/claude-directory | Accessible | 2026-05-07 | Full file structure: settings.json (committed), settings.local.json (gitignored), .mcp.json (committed), skills/, commands/, agents/, rules/, output-styles/. |
| 6 | MCP Configuration | https://code.claude.com/docs/en/mcp | Accessible | 2026-05-07 | Three transports (http/sse/stdio), three scopes (local/project/user), env var expansion in .mcp.json, plugin-provided MCP via plugin's .mcp.json. |
| 7 | Commands | https://code.claude.com/docs/en/commands | Accessible | 2026-05-07 | `/plugin install/uninstall/enable/disable`, `/reload-plugins`, `/skills`. |
| 8 | MCP Protocol Docs | https://modelcontextprotocol.io/docs/develop/connect-local-servers | Accessible | 2026-05-07 | Protocol-level docs for Claude Desktop — different config path than Claude Code, same JSON structure. |
| 9 | Superpowers | https://github.com/obra/superpowers | Accessible | 2026-05-07 | 7-phase TDD methodology plugin. 15 skills. Can conflict with `feature-dev`. |
| 10 | Community Registry | https://claude-plugins.dev | Accessible | 2026-05-07 | Complementary `npx claude-plugins install` CLI. Not official Anthropic. Lists 20 plugins. |
| 11 | Cookbooks | https://github.com/anthropics/claude-cookbooks | Accessible | 2026-05-07 | Jupyter recipes for Claude API, not Claude Code plugins. |

### Conflicts Found

No significant conflicts between sources. All documentation is consistent on:
- Three-scope model (local/project/user) for both plugins and MCP
- `.mcp.json` location at project root
- Official marketplace name `claude-plugins-official`
- Plugin structure (`.claude-plugin/plugin.json` + commands/agents/skills/hooks/.mcp.json)

---

## 3. Project Profile

| Attribute | Value |
|-----------|-------|
| **Status** | Greenfield — no code yet |
| **Languages** | Python 3.11+ (planned) |
| **Frameworks/Libraries** | pandas, geopandas, shapely, pyarrow, openpyxl |
| **Package Manager** | pip (no requirements.txt yet) |
| **Test Framework** | Not established (recommend pytest) |
| **Lint** | Not established (recommend ruff) |
| **Typecheck** | Not established (recommend pyright/mypy) |
| **CI Provider** | None |
| **Deployment Target** | None (batch pipeline, local execution) |
| **Git Remote** | None (not a git repo) |
| **CLAUDE.md** | Does not exist |
| **.claude/** | Does not exist |
| **.mcp.json** | Does not exist |
| **Security-sensitive files** | Template Excel only (no secrets) |
| **Classification** | Data/GIS engineering, batch pipeline |
| **Input** | Excel (~1200 rows, US/CA/MX postal codes) |
| **Output** | Enriched Excel, CSV, GeoJSON (EPSG:4326), exceptions CSV, run summary JSON |
| **Target consumers** | Power BI, Mapbox, ArcGIS, QGIS |

---

## 4. Current Claude Code Configuration Inventory

| Item | Status |
|------|--------|
| `CLAUDE.md` | Not present |
| `.claude/settings.json` | Not present |
| `.claude/settings.local.json` | Not present |
| `.mcp.json` | Not present |
| `.claude/skills/` | Not present |
| `.claude/agents/` | Not present |
| `.claude/commands/` | Not present |
| `.claude/rules/` | Not present |
| `.claude/output-styles/` | Not present |
| `.claude/hooks/` | Not present |
| Installed plugins | None |
| MCP servers | None |

**Conclusion:** Completely clean slate. No conflicts to resolve, no existing config to audit.

---

## 5. Plugin Decision Matrix

### 5.1 Universal Baseline (recommended for all projects)

| Plugin | Install Command | Scope | Why | What It Adds | Prerequisites | Conflicts |
|--------|----------------|-------|-----|--------------|---------------|-----------|
| `commit-commands` | `/plugin install commit-commands@claude-plugins-official` | project | Standardized git workflow | Commands: `/commit`, `/commit-push-pr`, `/clean_gone` | git repo | None |
| `code-review` | `/plugin install code-review@claude-plugins-official` | project | Multi-perspective code review | Command: `/code-review`; 5 parallel Sonnet agents (CLAUDE.md compliance, bugs, history, PR context, comments) | None | Overlaps with `pr-review-toolkit` (different focus) |
| `security-guidance` | `/plugin install security-guidance@claude-plugins-official` | project | Proactive security guardrails | Hook: PreToolUse — monitors 9 security patterns (SQL injection, secrets, etc.) | None | None |
| `context7` | `/plugin install context7@claude-plugins-official` | project | Up-to-date framework docs lookup | MCP server for fetching current library docs | None | None |

### 5.2 Conditional — Recommended for This Project

| Plugin | Install Command | Scope | Why | What It Adds | Prerequisites | Conflicts |
|--------|----------------|-------|-----|--------------|---------------|-----------|
| `pyright-lsp` | `/plugin install pyright-lsp@claude-plugins-official` | project | Python code intelligence | LSP integration for type checking, go-to-definition, diagnostics | `pyright-langserver` binary (`npm install -g pyright`) | None |
| `github` | `/plugin install github@claude-plugins-official` | project | Issues, PRs, Actions integration | GitHub-specific commands/skills/MCP | `gh` CLI authenticated (`gh auth status`) | None |
| `feature-dev` | `/plugin install feature-dev@claude-plugins-official` | project | Guided multi-file feature development | Command: `/feature-dev`; Agents: `code-explorer`, `code-architect`, `code-reviewer` | None | Overlaps with Superpowers (different methodology) |

### 5.3 Optional / Not Recommended Now

| Plugin | Why Not Now | When to Install |
|--------|-------------|-----------------|
| `superpowers` | Opinionated 7-phase TDD methodology. Overkill for a single-person pipeline project. | If the team adopts strict TDD + brainstorming + subagent-driven workflow |
| `pr-review-toolkit` | No PR workflow yet (no git repo). | When team grows and PR review becomes a bottleneck |
| `frontend-design` | No frontend/UI work. GIS pipeline project. | If a web dashboard is added |
| `plugin-dev` | Not building Claude Code plugins. | If the team starts building plugins |
| `agent-sdk-dev` | Not building Agent SDK apps. | If the team builds Claude Agent SDK apps |
| `mcp-server-dev` | Not building MCP servers. | If the team builds MCP servers |
| `hookify` | Useful but premature. No repeated patterns yet. | After the project has recurring mistakes to codify into hooks |
| `explanatory-output-style` | Educational mode. Not needed for experienced engineer. | For onboarding junior developers |
| `learning-output-style` | Learning mode. Not needed. | For educational use |

### 5.4 Plugins Verified as Existing in Official Marketplace

Based on the official docs and GitHub repos, these are confirmed Anthropic-authored:
- `commit-commands`, `code-review`, `security-guidance`, `context7`, `feature-dev`, `frontend-design`, `hookify`, `plugin-dev`, `pr-review-toolkit`, `agent-sdk-dev`
- All 11 LSP plugins (`pyright-lsp`, `typescript-lsp`, `rust-analyzer-lsp`, `gopls-lsp`, `clangd-lsp`, `jdtls-lsp`, `csharp-lsp`, `ruby-lsp`, `php-lsp`, `swift-lsp`, `kotlin-lsp`, `lua-lsp`)
- `github`, `gitlab`, `atlassian`, `asana`, `linear`, `notion`, `figma`, `vercel`, `firebase`, `supabase`, `slack`, `sentry`
- `superpowers` (third-party, listed in official marketplace)

### 5.5 Plugins NOT Verified

| Plugin Listed in Prompt | Verified? | Notes |
|-------------------------|-----------|-------|
| `claude-code-setup` | Not found in official sources | May not exist as a standalone plugin. Fallback: use `/init` skill instead. |
| `claude-md-management` | Not found in official sources | May not exist. Fallback: manually manage CLAUDE.md. |
| `code-simplifier` | Not found as a separate plugin | The `code-review` plugin includes a code-simplifier agent. Superpowers also has simplification. |
| `session-report` | Not found in official sources | May not exist as a standalone plugin. |
| `skill-creator` | Not found in official sources | May not exist. `plugin-dev` includes skill-reviewer agent. |

**Action:** During bootstrap, attempt installation. If "plugin not found," record in `docs/ai/bootstrap-errors.md` and proceed without it.

---

## 6. Recommended Project-Scope Install Commands

```bash
# Universal baseline (4 plugins)
claude plugin install commit-commands@claude-plugins-official --scope project
claude plugin install code-review@claude-plugins-official --scope project
claude plugin install security-guidance@claude-plugins-official --scope project
claude plugin install context7@claude-plugins-official --scope project

# Conditional — Python project (requires pyright-langserver)
# First: npm install -g pyright   (only if not already installed)
claude plugin install pyright-lsp@claude-plugins-official --scope project

# Conditional — GitHub integration (requires git repo + gh auth)
claude plugin install github@claude-plugins-official --scope project

# Conditional — multi-file feature development
claude plugin install feature-dev@claude-plugins-official --scope project
```

**Fallback:** If `claude plugin install ... --scope project` fails, use the interactive flow:
1. Type `/plugin`
2. Select "Discover" tab
3. Find the plugin
4. Select "Project" scope during installation

---

## 7. Language-Server Prerequisites

| Plugin | Binary Required | Install Command | Verify |
|--------|----------------|-----------------|--------|
| `pyright-lsp` | `pyright-langserver` | `npm install -g pyright` | `command -v pyright-langserver` |
| `typescript-lsp` | `typescript-language-server` | `npm install -g typescript typescript-language-server` | `command -v typescript-language-server` |

**For this project:** Only `pyright-langserver` is needed. TypeScript is not used.

---

## 8. MCP Decision Matrix

### 8.1 Assessment

| MCP Need | Assessment | Recommendation |
|----------|------------|----------------|
| Context7 docs lookup | Provided by `context7` plugin | Plugin-provided MCP. Do not add manually. |
| GitHub API | Provided by `github` plugin | Plugin-provided MCP. Do not add manually. |
| Filesystem access | Built into Claude Code | Not needed. |
| Database | Not applicable | Not needed. |
| Mapbox geocoding API | The pipeline calls Mapbox, but Claude Code does not need an MCP server for this | Not needed. The Python pipeline handles API calls internally. |
| Web fetch/reader | Already available as built-in tools + MCP plugin | Not needed. |
| Python execution | Built into Claude Code (Bash tool) | Not needed. |

### 8.2 Conclusion

**No additional MCP servers needed for this project.** The plugin-provided MCP servers from `context7` and `github` cover all requirements. Do not create a `.mcp.json` file unless a specific need arises (e.g., a custom geocoding validation MCP server in the future).

### 8.3 Future MCP Candidates (if needs change)

| MCP Server | When to Add | Scope | Transport |
|------------|-------------|-------|-----------|
| Custom geocode validator | If real-time postal code validation is needed during development | project | stdio |
| PostgreSQL/PostGIS | If data moves to a spatial database | project | stdio |

---

## 9. Recommended `.mcp.json` Strategy

**Do not create `.mcp.json` at this time.** No manually configured MCP servers are needed.

If created later, the strategy would be:

```json
{
  "mcpServers": {
    "example-future-server": {
      "type": "http",
      "url": "https://example.com/mcp",
      "headers": {
        "Authorization": "Bearer ${API_KEY}"
      }
    }
  }
}
```

Rules:
- Use `${VAR}` for secrets, never hardcode
- Use HTTP transport over SSE when both exist
- Commit `.mcp.json` to git for team sharing
- Do not duplicate plugin-provided servers
- Verify with `claude mcp list` and `/mcp`

---

## 10. Recommended `CLAUDE.md` Changes

Create `CLAUDE.md` at project root with the following structure:

```markdown
# Project: North America Generator Deployment Mapping Pipeline

## Purpose
Geocode ~1200 generator deployments across US/CA/MX from Excel input.
Produce enriched Excel, CSV, GeoJSON (EPSG:4326), QA reports.

## Stack
- Python 3.11+
- pandas, geopandas, shapely, pyarrow, openpyxl
- pytest, ruff, pyright

## Commands
- Run pipeline: `python src/run_pipeline.py --input data/input/clients.xlsx --output data/output`
- Tests: `pytest`
- Lint: `ruff check .`
- Typecheck: `pyright`

## Architecture
- `src/` — pipeline modules (clean_clients, normalize_postal, geocode, enrich, qa, export)
- `data/input/` — raw Excel files (gitignored)
- `data/output/` — generated outputs (gitignored)
- `data/sample/` — template files (committed)
- `tests/` — test suite

## Data Rules
- Never commit real client data
- Treat postal_code_raw as text (preserve leading zeros)
- geo_key = country_code + "|" + postal_code_norm
- Target: 98%+ match rate for valid postal codes

## Git Conventions
- Conventional commits
- PR required for main branch

## Plugin Usage
- Use `/code-review` before committing
- Use `/feature-dev` for multi-file features
- Use `/commit` for standardized commits

## MCP
- context7 for library docs lookup
- github for PR/issue integration
```

---

## 11. Recommended Hooks / Skills / Agents / Commands

### 11.1 Hooks (in `.claude/settings.json`)

| Hook | Event | Purpose |
|------|-------|---------|
| Block secrets commit | PreToolUse (Write/Edit) | Prevent `.env`, credentials from being written |
| Run ruff after edit | PostToolUse (Edit, Write on `*.py`) | Auto-format Python files |

**Recommendation:** Create these hooks only after the project has Python files. Use the `security-guidance` plugin's built-in PreToolUse hook as the baseline — it already monitors 9 security patterns.

### 11.2 Skills (in `.claude/skills/`)

| Skill | Purpose | When to Create |
|-------|---------|----------------|
| `pipeline-test` | Run pipeline with sample data, verify outputs | After pipeline code exists |
| `geocode-qa` | Run geocoding QA checks | After geocoding module exists |
| `data-review` | Review data quality of input Excel | After pipeline code exists |

**Recommendation:** Defer skill creation until after the pipeline is built. Skills should codify proven workflows, not hypothetical ones.

### 11.3 Agents (in `.claude/agents/`)

| Agent | Purpose | When to Create |
|-------|---------|----------------|
| `data-quality-reviewer` | Review input/output data quality | After pipeline exists |
| `geojson-validator` | Validate GeoJSON output | After GeoJSON export exists |

**Recommendation:** Defer agent creation. The `code-review` plugin's built-in agents cover most review needs.

### 11.4 Commands (in `.claude/commands/`)

| Command | Purpose | When to Create |
|---------|---------|----------------|
| `run-pipeline` | Run the full pipeline with defaults | After pipeline code exists |

**Recommendation:** Defer. The pipeline has a single-command interface (`python src/run_pipeline.py`), making a command wrapper low-value.

---

## 12. Security and Secrets Review

| Item | Status | Action |
|------|--------|--------|
| `.env` files | Not present | Will be needed for `MAPBOX_TOKEN`. Add to `.gitignore`. |
| API keys in code | Not applicable yet | Enforce via `security-guidance` plugin hook |
| Client data in Excel | Template only (no real data) | Add `data/input/*.xlsx` to `.gitignore` except `data/sample/` |
| `.mcp.json` secrets | Not applicable | Rule: use `${VAR}` placeholders only |
| `settings.local.json` | Not present | Will hold personal overrides. Auto-gitignored by Claude Code. |

**Recommended `.gitignore` entries:**
```
data/input/*.xlsx
data/input/*.csv
data/output/
.env
.env.*
.claude/settings.local.json
__pycache__/
*.pyc
.pyright/
```

---

## 13. Conflicts, Uncertainty, and Conservative Defaults

### 13.1 Unverified Plugins

The following plugins from the prompt's "universal baseline" list were **not found** in official sources:

| Plugin | Status | Conservative Default |
|--------|--------|---------------------|
| `claude-code-setup` | Not found in marketplace or GitHub | Skip. Use built-in `/init` instead. |
| `claude-md-management` | Not found | Skip. Manage CLAUDE.md manually. |
| `code-simplifier` | Not found as standalone | Skip. `code-review` plugin has simplification agent. |
| `session-report` | Not found | Skip. |

### 13.2 Decision Points

| Decision | Options | Default Recommendation | Rationale |
|----------|---------|----------------------|-----------|
| Superpowers vs feature-dev | (A) Superpowers, (B) feature-dev, (C) both | **B: feature-dev only** | Superpowers is opinionated methodology. feature-dev is lighter. Start simple. |
| pyright vs mypy | (A) pyright, (B) mypy, (C) both | **A: pyright** | pyright-lsp plugin provides LSP integration. mypy has no plugin. |
| pytest vs unittest | (A) pytest, (B) unittest | **A: pytest** | Standard in Python ecosystem. Pipeline prompt mentions assertions. |
| ruff vs flake8+black | (A) ruff, (B) flake8+black | **A: ruff** | Single tool, faster, replaces both. |

### 13.3 Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Plugin install fails (CLI not supporting --scope) | Medium | Low | Fallback to interactive `/plugin` flow |
| `pyright-langserver` not installed | Medium | Medium | Install via `npm install -g pyright` before plugin |
| No git repo (github plugin unusable) | High (currently) | Low | Initialize git + push to GitHub first |
| Superpowers + feature-dev conflict | Low (not installing Superpowers) | Low | Only install feature-dev |
| Plugin-provided MCP duplicates manually added MCP | Low | Low | Do not add manual MCP servers that plugins provide |

---

## 14. Final Acceptance Criteria

The bootstrap (Phase 2) is considered successful when:

- [ ] Git repo initialized with `.gitignore`
- [ ] `CLAUDE.md` created at project root
- [ ] `.claude/settings.json` created with project config
- [ ] `.claude/settings.local.json` created (gitignored)
- [ ] 4 baseline plugins installed at project scope: `commit-commands`, `code-review`, `security-guidance`, `context7`
- [ ] `pyright-lsp` installed at project scope (after pyright binary)
- [ ] `github` installed at project scope (after git repo + gh auth)
- [ ] `feature-dev` installed at project scope
- [ ] `/reload-plugins` executed and `/plugin` confirms all installed
- [ ] `/mcp` confirms no duplicate MCP servers
- [ ] `docs/ai/project-profile.md` written
- [ ] `docs/ai/plugin-inventory.md` written
- [ ] `docs/ai/bootstrap-errors.md` written (if any errors)
- [ ] `requirements.txt` or `pyproject.toml` created with dependencies
- [ ] Python source directory structure created (`src/`, `tests/`)

---

## 15. Copy-Paste Bootstrap Command Sequence for Next Session

### Phase 0: Preflight

```bash
# In the next Claude Code session, run:
pwd
git init
# Then: create GitHub repo and push, or use:
gh repo create lsn2-map --private --source=. --push
```

### Phase 1: Create .gitignore

```bash
# Create .gitignore
cat > .gitignore << 'EOF'
data/input/*.xlsx
data/input/*.csv
data/output/
.env
.env.*
.claude/settings.local.json
__pycache__/
*.pyc
.pyright/
*.egg-info/
dist/
build/
EOF
git add .gitignore
git commit -m "chore: initialize git repo with .gitignore"
```

### Phase 2: Install Baseline Plugins (project scope)

```bash
# Attempt CLI install (preferred)
claude plugin install commit-commands@claude-plugins-official --scope project
claude plugin install code-review@claude-plugins-official --scope project
claude plugin install security-guidance@claude-plugins-official --scope project
claude plugin install context7@claude-plugins-official --scope project

# If CLI fails, use interactive:
# /plugin → Discover → find plugin → install at Project scope
```

### Phase 3: Install Conditional Plugins

```bash
# Python LSP (install binary first)
npm install -g pyright
claude plugin install pyright-lsp@claude-plugins-official --scope project

# GitHub (after git repo + gh auth)
gh auth status  # verify auth
claude plugin install github@claude-plugins-official --scope project

# Feature development
claude plugin install feature-dev@claude-plugins-official --scope project
```

### Phase 4: Reload and Verify

```
/reload-plugins
/plugin
/mcp
```

### Phase 5: Create Project Structure

```bash
mkdir -p src tests data/input data/output
```

### Phase 6: Create CLAUDE.md

Use `/init` or manually create based on Section 10 of this report.

### Phase 7: Create Python Dependencies

```bash
# Create requirements.txt
cat > requirements.txt << 'EOF'
pandas>=2.1
geopandas>=0.14
shapely>=2.0
pyarrow>=14.0
openpyxl>=3.1
pytest>=7.4
ruff>=0.1
EOF
pip install -r requirements.txt
```

### Phase 8: Commit Claude Code Configuration

```bash
git add CLAUDE.md .claude/ docs/ai/ requirements.txt
git commit -m "chore: add Claude Code project configuration and dependencies"
```

---

## Appendix A: Plugin Quick Reference

| Plugin | Commands | Skills | Agents | Hooks | MCP | LSP |
|--------|----------|--------|--------|-------|-----|-----|
| commit-commands | `/commit`, `/commit-push-pr`, `/clean_gone` | — | — | — | — | — |
| code-review | `/code-review` | — | 5 parallel review agents | — | — | — |
| security-guidance | — | — | — | PreToolUse (9 patterns) | — | — |
| context7 | — | — | — | — | docs lookup MCP | — |
| pyright-lsp | — | — | — | — | — | pyright-langserver |
| github | GitHub-specific | GitHub-specific | — | — | GitHub API MCP | — |
| feature-dev | `/feature-dev` | — | explorer, architect, reviewer | — | — | — |
| superpowers | 15 skills | 15 skills | — | — | — | — |

## Appendix B: File Creation Checklist

| File | Committed? | Created When |
|------|-----------|--------------|
| `.gitignore` | Yes | Phase 1 |
| `CLAUDE.md` | Yes | Phase 6 |
| `.claude/settings.json` | Yes | Phase 4 (auto-created by plugin install) |
| `.claude/settings.local.json` | No | Phase 4 (manual, gitignored) |
| `requirements.txt` | Yes | Phase 7 |
| `src/` | Yes | Phase 5 |
| `tests/` | Yes | Phase 5 |
| `docs/ai/project-profile.md` | Yes | Phase 2 report |
| `docs/ai/plugin-inventory.md` | Yes | Phase 4 |
| `docs/ai/bootstrap-errors.md` | Yes | Phase 2-3 (if errors) |
| `docs/ai/claude-code-usage.md` | Yes | Phase 6 |
| `.mcp.json` | Yes | Not needed now |

---

**GO / NO-GO for Bootstrap: GO**

Prerequisites:
1. Initialize git repo and push to GitHub
2. Install `pyright-langserver` (`npm install -g pyright`)
3. Authenticate `gh` CLI (`gh auth login`)

All three are low-risk, reversible operations. After prerequisites are met, proceed with the Phase 2 bootstrap using the command sequence in Section 15.
