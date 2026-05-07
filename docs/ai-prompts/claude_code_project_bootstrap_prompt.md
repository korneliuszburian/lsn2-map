# PROMPT 2 — Claude Code Project Bootstrap / Force Plugin + MCP Setup Sequence

You are Claude Code operating in a repository. Your task is to execute a standardized, repeatable onboarding/bootstrap sequence for this repo.

This process must work for any new project. Prefer project-scoped configuration so future collaborators inherit the same Claude Code setup.

Do not implement product features. Focus only on setting up Claude Code, plugins, MCP, project memory, verification commands, and onboarding docs.

## Non-negotiable rules

1. Prefer project scope for team-shared Claude Code configuration.
2. Do not commit secrets.
3. Do not overwrite existing project files without inspecting them first.
4. Do not duplicate MCP servers that are already provided by plugins.
5. If a command is unsupported by this local Claude Code version, capture the error and provide the exact fallback slash-command or interactive step.
6. After installing/enabling/disabling plugins during an active Claude Code session, ask me to run `/reload-plugins` if you cannot run it yourself.
7. Use the official marketplace name `claude-plugins-official`.
8. Verify commands, plugin files, and generated configuration. Do not assume installation succeeded.

## Canonical references to follow

Use these as the source-of-truth set when deciding commands and best practices:

- https://code.claude.com/docs/en/discover-plugins
- https://github.com/anthropics/claude-plugins-official
- https://github.com/anthropics/claude-code/tree/main/plugins
- https://code.claude.com/docs/en/mcp
- https://code.claude.com/docs/en/best-practices
- https://code.claude.com/docs/en/claude-directory
- https://github.com/anthropics/claude-cookbooks
- https://platform.claude.com/cookbook/
- https://claude.com/plugins/github
- https://github.com/obra/superpowers

## Phase 0 — Preflight

Run these commands from the repository root. Capture stdout/stderr in the final report.

```bash
pwd
git rev-parse --show-toplevel
git status --short
git remote -v
claude --version
node --version || true
npm --version || true
python --version || true
python3 --version || true
gh --version || true
```

Inspect current Claude Code files:

```bash
ls -la
find . -maxdepth 3 -type f \( -name "CLAUDE.md" -o -name ".mcp.json" -o -path "./.claude/*" \) | sort
```

If there is no `docs/ai` directory, create it.

## Phase 1 — Detect project type

Inspect files and classify the project:

```bash
find . -maxdepth 3 -type f | sed 's#^\./##' | sort | head -300
```

Detect:
- languages
- package managers
- test commands
- lint commands
- typecheck commands
- CI files
- deployment files
- frontend/backend/data/infra/GIS/ML shape
- whether GitHub is used
- whether `CLAUDE.md` exists
- whether `.mcp.json` exists
- whether `.claude/settings.json` exists

Write findings to:

`docs/ai/project-profile.md`

## Phase 2 — Install universal baseline plugins in project scope

Attempt project-scope installation through the Claude Code CLI.

```bash
claude plugin install claude-code-setup@claude-plugins-official --scope project
claude plugin install claude-md-management@claude-plugins-official --scope project
claude plugin install commit-commands@claude-plugins-official --scope project
claude plugin install code-review@claude-plugins-official --scope project
claude plugin install code-simplifier@claude-plugins-official --scope project
claude plugin install security-guidance@claude-plugins-official --scope project
claude plugin install context7@claude-plugins-official --scope project
claude plugin install session-report@claude-plugins-official --scope project
```

If any plugin is not found:
1. try updating/adding the official marketplace using the documented interactive slash commands:
   - `/plugin marketplace update claude-plugins-official`
   - `/plugin marketplace add anthropics/claude-plugins-official`
2. retry the CLI install if available
3. if CLI project-scope install is unavailable, open `/plugin`, find the plugin in Discover, and install it at Project scope
4. record the fallback in `docs/ai/bootstrap-errors.md`

## Phase 3 — Install conditional plugins

Use the project profile from Phase 1.

### GitHub

If GitHub is the remote host or GitHub issues/PRs/actions are used:

```bash
claude plugin install github@claude-plugins-official --scope project
```

Also check `gh auth status`. If not authenticated, record that human authentication is required.

### Python

If Python files are present, check for Pyright:

```bash
command -v pyright-langserver || true
```

If available, install:

```bash
claude plugin install pyright-lsp@claude-plugins-official --scope project
```

If unavailable, record this prerequisite instead of silently skipping:

```bash
npm install -g pyright
```

Do not run global npm install unless explicitly allowed by the project owner.

### JavaScript / TypeScript

If JS/TS files are present, check for TypeScript language server:

```bash
command -v typescript-language-server || true
```

If available, install:

```bash
claude plugin install typescript-lsp@claude-plugins-official --scope project
```

If unavailable, record this prerequisite:

```bash
npm install -g typescript typescript-language-server
```

Do not run global npm install unless explicitly allowed by the project owner.

### Other languages

Install only when the language is present and the required language-server binary exists or is explicitly approved for installation:

