/**
 * Type definitions for API requests and responses
 */

// Query API Types
export interface QueryRequest {
  query: string;
  mode?: 'eli5' | 'exam' | 'research' | 'comparison';
  user_id?: string;
  session_id?: string;
  context?: Record<string, any>;
  stream?: boolean;
}

export interface Citation {
  chunk_id: string;
  text: string;
  source?: string;
  confidence?: number;
}

export interface ReasoningStep {
  step_number: number;
  content: string;
}

export interface QueryResponse {
  query: string;
  answer: string;
  confidence: number;
  citations: Citation[];
  sources_count: number;
  mode: string;
  reasoning_steps?: ReasoningStep[];
  validation_passed: boolean;
  validation_confidence?: string;
  query_id: string;
  session_id?: string;
  processing_time_ms: number;
  timestamp: string;
  knowledge_gaps?: string[];
  suggestions?: string[];
}

// Upload Types
export interface UploadRequest {
  content: string;
  metadata?: {
    title?: string;
    source?: string;
    topic?: string;
    tags?: string[];
    [key: string]: any;
  };
}

export interface UploadResponse {
  success: boolean;
  chunk_id?: string;
  message: string;
  quality_score?: number;
}

// Source/Chunk Types
export interface Chunk {
  id: string;
  content: string;
  metadata: {
    title?: string;
    source?: string;
    topic?: string;
    tags?: string[];
    quality_score?: number;
    confidence?: number;
    created_at?: string;
    last_accessed?: string;
    access_count?: number;
    [key: string]: any;
  };
  embedding?: number[];
}

export interface ChunksResponse {
  chunks: Chunk[];
  total: number;
  page: number;
  page_size: number;
}

// Memory Timeline Types
export interface MemoryEvent {
  id: string;
  event_type: 'query' | 'upload' | 'update' | 'prune';
  timestamp: string;
  description: string;
  metadata?: Record<string, any>;
}

export interface MemoryTimelineResponse {
  events: MemoryEvent[];
  total: number;
  stats?: {
    total_chunks: number;
    total_queries: number;
    avg_confidence: number;
    [key: string]: any;
  };
}

// Reasoning Modes
export interface ReasoningMode {
  id: string;
  name: string;
  description: string;
}

export interface ReasoningModesResponse {
  modes: ReasoningMode[];
  default: string;
}

// Error Response
export interface ErrorResponse {
  error: string;
  error_type: string;
  query?: string;
  timestamp: string;
  details?: Record<string, any>;
}
