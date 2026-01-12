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

export interface SearchResult {
  id: number;
  uuid: string;
  title: string;
  type: string;
  date: string | null;
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

// Helper to get cookie by name
function getCookie(name: string): string | null {
  if (!document.cookie) {
    return null;
  }
  const xsrfCookies = document.cookie
    .split(';')
    .map(c => c.trim())
    .filter(c => c.startsWith(name + '='));

  if (xsrfCookies.length === 0) {
    return null;
  }
  return decodeURIComponent(xsrfCookies[0].split('=')[1]);
}

async function fetchApi<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...options.headers,
  };

  // Add CSRF token if available
  const csrftoken = getCookie('csrftoken');
  if (csrftoken) {
    (headers as any)['X-CSRFToken'] = csrftoken;
  }

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  });
  if (!response.ok) {
    // Try to parse error message
    let errMsg = response.statusText;
    try {
      const errData = await response.json();
      if (errData.message) errMsg = errData.message;
    } catch (e) { }
    throw new Error(`API Error ${response.status}: ${errMsg}`);
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

  async flagDocument(uuid: string): Promise<{ success: boolean }> {
    return fetchApi<{ success: boolean }>(`/documents/${uuid}/flag`, {
      method: 'POST'
    });
  },

  async searchDocuments(query?: string, params?: Record<string, any>): Promise<SearchResponse> {
    const searchParams = new URLSearchParams();
    if (query) {
      searchParams.append('query', query);
    }
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

  async getStats(
    interval: 'day' | 'month' | 'year' = 'month',
    startDate?: string,
    endDate?: string,
    extraParams?: Record<string, any>
  ): Promise<StatsData[]> {
    const params = new URLSearchParams({ interval });
    if (startDate) params.append('start_date', startDate);
    if (endDate) params.append('end_date', endDate);
    if (extraParams) {
      Object.entries(extraParams).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== '') {
          params.append(key, String(value));
        }
      });
    }

    return fetchApi<StatsData[]>(`/documents/counts?${params.toString()}`);
  }
};
