/**
 * QCompass — Manifest form (rjsf wrapper).
 * @example <QcompassManifestForm domain="hep.lattice" onSubmit={...} />
 */
import { useEffect, useState } from "react";
import Form from "@rjsf/core";
import validator from "@rjsf/validator-ajv8";
import type { JSONSchema7 } from "json-schema";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { getManifestSchema } from "@/services/qcompass/manifestSchema";
import type { DomainId } from "@/lib/domains/types";

export function QcompassManifestForm({
  domain,
  onSubmit,
}: {
  domain: DomainId;
  onSubmit?: (data: Record<string, unknown>) => void;
}) {
  const [schema, setSchema] = useState<JSONSchema7 | null>(null);
  const [formData, setFormData] = useState<Record<string, unknown>>({});

  useEffect(() => {
    getManifestSchema(domain).then(setSchema).catch(() => setSchema(null));
  }, [domain]);

  if (!schema) {
    return <p className="text-xs text-muted-foreground">Loading manifest schema…</p>;
  }

  return (
    <Card className="p-4">
      <Form
        schema={schema}
        validator={validator}
        formData={formData}
        onChange={(e) => setFormData(e.formData as Record<string, unknown>)}
        onSubmit={(e) => onSubmit?.(e.formData as Record<string, unknown>)}
      >
        <div className="mt-4 flex justify-end gap-2">
          <Button type="button" variant="outline" onClick={() => setFormData({})}>
            Reset
          </Button>
          <Button type="submit">Submit</Button>
        </div>
      </Form>
    </Card>
  );
}
