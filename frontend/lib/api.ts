/**
 * API Client for Personal Knowledge Base Backend
 *
 * Strongly typed fetch functions for all backend endpoints.
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ============================================================================
// Types
// ============================================================================

/** Ingest request payload */
export interface IngestRequest {
  content: string;
  source?: string;
}

/** Ingest response */
export interface IngestResponse {
  success: boolean;
  message: string;
  chunks_ingested: number;
  source: string;
}

/** Query request payload */
export interface QueryRequest {
  question: string;
}

/** Context item from retrieval */
export interface ContextItem {
  content: string;
  source: string;
  relevance_score: number | null;
}

/** Query response with agent metadata */
export interface QueryResponse {
  answer: string;
  context: ContextItem[];
  score: number | null;
  critique: string | null;
}

/** Memory item from episodic store */
export interface MemoryItem {
  id: number;
  source: string;
  content: string;
  created_at: string;
  version: number;
  confidence: number;
}

/** Memory list response */
export interface MemoryResponse {
  total: number;
  items: MemoryItem[];
  sources: string[];
}

/** Memory stats response */
export interface MemoryStatsResponse {
  total_memories: number;
  sources: string[];
  source_counts: Record<string, number>;
}

/** Memory query parameters */
export interface MemoryQueryParams {
  source?: string;
  limit?: number;
  offset?: number;
  min_confidence?: number;
}

/** Health check response */
export interface HealthResponse {
  status: string;
  vector_db_path: string;
  sqlite_db_path: string;
  embedding_model: string;
  llm_configured: boolean;
}

/** API error */
export interface ApiError {
  detail: string;
}

/** Agent step for timeline visualization */
export interface AgentStep {
  name: string;
  status: "pending" | "running" | "completed" | "error";
  duration?: number;
  metadata?: Record<string, unknown>;
}

// ============================================================================
// Error Handling
// ============================================================================

class ApiClientError extends Error {
  constructor(
    message: string,
    public status: number,
    public detail?: string
  ) {
    super(message);
    this.name = "ApiClientError";
  }
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let detail = "Unknown error";
    try {
      const error: ApiError = await response.json();
      detail = error.detail;
    } catch {
      detail = response.statusText;
    }
    throw new ApiClientError(
      `API request failed: ${detail}`,
      response.status,
      detail
    );
  }
  return response.json();
}

// ============================================================================
// API Functions
// ============================================================================

/**
 * Ingest content into the knowledge base.
 */
export async function ingestContent(
  request: IngestRequest
): Promise<IngestResponse> {
  const response = await fetch(`${API_BASE_URL}/api/ingest`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(request),
  });
  return handleResponse<IngestResponse>(response);
}

/**
 * Query the knowledge base with a question.
 */
export async function queryKnowledgeBase(
  request: QueryRequest
): Promise<QueryResponse> {
  const response = await fetch(`${API_BASE_URL}/api/query`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(request),
  });
  return handleResponse<QueryResponse>(response);
}

/**
 * Get episodic memory history.
 */
export async function getMemory(
  params?: MemoryQueryParams
): Promise<MemoryResponse> {
  const searchParams = new URLSearchParams();

  if (params?.source) searchParams.set("source", params.source);
  if (params?.limit) searchParams.set("limit", params.limit.toString());
  if (params?.offset) searchParams.set("offset", params.offset.toString());
  if (params?.min_confidence)
    searchParams.set("min_confidence", params.min_confidence.toString());

  const queryString = searchParams.toString();
  const url = `${API_BASE_URL}/api/memory${queryString ? `?${queryString}` : ""}`;

  const response = await fetch(url, {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
    },
  });
  return handleResponse<MemoryResponse>(response);
}

/**
 * Get memory statistics.
 */
export async function getMemoryStats(): Promise<MemoryStatsResponse> {
  const response = await fetch(`${API_BASE_URL}/api/memory/stats`, {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
    },
  });
  return handleResponse<MemoryStatsResponse>(response);
}

/**
 * Get a specific memory by ID.
 */
export async function getMemoryById(id: number): Promise<MemoryItem> {
  const response = await fetch(`${API_BASE_URL}/api/memory/${id}`, {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
    },
  });
  return handleResponse<MemoryItem>(response);
}

/**
 * Health check.
 */
export async function checkHealth(): Promise<HealthResponse> {
  const response = await fetch(`${API_BASE_URL}/health`, {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
    },
  });
  return handleResponse<HealthResponse>(response);
}

/**
 * Derive agent steps from query response for timeline visualization.
 */
export function deriveAgentSteps(response: QueryResponse): AgentStep[] {
  const steps: AgentStep[] = [];

  // Plan step
  steps.push({
    name: "Plan",
    status: "completed",
    metadata: {
      description: "Optimized query for retrieval",
    },
  });

  // Retrieve step
  steps.push({
    name: "Retrieve",
    status: "completed",
    metadata: {
      documentsRetrieved: response.context.length,
      topScore: response.context[0]?.relevance_score ?? null,
    },
  });

  // Reason step
  steps.push({
    name: "Reason",
    status: response.answer ? "completed" : "error",
    metadata: {
      answerLength: response.answer?.length ?? 0,
    },
  });

  // Critique step
  steps.push({
    name: "Critique",
    status: response.score !== null ? "completed" : "pending",
    metadata: {
      groundednessScore: response.score,
      critique: response.critique,
    },
  });

  return steps;
}
