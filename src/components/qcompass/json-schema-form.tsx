import {
  type ChangeEvent,
  type FormEvent,
  useEffect,
  useMemo,
  useState,
} from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import type { JsonSchema } from "@/types/qcompass";

/**
 * Generic JSON-Schema → form renderer.
 *
 * Drives every domain manifest form. Per-domain customisation is
 * the JSON Schema itself (loaded by `getManifestSchema(domain)`); we
 * never hand-build a separate form per domain.
 *
 * Supported subset (sufficient for ChemistryProblem):
 *   - `type: "string"` with optional `enum` → <Select>
 *   - `type: "string"` (free) → <Input>
 *   - `type: "integer"` → <Input type="number" step="1">
 *   - `type: "number"` → <Input type="number" step="any">
 *   - `anyOf: [<typed>, {type: "null"}]` → optional variant of the typed form
 *   - `type: "array"` with `prefixItems: [int, int]` → tuple of two integer inputs
 *   - long strings (geometry) → <Textarea>
 *
 * Anything outside this subset renders as a typed JSON textarea so
 * the form NEVER silently drops fields.
 */
export interface JsonSchemaFormProps<T = Record<string, unknown>> {
  schema: JsonSchema;
  defaultValues?: Partial<T>;
  onSubmit: (values: T) => void;
  submitLabel?: string;
  isSubmitting?: boolean;
}

export function JsonSchemaForm<T = Record<string, unknown>>({
  schema,
  defaultValues,
  onSubmit,
  submitLabel = "Submit",
  isSubmitting = false,
}: JsonSchemaFormProps<T>) {
  const properties = useMemo(
    () => Object.entries(schema.properties ?? {}),
    [schema],
  );
  const initial = useMemo(
    () => buildInitialState(schema, defaultValues),
    [schema, defaultValues],
  );
  const [values, setValues] = useState<Record<string, unknown>>(initial);
  const [errors, setErrors] = useState<Record<string, string>>({});

  useEffect(() => {
    setValues(initial);
  }, [initial]);

  const handleChange = (name: string, next: unknown) => {
    setValues((prev) => ({ ...prev, [name]: next }));
  };

  const submit = (e: FormEvent) => {
    e.preventDefault();
    const validation = validate(schema, values);
    setErrors(validation);
    if (Object.keys(validation).length === 0) {
      onSubmit(values as T);
    }
  };

  return (
    <form onSubmit={submit} className="space-y-4">
      <div className="grid gap-4 md:grid-cols-2">
        {properties.map(([name, prop]) => (
          <Field
            key={name}
            name={name}
            schema={prop}
            value={values[name]}
            error={errors[name]}
            required={(schema.required ?? []).includes(name)}
            onChange={(next) => handleChange(name, next)}
          />
        ))}
      </div>
      <div className="flex items-center justify-end gap-2 pt-2">
        <Button type="submit" disabled={isSubmitting}>
          {isSubmitting ? "Submitting…" : submitLabel}
        </Button>
      </div>
    </form>
  );
}

interface FieldProps {
  name: string;
  schema: JsonSchema;
  value: unknown;
  error?: string;
  required: boolean;
  onChange: (next: unknown) => void;
}

function Field({ name, schema, value, error, required, onChange }: FieldProps) {
  const title = schema.title ?? humanise(name);
  const description = schema.description ?? "";
  const id = `qcf-${name}`;

  return (
    <div className="flex flex-col gap-1">
      <Label htmlFor={id}>
        {title}
        {required && (
          <span className="ml-1 text-[color:var(--accent-indigo)]">*</span>
        )}
      </Label>
      {renderInput(id, schema, value, onChange)}
      {description && (
        <p className="text-xs text-muted-foreground">{description}</p>
      )}
      {error && <p className="text-xs text-destructive">{error}</p>}
    </div>
  );
}

