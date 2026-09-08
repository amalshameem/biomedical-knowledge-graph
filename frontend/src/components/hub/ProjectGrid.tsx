import React from 'react';
import { Plus, Search, FolderKanban, Network, FileText, Sparkles, Database, CheckCircle2, BookOpen } from 'lucide-react';
import { Project } from '../../types';
import { ProjectCard } from './ProjectCard';

interface ProjectGridProps {
  projects: Project[];
  searchQuery: string;
  onSearchChange: (q: string) => void;
  onOpenProject: (project: Project) => void;
  onDeleteProject: (id: string, e: React.MouseEvent) => void;
  onNewProject: () => void;
}

export const ProjectGrid: React.FC<ProjectGridProps> = ({
  projects,
  searchQuery,
  onSearchChange,
  onOpenProject,
  onDeleteProject,
  onNewProject,
}) => {
  const filteredProjects = projects.filter(
    (p) =>
      p.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (p.description && p.description.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  const totalTriples = projects.reduce((acc, p) => acc + (p.total_triples || 0), 0);
  const totalDocs = projects.reduce((acc, p) => acc + (p.documents_count ?? p.documents?.length ?? (p.total_chunks > 0 ? 1 : 0)), 0);
  const completedProjects = projects.filter((p) => p.status === 'completed').length;

  return (
    <div className="max-w-7xl mx-auto px-6 py-8 space-y-6">
      {/* Action Header & Search */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-200">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight">
            Projects
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Biomedical literature extraction and interactive knowledge graph exploration.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          {/* Search bar */}
          <div className="relative">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => onSearchChange(e.target.value)}
              placeholder="Search projects..."
              className="bg-white border border-slate-300 rounded-lg pl-8 pr-3.5 py-1.5 text-xs text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-slate-800 focus:ring-1 focus:ring-slate-800 w-52 sm:w-64 transition-all shadow-2xs"
            />
          </div>

          {/* New Project Button */}
          <button
            onClick={onNewProject}
            className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-white font-semibold text-xs transition-colors shadow-xs shrink-0"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>New Project</span>
          </button>
        </div>
      </div>

      {/* Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
        {/* "+ New Project" Dropzone Tile */}
        <div
          onClick={onNewProject}
          className="group border-2 border-dashed border-slate-300 hover:border-slate-800 rounded-xl p-6 min-h-[190px] flex flex-col items-center justify-center cursor-pointer transition-all bg-slate-50/60 hover:bg-slate-100/70 text-center shadow-2xs hover:shadow-xs"
        >
          <div className="w-9 h-9 rounded-lg bg-white border border-slate-300 group-hover:border-slate-800 group-hover:bg-slate-900 group-hover:text-white flex items-center justify-center text-slate-700 transition-all mb-2.5 shadow-2xs">
            <Plus className="w-4 h-4" />
          </div>
          <h3 className="text-xs font-bold text-slate-900 transition-colors">
            Create New Project
          </h3>
          <p className="text-[11px] text-slate-500 mt-1 max-w-[200px] leading-relaxed">
            Upload biomedical research PDFs for GLiNER & LLM triple extraction
          </p>
        </div>

        {/* Existing Project Cards */}
        {filteredProjects.map((project) => (
          <ProjectCard
            key={project.id}
            project={project}
            onOpen={onOpenProject}
            onDelete={onDeleteProject}
          />
        ))}
      </div>

      {filteredProjects.length === 0 && searchQuery && (
        <div className="text-center py-16 text-slate-500 text-sm bg-white rounded-xl border border-slate-200 p-8">
          <BookOpen className="w-8 h-8 text-slate-300 mx-auto mb-2" />
          <p>No workspaces found matching "<span className="text-slate-800 font-semibold">{searchQuery}</span>".</p>
        </div>
      )}
    </div>
  );
};
