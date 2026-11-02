import { useEffect, useState } from "react";

/** True when the browser can create a WebGL context (client only). */
export function detectWebGL(): boolean {
  if (typeof window === "undefined") return false;
  try {
    const c = document.createElement("canvas");
    return Boolean(
      c.getContext("webgl2") || c.getContext("webgl") || c.getContext("experimental-webgl"),
    );
  } catch {
    return false;
  }
}

/**
 * `null` until checked on the client, then whether WebGL is available.
 * Panels render their R3F `<Canvas>` only when this is `true`: three.js
 * throws "Error creating WebGL context" otherwise (headless browsers,
 * disabled GPU, locked-down machines).
 */
export function useWebGLAvailable(): boolean | null {
  const [ok, setOk] = useState<boolean | null>(null);
  useEffect(() => {
    setOk(detectWebGL());
  }, []);
  return ok;
}
