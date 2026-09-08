import React, { useState, useEffect } from 'react';
import { X, Key, Database, Mail, Save, CheckCircle2, Server, Cpu, Eye, EyeOff, Globe, Sparkles } from 'lucide-react';
import { GlobalSettings } from '../../types';
import { api } from '../../services/api';

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const SettingsModal: React.FC<SettingsModalProps> = ({ isOpen, onClose }) => {
  const [activeTab, setActiveTab] = useState<'litellm' | 'pubmed' | 'neo4j'>('litellm');
  const [showKeys, setShowKeys] = useState<Record<string, boolean>>({});

  const [settings, setSettings] = useState<GlobalSettings>({
    default_provider: 'Ollama',
    openrouter_api_key: '',
    ollama_endpoint: 'http://localhost:11434',
    ollama_api_key: '',
    lmstudio_endpoint: 'http://localhost:1234/v1',
    anthropic_api_key: '',
    gemini_api_key: '',
    openai_api_key: '',
    openai_endpoint: 'https://api.openai.com/v1',
    groq_api_key: '',
    mistral_api_key: '',
    entrez_email: 'bot@example.com',
    entrez_api_key: '',
    neo4j_uri: 'bolt://localhost:7687',
    neo4j_user: 'neo4j',
    neo4j_password: '',
  });

  const [loading, setLoading] = useState(false);
  const [savedSuccess, setSavedSuccess] = useState(false);

  useEffect(() => {
    if (isOpen) {
      api.getSettings().then((data) => {
        setSettings((prev) => ({ ...prev, ...data }));
      }).catch(console.error);
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const toggleShowKey = (field: string) => {
    setShowKeys((prev) => ({ ...prev, [field]: !prev[field] }));
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      await api.updateSettings(settings);
      setSavedSuccess(true);
      setTimeout(() => {
        setSavedSuccess(false);
        onClose();
      }, 900);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const isConfigured = (val?: string) => Boolean(val && val.trim().length > 0);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-xs animate-fadeIn">
      <div className="bg-white border border-slate-300 rounded-2xl w-full max-w-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between bg-slate-50/80">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-slate-900 flex items-center justify-center text-white shadow-xs">
              <Server className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-slate-900">System Configuration & LiteLLM Settings</h2>
              <p className="text-[11px] text-slate-500">Configure global AI providers, PubMed literature queries, and Neo4j database</p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-200 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Tab Navigation */}
        <div className="flex border-b border-slate-200 bg-white px-6 gap-2 text-xs font-semibold">
          <button
            type="button"
            onClick={() => setActiveTab('litellm')}
            className={`py-3 px-3.5 border-b-2 transition-all flex items-center gap-2 ${activeTab === 'litellm'
                ? 'border-indigo-600 text-indigo-700 font-bold'
                : 'border-transparent text-slate-500 hover:text-slate-800'
              }`}
          >
            <Cpu className="w-3.5 h-3.5" />
            <span>LiteLLM Providers & Keys</span>
          </button>

          <button
            type="button"
            onClick={() => setActiveTab('pubmed')}
            className={`py-3 px-3.5 border-b-2 transition-all flex items-center gap-2 ${activeTab === 'pubmed'
                ? 'border-indigo-600 text-indigo-700 font-bold'
                : 'border-transparent text-slate-500 hover:text-slate-800'
              }`}
          >
            <Mail className="w-3.5 h-3.5" />
            <span>NCBI PubMed</span>
          </button>

          <button
            type="button"
            onClick={() => setActiveTab('neo4j')}
            className={`py-3 px-3.5 border-b-2 transition-all flex items-center gap-2 ${activeTab === 'neo4j'
                ? 'border-indigo-600 text-indigo-700 font-bold'
                : 'border-transparent text-slate-500 hover:text-slate-800'
              }`}
          >
            <Database className="w-3.5 h-3.5" />
            <span>Neo4j Graph Database</span>
          </button>
        </div>

        {/* Content Form */}
        <form onSubmit={handleSave} className="p-6 overflow-y-auto space-y-5 flex-1 text-xs custom-scrollbar">
          {/* TAB 1: LITELLM PROVIDERS */}
          {activeTab === 'litellm' && (
            <div className="space-y-4">
              {/* Default Provider Dropdown */}
              <div className="p-3.5 bg-indigo-50/60 border border-indigo-200 rounded-xl space-y-1.5">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-bold text-indigo-950 flex items-center gap-1.5">
                    Preferred Default LLM Provider
                  </label>
                  <span className="text-[10px] font-mono text-indigo-700 bg-white px-2 py-0.5 rounded border border-indigo-200">
                    LiteLLM Gateway
                  </span>
                </div>
                <select
                  value={settings.default_provider || 'Ollama'}
                  onChange={(e) => setSettings({ ...settings, default_provider: e.target.value })}
                  className="w-full bg-white border border-indigo-300 rounded-lg px-3 py-1.5 text-xs text-slate-900 font-medium focus:outline-none focus:border-indigo-600 focus:ring-1 focus:ring-indigo-600 shadow-2xs"
                >
                  <option value="Ollama">Ollama (Local / Cloud)</option>
                  <option value="LM Studio">LM Studio (Local OpenAI Format)</option>
                  <option value="OpenRouter">OpenRouter (100+ Models)</option>
                  <option value="Anthropic">Anthropic (Claude 3.5 Sonnet / Haiku)</option>
                  <option value="Google Gemini">Google Gemini (Gemini 2.0 Flash / Pro)</option>
                  <option value="OpenAI">OpenAI (GPT-4o / GPT-4o-mini / o1 / o3)</option>
                  <option value="Groq">Groq (Fast Llama 3.3 / DeepSeek R1)</option>
                  <option value="Mistral AI">Mistral AI (Mistral Large / Codestral)</option>
                </select>
                <p className="text-[11px] text-indigo-700 leading-relaxed">
                  This provider will be pre-selected when creating new extraction workflows.
                </p>
              </div>

              <div className="text-[11px] font-bold uppercase tracking-wider text-slate-400 pt-1">
                Provider Endpoints & API Credentials
              </div>

              {/* Local Providers Grid */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
                {/* Ollama (Local or Cloud) */}
                <div className="p-3.5 bg-slate-50 border border-slate-200 rounded-xl space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-slate-900">Ollama (Local / Cloud)</span>
                    {(isConfigured(settings.ollama_endpoint) || isConfigured(settings.ollama_api_key)) && (
                      <span className="text-[10px] font-mono text-emerald-700 bg-emerald-50 px-1.5 py-0.2 rounded border border-emerald-200 flex items-center gap-1">
                        <CheckCircle2 className="w-2.5 h-2.5" /> Ready
                      </span>
                    )}
                  </div>
                  <div>
                    <label className="block text-[10px] font-medium text-slate-500 mb-0.5">Base Endpoint URL</label>
                    <input
                      type="text"
                      value={settings.ollama_endpoint || ''}
                      onChange={(e) => setSettings({ ...settings, ollama_endpoint: e.target.value })}
                      placeholder="http://localhost:11434 or https://ollama.com/v1"
                      className="w-full bg-white border border-slate-300 rounded-lg px-2.5 py-1 text-xs text-slate-900 focus:outline-none focus:border-slate-800"
                    />
                  </div>
                  <div>
                    <label className="block text-[10px] font-medium text-slate-500 mb-0.5">API Key (Required for Ollama Cloud)</label>
                    <input
                      type={showKeys['ollama'] ? 'text' : 'password'}
                      value={settings.ollama_api_key || ''}
                      onChange={(e) => setSettings({ ...settings, ollama_api_key: e.target.value })}
                      placeholder="Enter key for Ollama Cloud"
                      className="w-full bg-white border border-slate-300 rounded-lg px-2.5 py-1 text-xs text-slate-900 focus:outline-none focus:border-slate-800"
                    />
                  </div>
                </div>

                {/* LM Studio */}
                <div className="p-3.5 bg-slate-50 border border-slate-200 rounded-xl space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-slate-900">LM Studio</span>
                    {isConfigured(settings.lmstudio_endpoint) && (
                      <span className="text-[10px] font-mono text-emerald-700 bg-emerald-50 px-1.5 py-0.2 rounded border border-emerald-200 flex items-center gap-1">
                        <CheckCircle2 className="w-2.5 h-2.5" /> Ready
                      </span>
                    )}
                  </div>
                  <div>
                    <label className="block text-[10px] font-medium text-slate-500 mb-0.5">Base Endpoint URL</label>
                    <input
                      type="text"
                      value={settings.lmstudio_endpoint || ''}
                      onChange={(e) => setSettings({ ...settings, lmstudio_endpoint: e.target.value })}
                      placeholder="http://localhost:1234/v1"
                      className="w-full bg-white border border-slate-300 rounded-lg px-2.5 py-1 text-xs text-slate-900 focus:outline-none focus:border-slate-800"
                    />
                  </div>
                  <p className="text-[10.5px] text-slate-500 pt-3">
                    Runs local models using standard OpenAI-compatible completions.
                  </p>
                </div>
              </div>

              {/* Cloud API Keys Grid */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
                {/* OpenRouter */}
                <div className="p-3.5 bg-slate-50 border border-slate-200 rounded-xl space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-slate-900">OpenRouter</span>
                    {isConfigured(settings.openrouter_api_key) ? (
                      <span className="text-[10px] font-mono text-emerald-700 bg-emerald-50 px-1.5 py-0.2 rounded border border-emerald-200">Active</span>
                    ) : (
                      <span className="text-[10px] font-mono text-slate-400">Optional</span>
                    )}
                  </div>
                  <div className="relative">
                    <input
                      type={showKeys['openrouter'] ? 'text' : 'password'}
                      value={settings.openrouter_api_key || ''}
                      onChange={(e) => setSettings({ ...settings, openrouter_api_key: e.target.value })}
                      placeholder="sk-or-v1-..."
                      className="w-full bg-white border border-slate-300 rounded-lg pl-2.5 pr-8 py-1 text-xs text-slate-900 focus:outline-none focus:border-slate-800"
                    />
                    <button
                      type="button"
                      onClick={() => toggleShowKey('openrouter')}
                      className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-700"
                    >
                      {showKeys['openrouter'] ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                    </button>
                  </div>
                </div>

                {/* Anthropic Claude */}
                <div className="p-3.5 bg-slate-50 border border-slate-200 rounded-xl space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-slate-900">Anthropic (Claude)</span>
                    {isConfigured(settings.anthropic_api_key) ? (
                      <span className="text-[10px] font-mono text-emerald-700 bg-emerald-50 px-1.5 py-0.2 rounded border border-emerald-200">Active</span>
                    ) : (
                      <span className="text-[10px] font-mono text-slate-400">Optional</span>
                    )}
                  </div>
                  <div className="relative">
                    <input
                      type={showKeys['anthropic'] ? 'text' : 'password'}
                      value={settings.anthropic_api_key || ''}
                      onChange={(e) => setSettings({ ...settings, anthropic_api_key: e.target.value })}
                      placeholder="sk-ant-api03-..."
                      className="w-full bg-white border border-slate-300 rounded-lg pl-2.5 pr-8 py-1 text-xs text-slate-900 focus:outline-none focus:border-slate-800"
                    />
                    <button
                      type="button"
                      onClick={() => toggleShowKey('anthropic')}
                      className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-700"
                    >
                      {showKeys['anthropic'] ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                    </button>
                  </div>
                </div>

                {/* Google Gemini */}
                <div className="p-3.5 bg-slate-50 border border-slate-200 rounded-xl space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-slate-900">Google Gemini</span>
                    {isConfigured(settings.gemini_api_key) ? (
                      <span className="text-[10px] font-mono text-emerald-700 bg-emerald-50 px-1.5 py-0.2 rounded border border-emerald-200">Active</span>
                    ) : (
                      <span className="text-[10px] font-mono text-slate-400">Optional</span>
                    )}
                  </div>
                  <div className="relative">
                    <input
                      type={showKeys['gemini'] ? 'text' : 'password'}
                      value={settings.gemini_api_key || ''}
                      onChange={(e) => setSettings({ ...settings, gemini_api_key: e.target.value })}
                      placeholder="AIzaSy..."
                      className="w-full bg-white border border-slate-300 rounded-lg pl-2.5 pr-8 py-1 text-xs text-slate-900 focus:outline-none focus:border-slate-800"
                    />
                    <button
                      type="button"
                      onClick={() => toggleShowKey('gemini')}
                      className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-700"
                    >
                      {showKeys['gemini'] ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                    </button>
                  </div>
                </div>

                {/* OpenAI */}
                <div className="p-3.5 bg-slate-50 border border-slate-200 rounded-xl space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-slate-900">OpenAI</span>
                    {isConfigured(settings.openai_api_key) ? (
                      <span className="text-[10px] font-mono text-emerald-700 bg-emerald-50 px-1.5 py-0.2 rounded border border-emerald-200">Active</span>
                    ) : (
                      <span className="text-[10px] font-mono text-slate-400">Optional</span>
                    )}
                  </div>
                  <div className="relative">
                    <input
                      type={showKeys['openai'] ? 'text' : 'password'}
                      value={settings.openai_api_key || ''}
                      onChange={(e) => setSettings({ ...settings, openai_api_key: e.target.value })}
                      placeholder="sk-proj-..."
                      className="w-full bg-white border border-slate-300 rounded-lg pl-2.5 pr-8 py-1 text-xs text-slate-900 focus:outline-none focus:border-slate-800"
                    />
                    <button
                      type="button"
                      onClick={() => toggleShowKey('openai')}
                      className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-700"
                    >
                      {showKeys['openai'] ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                    </button>
                  </div>
                </div>

                {/* Groq */}
                <div className="p-3.5 bg-slate-50 border border-slate-200 rounded-xl space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-slate-900">Groq (Ultra-Fast)</span>
                    {isConfigured(settings.groq_api_key) ? (
                      <span className="text-[10px] font-mono text-emerald-700 bg-emerald-50 px-1.5 py-0.2 rounded border border-emerald-200">Active</span>
                    ) : (
                      <span className="text-[10px] font-mono text-slate-400">Optional</span>
                    )}
                  </div>
                  <div className="relative">
                    <input
                      type={showKeys['groq'] ? 'text' : 'password'}
                      value={settings.groq_api_key || ''}
                      onChange={(e) => setSettings({ ...settings, groq_api_key: e.target.value })}
                      placeholder="gsk_..."
                      className="w-full bg-white border border-slate-300 rounded-lg pl-2.5 pr-8 py-1 text-xs text-slate-900 focus:outline-none focus:border-slate-800"
                    />
                    <button
                      type="button"
                      onClick={() => toggleShowKey('groq')}
                      className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-700"
                    >
                      {showKeys['groq'] ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                    </button>
                  </div>
                </div>

                {/* Mistral AI */}
                <div className="p-3.5 bg-slate-50 border border-slate-200 rounded-xl space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-slate-900">Mistral AI</span>
                    {isConfigured(settings.mistral_api_key) ? (
                      <span className="text-[10px] font-mono text-emerald-700 bg-emerald-50 px-1.5 py-0.2 rounded border border-emerald-200">Active</span>
                    ) : (
                      <span className="text-[10px] font-mono text-slate-400">Optional</span>
                    )}
                  </div>
                  <div className="relative">
                    <input
                      type={showKeys['mistral'] ? 'text' : 'password'}
                      value={settings.mistral_api_key || ''}
                      onChange={(e) => setSettings({ ...settings, mistral_api_key: e.target.value })}
                      placeholder="Mistral API key..."
                      className="w-full bg-white border border-slate-300 rounded-lg pl-2.5 pr-8 py-1 text-xs text-slate-900 focus:outline-none focus:border-slate-800"
                    />
                    <button
                      type="button"
                      onClick={() => toggleShowKey('mistral')}
                      className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-700"
                    >
                      {showKeys['mistral'] ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TAB 2: PUBMED SETTINGS */}
          {activeTab === 'pubmed' && (
            <div className="space-y-4">
              <div className="p-3.5 bg-slate-50 border border-slate-200 rounded-xl space-y-3">
                <div>
                  <label className="block text-xs font-bold text-slate-900 mb-1">
                    Contact Email (NCBI Required)
                  </label>
                  <input
                    type="email"
                    value={settings.entrez_email || ''}
                    onChange={(e) => setSettings({ ...settings, entrez_email: e.target.value })}
                    placeholder="researcher@institution.edu"
                    className="w-full bg-white border border-slate-300 rounded-lg px-3 py-1.5 text-xs text-slate-900 focus:outline-none focus:border-slate-800"
                    required
                  />
                  <p className="text-[11px] text-slate-500 mt-1">
                    NCBI E-Utilities requires a valid contact email to identify client requests.
                  </p>
                </div>

                <div>
                  <label className="block text-xs font-bold text-slate-900 mb-1">
                    Entrez API Key (Optional)
                  </label>
                  <input
                    type={showKeys['entrez'] ? 'text' : 'password'}
                    value={settings.entrez_api_key || ''}
                    onChange={(e) => setSettings({ ...settings, entrez_api_key: e.target.value })}
                    placeholder="Optional NCBI Entrez API key"
                    className="w-full bg-white border border-slate-300 rounded-lg px-3 py-1.5 text-xs text-slate-900 focus:outline-none focus:border-slate-800"
                  />
                  <p className="text-[11px] text-slate-500 mt-1">
                    Increases maximum request concurrency from 3 req/sec to 10 req/sec for faster literature enrichment.
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* TAB 3: NEO4J DATABASE */}
          {activeTab === 'neo4j' && (
            <div className="space-y-4">
              <div className="p-3.5 bg-slate-50 border border-slate-200 rounded-xl space-y-3">
                <div>
                  <label className="block text-xs font-bold text-slate-900 mb-1">
                    Neo4j Bolt URI
                  </label>
                  <input
                    type="text"
                    value={settings.neo4j_uri || ''}
                    onChange={(e) => setSettings({ ...settings, neo4j_uri: e.target.value })}
                    placeholder="bolt://localhost:7687"
                    className="w-full bg-white border border-slate-300 rounded-lg px-3 py-1.5 text-xs text-slate-900 focus:outline-none focus:border-slate-800"
                    required
                  />
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-bold text-slate-900 mb-1">Username</label>
                    <input
                      type="text"
                      value={settings.neo4j_user || ''}
                      onChange={(e) => setSettings({ ...settings, neo4j_user: e.target.value })}
                      placeholder="neo4j"
                      className="w-full bg-white border border-slate-300 rounded-lg px-3 py-1.5 text-xs text-slate-900 focus:outline-none focus:border-slate-800"
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-bold text-slate-900 mb-1">Password</label>
                    <input
                      type="password"
                      value={settings.neo4j_password || ''}
                      onChange={(e) => setSettings({ ...settings, neo4j_password: e.target.value })}
                      placeholder="••••••••"
                      className="w-full bg-white border border-slate-300 rounded-lg px-3 py-1.5 text-xs text-slate-900 focus:outline-none focus:border-slate-800"
                    />
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Footer actions */}
          <div className="pt-3 border-t border-slate-100 flex items-center justify-between">
            <div className="text-[11px] text-slate-500 font-medium">
              Changes are immediately applied to new extractions.
            </div>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={onClose}
                className="px-3.5 py-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold transition-colors"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={loading}
                className="px-4 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-white text-xs font-semibold transition-all shadow-xs flex items-center gap-1.5"
              >
                {savedSuccess ? (
                  <>
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                    <span>Settings Saved!</span>
                  </>
                ) : (
                  <>
                    <Save className="w-3.5 h-3.5" />
                    <span>{loading ? 'Saving...' : 'Save All Settings'}</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
};

