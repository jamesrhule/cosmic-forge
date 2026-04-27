import { createFileRoute, Link } from "@tanstack/react-router";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { PLAN_LIMITS, type SubscriptionTier } from "@/lib/billing";
import { Check, X } from "lucide-react";

export const Route = createFileRoute("/pricing")({
  head: () => ({
    meta: [
      { title: "Pricing · UCGLE-F1 Workbench" },
      {
        name: "description",
        content: "Free, Pro, Team and Enterprise plans for the UCGLE-F1 simulation workbench.",
      },
      { property: "og:title", content: "Pricing · UCGLE-F1 Workbench" },
      {
        property: "og:description",
        content: "Plans that scale with your simulation budget — from free exploratory runs to enterprise GPU pools.",
      },
    ],
  }),
  component: PricingPage,
});

const TIERS: { id: SubscriptionTier; price: string; tagline: string }[] = [
  { id: "free", price: "$0", tagline: "Explore the workbench" },
  { id: "pro", price: "$29/mo", tagline: "For working researchers" },
  { id: "team", price: "$99/mo", tagline: "For small collaborations" },
  { id: "enterprise", price: "Contact us", tagline: "Dedicated GPU pools + SSO" },
];

function fmt(n: number) {
  return Number.isFinite(n) ? n.toLocaleString() : "Unlimited";
}

function PricingPage() {
  return (
    <div className="mx-auto max-w-6xl px-4 py-16">
      <header className="text-center mb-12">
        <h1 className="text-4xl font-semibold tracking-tight">Pricing</h1>
        <p className="text-muted-foreground mt-3 max-w-xl mx-auto">
          Plans that scale with your simulation budget. Upgrade or cancel anytime.
        </p>
      </header>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {TIERS.map((t) => {
          const limits = PLAN_LIMITS[t.id];
          return (
            <Card key={t.id} className="flex flex-col">
              <CardHeader>
                <CardTitle className="capitalize">{t.id}</CardTitle>
                <p className="text-2xl font-semibold mt-2">{t.price}</p>
                <p className="text-sm text-muted-foreground">{t.tagline}</p>
              </CardHeader>
              <CardContent className="flex-1 flex flex-col">
                <ul className="space-y-2 text-sm flex-1">
                  <li>{fmt(limits.maxRunsPerMonth)} runs/month</li>
                  <li>{fmt(limits.maxConcurrentJobs)} concurrent jobs</li>
                  <li>{(limits.maxTimelineBytes / (1024 * 1024)).toFixed(0)} MB timeline cap</li>
                  <li className="flex items-center gap-2">
                    {limits.gpuAccess ? <Check className="size-4 text-primary" /> : <X className="size-4 text-muted-foreground" />}
                    GPU access
                  </li>
                  <li className="flex items-center gap-2">
                    {limits.prioritySupport ? <Check className="size-4 text-primary" /> : <X className="size-4 text-muted-foreground" />}
                    Priority support
                  </li>
                </ul>
                <Button asChild className="mt-6 w-full" variant={t.id === "pro" ? "default" : "secondary"}>
                  <Link to="/login">Get started</Link>
                </Button>
              </CardContent>
            </Card>
          );
        })}
      </div>
      <p className="text-center text-xs text-muted-foreground mt-10">
        Billing is in private preview — checkout is not yet wired. Contact us for early access.
      </p>
    </div>
  );
}
