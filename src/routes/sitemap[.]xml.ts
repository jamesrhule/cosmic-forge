import { createFileRoute } from "@tanstack/react-router";
import { renderSitemap } from "@/lib/seo";

export const Route = createFileRoute("/sitemap.xml")({
  server: {
    handlers: {
      GET: ({ request }) =>
        new Response(renderSitemap(new URL(request.url).origin), {
          headers: {
            "Content-Type": "application/xml; charset=utf-8",
            "Cache-Control": "public, max-age=3600",
          },
        }),
    },
  },
});
