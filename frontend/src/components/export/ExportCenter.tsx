import React from 'react';
import { Download, Archive, FileSpreadsheet, Network, FileCode, CheckCircle2 } from 'lucide-react';
import { Project } from '../../types';
import { api } from '../../services/api';

interface ExportCenterProps {
  project: Project;
}

export const ExportCenter: React.FC<ExportCenterProps> = ({ project }) => {
  const zipUrl = api.getExportZipUrl(project.id);
  const csvUrl = api.getExportCsvUrl(project.id);
  const graphmlUrl = api.getExportGraphmlUrl(project.id);

  return (
    <div className="max-w-4xl mx-auto space-y-6 py-4 animate-fadeIn">
      <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-xs">
        <div className="flex items-center gap-3 mb-2">
          <div className="w-9 h-9 rounded-lg bg-slate-100 border border-slate-200 text-slate-700 flex items-center justify-center">
            <Archive className="w-4 h-4" />
          </div>
          <div>
            <h2 className="text-base font-bold text-slate-900">Export & Download Center</h2>
            <p className="text-xs text-slate-500">
              Download structured data, graph files, and extraction archives.
            </p>
          </div>
        </div>

        {/* Primary ZIP Bundle Button */}
        <div className="mt-5 p-4 rounded-xl bg-slate-50 border border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <span className="text-[10px] font-bold text-slate-700 uppercase tracking-wider bg-slate-200/70 border border-slate-300 px-2 py-0.5 rounded">
              Complete Bundle
            </span>
            <h3 className="text-sm font-bold text-slate-900 mt-1">
              Full Knowledge Graph Archive (ZIP)
            </h3>
            <p className="text-xs text-slate-600 mt-0.5 max-w-lg">
              Includes combined CSV with evidence, GraphML file (Cytoscape/Gephi), and JSON run metadata.
            </p>
          </div>

          <a
            href={zipUrl}
            download
            className="flex items-center justify-center gap-1.5 px-4 py-2 rounded-lg bg-slate-900 hover:bg-slate-800 text-white font-semibold text-xs transition-colors shrink-0 shadow-2xs"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Download ZIP</span>
          </a>
        </div>

        {/* Individual File Download Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-6">
          {/* CSV Card */}
          <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 flex items-center justify-between gap-3 shadow-2xs">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-emerald-50 border border-emerald-100 text-emerald-600 flex items-center justify-center">
                <FileSpreadsheet className="w-4 h-4" />
              </div>
              <div>
                <h4 className="text-xs font-bold text-slate-900">CSV Triples Table</h4>
                <span className="text-[10px] text-slate-500">Entities, relations, evidence & PMIDs</span>
              </div>
            </div>
            <a
              href={csvUrl}
              download
              className="p-2 rounded-lg bg-white hover:bg-slate-100 border border-slate-200 text-slate-600 hover:text-slate-900 transition-colors shadow-2xs"
              title="Download CSV"
            >
              <Download className="w-4 h-4" />
            </a>
          </div>

          {/* GraphML Card */}
          <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 flex items-center justify-between gap-3 shadow-2xs">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-cyan-50 border border-cyan-100 text-cyan-600 flex items-center justify-center">
                <Network className="w-4 h-4" />
              </div>
              <div>
                <h4 className="text-xs font-bold text-slate-900">GraphML File</h4>
                <span className="text-[10px] text-slate-500">Importable into Gephi / Cytoscape desktop</span>
              </div>
            </div>
            <a
              href={graphmlUrl}
              download
              className="p-2 rounded-lg bg-white hover:bg-slate-100 border border-slate-200 text-slate-600 hover:text-slate-900 transition-colors shadow-2xs"
              title="Download GraphML"
            >
              <Download className="w-4 h-4" />
            </a>
          </div>
        </div>
      </div>
    </div>
  );
};
