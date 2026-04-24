import { useEffect, useState } from "react";
import { getProfile, type Profile } from "@/lib/profiles";
import { cn } from "@/lib/utils";

export interface AuthorBadgeProps {
  userId: string | null | undefined;
  className?: string;
  /** Hide handle, show only display name + avatar. */
  compact?: boolean;
}

/**
 * Author attribution chip for run cards. Reads `public.profiles` (cached).
 * Renders nothing for unauthored (system) runs.
 */
export function AuthorBadge({ userId, className, compact }: AuthorBadgeProps) {
  const [profile, setProfile] = useState<Profile | null>(null);

  useEffect(() => {
    let live = true;
    if (!userId) {
      setProfile(null);
      return;
    }
    void getProfile(userId).then((p) => {
      if (live) setProfile(p);
    });
    return () => {
      live = false;
    };
  }, [userId]);

  if (!userId) {
    return (
      <span
        className={cn(
          "inline-flex items-center gap-1 rounded-sm bg-muted px-1.5 py-0.5 text-[10px] uppercase tracking-wider text-muted-foreground",
          className,
        )}
      >
        catalog
      </span>
    );
  }

  const display = profile?.display_name ?? "Researcher";
  const handle = profile?.handle;
  const initial = display.slice(0, 1).toUpperCase();

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-sm bg-muted/60 px-1.5 py-0.5 text-[10px] text-muted-foreground",
        className,
      )}
      aria-label={`Authored by ${display}`}
    >
      {profile?.avatar_url ? (
        <img
          src={profile.avatar_url}
          alt=""
          className="h-3.5 w-3.5 rounded-full object-cover"
        />
      ) : (
        <span className="grid h-3.5 w-3.5 place-items-center rounded-full bg-primary/15 text-[8px] font-semibold text-primary">
          {initial}
        </span>
      )}
      <span className="font-medium text-foreground">{display}</span>
      {!compact && handle ? (
        <span className="font-mono text-muted-foreground">@{handle}</span>
      ) : null}
    </span>
  );
}
