import * as sdk from "@qcompass/frontend-sdk";
import { loadFixture, loadJsonlFixture, sleep } from "@/lib/fixtures";
import { api, apiStream, usesApi } from "@/lib/sdk";
import { ModelDescriptorListShape } from "@/lib/fixtureSchemas";
import {
  ServiceError,
  type AssistantEvent,
  type ChatMessage,
  type InstallEvent,
  type ModelDescriptor,
  type ModelStatus,
  type ToolName,
} from "@/types/domain";

/**
 * Send a chat message to the assistant and stream back token deltas,
 * tool calls, tool results, and the final completed message.
 *
 * @endpoint SSE POST /v1/chat
 */
export async function* sendMessage(params: {
  conversationId: string;
  messages: ChatMessage[];
  modelId: string;
  runContext?: { runId?: string; selection?: string };
  /** Optional cancel — caller aborts when the chat drawer closes. */
  signal?: AbortSignal;
}): AsyncIterable<AssistantEvent> {
  if (usesApi()) {
    // ChatRequest (generated from the API's OpenAPI document).
    const body: sdk.JsonRequest<"/v1/chat", "post"> = {
      conversationId: params.conversationId,
      messages: params.messages as unknown as sdk.Schemas["ChatMessage"][],
      modelId: params.modelId,
      runContext: params.runContext ?? null,
    };
    for await (const ev of apiStream((c) => sdk.chat(c, body, params.signal))) {
      if (ev.event === "done" || ev.event === "end") return;
      yield ev.data as AssistantEvent;
    }
    return;
  }

  const lastUser = [...params.messages].reverse().find((m) => m.role === "user");
  const transcript = pickTranscript(lastUser?.content ?? "");
  yield* loadJsonlFixture<AssistantEvent>(
    `chat/transcripts/${transcript}.jsonl`,
    80,
    params.signal,
  );
}

const TRANSCRIPT_KEYWORDS: Array<{ keywords: string[]; transcript: ToolName }> = [
  { keywords: ["compare", "diff"], transcript: "compare_runs" },
  { keywords: ["start", "run a", "kick off"], transcript: "start_run" },
  { keywords: ["benchmark", "v2", "v3"], transcript: "open_benchmark" },
  { keywords: ["audit", "summarize"], transcript: "summarize_audit" },
  { keywords: ["suggest", "next"], transcript: "suggest_parameters" },
  { keywords: ["report", "export"], transcript: "export_report" },
  { keywords: ["cite", "bibtex"], transcript: "cite_paper" },
  { keywords: ["overlay", "plot"], transcript: "plot_overlay" },
];

function pickTranscript(text: string): ToolName {
  const t = text.toLowerCase();
  for (const entry of TRANSCRIPT_KEYWORDS) {
    if (entry.keywords.some((k) => t.includes(k))) return entry.transcript;
  }
  return "load_run";
}

/**
 * List every model the assistant could route to (local + remote).
 *
 * @endpoint GET /api/models
 */
export async function listModels(): Promise<ModelDescriptor[]> {
  if (usesApi()) {
    return (await api((c) => sdk.listModels(c))) as unknown as ModelDescriptor[];
  }
  return loadFixture<ModelDescriptor[]>("models.json", {
    validate: (raw) => ModelDescriptorListShape.parse(raw) as unknown as ModelDescriptor[],
  });
}

/**
 * Install a local model. Streams progress events; the final event is
 * either `ready` or `error`.
 *
 * @endpoint SSE POST /api/models/{modelId}/install
 */
export async function* installModel(modelId: string): AsyncIterable<InstallEvent> {
  if (usesApi()) {
    for await (const ev of apiStream((c) => sdk.installModel(c, modelId))) {
      if (ev.event === "done" || ev.event === "end") return;
      yield ev.data as InstallEvent;
    }
    return;
  }
  yield* loadJsonlFixture<InstallEvent>("events/install-llama-8b.jsonl", 250);
}

/**
 * Uninstall a previously installed local model.
 *
 * @endpoint DELETE /api/models/{modelId}
 */
export async function uninstallModel(modelId: string): Promise<void> {
  if (usesApi()) {
    await api((c) => sdk.uninstallModel(c, modelId));
    return;
  }
  await sleep(300);
}

/**
 * Get the install status of a single model.
 *
 * @endpoint GET /api/models/{modelId}/status
 */
export async function getModelStatus(modelId: string): Promise<ModelStatus> {
  if (!modelId) {
    throw new ServiceError("INVALID_INPUT", "modelId is required");
  }
  if (usesApi()) {
    return (await api((c) => sdk.getModelStatus(c, modelId))) as unknown as ModelStatus;
  }
  // Fixture: every recommended model in the catalog is reported "ready"
  // so the UI can be exercised end-to-end without an actual install run.
  const recommended = new Set([
    "llama-3.1-8b-instruct-q4",
    "qwen2.5-14b-instruct-q4",
    "mistral-7b-instruct-q5",
  ]);
  if (recommended.has(modelId)) {
    return {
      state: "ready",
      installedAt: "2025-03-04T11:20:00Z",
      diskBytes: 4_780_000_000,
    };
  }
  return { state: "not_installed" };
}
