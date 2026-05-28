'use client';

import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import ForceGraph2D, { ForceGraphMethods } from 'react-force-graph-2d';
import { forceCollide, forceX, forceY } from 'd3-force';
import {
  Network,
  ZoomIn,
  ZoomOut,
  Maximize2,
  RefreshCw,
  Search,
  Pause,
  Play,
  Target,
} from 'lucide-react';
import { Card, CardHeader, CardContent } from '@/components/Card';
import { Button } from '@/components/Button';
import { Alert } from '@/components/Alert';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface MemoryNode {
  id: string;
  label: string;
  source: string;
  tags: string[];
  size: number;
  color: string;
  content: string;
  degree?: number;
  x?: number;
  y?: number;
}

interface MemoryLink {
  source: string | MemoryNode;
  target: string | MemoryNode;
  strength: number;
}

interface GraphData {
  nodes: MemoryNode[];
  links: MemoryLink[];
}

interface ViewportBounds {
  xMin: number;
  xMax: number;
  yMin: number;
  yMax: number;
}

const sourceColors: Record<string, string> = {
  user_input: '#6366f1',
  web_scrape: '#10b981',
  file_upload: '#f59e0b',
  api: '#ef4444',
  import: '#8b5cf6',
  default: '#64748b',
};

const tagColors: Record<string, string> = {
  python: '#3b82f6',
  javascript: '#eab308',
  typescript: '#3178c6',
  code: '#10b981',
  documentation: '#8b5cf6',
  tutorial: '#ec4899',
  research: '#f97316',
};

const DEFAULT_MIN_CONNECTIONS = 5;

