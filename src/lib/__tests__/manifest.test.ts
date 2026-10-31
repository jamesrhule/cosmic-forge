import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const apiFetchMock = vi.fn();
const BackendUnavailable = class extends Error {
  constructor() {
    super("backend not configured");
    this.name = "BackendUnavailable";
  }
};

vi.mock("@/lib/apiClient", () => ({
  apiFetch: apiFetchMock,
  BackendUnavailable,
  isBackendConfigured: () => true,
}));

import {
  clearManifestCache,
  getDomainTimeline,
  getManifest,
} from "@/services/manifest";
import type { VisualizationManifest } from "@/types/manifest";

const manifest: VisualizationManifest = {
  run_id: "chem-1",
  domain: "chemistry",
  frame_count: 60,
  formula_variant: null,
  bake_uri: null,
  metadata: { synthetic: true },
};

describe("manifest service", () => {
  beforeEach(() => {
    apiFetchMock.mockReset();
    localStorage.clear();
  });

  afterEach(() => {
    clearManifestCache();
  });

  it("hits the API the first time and caches the result", async () => {
    apiFetchMock.mockResolvedValueOnce(manifest);

    const a = await getManifest("chemistry", "chem-1");
    const b = await getManifest("chemistry", "chem-1");

    expect(a).toEqual(manifest);
    expect(b).toEqual(manifest);
    expect(apiFetchMock).toHaveBeenCalledTimes(1);
  });

  it("returns a synthetic stand-in when backend is unavailable", async () => {
    apiFetchMock.mockRejectedValueOnce(new BackendUnavailable());

    const m = await getManifest("hep", "hep-fallback");

    expect(m.domain).toBe("hep");
    expect(m.run_id).toBe("hep-fallback");
    expect(m.metadata.synthetic).toBe(true);
  });

  it("clearManifestCache evicts cached manifests", async () => {
    apiFetchMock.mockResolvedValue(manifest);

    await getManifest("chemistry", "chem-1");
    clearManifestCache();
    await getManifest("chemistry", "chem-1");

    expect(apiFetchMock).toHaveBeenCalledTimes(2);
  });

  it("getDomainTimeline returns empty frames on BackendUnavailable", async () => {
    apiFetchMock.mockRejectedValueOnce(new BackendUnavailable());
    apiFetchMock.mockRejectedValueOnce(new BackendUnavailable());

    const r = await getDomainTimeline("chemistry", "no-backend");
    expect(r.frames).toEqual([]);
    expect(r.manifest.run_id).toBe("no-backend");
  });
});
