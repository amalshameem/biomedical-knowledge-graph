import React, { useState } from 'react';
import { Filter, Search, RotateCcw, Maximize2, Minimize2, ChevronDown, ChevronRight, Check, SlidersHorizontal } from 'lucide-react';

export const RELATIONSHIP_COLORS: Record<string, { label: string; color: string; description: string }> = {
  "treats": { label: "Treats", color: "#0d9488", description: "Therapeutic efficacy" },
  "causes": { label: "Causes", color: "#be123c", description: "Pathogenesis / Etiology" },
  "predisposes": { label: "Predisposes", color: "#c2410c", description: "Risk factor / Susceptibility" },
  "positively_regulates": { label: "Positively Regulates", color: "#15803d", description: "Activation / Induction" },
  "negatively_regulates": { label: "Negatively Regulates", color: "#b91c1c", description: "Inhibition / Downregulation" },
  "interacts_with": { label: "Interacts With", color: "#4f46e5", description: "Direct molecular binding" },
  "associated_with": { label: "Associated With", color: "#6366f1", description: "General correlation" },
  "expressed_in": { label: "Expressed In", color: "#0284c7", description: "Anatomical localization" },
  "coexists_with": { label: "Coexists With", color: "#64748b", description: "Comorbidity" },
};

export const GRAPH_LAYOUTS = [
  { id: 'fcose', label: 'Fast Compound (fcose)', group: 'Physics & Clustering', desc: 'Biological clustering with compound physics' },
  { id: 'cola', label: 'Fluid Collision-Free (cola)', group: 'Physics & Clustering', desc: 'Smooth continuous physics with collision avoidance' },
  { id: 'cose', label: 'Classic Spring (cose)', group: 'Physics & Clustering', desc: 'Compound spring embedder force simulation' },
  { id: 'concentric', label: 'Concentric Hub Rings', group: 'Centrality & Flow', desc: 'Places highly connected hub genes/diseases in center ring' },
  { id: 'breadthfirst', label: 'Hierarchical Flow (DAG)', group: 'Centrality & Flow', desc: 'Top-down regulatory cascade and tree traversal' },
  { id: 'circle', label: 'Radial Circle', group: 'Geometric Formats', desc: 'Equidistant circular chord ring' },
  { id: 'grid', label: 'Sorted Matrix Grid', group: 'Geometric Formats', desc: 'Structured 2D matrix ordered by connectivity degree' },
  { id: 'random', label: 'Random Scatter', group: 'Geometric Formats', desc: 'Uniform canvas distribution' },
];

export const TAXONOMY_HIERARCHY: Record<string, { color: string; subcategories: string[] }> = {
  "Genes & Molecular Entities": {
    color: "#ef4444",
    subcategories: ["Gene or Gene Product", "Protein", "Enzyme", "Receptor", "Nucleic Acid"]
  },
  "Chemicals & Drugs": {
    color: "#10b981",
    subcategories: ["Chemical", "Drug", "Pharmacologic Substance", "Toxic Substance", "Substance", "Body Fluid"]
  },
  "Diseases & Phenotypes": {
    color: "#2563eb",
    subcategories: ["Disease", "Syndrome", "Neoplasm", "Pathologic Function", "Sign or Symptom", "Phenotypic Feature", "Clinical Finding"]
  },
  "Biological Processes & Pathways": {
    color: "#8b5cf6",
    subcategories: ["Biological Process", "Molecular Function", "Pathway", "Metabolic Process", "Biologic Function"]
  },
  "Anatomy & Cellular": {
    color: "#ec4899",
    subcategories: ["Cell", "Cellular Component", "Tissue", "Organ", "Anatomical Structure", "Anatomical Entity"]
  },
  "Organisms & Taxa": {
    color: "#16a34a",
    subcategories: ["Organism Taxon", "Virus", "Bacterium"]
  },
  "Procedures & Methods": {
    color: "#e11d48",
    subcategories: ["Diagnostic Procedure", "Therapeutic Procedure", "Laboratory Procedure", "Procedure"]
  },
  "Environmental & Other": {
    color: "#64748b",
    subcategories: ["Environmental Effect", "General Entity", "Unclassified"]
  }
};

