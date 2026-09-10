import React, { useEffect, useRef, useState, useMemo } from 'react';
import cytoscape from 'cytoscape';
// @ts-ignore
import fcose from 'cytoscape-fcose';
// @ts-ignore
import cola from 'cytoscape-cola';
import { CytoscapeGraphData, CytoscapeNodeData, CytoscapeEdgeData } from '../../types';
import { GraphControls, TAXONOMY_HIERARCHY, BASIC_TAXONOMY_HIERARCHY, RELATIONSHIP_COLORS } from './GraphControls';
import { InCanvasPopover, InCanvasPopoverState } from './NodeInspector';

// Register extensions safely
try {
  cytoscape.use(fcose);
  cytoscape.use(cola);
} catch (e) {}

// Gather all all default subcategories from hierarchy
const ALL_SUBCATEGORIES = new Set(
  Object.values(TAXONOMY_HIERARCHY).flatMap((cat) => cat.subcategories)
);

const getLayoutOptions = (name: string): any => {
  switch (name) {
    case 'fcose':
      return {
        name: 'fcose',
        quality: 'proof',
        randomize: true,
        animate: true,
        animationDuration: 650,
        fit: true,
        padding: 45,
        nodeRepulsion: 7500,
        idealEdgeLength: 85,
        edgeElasticity: 0.45,
        nestingFactor: 0.1,
        gravity: 0.25,
        numIter: 2500,
        tile: true,
        tilingPaddingVertical: 20,
        tilingPaddingHorizontal: 20,
      };

    case 'cola':
      return {
        name: 'cola',
        animate: true,
        animationDuration: 650,
        maxSimulationTime: 2000,
        fit: true,
        padding: 45,
        nodeSpacing: 45,
        edgeLength: 95,
        avoidOverlap: true,
        handleDisconnected: true,
      };

    case 'concentric':
      return {
        name: 'concentric',
        fit: true,
        padding: 45,
        animate: true,
        animationDuration: 650,
        concentric: (node: any) => node.data('degree') || 1,
        levelWidth: () => 2,
        minNodeSpacing: 40,
        avoidOverlap: true,
        equidistant: false,
        clockwise: true,
      };

    case 'breadthfirst':
      return {
        name: 'breadthfirst',
        fit: true,
        padding: 45,
        animate: true,
        animationDuration: 650,
        directed: true,
        spacingFactor: 1.3,
        avoidOverlap: true,
        circle: false,
      };

    case 'cose':
      return {
        name: 'cose',
        fit: true,
        padding: 45,
        animate: true,
        animationDuration: 650,
        nodeRepulsion: 8500,
        idealEdgeLength: 85,
        edgeElasticity: 100,
        nestingFactor: 5,
        gravity: 80,
        numIter: 1000,
        initialTemp: 200,
        coolingFactor: 0.95,
        minTemp: 1.0,
      };

    case 'circle':
      return {
        name: 'circle',
        fit: true,
        padding: 45,
        animate: true,
        animationDuration: 650,
        startAngle: (3 / 2) * Math.PI,
        clockwise: true,
        avoidOverlap: true,
      };

    case 'grid':
      return {
        name: 'grid',
        fit: true,
        padding: 45,
        animate: true,
        animationDuration: 650,
        avoidOverlap: true,
        condense: true,
        sort: (a: any, b: any) => (b.data('degree') || 0) - (a.data('degree') || 0),
      };

    case 'random':
      return {
        name: 'random',
        fit: true,
        padding: 45,
        animate: true,
        animationDuration: 650,
      };

    default:
      return {
        name: 'fcose',
        animate: true,
        animationDuration: 650,
        fit: true,
        padding: 45,
      };
  }
};

interface CytoscapeGraphProps {
  graphData: CytoscapeGraphData;
  minDegree: number;
  onMinDegreeChange: (deg: number) => void;
  selectedType: string;
  onSelectType: (type: string) => void;
  nerMode?: 'basic' | 'advanced';
}

