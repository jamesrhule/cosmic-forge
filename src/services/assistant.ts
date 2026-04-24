import { FEATURES } from "@/config/features";
import { loadFixture, loadJsonlFixture, sleep } from "@/lib/fixtures";
import { apiFetch, apiSse, isBackendConfigured } from "@/lib/apiClient";
import { trackError } from "@/lib/telemetry";
import { notifyLiveFallback } from "@/lib/serviceErrors";
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
 * Backend: SSE POST /v1/chat
 */
export async function* sendMessage(params: {
  conversationId: string;
  messages: ChatMessage[];
  modelId: string;
  runContext?: { runId?: string; selection?: string };
  /** Optional cancel — caller aborts when the chat drawer closes. */
  signal?: AbortSignal;
}): AsyncIterable<AssistantEvent> {
  if (FEATURES.liveBackend && isBackendConfigured()) {
    try {
      yield* apiSse<AssistantEvent>("/v1/chat", {
        method: "POST",
        body: {
          conversation_id: params.conversationId,
          messages: params.messages,
          model_id: params.modelId,
          run_context: params.runContext ?? null,
        },
        signal: params.signal,
      });
      return;
    } catch (err) {
      trackError("service_error", {
        scope: "send_message_live_failed",
        message: err instanceof Error ? err.message : String(err),
      });
      notifyLiveFallback("assistant", err);
      // Fall through to fixture fallback so the demo flow still works.
    }
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
 * Backend: GET /api/models
 */
export async function listModels(): Promise<ModelDescriptor[]> {
  if (FEATURES.liveModelManagement && isBackendConfigured()) {
    try {
      return await apiFetch<ModelDescriptor[]>("/api/models");
    } catch (err) {
      trackError("service_error", {
        scope: "list_models_live_failed",
        message: err instanceof Error ? err.message : String(err),
      });
      notifyLiveFallback("models", err);
    }
  }
  return loadFixture<ModelDescriptor[]>("models.json", {
    validate: (raw) => ModelDescriptorListShape.parse(raw) as unknown as ModelDescriptor[],
  });
}

/**
 * Install a local model. Streams progress events; the final event is
 * either `ready` or `error`.
 *
 * Backend: SSE POST /api/models/{modelId}/install
 */
export async function* installModel(modelId: string): AsyncIterable<InstallEvent> {
  if (FEATURES.liveModelManagement && isBackendConfigured()) {
    try {
      yield* apiSse<InstallEvent>(
        `/api/models/${encodeURIComponent(modelId)}/install`,
        { method: "POST" },
      );
      return;
    } catch (err) {
      trackError("service_error", {
        scope: "install_model_live_failed",
        modelId,
        message: err instanceof Error ? err.message : String(err),
      });
    }
  }
  yield* loadJsonlFixture<InstallEvent>("events/install-llama-8b.jsonl", 250);
}

/**
 * Uninstall a previously installed local model.
 *
 * Backend: DELETE /api/models/{modelId}
 */
export async function uninstallModel(modelId: string): Promise<void> {
  if (FEATURES.liveModelManagement && isBackendConfigured()) {
    try {
      await apiFetch<void>(`/api/models/${encodeURIComponent(modelId)}`, {
        method: "DELETE",
      });
      return;
    } catch (err) {
      trackError("service_error", {
        scope: "uninstall_model_live_failed",
        modelId,
        message: err instanceof Error ? err.message : String(err),
      });
    }
  }
  await sleep(300);
}

/**
 * Get the install status of a single model.
 *
 * Backend: GET /api/models/{modelId}/status
 */
export async function getModelStatus(modelId: string): Promise<ModelStatus> {
  if (!modelId) {
    throw new ServiceError("INVALID_INPUT", "modelId is required");
  }
  if (FEATURES.liveModelManagement && isBackendConfigured()) {
    try {
      return await apiFetch<ModelStatus>(
        `/api/models/${encodeURIComponent(modelId)}/status`,
      );
    } catch (err) {
      trackError("service_error", {
        scope: "model_status_live_failed",
        modelId,
        message: err instanceof Error ? err.message : String(err),
      });
    }
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
