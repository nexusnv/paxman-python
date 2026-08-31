# Paxman First Release Checklist — Pre-1.0

> **Scope:** Preparing `paxman-python` for its **first public PyPI release** — intentionally pre-1.0.
> **Location:** `docs/development/release/` (non-shipping, ephemeral — per `docs/development/AGENTS.md`)
> **Current state (2026-08-21):** `pyproject.toml:version = "0.2.0"`, no `CHANGELOG.md`, no git tags, no publish workflow, CI is test-only.

---

## 1. Version Number — What To Start With

### Recommendation: `0.1.0`

**Why `0.1.0` for a first public release (SemVer §4):**

| SemVer Range | Meaning | API stability promise |
|---|---|---|
| `0.1.0` – `0.y.z` | Initial development | **Anything MAY change at any time.** No stability guarantee. |
| `1.0.0` | First stable | Public API is stable; breaking changes bump MAJOR. |

- Paxman has 10 shipped capabilities with evolving contracts (`create_contract()` params still shifting per capability). Pre-1.0 signals *“API will break before 1.0, pin accordingly”* — exactly what you want.
- `0.1.0` is the conventional **first public release** for Python libs (used by `hatchling`, `ruff`, etc. on their first publish). `0.0.x` is reserved for private/internal scaffolding.
- Starting at `0.1.0` gives you room to iterate: `0.1.x` patch → `0.2.0` new capability/minor → `1.0.0` when contracts + `canonicalize()` are frozen.

### Your current `0.2.0` — two valid paths:

1. **Clean reset (recommended if never published to PyPI):** bump `pyproject.toml` back to `0.1.0` and publish `0.1.0` as the first tag. PyPI versions are immutable but since nothing is published yet there’s no cost.
2. **Keep `0.2.0`:** publish `0.2.0` as the first public version. Also valid — just document that `0.1.0` was skipped as an internal milestone. Slightly confusing for early adopters who look for `0.1.0` history, but SemVer-legal.

> **Rule for pre-1.0 going forward:** `0.MINOR.PATCH` — `MINOR` = new capability / contract param / breaking grammar tweak; `PATCH` = bugfix / provenance data fix compatible with same minor. Document this in `CONTRIBUTING.md` once you pick it.

**After this checklist, 1.0 criteria:** stable `canonicalize()` signature, stable `Contract`/`Capability` surfaces, frozen error taxonomy, and a promise that `MINOR` becomes `MAJOR` for breaking changes. Don’t set a date — set those gates.

---

## 2. Project Hygiene — Code Readiness

Pre-publish gate. All must be green before tagging:

- [ ] **Tests / quality gates pass locally:**
  ```bash
  uv run ruff check paxman/ tests/ && uv run ruff format --check paxman/ tests/ && uv run pyright && uv run import-linter lint && uv run pytest
  uv run coverage report --include="paxman/core/*,paxman/capabilities/*,paxman/engine/*,paxman/api/*" --fail-under=95
  ```