function renderInput(
  id: string,
  schema: JsonSchema,
  value: unknown,
  onChange: (next: unknown) => void,
) {
  const innerSchema = unwrapNullable(schema);
  const type = pickType(innerSchema);
  const enumValues = innerSchema.enum;

  if (enumValues) {
    return (
      <Select
        value={value === null || value === undefined ? "" : String(value)}
        onValueChange={(next) =>
          onChange(next === "" ? null : coerceEnum(next, innerSchema))
        }
      >
        <SelectTrigger id={id} className="font-mono text-sm">
          <SelectValue placeholder="—" />
        </SelectTrigger>
        <SelectContent>
          {enumValues.map((v) => (
            <SelectItem key={String(v)} value={String(v)}>
              {String(v)}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    );
  }

  if (type === "integer" || type === "number") {
    const step = type === "integer" ? 1 : "any";
    return (
      <Input
        id={id}
        type="number"
        step={step}
        value={value === null || value === undefined ? "" : String(value)}
        onChange={(e: ChangeEvent<HTMLInputElement>) => {
          const raw = e.target.value;
          if (raw === "") {
            onChange(null);
          } else {
            const parsed = type === "integer" ? Number.parseInt(raw, 10) : Number(raw);
            onChange(Number.isFinite(parsed) ? parsed : null);
          }
        }}
        className="font-mono text-sm"
      />
    );
  }

  if (type === "string") {
    const isLong =
      schema.format === "textarea" ||
      String(schema.title ?? "").toLowerCase().includes("geometry");
    if (isLong) {
      return (
        <Textarea
          id={id}
          value={value === null || value === undefined ? "" : String(value)}
          onChange={(e) => onChange(e.target.value === "" ? null : e.target.value)}
          rows={3}
          className="font-mono text-sm"
        />
      );
    }
    return (
      <Input
        id={id}
        type="text"
        value={value === null || value === undefined ? "" : String(value)}
        onChange={(e) => onChange(e.target.value === "" ? null : e.target.value)}
        className="font-mono text-sm"
      />
    );
  }

  if (type === "array" && innerSchema.prefixItems) {
    const tuple = Array.isArray(value) ? value : [null, null];
    const [a, b] = tuple as [unknown, unknown];
    return (
      <div className="flex items-center gap-2">
        <Input
          id={`${id}-0`}
          type="number"
          step={1}
          value={a === null || a === undefined ? "" : String(a)}
          onChange={(e) => {
            const v = e.target.value === "" ? null : Number.parseInt(e.target.value, 10);
            onChange([v, b]);
          }}
          className="font-mono text-sm"
        />
        <span className="text-xs text-muted-foreground">×</span>
        <Input
          id={`${id}-1`}
          type="number"
          step={1}
          value={b === null || b === undefined ? "" : String(b)}
          onChange={(e) => {
            const v = e.target.value === "" ? null : Number.parseInt(e.target.value, 10);
            onChange([a, v]);
          }}
          className="font-mono text-sm"
        />
      </div>
    );
  }

  // Fallback — render as JSON so no field is silently dropped.
  return (
    <Textarea
      id={id}
      value={value === undefined ? "" : JSON.stringify(value)}
      onChange={(e) => {
        try {
          onChange(e.target.value === "" ? null : JSON.parse(e.target.value));
        } catch {
          onChange(e.target.value);
        }
      }}
      rows={2}
      className="font-mono text-xs"
    />
  );
}

/* ──────────────────────── helpers ──────────────────────── */

function unwrapNullable(schema: JsonSchema): JsonSchema {
  if (schema.anyOf && schema.anyOf.length > 0) {
    const nonNull = schema.anyOf.find((s) => s.type !== "null");
    if (nonNull) {
      return { ...schema, ...nonNull };
    }
  }
  return schema;
}

function pickType(schema: JsonSchema): string | undefined {
  if (Array.isArray(schema.type)) {
    return schema.type.find((t) => t !== "null");
  }
  return schema.type;
}

function coerceEnum(raw: string, schema: JsonSchema): unknown {
  const numeric = schema.enum?.every((v) => typeof v === "number");
  if (numeric) {
    const parsed = Number(raw);
    return Number.isFinite(parsed) ? parsed : raw;
  }
  return raw;
}

function buildInitialState(
  schema: JsonSchema,
  overrides: Partial<unknown> | undefined,
): Record<string, unknown> {
  const init: Record<string, unknown> = {};
  for (const [name, prop] of Object.entries(schema.properties ?? {})) {
    if (overrides && (overrides as Record<string, unknown>)[name] !== undefined) {
      init[name] = (overrides as Record<string, unknown>)[name];
      continue;
    }
    init[name] = prop.default ?? null;
  }
  return init;
}

function validate(
  schema: JsonSchema,
  values: Record<string, unknown>,
): Record<string, string> {
  const errors: Record<string, string> = {};
  for (const required of schema.required ?? []) {
    const v = values[required];
    if (v === null || v === undefined || v === "") {
      errors[required] = "Required.";
    }
  }
  return errors;
}

function humanise(name: string): string {
  return name
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}
