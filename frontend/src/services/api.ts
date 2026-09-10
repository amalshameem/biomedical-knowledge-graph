import axios from 'axios';
import { Project, GlobalSettings, LLMProvider, CytoscapeGraphData } from '../types';

const API_BASE = '/api/v1';

export const api = {
  // Projects
  getProjects: async (): Promise<Project[]> => {
    const res = await axios.get(`${API_BASE}/projects`);
    return res.data;
  },

  createProject: async (name: string, description: string = '', ner_mode: string = 'advanced'): Promise<Project> => {
    const res = await axios.post(`${API_BASE}/projects`, { name, description, ner_mode });
    return res.data;
  },

  getProject: async (id: string): Promise<Project> => {
    const res = await axios.get(`${API_BASE}/projects/${id}`);
    return res.data;
  },

  deleteProject: async (id: string): Promise<void> => {
    await axios.delete(`${API_BASE}/projects/${id}`);
  },

  uploadDocuments: async (projectId: string, files: File[]): Promise<any> => {
    const formData = new FormData();
    files.forEach((file) => formData.append('files', file));
    const res = await axios.post(`${API_BASE}/projects/${projectId}/documents`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return res.data;
  },

  // Extraction & Status
  startExtraction: async (projectId: string, payload: { provider: string; endpoint?: string; api_key?: string; model: string; ner_mode?: string }): Promise<any> => {
    const res = await axios.post(`${API_BASE}/projects/${projectId}/extract`, payload);
    return res.data;
  },

  getProjectStatus: async (projectId: string): Promise<any> => {
    const res = await axios.get(`${API_BASE}/projects/${projectId}/status`);
    return res.data;
  },

  // Graph
  getGraph: async (projectId: string, minConnections: number = 1, entityType?: string): Promise<CytoscapeGraphData> => {
    const params = new URLSearchParams({ min_connections: String(minConnections) });
    if (entityType && entityType !== 'all') {
      params.append('entity_type', entityType);
    }
    const res = await axios.get(`${API_BASE}/projects/${projectId}/graph?${params.toString()}`);
    return res.data;
  },

  // LLM Providers & Models
  getProviders: async (): Promise<LLMProvider[]> => {
    const res = await axios.get(`${API_BASE}/llm/providers`);
    return res.data;
  },

  getModels: async (provider: string, endpoint: string = '', apiKey: string = ''): Promise<string[]> => {
    const params = new URLSearchParams({ provider, endpoint, api_key: apiKey });
    const res = await axios.get(`${API_BASE}/llm/models?${params.toString()}`);
    return res.data;
  },

  // Settings
  getSettings: async (): Promise<GlobalSettings> => {
    const res = await axios.get(`${API_BASE}/settings`);
    return res.data;
  },

  updateSettings: async (settings: GlobalSettings): Promise<GlobalSettings> => {
    const res = await axios.post(`${API_BASE}/settings`, settings);
    return res.data;
  },

  // Export URLs
  getExportZipUrl: (projectId: string): string => `${API_BASE}/projects/${projectId}/export`,
  getExportCsvUrl: (projectId: string): string => `${API_BASE}/projects/${projectId}/export/csv`,
  getExportGraphmlUrl: (projectId: string): string => `${API_BASE}/projects/${projectId}/export/graphml`,
};
