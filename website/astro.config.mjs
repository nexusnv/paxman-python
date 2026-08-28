import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';

// https://starlight.astro.build/reference/configuration/
export default defineConfig({
  site: 'https://nexusnv.github.io',
  base: '/paxman-python/',
  // Keep content in docs/user as single source of truth — website/src/content/docs
  // is a symlink to ../../docs/user. Preserve symlinks so Vite resolves the real files.
  vite: {
    resolve: {
      preserveSymlinks: true,
    },
  },
  integrations: [
    starlight({
      title: 'Paxman',
      description: 'Canonicalization authority resolver — deterministic, provenance-first.',
      tagline: 'Canonicalization authority resolver — deterministic, provenance-first.',
      favicon: '/favicon.svg',
      social: [
        {
          icon: 'github',
          label: 'GitHub',
          href: 'https://github.com/nexusnv/paxman-python',
        },
      ],
      editLink: {
        baseUrl: 'https://github.com/nexusnv/paxman-python/edit/main/docs/user/',
      },
      lastUpdated: true,
      customCss: [],
      sidebar: [
        { label: 'Home', slug: 'index' },
        { label: 'Getting Started', slug: 'getting-started' },
        {
          label: 'Concepts',
          autogenerate: { directory: 'concepts' },
        },
        {
          label: 'Capabilities',
          autogenerate: { directory: 'capabilities' },
        },
        { label: 'API Reference', slug: 'api-reference' },
        { label: 'Extending', slug: 'extending' },
        { label: 'Migration', slug: 'migration' },
      ],
      head: [
        {
          tag: 'meta',
          attrs: { property: 'og:image', content: 'https://nexusnv.github.io/paxman-python/og.png' },
        },
      ],
      expressiveCode: true,
      // Mermaid is rendered client-side — keep ```mermaid blocks as-is;
      // they degrade to code blocks until a mermaid integration is added.
      // To enable live diagrams, add `starlight-mermaid` later.
    }),
  ],
});
