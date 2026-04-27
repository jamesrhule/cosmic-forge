import { useTranslation } from "react-i18next";
import { SUPPORTED_LOCALES, type SupportedLocale } from "@/lib/i18n";

export function LocaleSwitcher({ className }: { className?: string }) {
  const { i18n } = useTranslation();
  const current = (i18n.resolvedLanguage ?? "en") as SupportedLocale;
  return (
    <select
      aria-label="Language"
      value={current}
      onChange={(e) => void i18n.changeLanguage(e.target.value)}
      className={className ?? "bg-background border border-border rounded-md px-2 py-1 text-sm"}
    >
      {SUPPORTED_LOCALES.map((lng) => (
        <option key={lng} value={lng}>
          {lng.toUpperCase()}
        </option>
      ))}
    </select>
  );
}