export const BASIC_TAXONOMY_HIERARCHY: Record<string, { color: string; subcategories: string[] }> = {
  "Diseases": {
    color: "#2563eb",
    subcategories: ["Disease"]
  },
  "Genes": {
    color: "#ef4444",
    subcategories: ["Gene"]
  },
  "Proteins": {
    color: "#dc2626",
    subcategories: ["Protein"]
  },
  "Drugs": {
    color: "#10b981",
    subcategories: ["Drug"]
  }
};

interface GraphControlsProps {
  layoutName: string;
  onLayoutChange: (name: string) => void;
  minDegree: number;
  onMinDegreeChange: (deg: number) => void;
  searchQuery: string;
  onSearchChange: (q: string) => void;
  categoriesCount?: Record<string, number>;
  subcategoriesCount?: Record<string, number>;
  activeSubcategories: Set<string>;
  onToggleSubcategory: (subcat: string) => void;
  onToggleCategory: (category: string, subcats: string[]) => void;
  onSelectAllTaxonomy: () => void;
  onClearTaxonomy: () => void;
  activeRelationships?: Set<string>;
  relationshipsCount?: Record<string, number>;
  onToggleRelationship?: (rel: string) => void;
  onSelectAllRelationships?: () => void;
  onClearRelationships?: () => void;
  onFitGraph: () => void;
  onResetLayout: () => void;
  isFullscreen?: boolean;
  onToggleFullscreen?: () => void;
  nerMode?: 'basic' | 'advanced';
}

