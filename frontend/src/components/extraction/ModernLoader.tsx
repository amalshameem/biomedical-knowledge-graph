import React from 'react';
import { Network, FileText, Cpu, Database, CheckCircle2, Loader2, AlertCircle, ArrowLeft, Layers } from 'lucide-react';
import { ExtractionProgressEvent } from '../../types';

interface ModernLoaderProps {
  progressEvent: ExtractionProgressEvent | null;
  projectName: string;
  onBackToHub?: () => void;
}

const STAGES = [
  { id: 'docling', label: 'Docling PDF Parsing', desc: 'Hierarchical chunking and table filtering' },
  { id: 'ner_gliner', label: 'GLiNER Biomedical NER', desc: '35 ontology labels extraction' },
  { id: 'llm_triples', label: 'LLM Triples & Evidence', desc: 'Strict standard relation extraction' },
  { id: 'normalizer', label: 'Entity Normalization', desc: 'HGNC / MeSH dictionary' },
  { id: 'pubmed', label: 'PubMed Enrichment', desc: 'NCBI Entrez verification & PMIDs' },
  { id: 'neo4j', label: 'Neo4j Graph Persistence', desc: 'Dual-write graph store sync' },
];

export const ModernLoader: React.FC<ModernLoaderProps> = ({ progressEvent, projectName, onBackToHub }) => {
  const currentStage = progressEvent?.stage || 'docling';
  const isError = currentStage === 'error';
  const progressPercent = Math.min(Math.round((progressEvent?.progress || 0.05) * 100), 100);

  const getStageStatus = (stageId: string) => {
    if (isError) return 'pending';
    const stageOrder = ['docling', 'ner_gliner', 'llm_triples', 'normalizer', 'pubmed', 'neo4j', 'completed'];
    const currentIndex = stageOrder.indexOf(currentStage);
    const stageIndex = stageOrder.indexOf(stageId);

    if (currentIndex > stageIndex || currentStage === 'completed') return 'completed';
    if (currentIndex === stageIndex) return 'active';
    return 'pending';
  };

  return (
    <div className="min-h-[70vh] flex flex-col items-center justify-center p-6 max-w-xl mx-auto animate-fadeIn">
      {/* Project & Header */}
      <div className="w-full mb-6 space-y-1.5 text-center">
        <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-slate-900 text-white shadow-2xs mb-2">
          <Loader2 className="w-3 h-3 animate-spin text-slate-300" />
          <span>Extraction in Progress</span>
        </div>
        <h2 className="text-xl font-bold text-slate-900 tracking-tight">
          {projectName}
        </h2>
        <p className="text-xs text-slate-500 font-mono max-w-md mx-auto truncate">
          {progressEvent?.message || 'Processing biomedical documents...'}
        </p>
      </div>

      {/* Error Card or Progress Card */}
      {isError ? (
        <div className="w-full bg-white border border-rose-200 rounded-xl p-6 shadow-xs mb-6 space-y-4 text-center">
          <div className="w-10 h-10 rounded-full bg-rose-50 border border-rose-200 flex items-center justify-center text-rose-600 mx-auto">
            <AlertCircle className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-slate-900">Pipeline Execution Failed</h3>
            <p className="text-xs text-rose-600 mt-1 font-mono">{progressEvent?.message}</p>
          </div>
          {onBackToHub && (
            <button
              onClick={onBackToHub}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-slate-900 hover:bg-slate-800 text-white text-xs font-semibold transition-colors shadow-2xs"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              <span>Back to Projects</span>
            </button>
          )}
        </div>
      ) : (
        <div className="w-full bg-white border border-slate-200 rounded-xl p-5 shadow-2xs mb-4 space-y-3">
          <div className="flex items-center justify-between text-xs font-medium">
            <span className="text-slate-700 font-semibold">Overall Pipeline Progress</span>
            <span className="text-slate-900 font-mono font-bold text-sm">
              {progressPercent}%
            </span>
          </div>

          <div className="h-2.5 w-full bg-slate-100 rounded-full overflow-hidden border border-slate-200">
            <div
              className="h-full bg-slate-900 rounded-full transition-all duration-300"
              style={{ width: `${progressPercent}%` }}
            />
          </div>

          {/* Live Metrics Row */}
          <div className="pt-1 flex items-center justify-between text-xs text-slate-500 font-mono">
            <div className="flex items-center gap-1.5">
              <Layers className="w-3.5 h-3.5 text-slate-400" />
              {progressEvent?.total_chunks ? (
                <span>Chunk <strong className="text-slate-800">{progressEvent.current_chunk}</strong> of <strong className="text-slate-800">{progressEvent.total_chunks}</strong></span>
              ) : (
                <span>Parsing PDF...</span>
              )}
            </div>
            <div className="flex items-center gap-1.5">
              <Network className="w-3.5 h-3.5 text-slate-400" />
              <span>Triples: <strong className="text-slate-900">{progressEvent?.triples_found || 0}</strong></span>
            </div>
          </div>
        </div>
      )}

      {/* Stage Checklist */}
      {!isError && (
        <div className="w-full bg-white border border-slate-200 rounded-xl divide-y divide-slate-100 overflow-hidden shadow-2xs">
          {STAGES.map((stage) => {
            const status = getStageStatus(stage.id);

            return (
              <div
                key={stage.id}
                className={`flex items-center justify-between px-4 py-3 text-xs transition-colors ${status === 'active' ? 'bg-slate-50' : ''
                  }`}
              >
                <div className="flex items-center gap-3">
                  {status === 'completed' ? (
                    <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                  ) : status === 'active' ? (
                    <Loader2 className="w-4 h-4 animate-spin text-slate-900 shrink-0" />
                  ) : (
                    <div className="w-4 h-4 rounded-full border border-slate-300 shrink-0" />
                  )}
                  <div>
                    <span className={`font-semibold ${status === 'active' ? 'text-slate-900' : status === 'completed' ? 'text-slate-800' : 'text-slate-400'}`}>
                      {stage.label}
                    </span>
                    <span className="text-[11px] text-slate-400 block">
                      {stage.desc}
                    </span>
                  </div>
                </div>

                <span className={`text-[10px] font-mono font-semibold uppercase tracking-wider px-2 py-0.5 rounded ${status === 'completed'
                    ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
                    : status === 'active'
                      ? 'bg-slate-900 text-white'
                      : 'text-slate-400'
                  }`}>
                  {status}
                </span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
