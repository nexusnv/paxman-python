# Paxman Docs — Astro Starlight

User documentation lives in `../docs/user` (single source of truth, Markdown with frontmatter).  
This `docs_site/` folder is the Astro Starlight site that builds those files and deploys to GitHub Pages at https://nexusnv.github.io/paxman-python/ .

## Local development

```bash
cd docs_site
npm ci            # install deps (Node 22+)
npm run dev       # http://localhost:4321/paxman-python/
npm run build     # outputs to docs_site/dist/
npm run preview   # preview built site
```

Content is consumed via a symlink `docs_site/src/content/docs -> ../../../docs/user` (preserved with `vite.resolve.preserveSymlinks`). Edit Markdown in `docs/user/*.md` — changes appear live in `npm run dev`.

## Publishing

### Versioned deploys — `docs_site/versions.json` is the source of truth

`docs_site/versions.json` (D3):

```json
{
  "versions": [],
  "latest": {"slug": "latest", "label": "latest", "source_ref": "dev"}
}
```

- `versions` — pinned immutable releases (`/vX.Y.Z/`), each entry `{slug, tag}` checked out at that git tag for its build. Starts empty (D3a): tags `v0.1.0`–`v0.2.2` predate versioned docs (they lack the `docs_site/` layout) and are not retro-built — they were never published at `/vX/` so no back-compat break (a follow-up could retro-build pre-rename tags, out of scope).
- `latest` — always the current `main`/`dev` build (`/latest/`). `stable` is a generated redirect to the last pinned slug, not a build (D4).

### Deploy recipe — `.github/workflows/docs.yml` (D2/D4/D5)

Push to `main` or `dev`, or push of a tag `v*.*.*`, rebuilds the **full** versioned site via `actions/deploy-pages@v4` (`build_type: workflow`, `https://nexusnv.github.io/paxman-python/`):

1. `read-versions` — checks out `docs_site/versions.json` from `main` on tag pushes (D3b), parses `versions[]` with `jq` into `pairs`/`count`/`last_slug`; on tag pushes also appends `github.ref_name` if absent.
2. `build-latest` — checks out `main` on tag pushes so `latest/` is semantically exact (tag content goes only to `/vX.Y.Z/`), `npm ci && npm run build` in `docs_site/` → `pages-latest` artifact. On PRs also uploads `site` preview artifact — no Pages deploy.
3. `build-versions` — matrix over `pairs` (skipped when `count == 0`, D3a); each entry checks out its `tag`, `npm ci && npm run build` → `pages-<slug>` artifact. No `npm` cache per tag (each tag has its own lockfile).
4. `merge-and-redirect` — assembles `site/latest/` + `site/<slug>/` for every pinned version, generates `site/index.html` → `meta refresh` to `./latest/` (D4) and, when `last_slug` is non-empty, `site/stable/index.html` → `../<last-slug>/`; uploads via `actions/upload-pages-artifact@v3`.
5. `deploy` — `actions/deploy-pages@v4` (guard `main || dev || tags/v*`).

All pushes ship the complete set, so no prior version is ever clobbered.

### How to cut a new version (D3b)

1. Open a PR **targeting `main`** that appends the new version to `docs_site/versions.json`:

   ```json
   { "slug": "vX.Y.Z", "tag": "vX.Y.Z" }
   ```

   Merge it to `main`.
2. Tag the release: `git tag -a vX.Y.Z -m "paxman vX.Y.Z"` and `git push origin vX.Y.Z`.

The tag push reads the maintained `versions.json` from `main` (so it already lists the new tag) and belt-and-braces appends `github.ref_name`; the workflow then builds `latest/` from `main` plus every pinned `vX.Y.Z/` and redeploys the full artifact — the new version appears at `/vX.Y.Z/` on that single tag run.

### Version switcher (starlight-versions@0.10.1)

`docs_site/astro.config.mjs` wires `starlight-versions` as a Starlight plugin conditionally:

```js
plugins: versionsConfig.versions.length
  ? [starlightVersions({ versions: versionsConfig.versions, current: { label: versionsConfig.latest.label } })]
  : []
```

With the pinned set initially empty (D3a) the switcher shows only `latest`. After the first `vX.Y.Z` entry is merged, the switcher appears in every build: `latest` (dev) plus each pinned `/vX.Y.Z/` with the plugin's "outdated" banner. `editLink.baseUrl` stays `https://github.com/nexusnv/paxman-python/edit/main/docs/user/` — `latest` edits land on `main`; pinned versions are immutable tag snapshots, so an `editLink` that points at `main` is acceptable.

### Back-compat and redirects (D4)

- `https://nexusnv.github.io/paxman-python/` (`site/index.html`) → `meta refresh` to `./latest/` — preserves root bookmark.
- `https://nexusnv.github.io/paxman-python/stable/` → `../<last-pinned>/` (only generated after the first tagged release).
- `https://nexusnv.github.io/paxman-python/latest/…` deep links are preserved; each pinned `site/vX.Y.Z/` is a full copy of that tag's built site, so old deep links (e.g. `/v0.3.0/capabilities/email/`) remain valid per version.

GitHub Pages is configured (`build_type: workflow`, `https://nexusnv.github.io/paxman-python/`).  
If you change `site`/`base` in `astro.config.mjs`, update the Pages URL accordingly.

## Markdown conventions (Starlight)

- Frontmatter required: `---\ntitle: "..."\n---` — first `# H1` was removed when migrating from MkDocs (title now comes from frontmatter).
- Admonitions: `:::note[Title]` / `:::tip` / `:::caution` / `:::danger` ... `:::` (MkDocs `!!!` converted).
- Tabs: `=== "label"` converted to `### label` headings (Starlight `<Tabs>` needs MDX — use plain headings unless MDX is needed).
- ` ```mermaid` blocks render as code via Expressive Code until a mermaid integration is added.
- Links to `../recipes/segmentation.md` or `../../README.md` (outside `docs/user`) were replaced with `https://github.com/nexusnv/paxman-python/...` URLs — Starlight content is isolated to `docs/user`.

## Why not MkDocs / Read the Docs?

MkDocs 2.0 introduces backward-incompatible, unlicensed changes (see https://squidfunk.github.io/mkdocs-material/blog/2026/02/18/mkdocs-2.0/ ). The project now builds only on GitHub Pages via Astro Starlight (Python `pyproject.toml` no longer has a `[dependency-groups].docs`).
