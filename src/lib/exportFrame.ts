/**
 * Tiny dependency-free PNG export helpers used by the visualizer's
 * `Export frame` action. We deliberately avoid pulling in `dom-to-image`
 * or `html2canvas` — the visualizer already costs ~600KB for Three.js.
 *
 * Two surfaces:
 *   - `exportCanvasPng(canvas)` for the R3F WebGL canvas (uses native
 *     `toBlob`).
 *   - `exportSvgPng(svg, { width, height, background })` for the 2D
 *     panels (Recharts, Sankey). Serialises the SVG, draws it onto an
 *     offscreen 2D canvas, then `toBlob`s the result.
 *
 * Both return a Promise<Blob>. The caller is responsible for wiring
 * the blob to a download anchor (kept out of this module so it can be
 * reused by the assistant tool dispatch in the future).
 */

export async function exportCanvasPng(canvas: HTMLCanvasElement): Promise<Blob> {
  return await new Promise<Blob>((resolve, reject) => {
    canvas.toBlob(
      (blob) => (blob ? resolve(blob) : reject(new Error("toBlob returned null"))),
      "image/png",
    );
  });
}

export interface ExportSvgPngOptions {
  width: number;
  height: number;
  /** CSS color drawn before the SVG. Defaults to transparent. */
  background?: string;
  /** devicePixelRatio scale-up. Defaults to 2. */
  scale?: number;
}

export async function exportSvgPng(svg: SVGSVGElement, opts: ExportSvgPngOptions): Promise<Blob> {
  const scale = opts.scale ?? 2;
  const w = Math.max(1, Math.round(opts.width * scale));
  const h = Math.max(1, Math.round(opts.height * scale));

  const xml = new XMLSerializer().serializeToString(svg);
  // Inline the namespace — `XMLSerializer` may omit it for inline SVGs.
  const withNs = xml.includes("xmlns=")
    ? xml
    : xml.replace("<svg", '<svg xmlns="http://www.w3.org/2000/svg"');
  const url = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(withNs)}`;

  const img = new Image();
  img.crossOrigin = "anonymous";
  await new Promise<void>((resolve, reject) => {
    img.onload = () => resolve();
    img.onerror = () => reject(new Error("Failed to rasterise SVG"));
    img.src = url;
  });

  const canvas = document.createElement("canvas");
  canvas.width = w;
  canvas.height = h;
  const ctx = canvas.getContext("2d");
  if (!ctx) throw new Error("2D canvas context unavailable");
  if (opts.background) {
    ctx.fillStyle = opts.background;
    ctx.fillRect(0, 0, w, h);
  }
  ctx.drawImage(img, 0, 0, w, h);

  return await new Promise<Blob>((resolve, reject) => {
    canvas.toBlob(
      (blob) => (blob ? resolve(blob) : reject(new Error("toBlob returned null"))),
      "image/png",
    );
  });
}

/** Convenience: trigger a browser download for a Blob. */
export function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
