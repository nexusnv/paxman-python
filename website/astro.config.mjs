import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';
import rehypeMermaid from 'rehype-mermaid';

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
  markdown: {
    rehypePlugins: [
      [
        rehypeMermaid,
        {
          strategy: 'img-svg',
          dark: true,
          mermaidConfig: {
            theme: 'base',
            themeVariables: { primaryColor: '#4f46e5' },
          },
        },
      ],
    ],
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
    }),
  ],
});