```bash
claude plugin install rust-analyzer-lsp@claude-plugins-official --scope project
claude plugin install gopls-lsp@claude-plugins-official --scope project
claude plugin install clangd-lsp@claude-plugins-official --scope project
claude plugin install jdtls-lsp@claude-plugins-official --scope project
claude plugin install csharp-lsp@claude-plugins-official --scope project
claude plugin install ruby-lsp@claude-plugins-official --scope project
claude plugin install php-lsp@claude-plugins-official --scope project
claude plugin install swift-lsp@claude-plugins-official --scope project
claude plugin install kotlin-lsp@claude-plugins-official --scope project
claude plugin install lua-lsp@claude-plugins-official --scope project
```

### Feature and PR workflow

If the repo has non-trivial multi-file features, install:

```bash
claude plugin install feature-dev@claude-plugins-official --scope project
```

If the repo uses PR review heavily, install:

```bash
claude plugin install pr-review-toolkit@claude-plugins-official --scope project
```

If the repo has frontend/UI work, install:

```bash
claude plugin install frontend-design@claude-plugins-official --scope project
```

### Superpowers

If the team wants opinionated brainstorming, TDD, systematic debugging, and subagent-driven development, install:

```bash
claude plugin install superpowers@claude-plugins-official --scope project
```

If installed, document that it is a methodology plugin and can overlap with `feature-dev`. Use `feature-dev` for explicit guided feature work and Superpowers for strict TDD/design/subagent discipline.

### Plugin/skill/MCP development

Install these only when the repository actually builds these extension types:

```bash
claude plugin install plugin-dev@claude-plugins-official --scope project
claude plugin install skill-creator@claude-plugins-official --scope project
claude plugin install agent-sdk-dev@claude-plugins-official --scope project
claude plugin install mcp-server-dev@claude-plugins-official --scope project
```

## Phase 4 — Reload and inspect plugins

If you are currently inside Claude Code and cannot run slash commands programmatically, ask me to run:

```text
/reload-plugins
/plugin
/mcp
/help
```

Then inspect installed plugin files where possible:

```bash
find ~/.claude/plugins -maxdepth 8 -type f \( -name "README.md" -o -name "plugin.json" -o -path "*/commands/*.md" -o -path "*/skills/*/SKILL.md" -o -path "*/agents/*.md" \) | sort | head -500
```

Create:

`docs/ai/plugin-inventory.md`

The inventory must list:
- plugin name
- scope if discoverable
- commands
- skills
- agents
- hooks
- MCP servers
- LSP servers
- prerequisites
- known usage triggers
- conflicts/overlaps

## Phase 5 — MCP setup

Run:

```bash
claude mcp list || true
```

If a project-shared MCP server is needed, use project scope.

Remote HTTP example:

```bash
claude mcp add --transport http --scope project docs https://your-mcp-server.example.com/mcp
```

Local stdio example:

```bash
claude mcp add --transport stdio --scope project local-tools -- npx -y your-mcp-package
```

Rules:
- use HTTP over SSE when both are available
- use stdio only for local tools/scripts
- do not store credentials directly in `.mcp.json`
- use environment variable placeholders in `.mcp.json`
- avoid duplicating plugin-provided MCP servers
- after editing `.mcp.json`, run `claude mcp list`, `claude mcp get <name>`, and `/mcp`

If `.mcp.json` is created or modified, inspect it and write a security note to:

`docs/ai/mcp-strategy.md`

## Phase 6 — CLAUDE.md and project Claude files

If `CLAUDE.md` does not exist, create a starter version. If it exists, audit it before editing.

The recommended `CLAUDE.md` must include:
- project purpose
- architecture overview
- development commands
- test/lint/typecheck commands
- data/secrets rules
- commit/PR conventions
- plugin usage rules
- MCP usage rules
- where to find onboarding docs
- rule: always verify with tests/lint/typecheck before claiming completion

Run or request the built-in initialization flow when useful:

```text
/init
```

If available and appropriate, use the `claude-md-management` plugin by asking:
- "audit my CLAUDE.md files"
- `/revise-claude-md`

Create or update:

- `CLAUDE.md`
- `docs/ai/claude-code-usage.md`
- `docs/ai/commands.md`

## Phase 7 — Hooks, skills, agents, and commands

Recommend but do not blindly create automation.

Create hooks only for deterministic, zero-exception rules:
- run formatter after edits
- block writes to secrets
- block accidental changes to generated files
- run lightweight lint/typecheck after code edits

Create project skills only for reusable domain workflows:
- project testing workflow
- release workflow
- data-pipeline workflow
- security review workflow
- incident/debug workflow

Create project agents only for specialized isolated reviews:
- security reviewer
- test coverage reviewer
- performance reviewer
- data quality reviewer
- frontend accessibility reviewer

Write recommendations to:

`docs/ai/claude-extensions-roadmap.md`

## Phase 8 — Verification

Run the project’s normal verification commands when discoverable, for example:

```bash
git status --short
```

Then run only commands that exist in this repository, such as:

```bash
npm test
npm run lint
npm run typecheck
pytest
ruff check .
mypy .
```

Do not invent commands. If no test/lint/typecheck command exists, say so and recommend one.

## Phase 9 — Final report

Create:

`docs/ai/claude-code-bootstrap-report.md`

The report must contain:

1. What was installed
2. What failed and why
3. What requires human manual action
4. Exact slash commands still needed
5. Exact auth still needed
6. Installed plugin inventory
7. MCP server inventory
8. CLAUDE.md status
9. Recommended next steps
10. Acceptance criteria status

The final message must include:
- changed files
- installed plugins
- pending manual commands
- pending auth
- warnings/conflicts
- next command to run
