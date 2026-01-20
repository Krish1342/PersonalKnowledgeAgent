'use client';

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Network, ZoomIn, ZoomOut, Maximize2, RefreshCw, Filter } from 'lucide-react';
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
}

interface MemoryLink {
  source: string;
  target: string;
  strength: number;
}

interface GraphData {
  nodes: MemoryNode[];
  links: MemoryLink[];
}

// Color mapping for sources
const sourceColors: Record<string, string> = {
  'user_input': '#6366f1',
  'web_scrape': '#10b981',
  'file_upload': '#f59e0b',
  'api': '#ef4444',
  'import': '#8b5cf6',
  'default': '#64748b',
};

const tagColors: Record<string, string> = {
  'python': '#3b82f6',
  'javascript': '#eab308',
  'typescript': '#3178c6',
  'code': '#10b981',
  'documentation': '#8b5cf6',
  'tutorial': '#ec4899',
  'research': '#f97316',
};

export default function GraphPage() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [graphData, setGraphData] = useState<GraphData>({ nodes: [], links: [] });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedNode, setSelectedNode] = useState<MemoryNode | null>(null);
  const [zoom, setZoom] = useState(1);
  const [filter, setFilter] = useState<string>('all');
  const [sources, setSources] = useState<string[]>([]);

  // Fetch memories and build graph
  const fetchGraphData = useCallback(async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch(`${API_BASE_URL}/api/v2/memory?limit=200`);
      if (!response.ok) throw new Error('Failed to fetch memories');
      
      const data = await response.json();
      const memories = data.memories || [];
      
      // Extract unique sources
      const uniqueSources = Array.from(new Set<string>(memories.map((m: any) => m.source || 'unknown')));
      setSources(uniqueSources);
      
      // Build nodes
      const nodes: MemoryNode[] = memories.map((memory: any) => ({
        id: `memory-${memory.id}`,
        label: memory.title?.substring(0, 30) || `Memory ${memory.id}`,
        source: memory.source,
        tags: memory.tags?.map((t: any) => t.name) || [],
        size: Math.min(20, Math.max(8, Math.log(memory.original_size || 100) * 2)),
        color: sourceColors[memory.source] || sourceColors.default,
      }));
      
      // Build links based on shared tags
      const links: MemoryLink[] = [];
      for (let i = 0; i < nodes.length; i++) {
        for (let j = i + 1; j < nodes.length; j++) {
          const sharedTags = nodes[i].tags.filter(t => nodes[j].tags.includes(t));
          if (sharedTags.length > 0) {
            links.push({
              source: nodes[i].id,
              target: nodes[j].id,
              strength: sharedTags.length / Math.max(nodes[i].tags.length, nodes[j].tags.length, 1),
            });
          }
          // Also link by same source
          if (nodes[i].source === nodes[j].source) {
            const existing = links.find(
              l => (l.source === nodes[i].id && l.target === nodes[j].id) ||
                   (l.source === nodes[j].id && l.target === nodes[i].id)
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

  // Simple force-directed layout simulation
  useEffect(() => {
    if (!canvasRef.current || graphData.nodes.length === 0) return;
    
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    
    // Set canvas size
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width * window.devicePixelRatio;
    canvas.height = rect.height * window.devicePixelRatio;
    ctx.scale(window.devicePixelRatio, window.devicePixelRatio);
    
    // Initialize positions
    const positions: Record<string, { x: number; y: number; vx: number; vy: number }> = {};
    graphData.nodes.forEach((node, i) => {
      const angle = (i / graphData.nodes.length) * 2 * Math.PI;
      const radius = 150;
      positions[node.id] = {
        x: rect.width / 2 + Math.cos(angle) * radius,
        y: rect.height / 2 + Math.sin(angle) * radius,
        vx: 0,
        vy: 0,
      };
    });
    
    // Filter nodes by source
    const filteredNodes = filter === 'all' 
      ? graphData.nodes 
      : graphData.nodes.filter(n => n.source === filter);
    const filteredNodeIds = new Set(filteredNodes.map(n => n.id));
    const filteredLinks = graphData.links.filter(
      l => filteredNodeIds.has(l.source) && filteredNodeIds.has(l.target)
    );
    
    // Animation loop
    let animationId: number;
    const simulate = () => {
      // Clear canvas
      ctx.fillStyle = '#030712';
      ctx.fillRect(0, 0, rect.width, rect.height);
      
      // Apply forces
      filteredNodes.forEach(node => {
        const pos = positions[node.id];
        
        // Center gravity
        pos.vx += (rect.width / 2 - pos.x) * 0.001;
        pos.vy += (rect.height / 2 - pos.y) * 0.001;
        
        // Repulsion from other nodes
        filteredNodes.forEach(other => {
          if (node.id === other.id) return;
          const otherPos = positions[other.id];
          const dx = pos.x - otherPos.x;
          const dy = pos.y - otherPos.y;
          const dist = Math.sqrt(dx * dx + dy * dy) || 1;
          const force = 500 / (dist * dist);
          pos.vx += (dx / dist) * force;
          pos.vy += (dy / dist) * force;
        });
      });
      
      // Spring forces from links
      filteredLinks.forEach(link => {
        const sourcePos = positions[link.source];
        const targetPos = positions[link.target];
        if (!sourcePos || !targetPos) return;
        
        const dx = targetPos.x - sourcePos.x;
        const dy = targetPos.y - sourcePos.y;
        const dist = Math.sqrt(dx * dx + dy * dy) || 1;
        const force = (dist - 100) * 0.01 * link.strength;
        
        sourcePos.vx += (dx / dist) * force;
        sourcePos.vy += (dy / dist) * force;
        targetPos.vx -= (dx / dist) * force;
        targetPos.vy -= (dy / dist) * force;
      });
      
      // Update positions with damping
      filteredNodes.forEach(node => {
        const pos = positions[node.id];
        pos.vx *= 0.9;
        pos.vy *= 0.9;
        pos.x += pos.vx;
        pos.y += pos.vy;
        
        // Bounds
        pos.x = Math.max(30, Math.min(rect.width - 30, pos.x));
        pos.y = Math.max(30, Math.min(rect.height - 30, pos.y));
      });
      
      // Draw links
      ctx.strokeStyle = 'rgba(99, 102, 241, 0.2)';
      ctx.lineWidth = 1;
      filteredLinks.forEach(link => {
        const sourcePos = positions[link.source];
        const targetPos = positions[link.target];
        if (!sourcePos || !targetPos) return;
        
        ctx.beginPath();
        ctx.moveTo(sourcePos.x * zoom, sourcePos.y * zoom);
        ctx.lineTo(targetPos.x * zoom, targetPos.y * zoom);
        ctx.stroke();
      });
      
      // Draw nodes
      filteredNodes.forEach(node => {
        const pos = positions[node.id];
        const isSelected = selectedNode?.id === node.id;
        
        // Glow effect
        if (isSelected) {
          const gradient = ctx.createRadialGradient(
            pos.x * zoom, pos.y * zoom, 0,
            pos.x * zoom, pos.y * zoom, node.size * 2 * zoom
          );
          gradient.addColorStop(0, node.color + '80');
          gradient.addColorStop(1, 'transparent');
          ctx.fillStyle = gradient;
          ctx.beginPath();
          ctx.arc(pos.x * zoom, pos.y * zoom, node.size * 2 * zoom, 0, Math.PI * 2);
          ctx.fill();
        }
        
        // Node circle
        ctx.fillStyle = node.color;
        ctx.beginPath();
        ctx.arc(pos.x * zoom, pos.y * zoom, node.size * zoom, 0, Math.PI * 2);
        ctx.fill();
        
        // Node label
        ctx.fillStyle = '#fff';
        ctx.font = `${10 * zoom}px system-ui`;
        ctx.textAlign = 'center';
        ctx.fillText(node.label, pos.x * zoom, (pos.y + node.size + 12) * zoom);
      });
      
      animationId = requestAnimationFrame(simulate);
    };
    
    simulate();
    
    // Handle clicks
    const handleClick = (e: MouseEvent) => {
      const rect = canvas.getBoundingClientRect();
      const x = (e.clientX - rect.left) / zoom;
      const y = (e.clientY - rect.top) / zoom;
      
      for (const node of filteredNodes) {
        const pos = positions[node.id];
        const dx = x - pos.x;
        const dy = y - pos.y;
        if (Math.sqrt(dx * dx + dy * dy) < node.size) {
          setSelectedNode(node);
          return;
        }
      }
      setSelectedNode(null);
    };
    
    canvas.addEventListener('click', handleClick);
    
    return () => {
      cancelAnimationFrame(animationId);
      canvas.removeEventListener('click', handleClick);
    };
  }, [graphData, zoom, filter, selectedNode]);

  return (
    <div className="min-h-[calc(100vh-4rem)] p-4 sm:p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
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
            {/* Filter */}
            <select
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              className="px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white text-xs sm:text-sm touch-manipulation flex-grow sm:flex-grow-0"
            >
              <option value="all">All Sources</option>
              {sources.map(source => (
                <option key={source} value={source}>{source}</option>
              ))}
            </select>
            
            {/* Zoom controls */}
            <div className="flex items-center gap-2 bg-gray-900 rounded-lg p-1">
              <Button
                variant="secondary"
                size="sm"
                onClick={() => setZoom(z => Math.max(0.5, z - 0.1))}
              >
                <ZoomOut className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
              </Button>
              <span className="text-gray-400 text-xs sm:text-sm w-10 sm:w-12 text-center">
                {Math.round(zoom * 100)}%
              </span>
              <Button
                variant="secondary"
                size="sm"
                onClick={() => setZoom(z => Math.min(2, z + 0.1))}
              >
                <ZoomIn className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
              </Button>
              <Button
                variant="secondary"
                size="sm"
                onClick={() => setZoom(1)}
              >
                <Maximize2 className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
              </Button>
            </div>
            <Button
              variant="secondary"
              size="sm"
              onClick={fetchGraphData}
              isLoading={loading}
            >
              <RefreshCw className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
            </Button>
          </div>
        </div>

        {error && (
          <Alert type="error" message={error} onClose={() => setError(null)} />
        )}

        <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
          {/* Graph Canvas */}
          <div className="lg:col-span-3">
            <Card>
              <CardContent className="p-0">
                <div className="relative h-[400px] sm:h-[500px] md:h-[600px] bg-gray-950 rounded-lg overflow-hidden">
                  {loading ? (
                    <div className="absolute inset-0 flex items-center justify-center">
                      <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-500"></div>
                    </div>
                  ) : graphData.nodes.length === 0 ? (
                    <div className="absolute inset-0 flex flex-col items-center justify-center text-gray-400 p-4">
                      <Network className="w-12 h-12 sm:w-16 sm:h-16 mb-4 opacity-50" />
                      <p className="text-sm sm:text-base">No memories to visualize</p>
                      <p className="text-xs sm:text-sm">Ingest some content to see the graph</p>
                    </div>
                  ) : (
                    <canvas
                      ref={canvasRef}
                      className="w-full h-full cursor-pointer touch-none"
                    />
                  )}
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Sidebar */}
          <div className="space-y-4">
            {/* Legend */}
            <Card>
              <CardHeader>
                <h3 className="font-semibold text-white">Legend</h3>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {Object.entries(sourceColors).filter(([k]) => k !== 'default').map(([source, color]) => (
                    <div key={source} className="flex items-center gap-2">
                      <div 
                        className="w-3 h-3 rounded-full"
                        style={{ backgroundColor: color }}
                      />
                      <span className="text-sm text-gray-300">{source}</span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* Stats */}
            <Card>
              <CardHeader>
                <h3 className="font-semibold text-white">Statistics</h3>
              </CardHeader>
              <CardContent>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-400">Total Nodes</span>
                    <span className="text-white">{graphData.nodes.length}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Total Links</span>
                    <span className="text-white">{graphData.links.length}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Avg Connections</span>
                    <span className="text-white">
                      {graphData.nodes.length > 0 
                        ? ((graphData.links.length * 2) / graphData.nodes.length).toFixed(1)
                        : 0
                      }
                    </span>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Selected Node */}
            {selectedNode && (
              <Card>
                <CardHeader>
                  <h3 className="font-semibold text-white">Selected Memory</h3>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    <div>
                      <p className="text-xs text-gray-400">Title</p>
                      <p className="text-white">{selectedNode.label}</p>
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
                    {selectedNode.tags.length > 0 && (
                      <div>
                        <p className="text-xs text-gray-400 mb-1">Tags</p>
                        <div className="flex flex-wrap gap-1">
                          {selectedNode.tags.map(tag => (
                            <span 
                              key={tag}
                              className="px-2 py-0.5 bg-gray-800 rounded text-xs text-gray-300"
                            >
                              {tag}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
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
