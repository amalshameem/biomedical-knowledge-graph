import React, { useState, useEffect, useCallback } from 'react';
import { X, Upload, FileText, Cpu, Sparkles, AlertCircle, Loader2, RefreshCw, Layers, CheckCircle2 } from 'lucide-react';
import { LLMProvider } from '../../types';
import { api } from '../../services/api';

interface NewProjectModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (projectData: {
    name: string;
    description: string;
    files: File[];
    provider: string;
    endpoint: string;
    apiKey: string;
    model: string;
    ner_mode: 'basic' | 'advanced';
  }) => Promise<void>;
}

export const NewProjectModal: React.FC<NewProjectModalProps> = ({ isOpen, onClose, onSubmit }) => {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [nerMode, setNerMode] = useState<'basic' | 'advanced'>('advanced');
  const [files, setFiles] = useState<File[]>([]);
  const [providers, setProviders] = useState<LLMProvider[]>([]);
  const [selectedProvider, setSelectedProvider] = useState('LM Studio');
  const [endpoint, setEndpoint] = useState('http://localhost:1234/v1');
  const [apiKey, setApiKey] = useState('');
  const [models, setModels] = useState<string[]>([]);
  const [selectedModel, setSelectedModel] = useState('');
  const [customModel, setCustomModel] = useState('');
  const [isCustomModel, setIsCustomModel] = useState(false);
  const [loadingModels, setLoadingModels] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  const [savedSettings, setSavedSettings] = useState<any>(null);

  // Fetch models directly from API
  const fetchLiveModels = useCallback((prov: string, ep: string, key: string) => {
    if (!prov) return;
    setLoadingModels(true);
    setErrorMsg('');
    api.getModels(prov, ep, key)
      .then((fetchedModels) => {
        const validModels = (fetchedModels || []).filter(
          (m) => !m.startsWith('Error') && !m.startsWith('Connection Failed') && !m.startsWith('No models')
        );
        setModels(validModels);
        if (validModels.length > 0) {
          setSelectedModel((prev) => (validModels.includes(prev) ? prev : validModels[0]));
          setIsCustomModel(false);
        } else {
          setSelectedModel('');
        }
      })
      .catch((err) => {
        console.error('Failed to fetch models:', err);
        setModels([]);
        setSelectedModel('');
      })
      .finally(() => setLoadingModels(false));
  }, []);

  // Reset state and fetch providers on open
  useEffect(() => {
    if (isOpen) {
      setName('');
      setDescription('');
      setFiles([]);
      setErrorMsg('');
      setSubmitting(false);
      setCustomModel('');
      setIsCustomModel(false);
      setNerMode('advanced');

      // Fetch default providers and load global settings
      Promise.all([api.getProviders(), api.getSettings()])
        .then(([provs, s]) => {
          setProviders(provs);
          setSavedSettings(s);

          const preferred = s.default_provider || (provs.length > 0 ? provs[0].name : 'Ollama');
          setSelectedProvider(preferred);

          const matchedProv = provs.find((p) => p.name === preferred);
          let initialEndpoint = matchedProv ? matchedProv.default_endpoint : '';
          let initialKey = '';

          // Preload key for default provider
          if (preferred === 'Ollama') {
            initialKey = s.ollama_api_key || '';
            if (s.ollama_endpoint) {
              initialEndpoint = s.ollama_endpoint;
            } else if (initialKey) {
              initialEndpoint = 'https://ollama.com/v1';
            }
          } else if (preferred === 'LM Studio') {
            if (s.lmstudio_endpoint) initialEndpoint = s.lmstudio_endpoint;
          } else if (preferred === 'OpenRouter') {
            initialKey = s.openrouter_api_key || '';
          } else if (preferred === 'Anthropic') {
            initialKey = s.anthropic_api_key || '';
          } else if (preferred === 'Google Gemini') {
            initialKey = s.gemini_api_key || '';
          } else if (preferred === 'OpenAI') {
            initialKey = s.openai_api_key || '';
            if (s.openai_endpoint) initialEndpoint = s.openai_endpoint;
          } else if (preferred === 'Groq') {
            initialKey = s.groq_api_key || '';
          } else if (preferred === 'Mistral AI') {
            initialKey = s.mistral_api_key || '';
          }

          setEndpoint(initialEndpoint);
          setApiKey(initialKey);
          fetchLiveModels(preferred, initialEndpoint, initialKey);
        })
        .catch(console.error);
    }
  }, [isOpen, fetchLiveModels]);

  // Dynamic model fetching whenever provider, endpoint, or key changes (debounced)
  useEffect(() => {
    if (!isOpen || !selectedProvider) return;

    const timer = setTimeout(() => {
      fetchLiveModels(selectedProvider, endpoint, apiKey);
    }, 300);

    return () => clearTimeout(timer);
  }, [isOpen, selectedProvider, endpoint, apiKey, fetchLiveModels]);

  if (!isOpen) return null;

  const handleProviderChange = (pName: string) => {
    setSelectedProvider(pName);
    const p = providers.find((item) => item.name === pName);
    let nextEndpoint = p ? p.default_endpoint : '';
    let nextKey = '';

    if (pName === 'Ollama') {
      nextKey = savedSettings?.ollama_api_key || '';
      if (savedSettings?.ollama_endpoint) {
        nextEndpoint = savedSettings.ollama_endpoint;
      } else if (nextKey) {
        nextEndpoint = 'https://ollama.com/v1';
      }
    } else if (pName === 'LM Studio') {
      nextKey = '';
      if (savedSettings?.lmstudio_endpoint) nextEndpoint = savedSettings.lmstudio_endpoint;
    } else if (pName === 'OpenRouter') {
      nextKey = savedSettings?.openrouter_api_key || '';
    } else if (pName === 'Anthropic') {
      nextKey = savedSettings?.anthropic_api_key || '';
    } else if (pName === 'Google Gemini') {
      nextKey = savedSettings?.gemini_api_key || '';
    } else if (pName === 'OpenAI') {
      nextKey = savedSettings?.openai_api_key || '';
      if (savedSettings?.openai_endpoint) nextEndpoint = savedSettings.openai_endpoint;
    } else if (pName === 'Groq') {
      nextKey = savedSettings?.groq_api_key || '';
    } else if (pName === 'Mistral AI') {
      nextKey = savedSettings?.mistral_api_key || '';
    }

    setEndpoint(nextEndpoint);
    setApiKey(nextKey);
  };

  const handleFileDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const droppedFiles = Array.from(e.dataTransfer.files).filter((f) => f.name.toLowerCase().endsWith('.pdf'));
    setFiles((prev) => [...prev, ...droppedFiles]);
  };

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const selected = Array.from(e.target.files).filter((f) => f.name.toLowerCase().endsWith('.pdf'));
      setFiles((prev) => [...prev, ...selected]);
    }
  };

  const removeFile = (idx: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== idx));
  };

  const effectiveModel = isCustomModel ? customModel.trim() : selectedModel;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      setErrorMsg('Please provide a project name.');
      return;
    }
    if (files.length === 0) {
      setErrorMsg('Please upload at least one PDF file.');
      return;
    }
    if (!effectiveModel) {
      setErrorMsg('Please select or specify a valid LLM model name.');
      return;
    }

    setSubmitting(true);
    setErrorMsg('');
    try {
      await onSubmit({
        name: name.trim(),
        description: description.trim(),
        files,
        provider: selectedProvider,
        endpoint,
        apiKey,
        model: effectiveModel,
        ner_mode: nerMode,
      });
      onClose();
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      setErrorMsg(typeof detail === 'string' ? detail : 'Failed to start extraction. Please verify your LLM endpoint and files.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 animate-fadeIn">
      <div className="bg-white border border-slate-300 rounded-xl w-full max-w-xl shadow-xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Modal Header */}
        <div className="px-5 py-3.5 border-b border-slate-200 flex items-center justify-between bg-white">
          <div className="flex items-center gap-2">
            <FileText className="w-4 h-4 text-slate-800" />
            <h2 className="text-sm font-bold text-slate-900">New Extraction Project</h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1 rounded text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Modal Form */}
        <form onSubmit={handleSubmit} className="p-5 overflow-y-auto space-y-4 flex-1 text-xs">
          {errorMsg && (
            <div className="p-3 rounded-lg bg-rose-50 border border-rose-200 flex items-center gap-2 text-rose-700 text-xs">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{errorMsg}</span>
            </div>
          )}

          {/* Project Details */}
          <div className="grid grid-cols-1 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Project Name <span className="text-rose-500">*</span>
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Lipocalin-2 IBD Knowledge Extraction"
                className="w-full bg-white border border-slate-300 rounded-lg px-3 py-1.5 text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-slate-800 focus:ring-1 focus:ring-slate-800 text-xs shadow-2xs"
                required
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Description (Optional)
              </label>
              <input
                type="text"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Brief summary or research focus"
                className="w-full bg-white border border-slate-300 rounded-lg px-3 py-1.5 text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-slate-800 focus:ring-1 focus:ring-slate-800 text-xs shadow-2xs"
              />
            </div>
          </div>

          {/* PDF Upload Dropzone */}
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Source PDF Document(s) <span className="text-rose-500">*</span>
            </label>
            <div
              onDragOver={(e) => e.preventDefault()}
              onDrop={handleFileDrop}
              className="border-2 border-dashed border-slate-300 hover:border-slate-500 rounded-xl p-5 flex flex-col items-center justify-center bg-slate-50/60 hover:bg-slate-100/60 transition-colors cursor-pointer text-center relative"
            >
              <input
                type="file"
                multiple
                accept=".pdf"
                onChange={handleFileInput}
                className="absolute inset-0 opacity-0 cursor-pointer"
              />
              <div className="w-8 h-8 rounded-md bg-white border border-slate-300 text-slate-600 flex items-center justify-center mb-1.5">
                <Upload className="w-4 h-4" />
              </div>
              <p className="text-xs font-semibold text-slate-800">
                Click or drag & drop PDF files here
              </p>
              <p className="text-[11px] text-slate-500 mt-0.5">
                Processed with IBM Docling text converter & hierarchical chunking
              </p>
            </div>

            {/* Uploaded files list */}
            {files.length > 0 && (
              <div className="mt-2 space-y-1">
                {files.map((file, idx) => (
                  <div
                    key={idx}
                    className="flex items-center justify-between p-2 rounded-lg bg-slate-50 border border-slate-200 text-xs"
                  >
                    <div className="flex items-center gap-2 text-slate-800">
                      <FileText className="w-3.5 h-3.5 text-slate-600 shrink-0" />
                      <span className="font-medium truncate max-w-sm">{file.name}</span>
                      <span className="text-slate-400 text-[10px]">
                        ({(file.size / (1024 * 1024)).toFixed(2)} MB)
                      </span>
                    </div>
                    <button
                      type="button"
                      onClick={() => removeFile(idx)}
                      className="p-1 text-slate-400 hover:text-rose-600 rounded transition-colors"
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Extraction Mode */}
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Extraction Mode
            </label>
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => setNerMode('basic')}
                className={`py-2 px-3 rounded-lg text-xs font-semibold border transition-all text-center ${
                  nerMode === 'basic'
                    ? 'bg-slate-900 border-slate-900 text-white shadow-xs'
                    : 'bg-white border-slate-300 text-slate-700 hover:bg-slate-50'
                }`}
              >
                Basic
              </button>
              <button
                type="button"
                onClick={() => setNerMode('advanced')}
                className={`py-2 px-3 rounded-lg text-xs font-semibold border transition-all text-center ${
                  nerMode === 'advanced'
                    ? 'bg-slate-900 border-slate-900 text-white shadow-xs'
                    : 'bg-white border-slate-300 text-slate-700 hover:bg-slate-50'
                }`}
              >
                Advance
              </button>
            </div>
          </div>

          {/* LLM Provider Configuration */}
          <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5 text-xs font-bold text-slate-900">
                <Cpu className="w-3.5 h-3.5 text-slate-700" />
                <span>LLM Extraction Engine</span>
              </div>
              <button
                type="button"
                onClick={() => setIsCustomModel(!isCustomModel)}
                className="text-[11px] text-slate-600 hover:text-slate-900 font-semibold"
              >
                {isCustomModel ? 'Use Detected Models' : 'Enter Model Manually'}
              </button>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">Provider</label>
                <select
                  value={selectedProvider}
                  onChange={(e) => handleProviderChange(e.target.value)}
                  className="w-full bg-white border border-slate-300 rounded-lg px-2.5 py-1.5 text-xs text-slate-800 focus:outline-none focus:border-slate-800 font-medium"
                >
                  {providers.length > 0 ? (
                    providers.map((p) => (
                      <option key={p.name} value={p.name}>
                        {p.name}
                      </option>
                    ))
                  ) : (
                    <>
                      <option value="Ollama">Ollama</option>
                      <option value="LM Studio">LM Studio</option>
                      <option value="OpenRouter">OpenRouter</option>
                      <option value="Anthropic">Anthropic</option>
                      <option value="Google Gemini">Google Gemini</option>
                      <option value="OpenAI">OpenAI</option>
                      <option value="Groq">Groq</option>
                      <option value="Mistral AI">Mistral AI</option>
                    </>
                  )}
                </select>
              </div>

              <div>
                <div className="flex items-center justify-between mb-1">
                  <label className="text-xs font-medium text-slate-700">
                    Model {isCustomModel && '(Custom)'}
                  </label>
                  <div className="flex items-center gap-1.5">
                    {!isCustomModel && models.length > 0 && (
                      <span className="text-[10px] font-mono text-emerald-600 font-medium">
                        {models.length} available
                      </span>
                    )}
                    <button
                      type="button"
                      title="Refresh models from API"
                      onClick={() => fetchLiveModels(selectedProvider, endpoint, apiKey)}
                      className="text-slate-400 hover:text-slate-700 transition p-0.5"
                    >
                      <RefreshCw className={`w-3 h-3 ${loadingModels ? 'animate-spin text-slate-700' : ''}`} />
                    </button>
                  </div>
                </div>
                {isCustomModel ? (
                  <input
                    type="text"
                    value={customModel}
                    onChange={(e) => setCustomModel(e.target.value)}
                    placeholder="e.g. meta-llama-3-8b, gpt-4o-mini"
                    className="w-full bg-white border border-slate-300 rounded-lg px-2.5 py-1.5 text-xs text-slate-800 placeholder:text-slate-400 focus:outline-none focus:border-slate-800 font-mono"
                  />
                ) : (
                  <div className="relative">
                    <select
                      value={selectedModel}
                      onChange={(e) => setSelectedModel(e.target.value)}
                      disabled={loadingModels || models.length === 0}
                      className="w-full bg-white border border-slate-300 rounded-lg px-2.5 py-1.5 text-xs text-slate-800 focus:outline-none focus:border-slate-800 disabled:opacity-75 font-mono pr-7"
                    >
                      {models.length === 0 ? (
                        <option value="">
                          {loadingModels
                            ? 'Fetching models from API...'
                            : selectedProvider === 'LM Studio'
                            ? 'Start LM Studio or enter model manually'
                            : selectedProvider === 'Ollama'
                            ? 'Enter Ollama API key or start local Ollama'
                            : `Enter ${selectedProvider} API key to fetch models`}
                        </option>
                      ) : (
                        models.map((m, i) => (
                          <option key={i} value={m}>
                            {m}
                          </option>
                        ))
                      )}
                    </select>
                    {loadingModels && (
                      <Loader2 className="w-3.5 h-3.5 animate-spin text-slate-600 absolute right-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
                    )}
                  </div>
                )}
              </div>
            </div>

            {/* Base Endpoint URL */}
            <div>
              <label className="block text-xs font-medium text-slate-700 mb-1">
                API Base Endpoint URL
              </label>
              <input
                type="text"
                value={endpoint}
                onChange={(e) => setEndpoint(e.target.value)}
                placeholder={
                  selectedProvider === 'Ollama'
                    ? (apiKey ? 'https://ollama.com' : 'http://localhost:11434')
                    : selectedProvider === 'LM Studio'
                    ? 'http://localhost:1234/v1'
                    : 'Provider default endpoint'
                }
                className="w-full bg-white border border-slate-300 rounded-lg px-2.5 py-1.5 text-xs text-slate-800 font-mono focus:outline-none focus:border-slate-800"
              />
            </div>

            {/* API Key for provider */}
            {selectedProvider !== 'LM Studio' && (
              <div>
                <div className="flex items-center justify-between mb-1">
                  <label className="text-xs font-medium text-slate-700">
                    {selectedProvider} API Key {selectedProvider === 'Ollama' ? '(Optional)' : ''}
                  </label>
                  {apiKey && (
                    <span className="text-[10px] text-emerald-600 font-medium">Preloaded from Settings</span>
                  )}
                </div>
                <input
                  type="password"
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  placeholder={
                    selectedProvider === 'Anthropic'
                      ? 'sk-ant-api03-...'
                      : selectedProvider === 'Google Gemini'
                      ? 'AIzaSy...'
                      : selectedProvider === 'OpenAI'
                      ? 'sk-proj-...'
                      : selectedProvider === 'Groq'
                      ? 'gsk_...'
                      : selectedProvider === 'OpenRouter'
                      ? 'sk-or-v1-...'
                      : selectedProvider === 'Mistral AI'
                      ? 'Mistral API key...'
                      : 'Enter API key or leave blank for local'
                  }
                  className="w-full bg-white border border-slate-300 rounded-lg px-2.5 py-1.5 text-xs text-slate-800 placeholder:text-slate-400 focus:outline-none focus:border-slate-800 font-mono"
                />
              </div>
            )}
          </div>

          {/* Action Buttons */}
          <div className="pt-2 flex items-center justify-end gap-2 border-t border-slate-200">
            <button
              type="button"
              onClick={onClose}
              className="px-3.5 py-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting || files.length === 0 || !effectiveModel}
              className="px-4 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 disabled:bg-slate-200 disabled:text-slate-400 text-white text-xs font-semibold transition-colors flex items-center gap-1.5 shadow-2xs"
            >
              {submitting ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  <span>Starting...</span>
                </>
              ) : (
                <span>Start Extraction</span>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
