import React from 'react';
import { X, ExternalLink, Quote, ArrowRight, Crosshair } from 'lucide-react';
import { CytoscapeNodeData, CytoscapeEdgeData } from '../../types';

export interface InCanvasPopoverState {
  type: 'node' | 'edge';
  x: number;
  y: number;
  nodeData?: CytoscapeNodeData;
  edgeData?: CytoscapeEdgeData;
  connections?: Array<{
    id: string;
    relationship: string;
    target: string;
    evidence?: string;
  }>;
}

interface InCanvasPopoverProps {
  popover: InCanvasPopoverState | null;
  containerWidth: number;
  containerHeight: number;
  onClose: () => void;
  onFocusNode?: (nodeId: string) => void;
}

export const InCanvasPopover: React.FC<InCanvasPopoverProps> = ({
  popover,
  containerWidth,
  containerHeight,
  onClose,
  onFocusNode,
}) => {
  if (!popover) return null;

  const cardWidth = 320;
  const cardHeight = 280;

  // Clamp coordinates within container viewport
  let left = popover.x - cardWidth / 2;
  let top = popover.y - cardHeight - 16;

  if (left < 12) left = 12;
  if (left + cardWidth > containerWidth - 12) left = Math.max(12, containerWidth - cardWidth - 12);
  if (top < 12) top = popover.y + 20; // Flip below if too close to top
  if (top + cardHeight > containerHeight - 12) top = Math.max(12, containerHeight - cardHeight - 12);

  return (
    <div
      style={{ left: `${left}px`, top: `${top}px`, width: `${cardWidth}px` }}
      className="absolute z-30 bg-white border border-slate-300 rounded-xl shadow-xl p-3.5 text-xs text-slate-800 animate-fadeIn pointer-events-auto"
      onClick={(e) => e.stopPropagation()}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-2 pb-2 border-b border-slate-200 mb-2.5">
        <div className="flex items-center gap-2 min-w-0">
          <span
            className="w-3 h-3 rounded-full shrink-0 border border-slate-300"
            style={{
              backgroundColor:
                popover.type === 'node'
                  ? popover.nodeData?.color || '#4f46e5'
                  : '#4f46e5',
            }}
          />
          <div className="min-w-0">
            <span className="text-[10px] uppercase font-bold tracking-wider text-slate-500 block leading-none">
              {popover.type === 'node' ? (popover.nodeData?.category || 'Entity') : 'Relationship'}
            </span>
            <h3 className="font-bold text-xs text-slate-900 truncate tracking-tight mt-0.5">
              {popover.type === 'node' ? popover.nodeData?.label : `${popover.edgeData?.source} → ${popover.edgeData?.target}`}
            </h3>
          </div>
        </div>

        <button
          onClick={onClose}
          className="p-1 text-slate-400 hover:text-slate-700 hover:bg-slate-100 rounded transition-colors shrink-0"
          title="Close Popover"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Node View */}
      {popover.type === 'node' && popover.nodeData && (
        <div className="space-y-2.5">
          {/* Classification Tags */}
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="px-2 py-0.5 rounded bg-slate-100 border border-slate-200 text-[10px] font-semibold text-slate-700">
              {popover.nodeData.sub_category || popover.nodeData.type}
            </span>
            <span className="px-2 py-0.5 rounded bg-slate-100 border border-slate-200 text-[10px] font-mono font-semibold text-slate-700">
              {popover.nodeData.degree} {popover.nodeData.degree === 1 ? 'connection' : 'connections'}
            </span>
          </div>

          {/* Connected Entities preview */}
          {popover.connections && popover.connections.length > 0 && (
            <div>
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block mb-1">
                Connected Relations ({popover.connections.length})
              </span>
              <div className="space-y-1 max-h-32 overflow-y-auto pr-1">
                {popover.connections.map((conn, idx) => (
                  <div
                    key={idx}
                    className="flex items-center justify-between p-1 rounded bg-slate-50 border border-slate-200 text-[11px]"
                  >
                    <div className="flex items-center gap-1 truncate min-w-0 pr-1">
                      <span className="font-mono text-indigo-700 font-bold text-[9.5px] uppercase shrink-0">
                        {conn.relationship.replace(/_/g, ' ')}
                      </span>
                      <ArrowRight className="w-2.5 h-2.5 text-slate-400 shrink-0" />
                      <span className="font-medium text-slate-800 truncate" title={conn.target}>
                        {conn.target}
                      </span>
                    </div>
                    {onFocusNode && (
                      <button
                        onClick={() => onFocusNode(conn.target)}
                        className="text-[10px] text-slate-500 hover:text-indigo-600 px-1 py-0.5 rounded hover:bg-white transition-colors shrink-0"
                        title={`Focus ${conn.target}`}
                      >
                        <Crosshair className="w-3 h-3" />
                      </button>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Quick Action: Center on Node */}
          {onFocusNode && (
            <div className="pt-1 border-t border-slate-200">
              <button
                onClick={() => onFocusNode(popover.nodeData!.id)}
                className="w-full flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-50 hover:bg-slate-100 text-slate-700 font-semibold text-xs transition-colors border border-slate-300"
              >
                <Crosshair className="w-3.5 h-3.5 text-slate-600" />
                <span>Center on Node</span>
              </button>
            </div>
          )}
        </div>
      )}

      {/* Edge View */}
      {popover.type === 'edge' && popover.edgeData && (
        <div className="space-y-2.5">
          {/* Relationship Tag */}
          <div className="flex items-center justify-center p-1.5 rounded-lg bg-slate-100 border border-slate-200">
            <span className="font-mono font-bold text-xs text-indigo-700 uppercase tracking-wide">
              {popover.edgeData.relationship.replace(/_/g, ' ')}
            </span>
          </div>

          {/* Evidence Quote */}
          <div>
            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block mb-1 flex items-center gap-1">
              <Quote className="w-3 h-3 text-slate-500" />
              <span>Verbatim Evidence</span>
            </span>
            <div className="p-2 rounded bg-slate-50 border border-slate-200 max-h-28 overflow-y-auto">
              <p className="text-[11px] text-slate-700 italic leading-relaxed font-sans">
                "{popover.edgeData.evidence || 'No verbatim sentence provided.'}"
              </p>
            </div>
          </div>

          {/* PubMed Link */}
          {popover.edgeData.pubmed_ids && (
            <div className="flex items-center gap-1.5 pt-1 border-t border-slate-200 flex-wrap">
              <span className="text-[10px] text-slate-500 font-bold uppercase">PubMed:</span>
              <div className="flex flex-wrap gap-1">
                {popover.edgeData.pubmed_ids.split(';').filter(Boolean).map((pmid, idx) => (
                  <a
                    key={idx}
                    href={`https://pubmed.ncbi.nlm.nih.gov/${pmid.trim()}/`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-emerald-50 border border-emerald-300 text-[10px] font-bold text-emerald-800 hover:bg-emerald-100 transition-colors"
                  >
                    <span>PMID {pmid.trim()}</span>
                    <ExternalLink className="w-2.5 h-2.5" />
                  </a>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
