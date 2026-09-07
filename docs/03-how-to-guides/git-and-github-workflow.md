# How to Follow the Git & GitHub Development Workflow

This guide details the engineering standards, branching conventions, commit rules, and automated CI quality gates required when contributing to FlowForge. Adhering to this workflow ensures predictable releases, clean git history, and zero regressions across backend, worker, and frontend services.

---

## The Feature-Branch Lifecycle Blueprint

FlowForge enforces a strict feature-branch workflow. All modifications originate on isolated branches and are integrated into `main` solely through verified, peer-reviewed Pull Requests:

```mermaid
%%{init: {
  'theme': 'dark',
  'themeVariables': {
    'darkMode': true,
    'background': '#0b0f19',
    'mainBkg': '#0f172a',
    'primaryColor': '#1e293b',
    'primaryTextColor': '#f8fafc',
    'primaryBorderColor': '#38bdf8',
    'lineColor': '#94a3b8',
    'secondaryColor': '#0f172a',
    'tertiaryColor': '#1e293b'
  }
}}%%
flowchart LR
    classDef git fill:#0c4a6e,stroke:#38bdf8,stroke-width:2px,color:#f0f9ff;
    classDef branch fill:#312e81,stroke:#818cf8,stroke-width:2px,color:#e0e7ff;
    classDef test fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#ecfdf5;
    classDef ci fill:#7f1d1d,stroke:#f87171,stroke-width:2px,color:#fef2f2;
    classDef merge fill:#581c87,stroke:#c084fc,stroke-width:2px,color:#faf5ff;

    Main[main branch]:::git -->|git checkout -b| Feat[feat/branch]:::branch
    Feat --> LocalDev[Develop & Run Tests\npytest + npm test]:::test
    LocalDev --> Commit[Conventional Commit\ngit commit -m 'feat(...)']:::git
    Commit --> Push[git push -u origin]:::git
    Push --> PR[Open GitHub Pull Request]:::branch
    PR --> CI[GitHub Actions CI Pipeline\nAutomated Validation]:::ci
    CI -->|All Checks Green| Review[Peer Code Review & Approval]:::test
    Review -->|Squash & Merge| MainMerge[Merged into main]:::merge
```

---

## Core Version Control Principles

1. **`main` is Always Deployable**: The `main` branch represents production-ready software. Direct commits or force-pushes to `main` are strictly forbidden by branch protection rules.
2. **One Concern per Branch**: Keep branches focused on a single feature, bug fix, or documentation update. Avoid bundling unrelated refactors into feature PRs.
3. **Continuous Local Testing**: Never push code that has not passed local verification suites (`pytest` and `npm test`).
4. **Clean, Atomic Commits**: Use semantic commit messages that explain *what* was changed and *why*.

---

## Step-by-Step Contribution Workflow

### Step 1: Synchronize Your Local `main` Branch
Before beginning any new work, synchronize your local repository with the remote `origin`:

```bash
git checkout main
git pull origin main
```

---

### Step 2: Create a Scoped Feature Branch
Create a descriptive branch name in lowercase using hyphens. Prefix the branch name with a semantic category:

- `feat/<feature-name>`: New functionality (e.g., `feat/webhook-retry-policy`)
- `fix/<bug-name>`: Bug fix (e.g., `fix/postgres-connection-leak`)
- `docs/<doc-topic>`: Documentation enhancements (e.g., `docs/api-reference-update`)
- `refactor/<scope>`: Code restructuring without behavior changes (e.g., `refactor/queue-router`)
- `test/<scope>`: Adding or improving test suites (e.g., `test/auth-edge-cases`)

```bash
git checkout -b feat/slack-notification-handler
```

---

### Step 3: Implement Changes and Verify Locally
Implement your modifications, then run the full test suite locally before staging any files:

