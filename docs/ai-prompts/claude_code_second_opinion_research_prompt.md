# PROMPT 1 — Claude Code 2nd Opinion Research / Project-Onboarding Audit

You are a senior Claude Code platform engineer, developer-experience architect, and skeptical 2nd-opinion reviewer.

Your task is to prepare a reusable Claude Code onboarding plan for the current repository. This process must work for any new project, not only this specific repo.

Do not implement product features. Do not jump into coding. First research, inspect, compare, and produce a decision-grade report.

## Canonical sources

Treat the following sources as the canonical source set. Use them as mutually-verifying references. If you have web access, browse them. If you do not have web access, use installed plugins, local docs, GitHub MCP, Context7, or the repository contents to verify what is available.

1. Official Claude Code plugin discovery and marketplace docs:
   - https://code.claude.com/docs/en/discover-plugins
   - https://github.com/anthropics/claude-plugins-official

2. Official Claude Code plugin examples/reference repo:
   - https://github.com/anthropics/claude-code/tree/main/plugins
   - especially plugins/README.md and plugin-specific README/plugin.json files

3. Claude Code and Claude best-practice material:
   - https://code.claude.com/docs/en/best-practices
   - https://code.claude.com/docs/en/claude-directory
   - https://code.claude.com/docs/en/commands
   - https://github.com/anthropics/claude-cookbooks
   - https://platform.claude.com/cookbook/

4. MCP docs and MCP configuration:
   - https://code.claude.com/docs/en/mcp
   - https://modelcontextprotocol.io/docs/develop/connect-local-servers
   - https://claudecn.com/en/docs/claude-code/advanced/mcp-servers/
   - https://claude-plugins.dev/skills/@fx/cc/managing-mcp-servers

5. Additional integration references:
   - https://claude.com/plugins/github
   - https://github.com/obra/superpowers

## Important default strategy

Use project-scoped configuration by default.

For MCP, prefer project scope and `.mcp.json` when the server should be shared by the team. Never commit secrets. Use environment variables such as `${GITHUB_TOKEN}`, `${API_KEY}`, or documented OAuth flows.

For plugins, prefer project scope when available because it makes onboarding repeatable. According to current Claude Code plugin docs, `/plugin install <name>@claude-plugins-official` installs from the official marketplace, while project-scope installation can be targeted through the CLI with `claude plugin install <plugin>@<marketplace> --scope project`. If the local Claude Code version does not support a specific CLI command, identify the fallback interactive `/plugin` flow and explicitly state what a human must click or run.

## Scope of the audit

Inspect the repository and produce a normalized onboarding plan covering:

1. Current project profile:
   - languages and frameworks
   - package managers
   - test/lint/typecheck commands
   - CI provider
   - deployment target
   - Git remote host
   - presence/quality of `CLAUDE.md`
   - presence/quality of `.claude/`
   - existing `.mcp.json`
   - existing hooks, skills, commands, agents, rules, output styles
   - security-sensitive files and secrets patterns
   - frontend/backend/data/GIS/ML classification if applicable

2. Plugin marketplace and plugin inventory:
   - verify official marketplace availability
   - list installed plugins
   - list missing recommended plugins
   - inspect plugin commands, skills, agents, hooks, MCP servers, and LSP servers
   - distinguish Anthropic-authored official plugins from third-party plugins listed in the official marketplace

3. Recommended plugin set, separated into categories:
   - Universal baseline
   - Language-specific LSP/code-intelligence plugins
   - GitHub/PR workflow plugins
   - Documentation/current-doc lookup plugins
   - Feature-development methodology plugins
   - Security/guardrail plugins
   - Frontend/design plugins
   - Data/infra/domain plugins
   - Optional/experimental plugins

4. For each recommended plugin, provide:
   - plugin name
   - install command
   - desired scope
   - why it helps onboarding
   - exact commands/skills/agents/hooks it adds, as verified from docs or local plugin files
   - when to use it
   - when not to use it
   - conflicts or overlaps with other plugins
   - prerequisites such as `gh`, `pyright-langserver`, `typescript-language-server`, `rust-analyzer`, etc.

