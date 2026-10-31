import { createFileRoute } from "@tanstack/react-router";
import { renderRobots } from "@/lib/seo";

export const Route = createFileRoute("/robots.txt")({
  server: {
    handlers: {
      GET: ({ request }) =>
        new Response(renderRobots(new URL(request.url).origin), {
          headers: {
            "Content-Type": "text/plain; charset=utf-8",
            "Cache-Control": "public, max-age=3600",
          },
        }),
    },
  },
});
