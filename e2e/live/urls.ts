/** The live stack's two servers (P4-02): scripts/live_stack.py and scripts/e2e_live_serve.sh. */
export const LIVE_API_URL = `http://127.0.0.1:${process.env.LIVE_API_PORT ?? "8791"}`;
export const LIVE_WEB_URL = `http://127.0.0.1:${process.env.LIVE_WEB_PORT ?? "4312"}`;
