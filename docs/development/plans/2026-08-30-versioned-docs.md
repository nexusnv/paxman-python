# Versioned Docs (Starlight) + Rename website/ → docs_site/ Implementation Plan (issue #96) — Rev.2

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enable versioned documentation with `website/` renamed to `docs_site/`: per-tag builds retained (`/v0.2.0/`, `/v0.2.1/`, `/v0.2.2/`, `/v0.3.0/`, …), `latest` (dev/main) always current, in-site Starlight version switcher — without overwriting previously deployed versions.

**Architecture:** Rename `website/` → `docs_site/` first. Versioning uses the `starlight-versions` integration for the in-site switcher plus a **single canonical deploy recipe**: `.github/workflows/docs.yml` reads `docs_site/versions.json` (single source of truth) and, on every deployable push, **builds every version in that file** (checking out each listed tag) and merges all outputs plus a generated root redirect into **one** `actions/deploy-pages` artifact. Because every deploy ships the complete set, no prior version is ever clobbered and the acceptance requirement "Pages deploy still uses `actions/deploy-pages`" holds.

**Tech Stack:** Astro ^7.2.9, `@astrojs/starlight` ^0.41.9, `starlight-versions` (HiDeoo; compat verified in spike against 0.41.x), GitHub Pages via `actions/upload-pages-artifact@v3` + `actions/deploy-pages@v4` (`build_type: workflow`), `npm` in `docs_site/`, `jq` for `versions.json` parsing in CI.

**References:** Issue #96; `website/astro.config.mjs:2,32`; `website/package.json:14-19` (`astro ^7.2.9`, `@astrojs/starlight ^0.41.9`); `website/src/content/docs` symlink → `../../../docs/user` (verified via `readlink`); `.github/workflows/docs.yml` (full file re-verified on `dev` `b26e3d5`); `.gitignore:4-5` (`website/dist/`, `website/node_modules/`); `docs/user/glossary.md:15`; git tags `v0.1.0, v0.2.0, v0.2.1, v0.2.2`.

---

## Locked decisions (resolve all prior review contradictions)

- **D1 — Task order:** rename (`Task 1`) → plugin spike inside `docs_site/` (`Task 2`) → versioning pipeline (`Task 3`) → verification (`Task 4`). No `docs_site/` references before the rename exists.
- **D2 — Single deploy recipe:** `actions/deploy-pages` + `build_type: workflow` (acceptance requirement). Version retention is achieved by building **all** versions from `versions.json` per deploy and merging artifacts — **not** `peaceiris/actions-gh-pages`, **not** a `gh-pages` branch, **not** `keep_files`.
- **D3 — `versions.json` schema (single canonical shape):**
  ```json
  {
    "versions": [
      {"slug": "v0.2.0", "label": "v0.2.0", "tag": "v0.2.0"},
      {"slug": "v0.2.1", "label": "v0.2.1", "tag": "v0.2.1"},
      {"slug": "v0.2.2", "label": "v0.2.2", "tag": "v0.2.2"}
    ],
    "latest": {"slug": "latest", "label": "latest", "source_ref": "dev"}
  }
  ```
  `slug` = URL subfolder; `tag` = git ref checked out for that build. `latest` has no tag — it builds the current ref (`dev`/`main`). `stable` alias is a generated redirect, not a build (D4).