export const CytoscapeGraph: React.FC<CytoscapeGraphProps> = ({
  graphData,
  minDegree,
  onMinDegreeChange,
  selectedType,
  onSelectType,
  nerMode = 'advanced',
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const wrapperRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<cytoscape.Core | null>(null);

  const [layoutName, setLayoutName] = useState('fcose');
  const [searchQuery, setSearchQuery] = useState('');
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [popoverState, setPopoverState] = useState<InCanvasPopoverState | null>(null);
  const [containerDimensions, setContainerDimensions] = useState({ width: 800, height: 600 });

  const currentHierarchy = nerMode === 'basic' ? BASIC_TAXONOMY_HIERARCHY : TAXONOMY_HIERARCHY;
  const currentAllSubcats = useMemo(() => new Set(
    Object.values(currentHierarchy).flatMap((cat) => cat.subcategories)
  ), [currentHierarchy]);

  // Taxonomy Filter State: all subcategories active by default (including dynamic types)
  const dynamicAllSubcats = useMemo(() => {
    const set = new Set<string>(currentAllSubcats);
    graphData.elements.nodes.forEach((n) => {
      const sub = n.data.sub_category || n.data.type;
      if (sub && (nerMode !== 'basic' || currentAllSubcats.has(sub))) {
        set.add(sub);
      }
    });
    return set;
  }, [graphData, currentAllSubcats, nerMode]);

  const [activeSubcategories, setActiveSubcategories] = useState<Set<string>>(dynamicAllSubcats);

  // Relationship Filter State: all 9 relationships active by default
  const [activeRelationships, setActiveRelationships] = useState<Set<string>>(
    new Set(Object.keys(RELATIONSHIP_COLORS))
  );

  // Sync activeSubcategories & activeRelationships when new graphData arrives
  useEffect(() => {
    setActiveSubcategories(new Set(dynamicAllSubcats));
    setActiveRelationships(new Set(Object.keys(RELATIONSHIP_COLORS)));
  }, [dynamicAllSubcats, graphData]);

  // Compute relationship counts from graphData
  const relationshipsCount = useMemo(() => {
    const counts: Record<string, number> = {};
    graphData.elements.edges.forEach((e) => {
      const rel = (e.data.relationship || '').toLowerCase().replace(/\s+/g, '_');
      if (rel) {
        counts[rel] = (counts[rel] || 0) + 1;
      }
    });
    return counts;
  }, [graphData]);

  // Compute category/subcategory counts from graphData
  const { categoriesCount, subcategoriesCount } = useMemo(() => {
    const subcatMap: Record<string, number> = {};
    const allKnownSubcats = Array.from(currentAllSubcats);

    graphData.elements.nodes.forEach((n) => {
      const rawSub = n.data.sub_category || n.data.type || 'Unclassified';
      const matched = allKnownSubcats.find(
        (s) => s.toLowerCase() === rawSub.toLowerCase()
      ) || rawSub;
      subcatMap[matched] = (subcatMap[matched] || 0) + 1;
    });

    const catMap: Record<string, number> = {};
    Object.entries(currentHierarchy).forEach(([catName, { subcategories }]) => {
      catMap[catName] = subcategories.reduce((acc, sub) => acc + (subcatMap[sub] || 0), 0);
    });

    return {
      categoriesCount: catMap,
      subcategoriesCount: subcatMap,
    };
  }, [graphData, currentHierarchy, currentAllSubcats]);

  // Track container dimensions for popover clamping
  useEffect(() => {
    if (!containerRef.current) return;
    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        setContainerDimensions({
          width: entry.contentRect.width,
          height: entry.contentRect.height,
        });
      }
      if (cyRef.current) {
        cyRef.current.resize();
      }
    });
    observer.observe(containerRef.current);
    return () => observer.disconnect();
  }, []);

  // Listen for fullscreen change events
  useEffect(() => {
    const handleFullscreenChange = () => {
      setIsFullscreen(!!document.fullscreenElement);
      if (cyRef.current) {
        setTimeout(() => {
          cyRef.current?.resize();
          cyRef.current?.fit(undefined, 40);
        }, 150);
      }
    };
    document.addEventListener('fullscreenchange', handleFullscreenChange);
    return () => document.removeEventListener('fullscreenchange', handleFullscreenChange);
  }, []);

  // Initialize and update Cytoscape instance
  useEffect(() => {
    if (!containerRef.current) return;

    const elements = [
      ...graphData.elements.nodes.map((n) => ({
        group: 'nodes' as const,
        data: n.data,
      })),
      ...graphData.elements.edges.map((e) => ({
        group: 'edges' as const,
        data: {
          ...e.data,
          color: e.data.color || RELATIONSHIP_COLORS[e.data.relationship]?.color || '#6366f1',
        },
      })),
    ];

    if (!cyRef.current) {
      cyRef.current = cytoscape({
        container: containerRef.current,
        elements,
        style: [
          // Node Base Style
          {
            selector: 'node',
            style: {
              'label': 'data(label)',
              'background-color': 'data(color)',
              'color': '#0f172a',
              'font-size': '10.5px',
              'font-family': 'Inter, sans-serif',
              'font-weight': 600,
              'text-valign': 'bottom',
              'text-margin-y': 4,
              'text-outline-color': '#ffffff',
              'text-outline-width': 2,
              'width': 'mapData(degree, 1, 25, 24, 48)',
              'height': 'mapData(degree, 1, 25, 24, 48)',
              'border-width': 1.5,
              'border-color': '#ffffff',
              'transition-property': 'background-color, border-color, border-width, opacity',
              'transition-duration': 0.15,
            },
          },
          // Node Selected / Highlighted
          {
            selector: 'node:selected, node.highlighted',
            style: {
              'border-width': 3,
              'border-color': '#4f46e5',
            },
          },
          // Node Hovered Neighbor
          {
            selector: 'node.hovered-neighbor',
            style: {
              'border-width': 2.5,
              'border-color': '#818cf8',
            },
          },
          // Edge Base Style (Semantic Relationship-colored arrows with distinct bidirectional curvature)
          {
            selector: 'edge',
            style: {
              'label': '',
              'curve-style': 'bezier',
              'control-point-step-size': 36,
              'loop-direction': '-45deg',
              'loop-sweep': '-90deg',
              'target-arrow-shape': 'triangle',
              'target-arrow-color': 'data(color)',
              'line-color': 'data(color)',
              'width': 1.8,
              'opacity': 0.8,
              'arrow-scale': 1.15,
              'font-size': '9px',
              'font-family': 'JetBrains Mono, monospace',
              'font-weight': 600,
              'color': '#0f172a',
              'text-rotation': 'autorotate',
              'text-background-color': '#ffffff',
              'text-background-opacity': 0.95,
              'text-background-padding': '2.5px',
              'text-background-shape': 'roundrectangle',
              'text-border-color': 'data(color)',
              'text-border-width': 1,
              'transition-property': 'line-color, target-arrow-color, width, opacity',
              'transition-duration': 0.15,
            },
          },
          // Connected edges when node is hovered/selected (brighter highlight)
          {
            selector: 'edge.connected-highlight',
            style: {
              'line-color': 'data(color)',
              'target-arrow-color': 'data(color)',
              'width': 2.4,
              'opacity': 0.95,
              'arrow-scale': 1.25,
            },
          },
          // Individual Edge Hovered / Selected (REVEALS relationship text on single edge)
          {
            selector: 'edge.hovered, edge:selected, edge.highlighted',
            style: {
              'label': 'data(label)',
              'line-color': 'data(color)',
              'target-arrow-color': 'data(color)',
              'width': 3.0,
              'opacity': 1,
              'arrow-scale': 1.35,
              'z-index': 999,
            },
          },
          // Faded state during search / filter
          {
            selector: '.faded',
            style: {
              'opacity': 0.08,
            },
          },
          // Hidden state for taxonomy and degree filtering
          {
            selector: '.hidden',
            style: {
              'display': 'none',
            },
          },
        ],
        layout: getLayoutOptions(layoutName),
      });

      const cy = cyRef.current;

      // Hover events on edges: Reveal relationship label for this specific edge
      cy.on('mouseover', 'edge', (evt) => {
        evt.target.addClass('hovered');
      });
      cy.on('mouseout', 'edge', (evt) => {
        evt.target.removeClass('hovered');
      });

      // Hover events on nodes: Highlight connected edges cleanly (no text explosion)
      cy.on('mouseover', 'node', (evt) => {
        const node = evt.target;
        node.connectedEdges().addClass('connected-highlight');
        node.neighborhood().nodes().addClass('hovered-neighbor');
      });
      cy.on('mouseout', 'node', (evt) => {
        const node = evt.target;
        node.connectedEdges().removeClass('connected-highlight');
        node.neighborhood().nodes().removeClass('hovered-neighbor');
      });

      // Tap Node: Open In-Canvas Popover Card right on the node
      cy.on('tap', 'node', (evt) => {
        const node = evt.target;
        const pos = node.renderedPosition();
        const connected = node.connectedEdges().map((e: any) => ({
          id: e.id(),
          relationship: e.data('relationship'),
          target: e.data('target') === node.id() ? e.data('source') : e.data('target'),
          evidence: e.data('evidence'),
        }));

        setPopoverState({
          type: 'node',
          x: pos.x,
          y: pos.y,
          nodeData: node.data(),
          connections: connected,
        });
      });

      // Tap Edge: Open In-Canvas Popover Card right at edge midpoint
      cy.on('tap', 'edge', (evt) => {
        const edge = evt.target;
        const midpoint = edge.renderedMidpoint();
        setPopoverState({
          type: 'edge',
          x: midpoint.x,
          y: midpoint.y,
          edgeData: edge.data(),
        });
      });

      // Tap Background: Dismiss popover
      cy.on('tap', (evt) => {
        if (evt.target === cy) {
          setPopoverState(null);
        }
      });
      cy.on('pan zoom', () => {
        setPopoverState(null);
      });

      // Automatically run layout once DOM container measurements have settled
      setTimeout(() => {
        if (cyRef.current) {
          cyRef.current.resize();
          const layout = cyRef.current.layout(getLayoutOptions(layoutName));
          layout.run();
        }
      }, 60);
    } else {
      cyRef.current.json({ elements });
      setTimeout(() => {
        if (cyRef.current) {
          cyRef.current.resize();
          runLayout(layoutName);
        }
      }, 60);
    }
  }, [graphData]);

  // Apply Subcategory, Relationship & MinDegree Filtering to Cytoscape elements
  useEffect(() => {
    if (!cyRef.current) return;
    const cy = cyRef.current;
    const allKnownSubcats = Array.from(currentAllSubcats);

    cy.batch(() => {
      cy.nodes().forEach((node) => {
        const rawSub = node.data('sub_category') || node.data('type') || 'Unclassified';
        const matchedSub = allKnownSubcats.find(
          (s) => s.toLowerCase() === rawSub.toLowerCase()
        ) || rawSub;

        const isTaxonomyActive = activeSubcategories.size > 0 && (
          activeSubcategories.has(matchedSub) ||
          activeSubcategories.has(rawSub) ||
          !allKnownSubcats.some(s => s.toLowerCase() === rawSub.toLowerCase())
        );
        const meetsDegree = (node.data('degree') || 0) >= minDegree;

        if (isTaxonomyActive && meetsDegree) {
          node.removeClass('hidden');
        } else {
          node.addClass('hidden');
        }
      });

      // Hide edges if either endpoint is hidden OR relationship is not active
      cy.edges().forEach((edge) => {
        const rel = (edge.data('relationship') || '').toLowerCase().replace(/\s+/g, '_');
        const isRelActive = activeRelationships.has(rel);
        if (edge.source().hasClass('hidden') || edge.target().hasClass('hidden') || !isRelActive) {
          edge.addClass('hidden');
        } else {
          edge.removeClass('hidden');
        }
      });
    });
  }, [activeSubcategories, activeRelationships, minDegree, currentAllSubcats]);

  const runLayout = (name: string) => {
    if (!cyRef.current) return;
    const layout = cyRef.current.layout(getLayoutOptions(name));
    layout.run();
  };

  const handleLayoutChange = (name: string) => {
    setLayoutName(name);
    runLayout(name);
  };

  const handleToggleFullscreen = () => {
    if (!wrapperRef.current) return;
    if (!document.fullscreenElement) {
      wrapperRef.current.requestFullscreen().catch(console.error);
    } else {
      document.exitFullscreen().catch(console.error);
    }
  };

  const handleFitGraph = () => {
    if (cyRef.current) {
      cyRef.current.fit(undefined, 40);
    }
  };

  const handleResetLayout = () => {
    runLayout(layoutName);
  };

  // Focus a specific node by ID
  const handleFocusNode = (nodeId: string) => {
    if (!cyRef.current) return;
    const cy = cyRef.current;
    const targetNode = cy.nodes().filter((n) => n.id() === nodeId || n.data('label') === nodeId);
    if (targetNode.length > 0) {
      cy.animate({
        center: { eles: targetNode },
        zoom: 1.4,
        duration: 350,
      });
      targetNode.select();

      const node: any = targetNode.first();
      const pos = node.renderedPosition();
      const connected = node.connectedEdges().map((e: any) => ({
        id: e.id(),
        relationship: e.data('relationship'),
        target: e.data('target') === node.id() ? e.data('source') : e.data('target'),
        evidence: e.data('evidence'),
      }));

      setPopoverState({
        type: 'node',
        x: pos.x,
        y: pos.y,
        nodeData: node.data(),
        connections: connected,
      });
    }
  };

  // Taxonomy Filter Handlers
  const handleToggleSubcategory = (subcat: string) => {
    setActiveSubcategories((prev) => {
      const next = new Set(prev);
      if (next.has(subcat)) next.delete(subcat);
      else next.add(subcat);
      return next;
    });
  };

  const handleToggleCategory = (category: string, subcats: string[]) => {
    setActiveSubcategories((prev) => {
      const next = new Set(prev);
      const allActive = subcats.every((s) => next.has(s));
      if (allActive) {
        subcats.forEach((s) => next.delete(s));
      } else {
        subcats.forEach((s) => next.add(s));
      }
      return next;
    });
  };

  const handleSelectAllTaxonomy = () => {
    setActiveSubcategories(new Set(dynamicAllSubcats));
  };

  const handleClearTaxonomy = () => {
    setActiveSubcategories(new Set());
  };

  // Relationship Filter Handlers
  const handleToggleRelationship = (rel: string) => {
    setActiveRelationships((prev) => {
      const next = new Set(prev);
      if (next.has(rel)) next.delete(rel);
      else next.add(rel);
      return next;
    });
  };

  const handleSelectAllRelationships = () => {
    setActiveRelationships(new Set(Object.keys(RELATIONSHIP_COLORS)));
  };

  const handleClearRelationships = () => {
    setActiveRelationships(new Set());
  };

  // Search highlighting
  useEffect(() => {
    if (!cyRef.current) return;
    const cy = cyRef.current;

    if (!searchQuery.trim()) {
      cy.elements().removeClass('faded highlighted');
      return;
    }

    const q = searchQuery.toLowerCase();
    const matchedNodes = cy.nodes().filter((n) => n.data('label')?.toLowerCase().includes(q));

    if (matchedNodes.length > 0) {
      cy.elements().addClass('faded').removeClass('highlighted');
      matchedNodes.removeClass('faded').addClass('highlighted');
      matchedNodes.connectedEdges().removeClass('faded').addClass('highlighted');
      cy.center(matchedNodes);
    } else {
      cy.elements().removeClass('faded highlighted');
    }
  }, [searchQuery]);

  return (
    <div
      ref={wrapperRef}
      className={`relative w-full h-full flex-1 min-h-0 bg-slate-50/60 border border-slate-200 overflow-hidden shadow-2xs ${
        isFullscreen ? 'fixed inset-0 z-50 rounded-none border-none' : 'rounded-2xl'
      }`}
    >
      {/* Cytoscape Canvas Container */}
      <div ref={containerRef} className="w-full h-full" />

      {/* Primary Floating Controls Overlay */}
      <GraphControls
        layoutName={layoutName}
        onLayoutChange={handleLayoutChange}
        minDegree={minDegree}
        onMinDegreeChange={onMinDegreeChange}
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        categoriesCount={categoriesCount}
        subcategoriesCount={subcategoriesCount}
        activeSubcategories={activeSubcategories}
        onToggleSubcategory={handleToggleSubcategory}
        onToggleCategory={handleToggleCategory}
        onSelectAllTaxonomy={handleSelectAllTaxonomy}
        onClearTaxonomy={handleClearTaxonomy}
        activeRelationships={activeRelationships}
        relationshipsCount={relationshipsCount}
        onToggleRelationship={handleToggleRelationship}
        onSelectAllRelationships={handleSelectAllRelationships}
        onClearRelationships={handleClearRelationships}
        onFitGraph={handleFitGraph}
        onResetLayout={handleResetLayout}
        isFullscreen={isFullscreen}
        onToggleFullscreen={handleToggleFullscreen}
        nerMode={nerMode}
      />

      {/* In-Canvas Contextual Popover Card (Directly On Clicked Element) */}
      <InCanvasPopover
        popover={popoverState}
        containerWidth={containerDimensions.width}
        containerHeight={containerDimensions.height}
        onClose={() => setPopoverState(null)}
        onFocusNode={handleFocusNode}
      />
    </div>
  );
};
