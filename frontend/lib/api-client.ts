/**
 * API Client for communicating with the backend
 */

import {
  QueryRequest,
  QueryResponse,
  UploadRequest,
  UploadResponse,
  ChunksResponse,
  MemoryTimelineResponse,
  ReasoningModesResponse,
  ErrorResponse
} from './types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public response?: ErrorResponse
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let errorData: ErrorResponse | undefined;
    try {
      errorData = await response.json();
    } catch {
      // Could not parse error response
    }
    
    throw new ApiError(
      errorData?.error || `HTTP ${response.status}: ${response.statusText}`,
      response.status,
      errorData
    );
  }
  
  return response.json();
}

export const apiClient = {
  /**
   * Query endpoint - Ask a question
   */
  async query(request: QueryRequest): Promise<QueryResponse> {
    const response = await fetch(`${API_BASE_URL}/query`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });
    
    return handleResponse<QueryResponse>(response);
  },

  /**
   * Stream query endpoint - Get real-time updates
   */
  async *queryStream(request: QueryRequest): AsyncGenerator<any, void, unknown> {
    const response = await fetch(`${API_BASE_URL}/query/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ ...request, stream: true }),
    });

    if (!response.ok) {
      throw new ApiError(
        `HTTP ${response.status}: ${response.statusText}`,
        response.status
      );
    }

    const reader = response.body?.getReader();
    if (!reader) {
      throw new Error('Response body is not readable');
    }

    const decoder = new TextDecoder();
    let buffer = '';

    try {
      while (true) {
        const { done, value } = await reader.read();
        
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        
        // Process SSE events
        const lines = buffer.split('\n\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6);
            try {
              yield JSON.parse(data);
            } catch {
              // Invalid JSON, skip
            }
          }
        }
      }
    } finally {
      reader.releaseLock();
    }
  },

  /**
   * Upload knowledge endpoint
   */
  async upload(request: UploadRequest): Promise<UploadResponse> {
    const response = await fetch(`${API_BASE_URL}/upload`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });
    
    return handleResponse<UploadResponse>(response);
  },

  /**
   * Get all chunks/sources
   */
  async getChunks(page: number = 1, pageSize: number = 20): Promise<ChunksResponse> {
    const response = await fetch(
      `${API_BASE_URL}/chunks?page=${page}&page_size=${pageSize}`
    );
    
    return handleResponse<ChunksResponse>(response);
  },

  /**
   * Get a specific chunk by ID
   */
  async getChunk(chunkId: string): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/chunks/${chunkId}`);
    return handleResponse(response);
  },

  /**
   * Delete a chunk
   */
  async deleteChunk(chunkId: string): Promise<{ success: boolean }> {
    const response = await fetch(`${API_BASE_URL}/chunks/${chunkId}`, {
      method: 'DELETE',
    });
    
    return handleResponse(response);
  },

  /**
   * Get memory timeline/events
   */
  async getMemoryTimeline(days: number = 7): Promise<MemoryTimelineResponse> {
    const response = await fetch(`${API_BASE_URL}/memory/timeline?days=${days}`);
    return handleResponse<MemoryTimelineResponse>(response);
  },

  /**
   * Get available reasoning modes
   */
  async getReasoningModes(): Promise<ReasoningModesResponse> {
    const response = await fetch(`${API_BASE_URL}/modes`);
    return handleResponse<ReasoningModesResponse>(response);
  },

  /**
   * Health check
   */
  async healthCheck(): Promise<{ status: string; timestamp: string; agents_loaded: boolean }> {
    const response = await fetch(`${API_BASE_URL}/health`);
    return handleResponse(response);
  }
};

export { ApiError };