- **D4 — Root + stable redirects:** generated **in CI after the artifact merge** (`printf` meta-refresh), not `docs_site/public/index.html` (which would collide with Starlight's root route). `dist/index.html` → `./latest/`; `dist/stable/index.html` → `./<last-pinned-slug>/`.
- **D5 — Deploy triggers:** `push` to `dev` or `main` → rebuild `latest/` (plus all pinned versions, unchanged) and redeploy full artifact; `push` of tag `v*.*.*` → append that version to `versions.json` (PR), build it, redeploy full artifact. Tag builds are immutable because the tag ref is pinned in `versions.json`.
- **D6 — Symlink:** `git mv website docs_site` preserves the relative symlink; verify `readlink docs_site/src/content/docs` == `../../../docs/user` (same depth — both `website/` and `docs_site/` are one level below repo root). Recreate only if broken.
- **D7 — `.gitignore`:** replace both `website/dist/` and `website/node_modules/` (verified at `.gitignore:4-5`).
- **D8 — Versions:** Astro ^7.2.9 / Starlight ^0.41.9 (from `website/package.json`, not the stale spec text). Spike must confirm `starlight-versions` compat with Starlight 0.41.x.
- **D9 — `docs.yml` cache:** `cache-dependency-path: website/package-lock.json` → `docs_site/package-lock.json`.

---

## File Structure

- Move: `website/*` → `docs_site/*` (`astro.config.mjs`, `package.json`, `package-lock.json`, `tsconfig.json`, `src/` incl. symlink, `public/`).
- Modify: `.gitignore:4-5` — `website/dist/` → `docs_site/dist/`, `website/node_modules/` → `docs_site/node_modules/`.
- Modify: `.github/workflows/docs.yml` — `paths` (`docs_site/**`), `cache-dependency-path` (D9), `working-directory`, `path`, and new versioned build/merge/deploy jobs per D2/D4/D5.
- Modify: `docs_site/astro.config.mjs` — add `starlight-versions` integration consuming `versions.json`; keep `site: 'https://nexusnv.github.io'`, `base: '/paxman-python/'` constant (plugin + artifact layout handle version subpaths; no per-version `--base` override unless the spike proves it necessary — record finding in `Decision:` notes).
- Create: `docs_site/versions.json` — canonical schema per D3.
- Modify: `docs_site/README.md` (ex `website/README.md`), `docs/user/glossary.md:15`, root `README.md`/`CONTRIBUTING.md`/`AGENTS.md`/`ARCHITECTURE.md` — replace `website/` references (verified hits: `docs/user/glossary.md:15` only; root docs clean).

No changes to `paxman/` (docs-only).

---

### Task 1: Rename `website/` → `docs_site/` (mechanical, no behavior change)

**Files:**
- Move: `website/*` → `docs_site/*`
- Modify: `.gitignore:4-5`, `.github/workflows/docs.yml`, `docs_site/README.md`, `docs/user/glossary.md:15`

- [ ] **Step 1: Move files**

```bash
git mv website docs_site
```

Verify: `ls docs_site/` shows `astro.config.mjs`, `package.json`, `package-lock.json`, `tsconfig.json`, `src/`, `public/`; and `readlink docs_site/src/content/docs` == `../../../docs/user` (D6). If the symlink broke, recreate: `rm docs_site/src/content/docs && ln -s ../../../docs/user docs_site/src/content/docs`.

- [ ] **Step 2: Update `.gitignore:4-5`** (D7)

Replace:
```
website/dist/
website/node_modules/
```
with:
```
docs_site/dist/
docs_site/node_modules/
```

- [ ] **Step 3: Update `.github/workflows/docs.yml` (mechanical only, D9)**

- `paths`: `website/**` → `docs_site/**` (both `push` and `pull_request` blocks)
- `cache-dependency-path: website/package-lock.json` → `docs_site/package-lock.json`
- all three `working-directory: website` → `working-directory: docs_site`
- PR-preview artifact `path: website/dist/` → `docs_site/dist/`
- Pages artifact `path: website/dist/` → `docs_site/dist/`

Do **not** change deploy logic in this task (that is Task 3).

- [ ] **Step 4: Update docs references**

- `docs_site/README.md`: all `website/` → `docs_site/`, dev command `cd docs_site && npm ci && npm run dev`.
- `docs/user/glossary.md:15`: `See website/astro.config.mjs.` → `See docs_site/astro.config.mjs.`
- Root `README.md`/`CONTRIBUTING.md`/`AGENTS.md`/`ARCHITECTURE.md`: verified no `website/` hits — no change (re-check with grep in Step 5).

- [ ] **Step 5: Verify rename is complete and buildable**

```bash
grep -rn "website" --exclude-dir=.git --exclude-dir=node_modules --exclude-dir=dist --exclude-dir=.venv --exclude-dir=.codegraph --exclude-dir=.ruff_cache . | grep -v "CHANGELOG.md" | grep -v "docs/development/"
```
Expected: no hits. Then:

```bash
cd docs_site && npm ci && npm run build
```
Expected: `docs_site/dist/` produced, no errors (Astro ^7.2.9, Starlight ^0.41.9, symlink resolves via `preserveSymlinks`).

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "docs: rename website/ to docs_site/ (#96)"
```

---

### Task 2: Plugin spike inside `docs_site/` (decision gate)

**Files:**
- Modify (on spike branch only): `docs_site/package.json`, `docs_site/astro.config.mjs`
- Modify: this plan file (record `Decision:`)

- [ ] **Step 1: Spike `starlight-versions`**

```bash
git checkout -b spike/starlight-versions
cd docs_site && npm install starlight-versions@latest --save-dev
```

Wire into `docs_site/astro.config.mjs` per plugin docs, reading `versions.json`:

```js
import starlightVersions from 'starlight-versions';
import versionsConfig from './versions.json';
// integrations: [ starlight({ ...existing... }), starlightVersions({ /* per plugin docs */ }) ],
```

Create a minimal `docs_site/versions.json` per D3 (may start with only `latest` until Task 3 populates tags). Verify with Astro ^7.2.9 + Starlight ^0.41.9:

```bash
npm run build && npm run dev
```
Record: switcher renders, build succeeds with `base: '/paxman-python/'` constant, no per-version `--base` needed.

- [ ] **Step 2: Spike `astro-mike` only if `starlight-versions` fails D8 compat**

```bash
npm uninstall starlight-versions && npm install astro-mike@latest --save-dev
```
Same verification. Note: `astro-mike`'s `mike`-style deploy conflicts with D2 (it manages its own `gh-pages` output) — only viable if it can emit into a merged `dist/`; otherwise it is rejected automatically.

- [ ] **Step 3: Record decision, clean up**

On the plan file, add:

```
Decision: starlight-versions@<exact-version> (compat: Starlight 0.41.9, Astro 7.2.9, build_type: workflow confirmed).
`site`/`base` remain constant; version subpaths come from versions.json + artifact layout.
```

Then: `git checkout fix/... && git branch -D spike/starlight-versions` (spike changes to `package.json`/`astro.config.mjs` are re-applied properly in Task 3).

- [ ] **Step 4: Commit the decision note**

```bash
git add docs/development/plans/2026-08-30-versioned-docs.md
git commit -m "docs(plan): record versioning plugin decision (#96)"
```

---

### Task 3: Versioning pipeline (single canonical recipe per D2/D3/D4/D5)

**Files:**
- Modify: `docs_site/package.json` (`starlight-versions` dep), `docs_site/astro.config.mjs` (integration + reads `versions.json`)
- Create: `docs_site/versions.json` (per D3, listing existing tags `v0.2.0`, `v0.2.1`, `v0.2.2`; `v0.3.0` appended when tagged)
- Modify: `.github/workflows/docs.yml` (versioned build matrix + merge + redirect)

- [ ] **Step 1: Add `versions.json` and wire the integration**

`docs_site/versions.json` (per D3, exact):

```json
{
  "versions": [
    {"slug": "v0.2.0", "label": "v0.2.0", "tag": "v0.2.0"},
    {"slug": "v0.2.1", "label": "v0.2.1", "tag": "v0.2.1"},
    {"slug": "v0.2.2", "label": "v0.2.2", "tag": "v0.2.2"}
  ],
  "latest": {"slug": "latest", "label": "latest", "source_ref": "dev"}
}
```

`docs_site/astro.config.mjs`:

```js
import starlightVersions from 'starlight-versions';
import versionsConfig from './versions.json';
// integrations: [ starlight({ ...existing... }), starlightVersions({ /* per plugin docs, fed from versionsConfig */ }) ],
```

Run `npm install` (adds dep) and `npm run build` — expect success with switcher present and `base` unchanged.

- [ ] **Step 2: Rewrite `docs.yml` build/deploy per D2/D4/D5**

Replace the single `build-docs` job with **three jobs** (a matrix needs job-level `strategy`, so versioned builds get their own job):

```yaml
  read-versions:
    name: Read versions.json
    runs-on: ubuntu-latest
    outputs:
      slugs: ${{ steps.versions.outputs.slugs }}
      tags: ${{ steps.versions.outputs.tags }}
      last_slug: ${{ steps.versions.outputs.last_slug }}
    steps:
      - uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262 # v4
        with:
          persist-credentials: false
      - id: versions
        run: |
          echo "slugs=$(jq -c '[.versions[].slug]' docs_site/versions.json)" >> "$GITHUB_OUTPUT"
          echo "tags=$(jq -c '[.versions[].tag]' docs_site/versions.json)" >> "$GITHUB_OUTPUT"
          echo "last_slug=$(jq -r '.versions[-1].slug' docs_site/versions.json)" >> "$GITHUB_OUTPUT"

  build-latest:
    name: Build latest (current ref)
    runs-on: ubuntu-latest
    needs: read-versions
    steps:
      - uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262 # v4
        with:
          persist-credentials: false
      - uses: actions/setup-node@v4
        with: { node-version: 22, cache: npm, cache-dependency-path: docs_site/package-lock.json }
      - run: cd docs_site && npm ci && npx playwright install --with-deps chromium && npm run build
      - uses: actions/upload-artifact@v4
        with: { name: pages-latest, path: docs_site/dist/ }

  build-versions:
    name: Build ${{ matrix.version.slug }}
    runs-on: ubuntu-latest
    needs: read-versions
    strategy:
      matrix:
        version: ${{ fromJSON(needs.read-versions.outputs.slugs_and_tags) }}
    steps:
      - uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262 # v4
        with:
          ref: ${{ matrix.version.tag }}
          persist-credentials: false
      # NOTE: each tag has its own docs_site/package-lock.json (from that tag);
      # npm ci inside docs_site/ uses the tag's own lockfile — no cache needed.
      - run: cd docs_site && npm ci && npx playwright install --with-deps chromium && npm run build
      - uses: actions/upload-artifact@v4
        with: { name: pages-${{ matrix.version.slug }}, path: docs_site/dist/ }

  merge-and-redirect:
    name: Assemble merged site
    runs-on: ubuntu-latest
    needs: [read-versions, build-latest, build-versions]
    steps:
      - uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262 # v4
        with:
          persist-credentials: false
      - uses: actions/download-artifact@v4
        with: { path: partials }
      - name: Assemble merged site
        run: |
          mkdir -p site
          cp -r partials/pages-latest/* site/latest/
          for slug_dir in partials/pages-v*/; do
            slug=$(basename "$slug_dir" | sed 's/^pages-//')
            mkdir -p "site/$slug"
            cp -r "$slug_dir"/* "site/$slug/"
          done
          printf '<!DOCTYPE html><meta http-equiv="refresh" content="0; url=./latest/">' > site/index.html
          mkdir -p site/stable
          printf '<!DOCTYPE html><meta http-equiv="refresh" content="0; url=../%s/">' \
            "$(jq -r '.versions[-1].slug' docs_site/versions.json)" > site/stable/index.html
      - uses: actions/upload-pages-artifact@v3
        with:
          path: site/
```

The existing `deploy` job (`actions/deploy-pages@v4`, `needs: merge-and-redirect` instead of `build-docs`) is unchanged. PR events keep the existing single-build artifact preview (no deploy, no matrix — guard matrix jobs with `if: github.event_name != 'pull_request'`).

- [ ] **Step 3: Verify locally**

```bash
cd docs_site && npm ci && npm run build
```
Expected: single `dist/` for the current ref (per-version `dist/vX/` trees are produced in CI by checking out each tag — not locally; local verification covers build health + switcher).

- [ ] **Step 4: Commit**

```bash
git add docs_site/versions.json docs_site/package.json docs_site/package-lock.json docs_site/astro.config.mjs .github/workflows/docs.yml
git commit -m "docs: versioned docs pipeline via versions.json + deploy-pages (#96)"
```

---

### Task 4: UX, docs, and full verification

**Files:**
- Modify: `docs_site/README.md` (publishing section), `docs/development/release/checklist.md`, `CHANGELOG.md`

- [ ] **Step 1: UX checks**

In `npm run dev`: version dropdown renders (starlight-versions), and in CI-built output confirm each pinned `dist/vX/` carries the plugin's "outdated" affordance and `editLink` resolves per version (Starlight `editLink.baseUrl` stays `main` for `latest`; pinned versions are immutable, so `editLink` pointing at `main` is acceptable — note in README).

- [ ] **Step 2: Docs updates**

`docs_site/README.md` publishing section: how to cut a new version (tag `vX.Y.Z` → append to `versions.json` → push tag → workflow rebuilds full set). `docs/development/release/checklist.md`: add "docs: append version to `versions.json` before tagging".

- [ ] **Step 3: Back-compat**

`https://nexusnv.github.io/paxman-python/` → generated `index.html` redirects to `./latest/` (D4); `latest/` deep links preserved; each pinned `vX/` is a full copy of that tag's site, so old deep links work per version.

- [ ] **Step 4: Full gate**

```bash
uv run ruff check paxman/ tests/
uv run ruff format --check paxman/ tests/
uv run pyright
uv run import-linter lint
uv run pytest -q
cd docs_site && npm ci && npm run build
```
Expected: all green (Python suite unchanged; docs build succeeds).

- [ ] **Step 5: No `website/` remains**

```bash
grep -rn "website" --exclude-dir=.git --exclude-dir=node_modules --exclude-dir=dist --exclude-dir=.venv --exclude-dir=.codegraph --exclude-dir=.ruff_cache .
```
Expected: only `CHANGELOG.md` historical entries.

- [ ] **Step 6: CHANGELOG.md**

Under `## [Unreleased]` → `### Changed`:

```markdown
- **Docs — versioned docs (#96):** `website/` renamed to `docs_site/`; Pages
  deploys now ship every version listed in `docs_site/versions.json`
  (`/vX.Y.Z/` immutable per tag, `/latest/` from `dev`, `/stable/` and root
  redirect to latest) with an in-site version switcher.
```

- [ ] **Step 7: Commit**

```bash
git add CHANGELOG.md docs_site/README.md docs/development/release/checklist.md
git commit -m "docs: changelog and release checklist for versioned docs (#96)"
```

---

## Self-Review

**1. Spec coverage:** rename (Task 1), plugin decision (Task 2), versioned pipeline with retention (Task 3, D2/D5), UX switcher/banner/editLink (Task 4 Step 1), docs + release checklist (Task 4 Step 2), back-compat/root redirect (Task 3 Step 2 + Task 4 Step 3), no `website/` remnants (Task 1 Step 5, Task 4 Step 5), CI + local build green (Task 4 Step 4). ✔

**2. Placeholder scan:** none — every step has exact commands, paths, expected outputs; the two `/* ... */` placeholders in JS snippets refer to the existing Starlight config block, quoted verbatim from `website/astro.config.mjs` in References. ✔

**3. Type consistency:** `versions.json` single schema (D3) used by plugin config, CI `jq` matrix, and redirect generation; `docs.yml` YAML; `astro.config.mjs` JS. ✔

---

## Execution Handoff

Plan complete and saved to `docs/development/plans/2026-08-30-versioned-docs.md`. Two execution options:

**1. Subagent-Driven (recommended)** — fresh subagent per task, review between tasks

**2. Inline Execution** — batch execution with checkpoints in this session
