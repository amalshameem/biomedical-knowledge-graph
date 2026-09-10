import React, { useState } from 'react';
import { Network, Table, Download, Layers, Clock } from 'lucide-react';
import { Project, CytoscapeGraphData } from '../../types';
import { CytoscapeGraph } from '../graph/CytoscapeGraph';
import { TriplesTable } from '../extraction/TriplesTable';
import { ExportCenter } from '../export/ExportCenter';

interface WorkspaceProps {
  project: Project;
  graphData: CytoscapeGraphData;
  minDegree: number;
  onMinDegreeChange: (deg: number) => void;
  selectedType: string;
  onSelectType: (type: string) => void;
}

export const Workspace: React.FC<WorkspaceProps> = ({
  project,
  graphData,
  minDegree,
  onMinDegreeChange,
  selectedType,
  onSelectType,
}) => {
  const [activeTab, setActiveTab] = useState<'graph' | 'table' | 'export'>('graph');
  const totalTriplesCount = project.triples?.length ?? project.total_triples ?? 0;

  return (
    <div className="w-full h-[calc(100vh-56px)] flex flex-col px-4 sm:px-6 py-3 gap-2.5 overflow-hidden animate-fadeIn">
      {/* Workspace Top Toolbar */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-2.5 bg-white border border-slate-200 rounded-xl px-4 py-2 shadow-xs shrink-0">
        {/* Project Info */}
        <div className="flex items-center gap-3">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-800 px-2 py-0.5 rounded bg-emerald-50 border border-emerald-300">
                Ready
              </span>
              <span className="text-xs text-slate-500 font-mono">
                {project.model || 'Default Model'}
              </span>
            </div>
            <h1 className="text-base font-bold text-slate-900 tracking-tight leading-tight mt-0.5 truncate max-w-md">
              {project.name}
            </h1>
          </div>
        </div>

        {/* Navigation Tabs */}
        <div className="flex items-center bg-slate-100 p-0.5 rounded-lg border border-slate-200 text-xs font-medium self-start lg:self-center">
          <button
            onClick={() => setActiveTab('graph')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md transition-all ${
              activeTab === 'graph'
                ? 'bg-white text-slate-900 font-semibold shadow-2xs border border-slate-200/80'
                : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200/60'
            }`}
          >
            <Network className="w-3.5 h-3.5" />
            <span>Interactive Graph</span>
          </button>

          <button
            onClick={() => setActiveTab('table')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md transition-all ${
              activeTab === 'table'
                ? 'bg-white text-slate-900 font-semibold shadow-2xs border border-slate-200/80'
                : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200/60'
            }`}
          >
            <Table className="w-3.5 h-3.5" />
            <span>Triples & Evidence Table</span>
          </button>

          <button
            onClick={() => setActiveTab('export')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md transition-all ${
              activeTab === 'export'
                ? 'bg-white text-slate-900 font-semibold shadow-2xs border border-slate-200/80'
                : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200/60'
            }`}
          >
            <Download className="w-3.5 h-3.5" />
            <span>Export Center</span>
          </button>
        </div>

        {/* Metric Badges */}
        <div className="flex items-center gap-2 text-xs self-end lg:self-center">
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-slate-50 border border-slate-200">
            <Network className="w-3.5 h-3.5 text-slate-600" />
            <span className="text-slate-900 font-bold font-mono text-xs">{totalTriplesCount}</span>
            <span className="text-slate-500 text-[11px]">triples</span>
          </div>

          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-slate-50 border border-slate-200">
            <Layers className="w-3.5 h-3.5 text-slate-600" />
            <span className="text-slate-900 font-bold font-mono text-xs">{project.total_chunks}</span>
            <span className="text-slate-500 text-[11px]">chunks</span>
          </div>

          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-slate-50 border border-slate-200">
            <Clock className="w-3.5 h-3.5 text-slate-500" />
            <span className="text-slate-900 font-mono text-xs font-semibold">{project.execution_time.toFixed(1)}s</span>
          </div>
        </div>
      </div>

      {/* Main Full-Height Content Area */}
      <div className="flex-1 min-h-0 w-full flex flex-col overflow-hidden">
        {activeTab === 'graph' && (
          <CytoscapeGraph
            graphData={graphData}
            minDegree={minDegree}
            onMinDegreeChange={onMinDegreeChange}
            selectedType={selectedType}
            onSelectType={onSelectType}
            nerMode={project.ner_mode}
          />
        )}

        {activeTab === 'table' && (
          <div className="flex-1 min-h-0 overflow-y-auto pr-1">
            <TriplesTable triples={project.triples || []} projectName={project.name} />
          </div>
        )}

        {activeTab === 'export' && (
          <div className="flex-1 min-h-0 overflow-y-auto pr-1">
            <ExportCenter project={project} />
          </div>
        )}
      </div>
    </div>
  );
};
