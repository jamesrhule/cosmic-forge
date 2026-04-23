import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/** Format a byte count as e.g. "3.21 GB". */
export function formatBytes(bytes: number, fractionDigits = 2): string {
  if (!Number.isFinite(bytes) || bytes <= 0) return "0 B";
  const units = ["B", "KB", "MB", "GB", "TB"];
  const i = Math.min(units.length - 1, Math.floor(Math.log10(bytes) / 3));
  const value = bytes / 10 ** (i * 3);
  return `${value.toFixed(fractionDigits)} ${units[i]}`;
}

/** Format a number in scientific notation with a fixed number of sig figs. */
export function formatSci(value: number, sig = 3): string {
  if (!Number.isFinite(value)) return String(value);
  if (value === 0) return "0";
  const exp = Math.floor(Math.log10(Math.abs(value)));
  const mantissa = value / 10 ** exp;
  return `${mantissa.toFixed(sig - 1)}\u00d710${superscript(exp)}`;
}

const SUP_DIGITS: Record<string, string> = {
  "0": "⁰",
  "1": "¹",
  "2": "²",
  "3": "³",
  "4": "⁴",
  "5": "⁵",
  "6": "⁶",
  "7": "⁷",
  "8": "⁸",
  "9": "⁹",
  "-": "⁻",
};

function superscript(n: number): string {
  return String(n)
    .split("")
    .map((c) => SUP_DIGITS[c] ?? c)
    .join("");
}

export function shortId(id: string, len = 8): string {
  return id.length > len ? id.slice(0, len) : id;
}
