# Paxman Docs — Astro Starlight

User documentation lives in `../docs/user` (single source of truth, Markdown with frontmatter).  
This `website/` folder is the Astro Starlight site that builds those files and deploys to GitHub Pages at https://nexusnv.github.io/paxman-python/ .

## Local development

```bash
cd website
npm ci            # install deps (Node 22+)
npm run dev       # http://localhost:4321/paxman-python/
npm run build     # outputs to website/dist/
npm run preview   # preview built site
```

Content is consumed via a symlink `website/src/content/docs -> ../../../docs/user` (preserved with `vite.resolve.preserveSymlinks`). Edit Markdown in `docs/user/*.md` — changes appear live in `npm run dev`.

## Publishing

Push to `main` triggers `.github/workflows/docs.yml`:

1. `npm ci && npm run build` in `website/` → `website/dist/`
2. `actions/upload-pages-artifact@v3` with `path: website/dist/`
3. `actions/deploy-pages@v4` (environment `github-pages`)

PRs upload `website/dist/` as a normal artifact (`site`) for preview — no Pages deploy.

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
