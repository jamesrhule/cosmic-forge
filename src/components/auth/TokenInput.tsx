/**
 * QCompass — Bearer token input dialog (scaffolding).
 * @example <TokenInput open={open} onOpenChange={setOpen} />
 */
import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { useAuth } from "@/store/auth";

export interface TokenInputProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function TokenInput({ open, onOpenChange }: TokenInputProps) {
  const setToken = useAuth((s) => s.setToken);
  const current = useAuth((s) => s.token);
  const [value, setValue] = useState(current ?? "");
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>QCompass bearer token</DialogTitle>
          <DialogDescription>
            Paste a backend-issued token. Stored in memory only — refresh
            wipes it.
          </DialogDescription>
        </DialogHeader>
        <Textarea
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder="eyJ…"
          rows={4}
          className="font-mono text-xs"
        />
        <DialogFooter>
          <Button variant="ghost" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            onClick={() => {
              setToken(value.trim() || null);
              onOpenChange(false);
            }}
          >
            Save
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
