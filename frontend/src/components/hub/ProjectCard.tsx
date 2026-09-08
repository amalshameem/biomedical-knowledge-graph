import React from 'react';
import { Network, FileText, Trash2, ArrowUpRight, CheckCircle2, AlertCircle, Loader2 } from 'lucide-react';
import { Project } from '../../types';

interface ProjectCardProps {
  project: Project;
  onOpen: (project: Project) => void;
  onDelete: (id: string, e: React.MouseEvent) => void;
}

export const ProjectCard: React.FC<ProjectCardProps> = ({ project, onOpen, onDelete }) => {
  const getStatusBadge = () => {
    switch (project.status) {
      case 'completed':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10.5px] font-semibold bg-emerald-50 text-emerald-800 border border-emerald-300">
            <CheckCircle2 className="w-3 h-3 text-emerald-600" />
            Ready
          </span>
        );
      case 'processing':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10.5px] font-semibold bg-slate-100 text-slate-700 border border-slate-300 animate-pulse">
            <Loader2 className="w-3 h-3 animate-spin text-slate-700" />
            Processing
          </span>
        );
      case 'failed':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10.5px] font-semibold bg-rose-50 text-rose-700 border border-rose-200">
            <AlertCircle className="w-3 h-3 text-rose-600" />
            Failed
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10.5px] font-semibold bg-slate-100 text-slate-600 border border-slate-200">
            Draft
          </span>
        );
    }
  };

  const formatDate = (isoString: string) => {
    try {
      const d = new Date(isoString);
      return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
    } catch {
      return '';
    }
  };

  const handleDelete = (e: React.MouseEvent) => {
    e.stopPropagation();
    onDelete(project.id, e);
  };

  const docsCount = project.documents_count ?? project.documents?.length ?? (project.total_chunks > 0 ? 1 : 0);

  return (
    <div
      onClick={() => onOpen(project)}
      className="group relative bg-white border border-slate-200 hover:border-slate-400 rounded-xl p-4 cursor-pointer transition-all flex flex-col justify-between overflow-hidden shadow-2xs hover:shadow-xs"
    >
      <div>
        {/* Card Header */}
        <div className="flex items-start justify-between gap-2 mb-2.5">
          <div className="w-7 h-7 rounded-md bg-slate-100 border border-slate-200 flex items-center justify-center text-slate-700 group-hover:bg-slate-900 group-hover:text-white transition-colors">
            <Network className="w-3.5 h-3.5" />
          </div>
          <div className="flex items-center gap-1.5">
            {getStatusBadge()}
            <button
              type="button"
              onClick={handleDelete}
              className="p-1 rounded opacity-0 group-hover:opacity-100 hover:bg-rose-50 text-slate-400 hover:text-rose-600 transition-opacity"
              title="Delete Project"
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {/* Project Title & Description */}
        <h3 className="text-sm font-bold text-slate-900 group-hover:text-slate-900 transition-colors line-clamp-1 mb-1">
          {project.name}
        </h3>
        <p className="text-xs text-slate-500 line-clamp-2 min-h-[2rem]">
          {project.description || (project.model ? `Model: ${project.model}` : 'No description provided')}
        </p>
      </div>

      {/* Metrics & Footer */}
      <div className="pt-3 mt-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500 font-medium">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1" title="Extracted Triples">
            <Network className="w-3 h-3 text-slate-600" />
            <span className="font-bold text-slate-800 font-mono text-xs">{project.total_triples}</span>
            <span className="text-[11px] text-slate-500">triples</span>
          </div>
          <div className="flex items-center gap-1" title="Source Documents">
            <FileText className="w-3 h-3 text-slate-400" />
            <span className="font-bold text-slate-800 font-mono text-xs">{docsCount}</span>
            <span className="text-[11px] text-slate-500">{docsCount === 1 ? 'doc' : 'docs'}</span>
          </div>
        </div>

        <span className="text-[10px] text-slate-400 font-mono">
          {formatDate(project.created_at)}
        </span>
      </div>
    </div>
  );
};