```bash
# 1. Run the backend test suite with coverage
cd backend
pytest --cov=app --cov=tasks

# 2. Run the frontend lint and test suites
cd ../frontend
npm run lint
npm test

# Return to repository root
cd ..
```

> [!TIP]
> To test complete container interactions, run `docker compose -f infrastructure/docker-compose.yml up --build -d` and confirm all 5 containers report healthy via `docker compose -f infrastructure/docker-compose.yml ps`.

---

### Step 4: Stage Files and Commit Using Conventional Commits
Stage only the files relevant to your task and commit using our Conventional Commits format:

```bash
git add worker/tasks/registry.py worker/tasks/slack.py
git commit -m "feat(worker): implement slack webhook notification handler"
```

---

### Step 5: Push Your Branch to GitHub
Push your local branch to the remote repository and set the upstream tracking reference:

```bash
git push -u origin feat/slack-notification-handler
```

---

### Step 6: Open and Document Your Pull Request
1. Open the repository on GitHub: `https://github.com/chandadiya2004/FlowForge`.
2. Click the **"Compare & pull request"** button.
3. Ensure the base branch is set to `main` and the compare branch is your feature branch.
4. Structure your Pull Request description using this template:

```markdown
## Summary
Brief explanation of what this PR implements and why.

## Changes Made
- Added slack notification handler in worker/tasks/
- Registered new handler type in TASK_REGISTRY
- Added unit tests covering webhook payloads and timeout handling

## Verification
- [x] Backend test suite passes (`pytest`)
- [x] Frontend test suite passes (`npm test`)
- [x] Tested locally inside Docker Compose
```

5. Click **"Create pull request"**.

---

## Conventional Commits Specification

FlowForge adheres to the **Conventional Commits 1.0.0** specification. Every commit message must follow this structure:

```text
<type>(<optional scope>): <imperative description>

[optional body explaining context or rationale]

[optional footer(s) such as Closes #123]
```

### Supported Commit Types

| Type | Intended Purpose | Concrete Example |
| :--- | :--- | :--- |
| **`feat`** | Introduces a new feature or user-facing capability | `feat(api): add batch cancel endpoint for pending jobs` |
| **`fix`** | Patches a bug in existing production code | `fix(worker): handle null json payload in sleep handler` |
| **`docs`** | Documentation creation or edits only | `docs(tutorials): add dark-mode mermaid diagrams to docker guide` |
| **`test`** | Adds or refactors unit/integration tests without altering app code | `test(auth): add expired jwt access token validation test` |
| **`refactor`**| Restructures code without changing behavior or fixing bugs | `refactor(backend): extract queue routing logic to dedicated module` |
| **`chore`** | Routine maintenance, dependency bumps, or tool configuration | `chore(deps): update next.js to 16.3.4 and tailwindcss to v4` |
| **`ci`** | Modifications to GitHub Actions workflows or build scripts | `ci(github): add docker buildx cache to action pipeline` |

### Formatting Best Practices
- **Use the imperative mood**: "add feature" not "added feature" or "adds feature".
- **Keep the subject line concise**: 50–72 characters maximum.
- **Do not end the subject with a period**: `feat(db): add index` (not `feat(db): add index.`).

---

## Automated CI Pipeline Quality Gates