export default function GraphPage() {
  const fgRef = useRef<ForceGraphMethods>();
  const containerRef = useRef<HTMLDivElement>(null);
  const clusterDrawnRef = useRef(false);
  const [graphData, setGraphData] = useState<GraphData>({ nodes: [], links: [] });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedNode, setSelectedNode] = useState<MemoryNode | null>(null);
  const [hoveredNode, setHoveredNode] = useState<MemoryNode | null>(null);
  const [zoom, setZoom] = useState(1);
  const [sources, setSources] = useState<string[]>([]);
  const [typeFilters, setTypeFilters] = useState<Record<string, boolean>>({});
  const [minConnections, setMinConnections] = useState(DEFAULT_MIN_CONNECTIONS);
  const [searchTerm, setSearchTerm] = useState('');
  const [focusMode, setFocusMode] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [mousePosition, setMousePosition] = useState({ x: 0, y: 0 });
  const [viewportBounds, setViewportBounds] = useState<ViewportBounds>({
    xMin: -Infinity,
    xMax: Infinity,
    yMin: -Infinity,
    yMax: Infinity,
  });

  const fetchGraphData = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`${API_BASE_URL}/api/memory?limit=200`);
      if (!response.ok) throw new Error('Failed to fetch memories');

      const data = await response.json();
      const memories = data.items || [];

      const uniqueSources = Array.from(
        new Set<string>(memories.map((m: any) => m.source || 'unknown'))
      );
      setSources(uniqueSources);
      setTypeFilters((prev) => {
        if (Object.keys(prev).length > 0) return prev;
        const next: Record<string, boolean> = {};
        uniqueSources.forEach((source) => {
          next[source] = true;
        });
        return next;
      });

      const nodes: MemoryNode[] = memories.map((memory: any) => {
        const rawContent = memory.content || '';
        const contentPreview = rawContent.substring(0, 60).trim();
        const label =
          contentPreview.length > 45
            ? `${contentPreview.substring(0, 45)}...`
            : contentPreview || `Memory ${memory.id}`;

        const contentLower = rawContent.toLowerCase();
        const extractedTags: string[] = [];
        Object.keys(tagColors).forEach((tag) => {
          if (contentLower.includes(tag)) extractedTags.push(tag);
        });

        return {
          id: `memory-${memory.id}`,
          label,
          source: memory.source || 'unknown',
          tags: extractedTags,
          size: Math.min(20, Math.max(8, Math.log((rawContent.length || 100)) * 2)),
          color: sourceColors[memory.source] || sourceColors.default,
          content: rawContent,
        };
      });

      const links: MemoryLink[] = [];
      for (let i = 0; i < nodes.length; i += 1) {
        for (let j = i + 1; j < nodes.length; j += 1) {
          const sharedTags = nodes[i].tags.filter((t) => nodes[j].tags.includes(t));
          if (sharedTags.length > 0) {
            links.push({
              source: nodes[i].id,
              target: nodes[j].id,
              strength:
                sharedTags.length /
                Math.max(nodes[i].tags.length, nodes[j].tags.length, 1),
            });
          }

          if (nodes[i].source === nodes[j].source) {
            const existing = links.find(
              (link) =>
                (link.source === nodes[i].id && link.target === nodes[j].id) ||
                (link.source === nodes[j].id && link.target === nodes[i].id)
            );
            if (existing) {
              existing.strength += 0.2;
            } else {
              links.push({
                source: nodes[i].id,
                target: nodes[j].id,
                strength: 0.2,
              });
            }
          }
        }
      }

      setGraphData({ nodes, links });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load graph');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchGraphData();
  }, [fetchGraphData]);

  const graphWithStats = useMemo(() => {
    const degreeMap = new Map<string, number>();
    graphData.links.forEach((link) => {
      const sourceId = typeof link.source === 'string' ? link.source : link.source.id;
      const targetId = typeof link.target === 'string' ? link.target : link.target.id;
      degreeMap.set(sourceId, (degreeMap.get(sourceId) || 0) + 1);
      degreeMap.set(targetId, (degreeMap.get(targetId) || 0) + 1);
    });

    const nodes = graphData.nodes.map((node) => ({
      ...node,
      degree: degreeMap.get(node.id) || 0,
    }));

    const neighbors = new Map<string, Set<string>>();
    graphData.links.forEach((link) => {
      const sourceId = typeof link.source === 'string' ? link.source : link.source.id;
      const targetId = typeof link.target === 'string' ? link.target : link.target.id;
      if (!neighbors.has(sourceId)) neighbors.set(sourceId, new Set());
      if (!neighbors.has(targetId)) neighbors.set(targetId, new Set());
      neighbors.get(sourceId)?.add(targetId);
      neighbors.get(targetId)?.add(sourceId);
    });

    return { nodes, links: graphData.links, neighbors };
  }, [graphData]);

  const filteredGraph = useMemo(() => {
    const activeTypes = Object.entries(typeFilters)
      .filter(([, enabled]) => enabled)
      .map(([type]) => type);

    const nodesById = new Map(graphWithStats.nodes.map((node) => [node.id, node]));
    let nodes = graphWithStats.nodes.filter((node) =>
      activeTypes.length === 0 ? true : activeTypes.includes(node.source)
    );

    nodes = nodes.filter((node) => (node.degree || 0) >= minConnections);

    let links = graphWithStats.links.filter((link) => {
      const sourceId = typeof link.source === 'string' ? link.source : link.source.id;
      const targetId = typeof link.target === 'string' ? link.target : link.target.id;
      return nodesById.has(sourceId) && nodesById.has(targetId);
    });

    if (focusMode && selectedNode) {
      const focusIds = new Set<string>();
      focusIds.add(selectedNode.id);

      const firstHop = graphWithStats.neighbors.get(selectedNode.id) || new Set();
      firstHop.forEach((id) => focusIds.add(id));

      firstHop.forEach((id) => {
        graphWithStats.neighbors.get(id)?.forEach((neighbor) => focusIds.add(neighbor));
      });

      nodes = nodes.filter((node) => focusIds.has(node.id));
      links = links.filter((link) => {
        const sourceId = typeof link.source === 'string' ? link.source : link.source.id;
        const targetId = typeof link.target === 'string' ? link.target : link.target.id;
        return focusIds.has(sourceId) && focusIds.has(targetId);
      });
    }

    return { nodes, links };
  }, [graphWithStats, typeFilters, minConnections, focusMode, selectedNode]);

  const updateViewportBounds = useCallback(() => {
    if (!fgRef.current || !containerRef.current) return;
    const width = containerRef.current.clientWidth;
    const height = containerRef.current.clientHeight;
    const topLeft = fgRef.current.screen2GraphCoords(0, 0);
    const bottomRight = fgRef.current.screen2GraphCoords(width, height);

    setViewportBounds({
      xMin: Math.min(topLeft.x, bottomRight.x),
      xMax: Math.max(topLeft.x, bottomRight.x),
      yMin: Math.min(topLeft.y, bottomRight.y),
      yMax: Math.max(topLeft.y, bottomRight.y),
    });
  }, []);

  useEffect(() => {
    updateViewportBounds();
  }, [zoom, updateViewportBounds]);

  useEffect(() => {
    const handleResize = () => updateViewportBounds();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [updateViewportBounds]);

  const nodeRadius = useCallback((node: MemoryNode) => Math.max(6, node.size), []);

  const clusterCentroids = useMemo(() => {
    const center = { x: 0, y: 0 };
    const types = sources.length > 0 ? sources : Object.keys(sourceColors).filter((k) => k !== 'default');
    const radius = 220;
    const map: Record<string, { x: number; y: number; color: string }> = {};
    types.forEach((type, index) => {
      const angle = (index / types.length) * Math.PI * 2;
      map[type] = {
        x: center.x + Math.cos(angle) * radius,
        y: center.y + Math.sin(angle) * radius,
        color: sourceColors[type] || sourceColors.default,
      };
    });
    return map;
  }, [sources]);

  const clusterForce = useMemo(() => {
    const strength = 0.15;
    let nodes: MemoryNode[] = [];

    const force = (alpha: number) => {
      nodes.forEach((node) => {
        const centroid = clusterCentroids[node.source];
        if (!centroid || node.x === undefined || node.y === undefined) return;
        node.vx = (node.vx || 0) + (centroid.x - node.x) * strength * alpha;
        node.vy = (node.vy || 0) + (centroid.y - node.y) * strength * alpha;
      });
    };

    force.initialize = (initNodes: MemoryNode[]) => {
      nodes = initNodes;
    };

    return force;
  }, [clusterCentroids]);

  useEffect(() => {
    if (!fgRef.current) return;

    fgRef.current.d3Force('link')?.distance(80).strength(0.3);
    fgRef.current.d3Force('charge')?.strength(-300).distanceMax(400);
    fgRef.current.d3Force('collision', forceCollide<MemoryNode>().radius((node) => nodeRadius(node) + 12).strength(1));
    fgRef.current.d3Force('center')?.x(0).y(0);
    fgRef.current.d3Force('x', forceX(0).strength(0.05));
    fgRef.current.d3Force('y', forceY(0).strength(0.05));
    fgRef.current.d3Force('cluster', clusterForce as any);

    const fgAny = fgRef.current as unknown as {
      d3AlphaDecay?: (value: number) => void;
      d3VelocityDecay?: (value: number) => void;
    };
    fgAny.d3AlphaDecay?.(0.02);
    fgAny.d3VelocityDecay?.(0.4);
    fgRef.current.d3ReheatSimulation();
  }, [clusterForce, nodeRadius, filteredGraph.nodes.length]);

  useEffect(() => {
    if (!fgRef.current) return;
    if (isPaused) {
      fgRef.current.pauseAnimation();
    } else {
      fgRef.current.resumeAnimation();
      fgRef.current.d3ReheatSimulation();
    }
  }, [isPaused]);

  const handleZoom = useCallback(
    (transform: { k: number }) => {
      setZoom(transform.k);
      updateViewportBounds();
    },
    [updateViewportBounds]
  );

  const isNodeInViewport = useCallback(
    (node?: MemoryNode | null) => {
      if (!node || node.x === undefined || node.y === undefined) return false;
      return (
        node.x >= viewportBounds.xMin &&
        node.x <= viewportBounds.xMax &&
        node.y >= viewportBounds.yMin &&
        node.y <= viewportBounds.yMax
      );
    },
    [viewportBounds]
  );

  const focusedNode = hoveredNode || selectedNode;

  const linkVisibility = useCallback(
    (link: MemoryLink) => {
      const source = link.source as MemoryNode;
      const target = link.target as MemoryNode;
      if (!source || !target) return false;

      const inView = isNodeInViewport(source) && isNodeInViewport(target);
      if (!inView) return false;

      if (!focusedNode) return true;

      return source.id === focusedNode.id || target.id === focusedNode.id;
    },
    [focusedNode, isNodeInViewport]
  );

  const linkWidth = useCallback(
    (link: MemoryLink) => {
      if (!focusedNode) return 0.3;
      const source = link.source as MemoryNode;
      const target = link.target as MemoryNode;
      return source?.id === focusedNode.id || target?.id === focusedNode.id ? 1.5 : 0.3;
    },
    [focusedNode]
  );

  const linkColor = useCallback(
    (link: MemoryLink) => {
      if (!focusedNode) return 'rgba(148, 163, 184, 0.08)';
      const source = link.source as MemoryNode;
      const target = link.target as MemoryNode;
      const isFocused = source?.id === focusedNode.id || target?.id === focusedNode.id;
      return isFocused ? 'rgba(99, 102, 241, 0.9)' : 'rgba(148, 163, 184, 0.02)';
    },
    [focusedNode]
  );

  const nodeCanvasObject = useCallback(
    (node: MemoryNode, ctx: CanvasRenderingContext2D, globalScale: number) => {
      const radius = nodeRadius(node);
      const isFocused = focusedNode && (node.id === focusedNode.id || graphWithStats.neighbors.get(focusedNode.id)?.has(node.id));
      const isDimmed = focusedNode && !isFocused;

      if (node.x === undefined || node.y === undefined) return;

      ctx.beginPath();
      ctx.fillStyle = isDimmed ? 'rgba(71, 85, 105, 0.25)' : node.color;
      ctx.arc(node.x, node.y, radius, 0, Math.PI * 2);
      ctx.fill();

      const zoomLevel = globalScale;
      let showLabel = false;
      if (zoomLevel < 0.5) {
        showLabel = false;
      } else if (zoomLevel < 1) {
        showLabel = (node.degree || 0) > 20;
      } else if (zoomLevel < 2) {
        showLabel = (node.degree || 0) > 5;
      } else {
        showLabel = isNodeInViewport(node);
      }

      if (!showLabel) return;

      const fontSize = Math.max(10, 12 / zoomLevel);
      ctx.font = `${fontSize}px "IBM Plex Sans", sans-serif`;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillStyle = isDimmed ? 'rgba(148, 163, 184, 0.5)' : '#f8fafc';
      ctx.fillText(node.label, node.x, node.y + radius + 10 / zoomLevel);
    },
    [focusedNode, graphWithStats.neighbors, isNodeInViewport, nodeRadius]
  );

  const renderClusterBackground = useCallback(
    (ctx: CanvasRenderingContext2D) => {
      if (clusterDrawnRef.current) return;
      clusterDrawnRef.current = true;

      Object.values(clusterCentroids).forEach((centroid) => {
        ctx.beginPath();
        ctx.fillStyle = `${centroid.color}0D`;
        ctx.strokeStyle = `${centroid.color}1A`;
        ctx.lineWidth = 1;
        ctx.arc(centroid.x, centroid.y, 140, 0, Math.PI * 2);
        ctx.fill();
        ctx.stroke();
      });
    },
    [clusterCentroids]
  );

  const topConnections = useCallback(
    (node: MemoryNode | null) => {
      if (!node) return [];
      const neighbors = Array.from(graphWithStats.neighbors.get(node.id) || []);
      return neighbors
        .map((id) => graphWithStats.nodes.find((n) => n.id === id))
        .filter(Boolean)
        .slice(0, 3) as MemoryNode[];
    },
    [graphWithStats]
  );

  const handleSearch = useCallback(() => {
    const term = searchTerm.trim().toLowerCase();
    if (!term) return;

    const match = graphWithStats.nodes.find(
      (node) => node.label.toLowerCase().includes(term) || node.content.toLowerCase().includes(term)
    );

    if (match && fgRef.current) {
      setSelectedNode(match);
      setFocusMode(true);
      fgRef.current.centerAt(match.x || 0, match.y || 0, 600);
      fgRef.current.zoom(2, 600);
    }
  }, [graphWithStats.nodes, searchTerm]);

  const resetView = useCallback(() => {
    if (!fgRef.current) return;
    fgRef.current.centerAt(0, 0, 600);
    fgRef.current.zoom(1, 600);
    setZoom(1);
  }, []);

  const focusOnNode = useCallback((node: MemoryNode) => {
    if (!fgRef.current) return;
    fgRef.current.centerAt(node.x || 0, node.y || 0, 600);
    fgRef.current.zoom(2, 600);
    setFocusMode(true);
  }, []);

  const handleMouseMove = useCallback((event: React.MouseEvent<HTMLDivElement>) => {
    const rect = event.currentTarget.getBoundingClientRect();
    setMousePosition({ x: event.clientX - rect.left, y: event.clientY - rect.top });
  }, []);

  const tooltipNode = hoveredNode || selectedNode;
  const allConnections = useCallback(
    (node: MemoryNode | null) => {
      if (!node) return [];
      const neighbors = Array.from(graphWithStats.neighbors.get(node.id) || []);
      return neighbors
        .map((id) => graphWithStats.nodes.find((n) => n.id === id))
        .filter(Boolean) as MemoryNode[];
    },
    [graphWithStats]
  );

  return (
    <div className="min-h-[calc(100vh-4rem)] p-4 sm:p-6">
      <div className="max-w-7xl mx-auto">
        <div className="flex flex-col gap-3 sm:gap-4 mb-4 sm:mb-6">
          <div>
            <h1 className="text-xl sm:text-2xl font-bold text-white flex items-center gap-2">
              <Network className="w-6 h-6 sm:w-7 sm:h-7 text-indigo-500" />
              Knowledge Graph
            </h1>
            <p className="text-sm sm:text-base text-gray-400 mt-1">
              Visualize connections between your memories
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <div className="flex items-center gap-2 bg-gray-900 rounded-lg p-1">
              <Button
                variant="secondary"
                size="sm"
                onClick={() => fgRef.current?.zoom(Math.max(0.4, zoom - 0.1), 300)}
              >
                <ZoomOut className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
              </Button>
              <span className="text-gray-400 text-xs sm:text-sm w-10 sm:w-12 text-center">
                {Math.round(zoom * 100)}%
              </span>
              <Button
                variant="secondary"
                size="sm"
                onClick={() => fgRef.current?.zoom(Math.min(3, zoom + 0.1), 300)}
              >
                <ZoomIn className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
              </Button>
              <Button variant="secondary" size="sm" onClick={resetView}>
                <Maximize2 className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
              </Button>
            </div>
            <Button variant="secondary" size="sm" onClick={fetchGraphData} isLoading={loading}>
              <RefreshCw className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
            </Button>
          </div>
        </div>

        {error && <Alert type="error" message={error} onClose={() => setError(null)} />}

        <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
          <div className="lg:col-span-3">
            <Card>
              <CardContent className="p-0">
                <div
                  ref={containerRef}
                  onMouseMove={handleMouseMove}
                  className="relative h-[420px] sm:h-[520px] md:h-[640px] bg-gray-950 rounded-lg overflow-hidden"
                >
                  {loading ? (
                    <div className="absolute inset-0 flex items-center justify-center">
                      <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-500" />
                    </div>
                  ) : filteredGraph.nodes.length === 0 ? (
                    <div className="absolute inset-0 flex flex-col items-center justify-center text-gray-400 p-4">
                      <Network className="w-12 h-12 sm:w-16 sm:h-16 mb-4 opacity-50" />
                      <p className="text-sm sm:text-base">No memories to visualize</p>
                      <p className="text-xs sm:text-sm">Ingest some content to see the graph</p>
                    </div>
                  ) : (
                    <ForceGraph2D
                      ref={fgRef}
                      graphData={filteredGraph}
                      backgroundColor="#030712"
                      nodeRelSize={4}
                      nodeVal={(node) => (node as MemoryNode).size}
                      nodeColor={(node) => (node as MemoryNode).color}
                      nodeVisibility={(node) => isNodeInViewport(node as MemoryNode)}
                      linkDirectionalParticles={0}
                      linkVisibility={linkVisibility}
                      linkColor={linkColor}
                      linkWidth={linkWidth}
                      onRenderFramePre={(ctx) => {
                        clusterDrawnRef.current = false;
                        renderClusterBackground(ctx);
                      }}
                      onZoom={handleZoom}
                      onNodeHover={(node) => setHoveredNode((node as MemoryNode) || null)}
                      onNodeClick={(node) => setSelectedNode(node as MemoryNode)}
                      onEngineTick={updateViewportBounds}
                      nodeCanvasObject={nodeCanvasObject}
                      enableNodeDrag={!isPaused}
                    />
                  )}

                  {tooltipNode && (
                    <div
                      className="absolute z-10 max-w-xs rounded-lg bg-gray-900/95 border border-gray-800 shadow-xl p-3 text-xs text-gray-200"
                      style={{
                        left: Math.min(mousePosition.x + 12, 360),
                        top: Math.min(mousePosition.y + 12, 320),
                      }}
                    >
                      <div className="text-sm font-semibold text-white mb-2">
                        {tooltipNode.label}
                      </div>
                      <div className="flex items-center gap-2 mb-2">
                        <span
                          className="px-2 py-0.5 rounded text-[11px] text-white"
                          style={{ backgroundColor: tooltipNode.color }}
                        >
                          {tooltipNode.source}
                        </span>
                        <span className="text-gray-400">
                          {(tooltipNode.degree || 0).toLocaleString()} connections
                        </span>
                      </div>
                      <div className="text-gray-400">
                        Top connections: {topConnections(tooltipNode).map((node) => node.label).join(', ') || 'None'}
                      </div>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>

          <div className="space-y-4">
            <Card>
              <CardHeader>
                <h3 className="font-semibold text-white">Controls</h3>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <label className="text-xs text-gray-400">Search</label>
                  <div className="mt-2 flex gap-2">
                    <input
                      value={searchTerm}
                      onChange={(event) => setSearchTerm(event.target.value)}
                      placeholder="Find a node"
                      className="flex-1 px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm text-white"
                    />
                    <Button variant="secondary" size="sm" onClick={handleSearch}>
                      <Search className="w-4 h-4" />
                    </Button>
                  </div>
                </div>

                <div>
                  <label className="text-xs text-gray-400">Min connections: {minConnections}</label>
                  <input
                    type="range"
                    min={0}
                    max={30}
                    step={1}
                    value={minConnections}
                    onChange={(event) => setMinConnections(Number(event.target.value))}
                    className="w-full mt-2"
                  />
                </div>

                <div className="space-y-2">
                  <div className="text-xs text-gray-400">Filter by type</div>
                  {sources.map((source) => (
                    <label key={source} className="flex items-center gap-2 text-sm text-gray-300">
                      <input
                        type="checkbox"
                        checked={typeFilters[source] ?? true}
                        onChange={(event) =>
                          setTypeFilters((prev) => ({
                            ...prev,
                            [source]: event.target.checked,
                          }))
                        }
                      />
                      <span
                        className="inline-block w-2.5 h-2.5 rounded-full"
                        style={{ backgroundColor: sourceColors[source] || sourceColors.default }}
                      />
                      {source}
                    </label>
                  ))}
                </div>

                <div className="flex flex-wrap gap-2">
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => setFocusMode((prev) => !prev)}
                  >
                    <Target className="w-4 h-4" />
                    {focusMode ? 'Focus mode on' : 'Focus mode off'}
                  </Button>
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => setIsPaused((prev) => !prev)}
                  >
                    {isPaused ? <Play className="w-4 h-4" /> : <Pause className="w-4 h-4" />}
                    {isPaused ? 'Resume' : 'Pause'}
                  </Button>
                  <Button variant="secondary" size="sm" onClick={resetView}>
                    Reset view
                  </Button>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <h3 className="font-semibold text-white">Legend</h3>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {Object.entries(sourceColors)
                    .filter(([key]) => key !== 'default')
                    .map(([source, color]) => (
                      <div key={source} className="flex items-center gap-2">
                        <div className="w-3 h-3 rounded-full" style={{ backgroundColor: color }} />
                        <span className="text-sm text-gray-300">{source}</span>
                      </div>
                    ))}
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <h3 className="font-semibold text-white">Statistics</h3>
              </CardHeader>
              <CardContent>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-400">Total Nodes</span>
                    <span className="text-white">{filteredGraph.nodes.length}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Total Links</span>
                    <span className="text-white">{filteredGraph.links.length}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Avg Connections</span>
                    <span className="text-white">
                      {filteredGraph.nodes.length > 0
                        ? ((filteredGraph.links.length * 2) / filteredGraph.nodes.length).toFixed(1)
                        : 0}
                    </span>
                  </div>
                </div>
              </CardContent>
            </Card>

            {selectedNode && (
              <Card>
                <CardHeader>
                  <h3 className="font-semibold text-white">Selected Memory</h3>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    <div>
                      <p className="text-xs text-gray-400">Title</p>
                      <p className="text-white text-sm">{selectedNode.label}</p>
                    </div>
                    <div>
                      <p className="text-xs text-gray-400">Source</p>
                      <span
                        className="inline-block px-2 py-1 rounded text-xs text-white"
                        style={{ backgroundColor: selectedNode.color }}
                      >
                        {selectedNode.source}
                      </span>
                    </div>
                    <div>
                      <p className="text-xs text-gray-400">Connections</p>
                      <p className="text-sm text-gray-200">
                        {(selectedNode.degree || 0).toLocaleString()} total
                      </p>
                    </div>
                    <div>
                      <p className="text-xs text-gray-400">Preview</p>
                      <p className="text-sm text-gray-200 line-clamp-4">
                        {selectedNode.content || 'No content available.'}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs text-gray-400">Connections</p>
                      <div className="mt-2 max-h-28 overflow-y-auto space-y-1 text-sm text-gray-300">
                        {allConnections(selectedNode).length === 0
                          ? 'No linked nodes'
                          : allConnections(selectedNode).map((node) => (
                              <div key={node.id} className="truncate">
                                {node.label}
                              </div>
                            ))}
                      </div>
                    </div>
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => focusOnNode(selectedNode)}
                    >
                      Focus on this node
                    </Button>
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
