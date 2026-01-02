import { MOCK_DOCUMENTS } from '../data/mock';

// Types derived from Backend DocumentOut schema
export interface Document {
  id: number;
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

  async getDocument(id: string | number): Promise<Document> {
    // Determine if id is UUID or int. 
    // The backend `document_detail` view uses UUID in URL, but `DocumentOut` has int ID.
    // Wait, the backend view `document_detail` is a Django view returning HTML, not JSON API.
    // The API `list_documents` returns `DocumentOut` which has integer `id`.
    // But we don't have a single document API endpoint in `api.py`.
    // We should probably rely on `list_documents` with filter or add a detail endpoint.
    // Checking `urls.py`: `path("documents/<uuid:document_uuid>/", documents_views.document_detail)` is HTML.
    // The task plan didn't explicitly ask for a JSON detail endpoint, but we need one for the React app if we are not using the django view.
    // However, the React app seems to be a single page app.
    // Let's assume we need to add a detail endpoint or use the list endpoint.
    // Actually, `list_documents` returns `list[DocumentOut]`.
    // Let's check `api.py` again.
    // There is no single document retrieval endpoint in `api.py`.
    // I should add one.
    // For now, I'll filter by ID using list if possible, but `list_documents` doesn't filter by ID.
    // I will add `retrieve_document` to `api.py`.

    // TEMPORARY: using list and filtering client side or mock fall back?
    // No, I should implement the backend endpoint.
    // I'll proceed with writing this client assuming the endpoint exists (documents/{id})
    // Note: The React route uses `id`, which might be int or uuid. `DocumentOut` uses int `id`.
    // The backend `Document` model has `uuid` and `id`.
    // I'll assume we'll use integer ID for API consistency.

    return fetchApi<Document>(`/documents/${id}`);
  },

  async summarizeDocument(id: number): Promise<{ summary: string }> {
    return fetchApi<{ summary: string }>(`/documents/${id}/summarize`, {
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
