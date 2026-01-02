import { MOCK_DOCUMENTS } from '../data/mock';

// Types derived from Backend DocumentOut schema
export interface Document {
  id: number;
  uuid: string;
  title: string;
  type: string; // slug
  date: string | null;
  content: string | null;
  summary: string | null;
  number: string | null;
}

export interface DocumentType {
  id: number;
  label: string; // mapped from name
}

export interface VectorStore {
  uuid: string;
  name: string;
  description?: string;
}

export interface SearchResult {
  text: string;
  type: string;
  filename: string;
  score: number;
  attributes: Record<string, any>;
}

export interface SearchResponse {
  data: SearchResult[];
  has_more: boolean;
}

export interface StatsData {
  period: string;
  type: string;
  count: number;
}

const API_BASE = '/api';

async function fetchApi<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${endpoint}`, options);
  if (!response.ok) {
    throw new Error(`API Error: ${response.statusText}`);
  }
  return response.json();
}

export const api = {
  // Documents
  async listDocuments(params?: Record<string, any>): Promise<Document[]> {
    const searchParams = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== '') {
          searchParams.append(key, String(value));
        }
      });
    }
    return fetchApi<Document[]>(`/documents/list?${searchParams.toString()}`);
  },

  async getDocument(uuid: string): Promise<Document> {
    return fetchApi<Document>(`/documents/${uuid}`);
  },

  async summarizeDocument(uuid: string): Promise<{ summary: string }> {
    return fetchApi<{ summary: string }>(`/documents/${uuid}/summarize`, {
      method: 'POST'
    });
  },

  async searchDocuments(query: string, params?: Record<string, any>): Promise<SearchResponse> {
    const searchParams = new URLSearchParams({ query });
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== '') {
          searchParams.append(key, String(value));
        }
      });
    }
    return fetchApi<SearchResponse>(`/documents/search?${searchParams.toString()}`);
  },

  async getDocumentTypes(): Promise<DocumentType[]> {
    return fetchApi<DocumentType[]>('/documents/types');
  },

  async getStats(interval: 'day' | 'month' | 'year' = 'month', startDate?: string, endDate?: string): Promise<StatsData[]> {
    const params = new URLSearchParams({ interval });
    if (startDate) params.append('start_date', startDate);
    if (endDate) params.append('end_date', endDate);

    return fetchApi<StatsData[]>(`/documents/counts?${params.toString()}`);
  }
};