Every push and Pull Request triggers the automated GitHub Actions CI pipeline defined in [.github/workflows/ci.yml](file:///d:/Edutation(P)/FlowForge/.github/workflows/ci.yml):

```mermaid
%%{init: {
  'theme': 'dark',
  'themeVariables': {
    'darkMode': true,
    'background': '#0b0f19',
    'mainBkg': '#0f172a',
    'primaryColor': '#1e293b',
    'primaryTextColor': '#f8fafc',
    'primaryBorderColor': '#38bdf8',
    'lineColor': '#94a3b8',
    'secondaryColor': '#0f172a',
    'tertiaryColor': '#1e293b'
  }
}}%%
flowchart TD
    classDef trigger fill:#0c4a6e,stroke:#38bdf8,stroke-width:2px,color:#f0f9ff;
    classDef job fill:#312e81,stroke:#818cf8,stroke-width:2px,color:#e0e7ff;
    classDef gate fill:#1e293b,stroke:#e2e8f0,stroke-width:2px,color:#f8fafc;
    classDef success fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#ecfdf5;
    classDef fail fill:#7f1d1d,stroke:#f87171,stroke-width:2px,color:#fef2f2;

    Event([Push or PR Opened]):::trigger --> Trigger[GitHub Actions Engine]:::trigger

    subgraph ParallelGates [Parallel Quality Gates]
        Trigger --> BackendJob["backend-tests\n- PostgreSQL 16 & Redis 7 Services\n- Alembic Migrations\n- Pytest + Coverage"]:::job
        Trigger --> FrontendJob["frontend-tests\n- Node 20 Setup\n- ESLint Linting\n- Jest Unit Tests\n- Next.js Production Build"]:::job
    end

    BackendJob --> MergeGate{Both Jobs Passed?}:::gate
    FrontendJob --> MergeGate

    MergeGate -->|No (Failing Checks)| Blocked["Merge Blocked\nInspect Red CI Logs"]:::fail
    MergeGate -->|Yes (Green Checks)| DockerJob["docker-publish\n(Build & Push Multi-Arch Images)"]:::job
    DockerJob --> Merged["Ready for Review & Merge"]:::success

    style ParallelGates fill:#0f172a,stroke:#334155,stroke-width:1.5px,color:#e2e8f0
```

### The Three Automated Quality Gates:

1. **`backend-tests`**:
   - Spawns live containerized `postgres:16-alpine` and `redis:7-alpine` services in GitHub Actions.
   - Executes database schema evolution via `alembic upgrade head`.
   - Runs the backend test suite with coverage enforcement: `pytest --cov=app --cov=tasks --cov-report=term-missing`.
2. **`frontend-tests`**:
   - Provisions Node.js 20 with clean dependency caching (`npm ci`).
   - Runs code quality checks: `npm run lint`.
   - Executes Jest unit test suites: `npm test`.
   - Validates production bundle compilation: `npm run build`.
3. **`docker-publish`**:
   - Triggered only after `backend-tests` and `frontend-tests` succeed.
   - Validates that `backend/Dockerfile`, `worker/Dockerfile`, and `frontend/Dockerfile` build cleanly without cache corruption.

> [!IMPORTANT]
> A Pull Request cannot be merged if any quality gate fails. Always check the **Checks** tab on your PR to inspect error logs and stack traces if a check reports red.

---

## Practical Git Recipes & Troubleshooting

### Keeping Your Branch Synchronized with `main`
If changes have merged to `main` while you were working, rebase your feature branch to keep history linear:

```bash
git checkout main
git pull origin main
git checkout feat/your-branch
git rebase main
```
If merge conflicts occur, resolve the conflicting files, run `git add <resolved-files>`, and continue with `git rebase --continue`.

### Modifying Your Last Commit (Before Pushing)
If you made a typo in your commit message or forgot a file:

```bash
git add forgotten_file.py
git commit --amend --no-edit
```

### Cleaning Up Stale Local Branches
After your PR merges on GitHub, clean up your local workstation:

```bash
git checkout main
git pull origin main
git branch -d feat/your-branch
```

---

## Related Documentation & References

- [CI/CD Pipeline Reference](../04-reference/ci-cd-pipeline.md) — Comprehensive technical reference for GitHub Actions workflows.
- [Running the Test Suite How-To](running-the-test-suite.md) — How to run pytest and Jest suites locally.
- [Deploying to Production How-To](deploying-to-production.md) — Production deployment procedures and image releases.
- [Getting Started Tutorial](../02-tutorials/getting-started.md) — Multi-container local orchestration tutorial.
- [Platform Overview](../01-introduction/overview.md) — System philosophy and architecture.