5. MCP strategy:
   - what should be plugin-provided MCP versus manually configured MCP
   - which MCP servers should be project-scoped
   - example `claude mcp add ... --scope project` commands
   - example `.mcp.json` snippets using environment variable placeholders
   - auth/OAuth/secrets strategy
   - duplicate-server avoidance strategy
   - verification commands: `claude mcp list`, `claude mcp get <server>`, `/mcp`

6. Claude Code project files:
   - recommended `CLAUDE.md` structure
   - what belongs in `.claude/settings.json`
   - what belongs in `.claude/settings.local.json`
   - what belongs in `.mcp.json`
   - whether to create `.claude/skills/`
   - whether to create `.claude/agents/`
   - whether to create `.claude/rules/`
   - whether to create `.claude/commands/`
   - whether to add hooks
   - what should be committed versus local-only

7. Best-practice workflow:
   - explore first, then plan, then implement, then verify, then commit
   - use subagents for investigation and code review
   - use hooks for deterministic guardrails
   - use skills for reusable domain/project workflows
   - use Context7 or current docs lookup for version-specific framework/API work
   - use Superpowers only if the team accepts its opinionated TDD/subagent methodology; otherwise identify it as optional
   - use GitHub plugin or `gh` for issues, PRs, reviews, Actions, and repo context
   - use code intelligence LSP plugins only when their required language-server binaries are installed

## Standard recommendation model

Use this as a starting point, but adjust based on the repository.

### Universal baseline candidates

- `claude-code-setup`
- `claude-md-management`
- `commit-commands`
- `code-review`
- `code-simplifier`
- `security-guidance`
- `context7`
- `session-report`

### Conditional candidates

- `github` if repo is on GitHub or uses GitHub issues/PRs/actions
- `pyright-lsp` if Python code is present and `pyright-langserver` is installed or can be installed
- `typescript-lsp` if JS/TS code is present and `typescript-language-server` is installed or can be installed
- `rust-analyzer-lsp`, `gopls-lsp`, `jdtls-lsp`, `clangd-lsp`, `csharp-lsp`, `ruby-lsp`, `php-lsp`, `swift-lsp`, `kotlin-lsp`, `lua-lsp` as language-specific candidates
- `feature-dev` for complex multi-file feature work
- `pr-review-toolkit` for teams that want specialized PR review agents
- `frontend-design` for frontend/UI projects
- `hookify` when repeated mistakes should become deterministic hooks
- `superpowers` when the team wants a strict brainstorming/design/TDD/subagent workflow
- `plugin-dev` only when the team is building plugins
- `skill-creator` only when the team is building reusable skills
- `agent-sdk-dev` only when the repo builds Agent SDK apps
- `mcp-server-dev` only when the repo builds MCP servers

## Conflict policy

If sources conflict, report the conflict and choose the most conservative default:
- official Claude Code docs beat community docs
- local installed plugin metadata beats old README examples
- project scope beats user scope for team onboarding
- no secrets in committed files
- HTTP MCP transport beats SSE when both exist
- avoid duplicate MCP servers when a plugin already provides one
- do not install global binaries unless necessary and documented
- do not enable opinionated methodology plugins unless the project wants that workflow

## Required output

Create or update a report at:

`docs/ai/claude-code-onboarding-research.md`

The report must contain:

1. Executive summary
2. Source verification table with URLs checked and dates
3. Project profile
4. Current Claude Code configuration inventory
5. Plugin decision matrix
6. Recommended project-scope install commands
7. Language-server prerequisites
8. MCP decision matrix
9. Recommended `.mcp.json` strategy
10. Recommended `CLAUDE.md` changes
11. Recommended hooks/skills/agents/commands
12. Security and secrets review
13. Conflicts, uncertainty, and conservative defaults
14. Final acceptance criteria
15. Copy-paste bootstrap command sequence for the next Claude Code session

Do not hide uncertainty. If you cannot verify a plugin, say so and include the exact command or source to verify it.