- [ ] **README install path verified** — `pip install paxman` snippet matches real PyPI name (name `paxman` must be available — check below).
- [ ] **LICENSE.md correctness** — currently `Copyright (c) 2026 Azahari Zaman` under `nexusnv/paxman-python`. Decide if copyright holder should be `nexusnv` / personal / org. Ensure `license = "MIT"` and `license-files = ["LICENSE.md"]` are correct (you already have them).
- [ ] **Version source-of-truth** — single `pyproject.toml:project.version`. No `paxman/__version__` drift (currently no `__version__` attribute — intentionally ok; Hatchling reads `pyproject.toml`). Decide if you will expose `paxman.__version__` (recommended: add `import importlib.metadata; __version__ = metadata.version("paxman")`).
- [ ] **CHANGELOG.md created** (does not exist today) — `## [0.1.0] - 2026-08-XX` with: shipped capabilities (10), Python req `>=3.11`, install note, provenance table. Use [Keep a Changelog](https://keepachangelog.com/) + SemVer.
- [ ] **Docs sanity** — `README.md`, `ARCHITECTURE.md`, `CONTRIBUTING.md` have no `azaharizaman/` stale links (you already migrated to `nexusnv` in `d509b65` — spot-check `docs/`).
- [ ] **`dist/` is gitignored** — yes (`.gitignore` covers it). Clean `dist/` before build.
- [ ] **Generated data committed** — run `uv run python tools/regenerate_currency_data.py --check` / `regenerate_si_prefix_data.py --check` / `regenerate_isbn_range_data.py --check` — CI already checks two of these; add ISBN check if you keep it.

---

## 3. Packaging Configuration — `pyproject.toml` Fixes Before Publish

Current `pyproject.toml` is *minimally publishable* but needs hardening:

- [ ] **PyPI name availability** — verify `paxman` is available (or reserved by you) on PyPI + TestPyPI: `https://pypi.org/project/paxman/` and `https://test.pypi.org/project/paxman/`.
- [ ] **Add missing `[project]` metadata** (strongly recommended for PyPI trust + discoverability):
  ```toml
  authors = [{ name = "Azahari Zaman", email = "you@nexusnv.com" }]
  maintainers = [{ name = "nexusnv" }]
  keywords = ["canonicalization", "provenance", "iso", "rfc", "validation"]
  classifiers = [
    "Development Status :: 3 - Alpha",  # for 0.1.0; move to 4 - Beta at 0.5, 5 - Production/Stable at 1.0
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: 3.13",
    "Topic :: Software Development :: Libraries :: Python Modules",
    "Typing :: Typed",
  ]
  readme = "README.md"  # already present — keep
  ```
- [ ] **Fix `[project.urls]`** — `Issues` currently points to repo root, should be `https://github.com/nexusnv/paxman-python/issues`:
  ```toml
  [project.urls]
  Homepage = "https://github.com/nexusnv/paxman-python"
  Repository = "https://github.com/nexusnv/paxman-python"
  Issues = "https://github.com/nexusnv/paxman-python/issues"
  Changelog = "https://github.com/nexusnv/paxman-python/blob/main/CHANGELOG.md"
  Documentation = "https://github.com/nexusnv/paxman-python#readme"
  ```
- [ ] **`requires-python` pin** — keep `>=3.11` (you already have it). Add `python-requires` classifier alignment (above).
- [ ] **Build config explicit** — you have `[build-system] requires = ["hatchling"]` + `[tool.hatch.build.targets.wheel] packages = ["paxman"]`. Add sdist include for `README.md`/`LICENSE.md` if not auto-included (Hatchling includes them by default via `license-files`).
- [ ] **Add `__typed` marker** if you ship types: create `paxman/py.typed` (empty file) so `pyright --strict` consumers get types. (Recommended since you enforce strict pyright.)
- [ ] **Version strategy decision** — static `version = "0.1.0"` in `pyproject.toml` (simple, recommended for first release) vs dynamic `setuptools_scm`/`hatch-vcs` later. Don’t add `hatch-vcs` now unless you want tag-driven versioning.
- [ ] **Dry build + inspect:**
  ```bash
  uv build  # or: uv run hatch build
  tar tzf dist/paxman-0.1.0.tar.gz | head -30
  unzip -l dist/paxman-0.1.0-py3-none-any.whl | head -30
  uv run twine check dist/*  # add twine to dev group if needed
  ```

---

## 4. CI / CD and GitHub Configuration

### 4.1 New workflow: `publish.yml` (Trusted Publishing — no API tokens)

- [ ] **Create `.github/workflows/publish.yml`:**
  ```yaml
  name: Publish
  on:
    push:
      tags: ["v*.*.*"]        # v0.1.0, v0.2.0, v1.0.0
    workflow_dispatch:        # manual dry-run
  permissions:
    contents: write           # for GitHub Release creation
    id-token: write           # for PyPI OIDC
  jobs:
    build:
      runs-on: ubuntu-latest
      steps:
        - uses: actions/checkout@v4
        - uses: astral-sh/setup-uv@v4
        - run: uv build
        - run: uv run twine check dist/*  # optional but recommended
        - uses: actions/upload-artifact@v4
          with: { name: dist, path: dist/ }
    publish:
      needs: build
      runs-on: ubuntu-latest
      environment: pypi        # protects with required reviewers if you add them
      permissions: { id-token: write }
      steps:
        - uses: actions/download-artifact@v4
          with: { name: dist, path: dist/ }
        - uses: pypa/gh-action-pypi-publish@release/v1
          # No username/password — uses OIDC via Trusted Publisher
    release:
      needs: publish
      runs-on: ubuntu-latest
      permissions: { contents: write }
      steps:
        - uses: softprops/action-gh-release@v2
          with:
            generate_release_notes: true
            files: dist/*
  ```
- [ ] **Branch/tag protection:** Settings → Branches → protect `main` (require CI `ci` job passing, no force-push). Optionally protect `v*` tags.
- [ ] **Environments:** Settings → Environments → create `pypi` (no required reviewers for `0.1.0`; add reviewers before `1.0`).
- [ ] **Update existing `ci.yml`** — ensure it runs on `tags: ["v*"]` too or that `publish.yml` re-runs checks. Current `ci.yml` triggers on `push: branches: [main, feature/**, refactor/**]` — tags won’t run CI unless added. Either add `tags: ["v*"]` or make `publish.build` run `ruff/pyright/pytest` before `uv build`.
- [ ] **Add badge** to `README.md` once workflow lands (optional, after first green run).

### 4.2 Release hygiene in GitHub

- [ ] **About section** filled: description *“Canonicalization authority resolver”*, homepage = `https://github.com/nexusnv/paxman-python`, topics: `canonicalization`, `provenance`, `python`, `iso3166`, `rfc5322`, etc.
- [ ] **Releases vs tags policy** — use annotated tags `v0.1.0` (`git tag -a v0.1.0 -m "paxman 0.1.0"`), push tags, let `publish.yml` create the GitHub Release. Don’t create releases manually.
- [ ] **Issue/PR templates** (optional, nice before public): `.github/ISSUE_TEMPLATE/bug_report.md`, `feature_request.md`, `PULL_REQUEST_TEMPLATE.md`.

---

## 5. Accounts / Logins To Register Before Release

Register these **before** you configure Trusted Publishing — you need admin on both sides:

| # | Account / Service | What to do | URL | Who needs it |
|---|---|---|---|---|
| 1 | **PyPI** | Create account + verify email + enable **2FA (TOTP or WebAuthn)**. Check that `paxman` name is claimable. If taken, decide on `paxman-canonical` etc. *before* editing `pyproject.toml:name`. | https://pypi.org/account/register/ | Primary maintainer |
| 2 | **TestPyPI** | Same as PyPI (separate account DB). Use for dry-run publish. | https://test.pypi.org/account/register/ | Same |
| 3 | **PyPI Trusted Publisher** | PyPI → Your project → Settings → Publishing → “Add a new pending publisher” → Owner `nexusnv`, Repo `paxman-python`, Workflow `publish.yml`, Environment `pypi`. Repeat on TestPyPI with environment `testpypi`. | https://pypi.org/manage/account/publishing/ | Admin on `nexusnv/paxman-python` |
| 4 | **TestPyPI Trusted Publisher** | Same as #3 on TestPyPI — point to same repo/workflow but environment `testpypi`. Needed for `publish-test.yml` or `workflow_dispatch` dry runs. | https://test.pypi.org/manage/account/publishing/ | Same |
| 5 | **GitHub** | Ensure `nexusnv/paxman-python` has you as **Admin**, 2FA enabled, and `gh` CLI authenticated (`gh auth status` → `azaharizaman` — already logged in). | https://github.com/nexusnv/paxman-python/settings/access | Maintainers |
| 6 | **Email for `project.authors`** | A stable contact address (personal or `contact@nexusnv.com`) for `pyproject.toml:authors.email` and `SECURITY.md`. | — | — |
| 7 | **(Optional) ReadTheDocs / GitHub Pages** | Only if you plan hosted docs beyond `README.md`. Not required for `0.1.0`. | https://readthedocs.org/ | — |
| 8 | **(Optional) Sigstore / OIDC sanity** | No account needed — PyPI Trusted Publishing uses GitHub OIDC + Sigstore automatically. Just don’t create a classic API token unless OIDC fails. | — | — |

> **Do NOT create a PyPI API token** unless Trusted Publishing is unavailable. OIDC is more secure and is what `pypa/gh-action-pypi-publish` expects. If you must, scope it to project `paxman` only and store as `PYPI_API_TOKEN` secret — but prefer OIDC.

---

## 6. Pre-Release Dry-Run (Do This Once, Before `0.1.0`)

- [ ] `uv sync --all-extras && uv run pytest && uv run pyright && uv run ruff check paxman/ tests/`
- [ ] Set version to `0.1.0` (or keep `0.2.0` — per §1 decision) in `pyproject.toml`.
- [ ] `uv build && uv run twine check dist/*` — no warnings.
- [ ] **TestPyPI publish:** push tag `v0.1.0rc1` or `workflow_dispatch` to exercise Trusted Publisher on TestPyPI; then `uv run --with paxman --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ python -c "import paxman; print(paxman.__version__)"` (or inspect built metadata).
- [ ] **Local install smoke test:**
  ```bash
  python -m venv /tmp/paxman-smoke && /tmp/paxman-smoke/bin/pip install dist/paxman-0.1.0-py3-none-any.whl
  /tmp/paxman-smoke/bin/python -c "import paxman; from paxman.capabilities import Email; paxman.register_all_shipped(); print(paxman.canonicalize('user@Example.COM', Email.create_contract()).canonicalized_value)"
  ```
- [ ] Verify `CHANGELOG.md`, `README.md` install snippet, and `project.urls` render correctly on TestPyPI project page.

---

## 7. Release Day Procedure — `0.1.0` (or `0.2.0`)

1. [ ] Final `main` is green (`ci` passing on `main`).
2. [ ] Bump `pyproject.toml:version` to target (`0.1.0`), update `CHANGELOG.md` date.
3. [ ] Commit: `chore(release): paxman 0.1.0` → push to `main` (through PR if `main` is protected).
4. [ ] Docs: open PR appending the new version to `versions.json` **targeting `main`** and merge it before cutting the tag (D3b) — entry `{"slug": "v0.1.0", "tag": "v0.1.0"}` in `docs_site/versions.json` (see `docs_site/README.md` § Publishing).
5. [ ] Tag: `git tag -a v0.1.0 -m "paxman 0.1.0 — first public release"` + `git push origin v0.1.0`.
6. [ ] Watch `Publish` workflow — build → `twine check` → `pypa/gh-action-pypi-publish` → GitHub Release appears with `dist/*` attached. For docs, the tag push rebuilds the full versioned site (`latest/` from `main` plus every `vX.Y.Z/` in `versions.json`, including the new tag — D3b) and deploys via `actions/deploy-pages`.
7. [ ] Verify on PyPI: `https://pypi.org/project/paxman/0.1.0/` shows correct README, classifiers, `pip install paxman==0.1.0` works in a clean venv. Verify docs at `https://nexusnv.github.io/paxman-python/v0.1.0/` and that `latest/`/`stable/` redirects are intact.
8. [ ] Announce (Issues/Discussions, internal channels). Close milestone.

---

## 8. Immediately After — Post-Release Hygiene

- [ ] Bump `pyproject.toml` to next dev version: `0.2.0.dev0` or `0.1.1.dev0` (or keep `0.2.0` if you shipped `0.1.0`). Prevents accidental re-publish of same version.
- [ ] Add `CHANGELOG.md: ## [Unreleased]` section.
- [ ] Decide on `paxman/py.typed` + `paxman/__version__` follow-ups as separate PRs.
- [ ] Open tracking issue for `1.0` gates (API freeze criteria).
- [ ] Archive this checklist — it’s ephemeral per `docs/development/AGENTS.md`. The durable record is the git tag + GitHub Release + `CHANGELOG.md`.

---

## Appendix — What’s Already Done

- `pyproject.toml` uses `hatchling`, `uv` toolchain, `ruff`/`pyright`/`import-linter`/`pytest` with 95% gates.
- `LICENSE.md` (MIT), `.gitignore` (`dist/`), CI matrix `3.11–3.13` — all present.
- Registry URLs migrated to `nexusnv/paxman-python` (`d509b65`).
- `dist/paxman-0.2.0-py3-none-any.whl` + `.tar.gz` build artifacts present locally (re-build before publish).

## Appendix — What’s Missing (This Checklist Fills)

- `CHANGELOG.md`, `CHANGELOG` URL in `project.urls`, `classifiers`/`keywords`/`authors`.
- `paxman/py.typed`, `paxman/__version__` exposure.
- `publish.yml` with OIDC Trusted Publishing (no workflow exists today).
- TestPyPI/PyPI publisher registrations + accounts.
- Release tag `v0.1.0` (or `v0.2.0`) — no tags exist yet.
