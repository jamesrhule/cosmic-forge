import { Link } from "@tanstack/react-router";
import { LogIn, LogOut, ShieldCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useAuth } from "@/lib/auth";
import { cn } from "@/lib/utils";

export interface UserMenuProps {
  className?: string;
  /** Path to redirect back to after login (defaults to current). */
  redirectPath?: string;
}

export function UserMenu({ className, redirectPath }: UserMenuProps) {
  const { user, hasRole, signOut, loading } = useAuth();

  if (loading) {
    return <div className={cn("h-7 w-16 animate-pulse rounded-md bg-muted", className)} />;
  }

  if (!user) {
    const search = redirectPath ? { redirect: redirectPath } : undefined;
    return (
      <Button asChild size="sm" variant="outline" className={cn("h-7 gap-1.5 px-2 text-xs", className)}>
        <Link to="/login" search={search as never}>
          <LogIn className="h-3.5 w-3.5" />
          Sign in
        </Link>
      </Button>
    );
  }

  const isAdmin = hasRole("admin");
  const initial = (user.email ?? "?").slice(0, 1).toUpperCase();

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button
          type="button"
          className={cn(
            "inline-flex items-center gap-1.5 rounded-md border bg-background px-1.5 py-0.5 text-xs hover:bg-muted focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring",
            className,
          )}
          aria-label={`Signed in as ${user.email}`}
        >
          <span className="grid h-5 w-5 place-items-center rounded-full bg-primary/15 text-[10px] font-semibold text-primary">
            {initial}
          </span>
          <span className="max-w-[10rem] truncate font-mono text-[11px] text-foreground">
            {user.email}
          </span>
          {isAdmin ? (
            <span className="flex items-center gap-0.5 rounded-sm bg-amber-500/15 px-1 text-[10px] font-medium text-amber-600 dark:text-amber-400">
              <ShieldCheck className="h-2.5 w-2.5" />
              admin
            </span>
          ) : null}
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-52">
        <DropdownMenuLabel className="text-xs font-normal text-muted-foreground">
          {user.email}
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuItem onSelect={() => void signOut()} className="text-xs">
          <LogOut className="mr-2 h-3.5 w-3.5" />
          Sign out
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
