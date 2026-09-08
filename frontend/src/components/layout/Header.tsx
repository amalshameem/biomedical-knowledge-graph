import React from 'react';
import { Settings, Network, ChevronRight, Home, Database, Globe } from 'lucide-react';
import { Project } from '../../types';

interface HeaderProps {
  currentProject: Project | null;
  onNavigateHome: () => void;
  onOpenSettings: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  currentProject,
  onNavigateHome,
  onOpenSettings,
}) => {
  return (
    <header className="h-14 border-b border-slate-200 bg-white/95 backdrop-blur-xs px-6 flex items-center justify-between sticky top-0 z-40 shadow-2xs">
      <div className="flex items-center gap-3">
        <button
          onClick={onNavigateHome}
          className="flex items-center gap-2.5 text-slate-900 hover:text-slate-700 transition-colors font-bold text-sm tracking-tight group"
        >
          <div className="w-7 h-7 rounded-lg bg-slate-900 flex items-center justify-center text-white shadow-xs group-hover:bg-slate-800 transition-colors">
            <Network className="w-4 h-4" />
          </div>
          <span className="font-bold tracking-tight text-slate-900 text-sm">
            Biomedical Knowledge Graph
          </span>
        </button>

        {currentProject && (
          <div className="flex items-center gap-1.5 text-xs text-slate-400 ml-2">
            <ChevronRight className="w-3.5 h-3.5 text-slate-300" />
            <button
              onClick={onNavigateHome}
              className="hover:text-slate-900 flex items-center gap-1 transition-colors font-medium text-slate-600"
            >
              <Home className="w-3.5 h-3.5" />
              <span>Projects</span>
            </button>
            <ChevronRight className="w-3.5 h-3.5 text-slate-300" />
            <span className="text-slate-900 font-semibold px-2.5 py-0.5 rounded-md bg-slate-100 border border-slate-200/80 max-w-sm truncate text-xs">
              {currentProject.name}
            </span>
          </div>
        )}
      </div>

      <div className="flex items-center gap-2">
        <button
          onClick={onOpenSettings}
          className="px-3 py-1.5 rounded-lg bg-white hover:bg-slate-50 border border-slate-200 text-slate-700 hover:text-slate-900 transition-all flex items-center gap-1.5 text-xs font-semibold shadow-2xs hover:border-slate-300"
          title="Global Settings (LLM Providers, Neo4j, Entrez)"
        >
          <Settings className="w-3.5 h-3.5 text-slate-500" />
          <span>Settings</span>
        </button>
      </div>
    </header>
  );
};
