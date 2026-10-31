/**
 * robots.txt and sitemap.xml, rendered per request so every URL is absolute
 * (the sitemap protocol and robots.txt `Sitemap:` require absolute URLs, and
 * the production origin isn't known at build time). Served by
 * `src/routes/robots[.]txt.ts` and `src/routes/sitemap[.]xml.ts`.
 */

export interface SitemapEntry {
  path: string;
  changefreq: string;
  priority: string;
}

export const SITEMAP_ENTRIES: SitemapEntry[] = [
  { path: "/", changefreq: "weekly", priority: "1.0" },
  { path: "/visualizer", changefreq: "weekly", priority: "0.8" },
  { path: "/visualizer/kawai-kim-natural", changefreq: "monthly", priority: "0.6" },
  { path: "/visualizer/starobinsky-standard", changefreq: "monthly", priority: "0.6" },
  { path: "/visualizer/gb-off-control", changefreq: "monthly", priority: "0.6" },
  { path: "/visualizer/f2-nieh-yan-demo", changefreq: "monthly", priority: "0.6" },
  { path: "/visualizer/f3-large-N-demo", changefreq: "monthly", priority: "0.6" },
  { path: "/visualizer/f5-resonance-demo", changefreq: "monthly", priority: "0.6" },
  { path: "/visualizer/f7-stacked-demo", changefreq: "monthly", priority: "0.6" },
];

/** Paths crawlers must not index (internal tools, APIs, auth callbacks). */
export const DISALLOWED_PATHS = ["/qa", "/api/", "/auth/", "/reset-password"];

export function renderRobots(origin: string): string {
  return [
    "User-agent: *",
    "Allow: /",
    "Allow: /visualizer",
    "Allow: /visualizer/*",
    ...DISALLOWED_PATHS.map((p) => `Disallow: ${p}`),
    "",
    `Sitemap: ${origin}/sitemap.xml`,
    "",
  ].join("\n");
}

const xmlEscape = (s: string) =>
  s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");

export function renderSitemap(origin: string): string {
  const urls = SITEMAP_ENTRIES.map(
    (e) =>
      `  <url>\n    <loc>${xmlEscape(origin + e.path)}</loc>\n` +
      `    <changefreq>${e.changefreq}</changefreq>\n    <priority>${e.priority}</priority>\n  </url>`,
  ).join("\n");
  return `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${urls}\n</urlset>\n`;
}