export const GraphControls: React.FC<GraphControlsProps> = ({
  layoutName,
  onLayoutChange,
  minDegree,
  onMinDegreeChange,
  searchQuery,
  onSearchChange,
  categoriesCount = {},
  subcategoriesCount = {},
  activeSubcategories,
  onToggleSubcategory,
  onToggleCategory,
  onSelectAllTaxonomy,
  onClearTaxonomy,
  activeRelationships,
  relationshipsCount = {},
  onToggleRelationship,
  onSelectAllRelationships,
  onClearRelationships,
  onFitGraph,
  onResetLayout,
  isFullscreen = false,
  onToggleFullscreen,
  nerMode = 'advanced',
}) => {
  const [isFilterOpen, setIsFilterOpen] = useState(false);
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(new Set());
  const currentHierarchy = nerMode === 'basic' ? BASIC_TAXONOMY_HIERARCHY : TAXONOMY_HIERARCHY;

  const toggleCategoryExpand = (cat: string) => {
    setExpandedCategories((prev) => {
      const next = new Set(prev);
      if (next.has(cat)) next.delete(cat);
      else next.add(cat);
      return next;
    });
  };

  return (
    <div className="absolute left-3 top-3 z-20 flex flex-col gap-2 max-w-sm w-full pointer-events-none">
      {/* Primary Toolbar Bar */}
      <div className="bg-white border border-slate-300 rounded-xl p-3 shadow-md pointer-events-auto space-y-2.5">
        {/* Search & Action Row */}
        <div className="flex items-center gap-2">
          {/* Search Box */}
          <div className="relative flex-1">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => onSearchChange(e.target.value)}
              placeholder="Search entities in graph..."
              className="w-full bg-slate-50 border border-slate-300 rounded-lg pl-8 pr-3 py-1.5 text-xs text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-indigo-600 focus:ring-1 focus:ring-indigo-600 transition-all font-medium"
            />
          </div>

          {/* Toggle Filter Drawer Button */}
          <button
            onClick={() => setIsFilterOpen(!isFilterOpen)}
            className={`px-2.5 py-1.5 rounded-lg border transition-all text-xs font-semibold flex items-center gap-1.5 ${
              isFilterOpen
                ? 'bg-indigo-600 border-indigo-600 text-white'
                : 'bg-slate-50 hover:bg-slate-100 border-slate-300 text-slate-700'
            }`}
            title="Filter by Categories and Sub-categories"
          >
            <Filter className="w-3.5 h-3.5" />
            <span className="hidden sm:inline text-xs">Filter</span>
          </button>

          {/* Fit to Viewport */}
          <button
            onClick={onFitGraph}
            className="p-1.5 rounded-lg bg-slate-50 hover:bg-slate-100 border border-slate-300 text-slate-700 hover:text-slate-900 transition-colors"
            title="Fit to Screen"
          >
            <Maximize2 className="w-3.5 h-3.5" />
          </button>

          {/* Reset Physics Layout */}
          <button
            onClick={onResetLayout}
            className="p-1.5 rounded-lg bg-slate-50 hover:bg-slate-100 border border-slate-300 text-slate-700 hover:text-slate-900 transition-colors"
            title="Re-run Physics Layout"
          >
            <RotateCcw className="w-3.5 h-3.5" />
          </button>

          {/* Fullscreen Toggle */}
          {onToggleFullscreen && (
            <button
              onClick={onToggleFullscreen}
              className={`p-1.5 rounded-lg border transition-colors ${
                isFullscreen
                  ? 'bg-indigo-50 border-indigo-300 text-indigo-700 font-bold'
                  : 'bg-slate-50 hover:bg-slate-100 border-slate-300 text-slate-700 hover:text-slate-900'
              }`}
              title={isFullscreen ? 'Exit Fullscreen' : 'Fullscreen Canvas'}
            >
              {isFullscreen ? <Minimize2 className="w-3.5 h-3.5" /> : <Maximize2 className="w-3.5 h-3.5 text-indigo-600" />}
            </button>
          )}
        </div>

        {/* Compact Layout & Degree Control */}
        <div className="grid grid-cols-2 gap-3 pt-2 border-t border-slate-200 text-xs">
          <div>
            <label className="block text-[10px] font-bold uppercase text-slate-500 mb-1">
              Layout
            </label>
            <select
              value={layoutName}
              onChange={(e) => onLayoutChange(e.target.value)}
              className="w-full bg-slate-50 border border-slate-300 rounded-lg px-2 py-1 text-xs text-slate-900 font-medium focus:outline-none focus:border-indigo-600"
            >
              <optgroup label="Physics & Force-Directed">
                <option value="fcose">Fast Compound (fcose)</option>
                <option value="cola">Fluid Smooth (cola)</option>
                <option value="cose">Classic Spring (cose)</option>
              </optgroup>
              <optgroup label="Hierarchy & Centrality">
                <option value="concentric">Concentric Hub Rings</option>
                <option value="breadthfirst">Hierarchical Flow (DAG)</option>
              </optgroup>
              <optgroup label="Geometric Formats">
                <option value="circle">Radial Circle</option>
                <option value="grid">Sorted Matrix Grid</option>
                <option value="random">Random Scatter</option>
              </optgroup>
            </select>
          </div>

          <div>
            <div className="flex items-center justify-between text-[10px] font-bold uppercase text-slate-500 mb-1">
              <span>Min Connections</span>
              <span className="text-indigo-600 font-mono font-bold">{minDegree}</span>
            </div>
            <input
              type="range"
              min="1"
              max="10"
              value={minDegree}
              onChange={(e) => onMinDegreeChange(parseInt(e.target.value))}
              className="w-full h-1.5 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-indigo-600 my-1.5 block"
            />
          </div>
        </div>
      </div>

      {/* Expandable Hierarchical Taxonomy Filter Drawer */}
      {isFilterOpen && (
        <div className="bg-white border border-slate-300 rounded-xl p-3.5 shadow-xl pointer-events-auto space-y-3 animate-fadeIn max-h-[65vh] flex flex-col">
          {/* Header & Bulk Actions */}
          <div className="flex items-center justify-between pb-2 border-b border-slate-200 shrink-0">
            <div className="flex items-center gap-1.5">
              <SlidersHorizontal className="w-3.5 h-3.5 text-indigo-600" />
              <span className="text-xs font-bold text-slate-900">Entity Categories</span>
            </div>
            <div className="flex items-center gap-2 text-xs">
              <button
                onClick={onSelectAllTaxonomy}
                className="text-indigo-600 hover:text-indigo-800 font-semibold"
              >
                Select All
              </button>
              <span className="text-slate-300">|</span>
              <button
                onClick={onClearTaxonomy}
                className="text-slate-500 hover:text-rose-600 font-semibold"
              >
                Clear
              </button>
            </div>
          </div>

          {/* Categories Filter (Flat for Basic, Hierarchical for Advanced) */}
          <div className="flex-1 overflow-y-auto space-y-2 pr-1 text-xs">
            {nerMode === 'basic' ? (
              <div className="space-y-1.5">
                {Object.entries(BASIC_TAXONOMY_HIERARCHY).map(([categoryName, { color, subcategories }]) => {
                  const sub = subcategories[0];
                  const isActive = activeSubcategories.has(sub);
                  const count = subcategoriesCount[sub] || categoriesCount[categoryName] || 0;

                  return (
                    <label
                      key={categoryName}
                      className="flex items-center justify-between p-2 rounded-lg border border-slate-200 bg-slate-50/70 hover:bg-slate-100 cursor-pointer transition-colors"
                    >
                      <div className="flex items-center gap-2 min-w-0">
                        <input
                          type="checkbox"
                          checked={isActive}
                          onChange={() => onToggleSubcategory(sub)}
                          className="w-4 h-4 rounded text-indigo-600 border-slate-300 focus:ring-indigo-500 cursor-pointer"
                        />
                        <span
                          className="w-2.5 h-2.5 rounded-full shrink-0 border border-slate-300"
                          style={{ backgroundColor: color }}
                        />
                        <span className="font-semibold text-slate-800 text-xs truncate">
                          {categoryName}
                        </span>
                      </div>

                      <span className="text-[10px] font-mono font-medium px-1.5 py-0.5 rounded bg-white border border-slate-200 text-slate-600">
                        {count}
                      </span>
                    </label>
                  );
                })}
              </div>
            ) : (
              Object.entries(currentHierarchy).map(([categoryName, { color, subcategories }]) => {
                const catCount = subcategories.reduce((acc, sub) => acc + (subcategoriesCount[sub] || 0), 0);
                const isExpanded = expandedCategories.has(categoryName);
                const activeCountInCat = subcategories.filter((s) => activeSubcategories.has(s)).length;
                const isAllCatActive = activeCountInCat === subcategories.length;

                return (
                  <div key={categoryName} className="rounded-lg border border-slate-200 bg-slate-50/70 overflow-hidden">
                    {/* Category Header Row */}
                    <div className="flex items-center justify-between p-2 hover:bg-slate-100 transition-colors">
                      <div className="flex items-center gap-2 min-w-0">
                        <button
                          onClick={() => toggleCategoryExpand(categoryName)}
                          className="p-0.5 text-slate-500 hover:text-slate-800 transition-colors"
                        >
                          {isExpanded ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
                        </button>
                        <button
                          onClick={() => onToggleCategory(categoryName, subcategories)}
                          className={`w-4 h-4 rounded border flex items-center justify-center transition-all ${
                            isAllCatActive
                              ? 'bg-indigo-600 border-indigo-600 text-white'
                              : activeCountInCat > 0
                              ? 'bg-indigo-100 border-indigo-400 text-indigo-700'
                              : 'bg-white border-slate-300'
                          }`}
                        >
                          {isAllCatActive && <Check className="w-2.5 h-2.5 stroke-[3]" />}
                          {!isAllCatActive && activeCountInCat > 0 && <span className="w-1.5 h-1.5 bg-indigo-600 rounded-xs" />}
                        </button>
                        <span
                          className="w-2.5 h-2.5 rounded-full shrink-0 border border-slate-300"
                          style={{ backgroundColor: color }}
                        />
                        <span className="font-semibold text-slate-800 text-xs truncate">
                          {categoryName}
                        </span>
                      </div>

                      <span className="text-[10px] font-mono font-medium px-1.5 py-0.2 rounded bg-white border border-slate-200 text-slate-600">
                        {catCount}
                      </span>
                    </div>

                    {/* Sub-categories List */}
                    {isExpanded && (
                      <div className="pl-7 pr-2 pb-2 pt-1 border-t border-slate-200 space-y-1 bg-white">
                        {subcategories.map((subcat) => {
                          const isSubActive = activeSubcategories.has(subcat);
                          const subCount = subcategoriesCount[subcat] || 0;

                          return (
                            <label
                              key={subcat}
                              className="flex items-center justify-between p-1 rounded hover:bg-slate-50 cursor-pointer transition-colors text-xs"
                            >
                              <div className="flex items-center gap-2 truncate">
                                <input
                                  type="checkbox"
                                  checked={isSubActive}
                                  onChange={() => onToggleSubcategory(subcat)}
                                  className="w-3.5 h-3.5 rounded text-indigo-600 border-slate-300 focus:ring-indigo-500"
                                />
                                <span className="text-slate-700 font-medium truncate">
                                  {subcat}
                                </span>
                              </div>
                              <span className="text-[10px] font-mono text-slate-400">
                                {subCount}
                              </span>
                            </label>
                          );
                        })}
                      </div>
                    )}
                  </div>
                );
              })
            )}
          </div>

          {/* Interactive Relationship Filter (Both Basic & Advanced) */}
          <div className="pt-2.5 border-t border-slate-200 shrink-0">
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-xs font-bold text-slate-900">Relationships</span>
              <div className="flex items-center gap-2 text-xs">
                <button
                  onClick={onSelectAllRelationships}
                  className="text-indigo-600 hover:text-indigo-800 font-semibold text-[11px]"
                >
                  Select All
                </button>
                <span className="text-slate-300">|</span>
                <button
                  onClick={onClearRelationships}
                  className="text-slate-500 hover:text-rose-600 font-semibold text-[11px]"
                >
                  Clear
                </button>
              </div>
            </div>

            <div className="grid grid-cols-1 gap-1 max-h-36 overflow-y-auto pr-1">
              {Object.entries(RELATIONSHIP_COLORS).map(([key, { label, color }]) => {
                const isActive = activeRelationships ? activeRelationships.has(key) : true;
                const count = relationshipsCount ? relationshipsCount[key] || 0 : 0;

                return (
                  <label
                    key={key}
                    className="flex items-center justify-between px-2 py-1 rounded bg-slate-50 border border-slate-200 hover:bg-slate-100 cursor-pointer transition-colors text-xs"
                  >
                    <div className="flex items-center gap-1.5 min-w-0">
                      <input
                        type="checkbox"
                        checked={isActive}
                        onChange={() => onToggleRelationship && onToggleRelationship(key)}
                        className="w-3.5 h-3.5 rounded text-indigo-600 border-slate-300 focus:ring-indigo-500 cursor-pointer"
                      />
                      <span
                        className="w-2.5 h-2.5 rounded-full shrink-0"
                        style={{ backgroundColor: color }}
                      />
                      <span className="font-semibold text-slate-800 truncate font-mono text-[10px]">
                        {label}
                      </span>
                    </div>
                    <span className="text-[10px] font-mono text-slate-500 font-medium px-1 rounded bg-white border border-slate-200">
                      {count}
                    </span>
                  </label>
                );
              })}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
