import React, { useState } from 'react';
import { Search, Download, ExternalLink, ChevronDown, ChevronRight, Table } from 'lucide-react';
import { TripleItem } from '../../types';

interface TriplesTableProps {
  triples: TripleItem[];
  projectName: string;
}

export const TriplesTable: React.FC<TriplesTableProps> = ({ triples, projectName }) => {
  const [search, setSearch] = useState('');
  const [expandedRows, setExpandedRows] = useState<Record<number, boolean>>({});

  const toggleRow = (idx: number) => {
    setExpandedRows((prev) => ({ ...prev, [idx]: !prev[idx] }));
  };

  const filteredTriples = triples.filter(
    (t) =>
      t.entity1.toLowerCase().includes(search.toLowerCase()) ||
      t.entity2.toLowerCase().includes(search.toLowerCase()) ||
      t.relationship.toLowerCase().includes(search.toLowerCase()) ||
      t.entity1_type.toLowerCase().includes(search.toLowerCase()) ||
      t.entity2_type.toLowerCase().includes(search.toLowerCase()) ||
      (t.evidence && t.evidence.toLowerCase().includes(search.toLowerCase()))
  );

  const handleDownloadCsv = () => {
    const headers = ['Entity 1', 'Entity 1 Type', 'Relationship', 'Entity 2', 'Entity 2 Type', 'Evidence', 'PubMed IDs'];
    const rows = filteredTriples.map((t) => [
      `"${t.entity1.replace(/"/g, '""')}"`,
      `"${t.entity1_type.replace(/"/g, '""')}"`,
      `"${t.relationship.replace(/"/g, '""')}"`,
      `"${t.entity2.replace(/"/g, '""')}"`,
      `"${t.entity2_type.replace(/"/g, '""')}"`,
      `"${(t.evidence || '').replace(/"/g, '""')}"`,
      `"${(t.pubmed_ids || '').replace(/"/g, '""')}"`,
    ]);

    const csvContent = 'data:text/csv;charset=utf-8,' + [headers.join(','), ...rows.map((r) => r.join(','))].join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `${projectName}_triples.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-xs space-y-3 p-4">
      {/* Top Header Row */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-slate-200">
        <div className="flex items-center gap-2">
          <Table className="w-4 h-4 text-slate-700" />
          <h2 className="text-sm font-bold text-slate-900">Extracted Semantic Triples</h2>
          <span className="px-2 py-0.5 rounded bg-slate-100 border border-slate-200 text-xs font-mono font-medium text-slate-700">
            {filteredTriples.length} of {triples.length}
          </span>
        </div>

        <div className="flex items-center gap-2.5">
          <div className="relative">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search entities, evidence..."
              className="bg-slate-50 border border-slate-300 rounded-lg pl-8 pr-3 py-1.5 text-xs text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-indigo-600 focus:ring-1 focus:ring-indigo-600 w-52 sm:w-64 transition-all"
            />
          </div>

          <button
            onClick={handleDownloadCsv}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-50 hover:bg-slate-100 border border-slate-300 text-xs font-semibold text-slate-700 hover:text-slate-900 transition-colors"
            title="Download CSV"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Export CSV</span>
          </button>
        </div>
      </div>

      {/* Table Container */}
      <div className="overflow-x-auto rounded-lg border border-slate-200">
        <table className="w-full text-left text-xs border-collapse">
          <thead>
            <tr className="bg-slate-100/80 text-slate-700 uppercase font-semibold text-[10px] tracking-wider border-b border-slate-200">
              <th className="py-2.5 px-2 w-7 text-center"></th>
              <th className="py-2.5 px-3 font-bold">Entity 1</th>
              <th className="py-2.5 px-3">Type</th>
              <th className="py-2.5 px-3 font-bold">Relationship</th>
              <th className="py-2.5 px-3 font-bold">Entity 2</th>
              <th className="py-2.5 px-3">Type</th>
              <th className="py-2.5 px-3">Evidence Quote</th>
              <th className="py-2.5 px-3">PubMed</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 text-slate-800">
            {filteredTriples.map((t, idx) => {
              const isExpanded = !!expandedRows[idx];
              return (
                <React.Fragment key={idx}>
                  <tr className="hover:bg-slate-50 transition-colors">
                    <td className="py-2 px-2 text-center">
                      {t.evidence ? (
                        <button
                          onClick={() => toggleRow(idx)}
                          className="p-0.5 rounded text-slate-400 hover:text-slate-700"
                        >
                          {isExpanded ? (
                            <ChevronDown className="w-3.5 h-3.5" />
                          ) : (
                            <ChevronRight className="w-3.5 h-3.5" />
                          )}
                        </button>
                      ) : null}
                    </td>
                    <td className="py-2 px-3 font-semibold text-slate-900">{t.entity1}</td>
                    <td className="py-2 px-3 text-slate-600 text-[11px]">{t.entity1_type}</td>
                    <td className="py-2 px-3">
                      <span className="font-mono font-bold text-indigo-700 uppercase text-[10px] bg-indigo-50 px-1.5 py-0.5 rounded border border-indigo-100">
                        {t.relationship.replace(/_/g, ' ')}
                      </span>
                    </td>
                    <td className="py-2 px-3 font-semibold text-slate-900">{t.entity2}</td>
                    <td className="py-2 px-3 text-slate-600 text-[11px]">{t.entity2_type}</td>
                    <td className="py-2 px-3 max-w-xs truncate text-slate-600 italic">
                      {t.evidence ? `"${t.evidence}"` : <span className="text-slate-400">—</span>}
                    </td>
                    <td className="py-2 px-3">
                      {t.pubmed_ids && t.pubmed_ids !== 'No match found' && t.pubmed_ids !== 'Unknown' ? (
                        <div className="flex items-center gap-1 flex-wrap">
                          {t.pubmed_ids.split(';').map((pmid, pIdx) => (
                            <a
                              key={pIdx}
                              href={`https://pubmed.ncbi.nlm.nih.gov/${pmid.trim()}/`}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded bg-emerald-50 hover:bg-emerald-100 text-emerald-800 border border-emerald-300 font-mono text-[10px] font-semibold transition-colors"
                            >
                              <span>{pmid.trim()}</span>
                              <ExternalLink className="w-2 h-2" />
                            </a>
                          ))}
                        </div>
                      ) : (
                        <span className="text-slate-400 text-[10px]">{t.pubmed_ids || '—'}</span>
                      )}
                    </td>
                  </tr>

                  {/* Expanded Evidence Row */}
                  {isExpanded && t.evidence && (
                    <tr className="bg-slate-50">
                      <td colSpan={8} className="py-2.5 px-6 text-xs text-slate-800">
                        <div className="p-3 rounded bg-white border border-slate-200">
                          <span className="font-semibold text-[10px] uppercase text-slate-500 block mb-1">
                            Full Verbatim Evidence (Source Document):
                          </span>
                          <p className="italic text-slate-800 leading-relaxed font-sans">
                            "{t.evidence}"
                          </p>
                        </div>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};
