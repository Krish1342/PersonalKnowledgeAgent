/**
 * Enhanced API Client for Second Brain
 * Supports Clerk authentication and v2 API endpoints
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ============================================================================
// Types - Enhanced for v2 API
// ============================================================================

export interface TagItem {
  id: number;
  name: string;
  color: string;
  user_id?: string;
}

export interface MemoryItemV2 {
  id: number;
  user_id?: string;
  source: string;
  content: string;
  title?: string;
  summary?: string;
  created_at: string;
  updated_at?: string;
  version: number;
  confidence: number;
  is_bookmarked: boolean;
  view_count: number;
  original_size: number;
  compressed_size: number;
  compression_ratio: number;
  tags: TagItem[];
}

export interface MemoryListResponseV2 {
  memories: MemoryItemV2[];
  total: number;
  page: number;
  page_size: number;
}

export interface StorageStats {
  total_memories: number;
  bookmarked_count: number;
  total_original_bytes: number;
  total_compressed_bytes: number;
  storage_saved_bytes: number;
  storage_saved_percent: number;
  average_compression_ratio: number;
  sources: Record<string, number>;
}

export interface SearchHistoryItem {
  id: number;
  query: string;
  results_count: number;
  created_at: string;
}

export interface ContentAnalysis {
  title: string;
  summary: string;
  tags: string[];
  keywords: string[];
}

export interface ExportData {
  exported_at: string;
  user_id?: string;
  memories: MemoryItemV2[];
  tags: TagItem[];
  stats: StorageStats;
}

export interface ImportResult {
  success: boolean;
  imported: number;
  skipped_duplicates: number;
}

export interface MemoryQueryParamsV2 {
  source?: string;
  tag?: string;
  bookmarked?: boolean;
  search?: string;
  limit?: number;
  offset?: number;
}

// ============================================================================
// Auth Helper
// ============================================================================

let authToken: string | null = null;

export function setAuthToken(token: string | null) {
  authToken = token;
}

function getHeaders(): HeadersInit {
  const headers: HeadersInit = {
    "Content-Type": "application/json",
  };
  if (authToken) {
    headers["Authorization"] = `Bearer ${authToken}`;
  }
  return headers;
}

// ============================================================================
// Error Handling
// ============================================================================

export class ApiClientError extends Error {
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
      const error = await response.json();
      detail = error.detail || error.message || "Request failed";
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
// V2 Memory API Functions
// ============================================================================

/**
 * Get memories with enhanced filtering (v2)
 */
export async function getMemoriesV2(
  params?: MemoryQueryParamsV2
): Promise<MemoryListResponseV2> {
  const searchParams = new URLSearchParams();
  
  if (params?.source) searchParams.set("source", params.source);
  if (params?.tag) searchParams.set("tag", params.tag);
  if (params?.bookmarked) searchParams.set("bookmarked", "true");
  if (params?.search) searchParams.set("search", params.search);
  if (params?.limit) searchParams.set("limit", params.limit.toString());
  if (params?.offset) searchParams.set("offset", params.offset.toString());
  
  const queryString = searchParams.toString();
  const url = `${API_BASE_URL}/api/v2/memory${queryString ? `?${queryString}` : ""}`;
  
  const response = await fetch(url, {
    method: "GET",
    headers: getHeaders(),
  });
  return handleResponse<MemoryListResponseV2>(response);
}

/**
 * Get memory by ID (v2)
 */
export async function getMemoryByIdV2(id: number): Promise<MemoryItemV2> {
  const response = await fetch(`${API_BASE_URL}/api/v2/memory/${id}`, {
    method: "GET",
    headers: getHeaders(),
  });
  return handleResponse<MemoryItemV2>(response);
}

/**
 * Get storage statistics (v2)
 */
export async function getStorageStats(): Promise<StorageStats> {
  const response = await fetch(`${API_BASE_URL}/api/v2/memory/stats`, {
    method: "GET",
    headers: getHeaders(),
  });
  return handleResponse<StorageStats>(response);
}

/**
 * Get all sources
 */
export async function getSourcesV2(): Promise<string[]> {
  const response = await fetch(`${API_BASE_URL}/api/v2/memory/sources`, {
    method: "GET",
    headers: getHeaders(),
  });
  return handleResponse<string[]>(response);
}

/**
 * Get all tags
 */
export async function getTagsV2(): Promise<TagItem[]> {
  const response = await fetch(`${API_BASE_URL}/api/v2/memory/tags`, {
    method: "GET",
    headers: getHeaders(),
  });
  return handleResponse<TagItem[]>(response);
}

/**
 * Toggle bookmark status
 */
export async function toggleBookmark(memoryId: number): Promise<{ memory_id: number; is_bookmarked: boolean }> {
  const response = await fetch(`${API_BASE_URL}/api/v2/memory/bookmark`, {
    method: "POST",
    headers: getHeaders(),
    body: JSON.stringify({ memory_id: memoryId }),
  });
  return handleResponse(response);
}

/**
 * Add tags to a memory
 */
export async function addTagsToMemory(memoryId: number, tags: string[]): Promise<{ memory_id: number; tags_added: string[] }> {
  const response = await fetch(`${API_BASE_URL}/api/v2/memory/tags`, {
    method: "POST",
    headers: getHeaders(),
    body: JSON.stringify({ memory_id: memoryId, tags }),
  });
  return handleResponse(response);
}

/**
 * Analyze content for auto-tagging
 */
export async function analyzeContent(content: string): Promise<ContentAnalysis> {
  const response = await fetch(`${API_BASE_URL}/api/v2/memory/analyze`, {
    method: "POST",
    headers: getHeaders(),
    body: JSON.stringify({ content }),
  });
  return handleResponse<ContentAnalysis>(response);
}

/**
 * Get search history
 */
export async function getSearchHistory(limit: number = 20): Promise<SearchHistoryItem[]> {
  const response = await fetch(`${API_BASE_URL}/api/v2/memory/search-history?limit=${limit}`, {
    method: "GET",
    headers: getHeaders(),
  });
  return handleResponse<SearchHistoryItem[]>(response);
}

/**
 * Export all data
 */
export async function exportData(): Promise<ExportData> {
  const response = await fetch(`${API_BASE_URL}/api/v2/memory/export`, {
    method: "GET",
    headers: getHeaders(),
  });
  return handleResponse<ExportData>(response);
}

/**
 * Import data
 */
export async function importData(data: ExportData): Promise<ImportResult> {
  const response = await fetch(`${API_BASE_URL}/api/v2/memory/import`, {
    method: "POST",
    headers: getHeaders(),
    body: JSON.stringify({ data }),
  });
  return handleResponse<ImportResult>(response);
}

// ============================================================================
// Health Check
// ============================================================================

export interface HealthResponseV2 {
  status: string;
  service: string;
  version: string;
  auth_enabled: boolean;
  environment: string;
}

export async function checkHealthV2(): Promise<HealthResponseV2> {
  const response = await fetch(`${API_BASE_URL}/`, {
    method: "GET",
    headers: getHeaders(),
  });
  return handleResponse<HealthResponseV2>(response);
}

// Re-export original API functions for backwards compatibility
export * from './api';
