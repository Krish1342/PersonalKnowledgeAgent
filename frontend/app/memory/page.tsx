"use client";

import React, { useState, useEffect } from "react";
import {
  Database,
  Loader2,
  Search,
  RefreshCw,
  Calendar,
  Tag,
  Hash,
  ChevronRight,
  X,
  FileText,
} from "lucide-react";
import { getMemory, getMemoryStats } from "@/lib/api";
import type { MemoryItem, MemoryStatsResponse } from "@/lib/api";
import { Card, CardContent } from "@/components/Card";
import { Button } from "@/components/Button";
import { Alert } from "@/components/Alert";
import { Modal } from "@/components/Modal";

export default function MemoryPage() {
  const [items, setItems] = useState<MemoryItem[]>([]);
  const [stats, setStats] = useState<MemoryStatsResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedSource, setSelectedSource] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedMemory, setSelectedMemory] = useState<MemoryItem | null>(null);

  useEffect(() => {
    loadData();
  }, [selectedSource]);

  const loadData = async () => {
    try {
      setIsLoading(true);
      setError(null);

      const [memoryResponse, statsResponse] = await Promise.all([
        getMemory({ source: selectedSource || undefined, limit: 100 }),
        getMemoryStats(),
      ]);

      setItems(memoryResponse.items);
      setStats(statsResponse);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load memory");
    } finally {
      setIsLoading(false);
    }
  };

  const filteredItems = items.filter((item) =>
    searchQuery
      ? item.content.toLowerCase().includes(searchQuery.toLowerCase()) ||
        item.source.toLowerCase().includes(searchQuery.toLowerCase())
      : true
  );

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const getConfidenceBadge = (confidence: number) => {
    if (confidence >= 0.9) return { color: "bg-green-500/20 text-green-400", label: "High" };
    if (confidence >= 0.7) return { color: "bg-blue-500/20 text-blue-400", label: "Good" };
    if (confidence >= 0.5) return { color: "bg-yellow-500/20 text-yellow-400", label: "Fair" };
    return { color: "bg-red-500/20 text-red-400", label: "Low" };
  };

  return (
    <div className="min-h-screen bg-gray-950 py-8">
      <div className="max-w-6xl mx-auto px-4">
        {/* Page Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
          <div>
            <h1 className="text-3xl font-bold text-white mb-2">Memory</h1>
            <p className="text-gray-400">Browse all your stored knowledge</p>
          </div>
          <Button
            variant="secondary"
            onClick={loadData}
            icon={<RefreshCw className="w-4 h-4" />}
          >
            Refresh
          </Button>
        </div>

        {/* Error Alert */}
        {error && (
          <div className="mb-6">
            <Alert type="error" message={error} onClose={() => setError(null)} />
          </div>
        )}

        {/* Stats Cards */}
        {stats && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
            <Card>
              <CardContent className="py-4">
                <p className="text-sm text-gray-400 mb-1">Total Entries</p>
                <p className="text-2xl font-bold text-white">{stats.total_memories}</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="py-4">
                <p className="text-sm text-gray-400 mb-1">Sources</p>
                <p className="text-2xl font-bold text-white">{stats.sources.length}</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="py-4">
                <p className="text-sm text-gray-400 mb-1">Filtered</p>
                <p className="text-2xl font-bold text-white">{filteredItems.length}</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="py-4">
                <p className="text-sm text-gray-400 mb-1">Active Filter</p>
                <p className="text-2xl font-bold text-white truncate">
                  {selectedSource || "All"}
                </p>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Filters */}
        <Card className="mb-6">
          <CardContent className="py-4">
            <div className="flex flex-col md:flex-row gap-4">
              {/* Search */}
              <div className="flex-1 relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search memories..."
                  className="
                    w-full pl-10 pr-4 py-2 bg-gray-800 border border-gray-700 rounded-lg
                    text-white placeholder-gray-500
                    focus:outline-none focus:border-green-500
                  "
                />
              </div>

              {/* Source Filter */}
              {stats && stats.sources.length > 0 && (
                <div className="flex flex-wrap gap-2">
                  <button
                    onClick={() => setSelectedSource(null)}
                    className={`
                      px-3 py-2 rounded-lg text-sm font-medium transition-colors
                      ${selectedSource === null
                        ? "bg-green-600 text-white"
                        : "bg-gray-800 text-gray-300 hover:bg-gray-700"
                      }
                    `}
                  >
                    All
                  </button>
                  {stats.sources.map((source) => (
                    <button
                      key={source}
                      onClick={() => setSelectedSource(source)}
                      className={`
                        px-3 py-2 rounded-lg text-sm font-medium transition-colors
                        ${selectedSource === source
                          ? "bg-green-600 text-white"
                          : "bg-gray-800 text-gray-300 hover:bg-gray-700"
                        }
                      `}
                    >
                      {source}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Loading State */}
        {isLoading && (
          <div className="flex items-center justify-center py-20">
            <Loader2 className="w-8 h-8 animate-spin text-green-500" />
          </div>
        )}

        {/* Empty State */}
        {!isLoading && filteredItems.length === 0 && (
          <div className="text-center py-20">
            <div className="inline-flex p-4 rounded-full bg-gray-800 mb-4">
              <Database className="w-8 h-8 text-gray-500" />
            </div>
            <h2 className="text-xl font-semibold text-white mb-2">
              {searchQuery || selectedSource ? "No matches found" : "No memories yet"}
            </h2>
            <p className="text-gray-400">
              {searchQuery || selectedSource
                ? "Try adjusting your search or filters"
                : "Start by ingesting some content"}
            </p>
          </div>
        )}

        {/* Memory List */}
        {!isLoading && filteredItems.length > 0 && (
          <div className="space-y-3">
            {filteredItems.map((item) => {
              const confidence = getConfidenceBadge(item.confidence);
              return (
                <Card
                  key={item.id}
                  hoverable
                  onClick={() => setSelectedMemory(item)}
                >
                  <CardContent className="py-4">
                    <div className="flex items-start gap-4">
                      <div className="flex-shrink-0 w-10 h-10 bg-gray-800 rounded-lg flex items-center justify-center">
                        <FileText className="w-5 h-5 text-gray-400" />
                      </div>
                      
                      <div className="flex-1 min-w-0">
                        <div className="flex flex-wrap items-center gap-2 mb-2">
                          <span className="text-xs px-2 py-1 bg-blue-500/20 text-blue-400 rounded">
                            {item.source}
                          </span>
                          <span className={`text-xs px-2 py-1 rounded ${confidence.color}`}>
                            {confidence.label}
                          </span>
                          <span className="text-xs text-gray-500">
                            #{item.id}
                          </span>
                        </div>
                        
                        <p className="text-gray-300 line-clamp-2 mb-2">
                          {item.content}
                        </p>
                        
                        <p className="text-xs text-gray-500 flex items-center gap-1">
                          <Calendar className="w-3 h-3" />
                          {formatDate(item.created_at)}
                        </p>
                      </div>

                      <ChevronRight className="w-5 h-5 text-gray-600 flex-shrink-0" />
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        )}

        {/* Memory Detail Modal */}
        <Modal
          isOpen={selectedMemory !== null}
          onClose={() => setSelectedMemory(null)}
          title="Memory Details"
        >
          {selectedMemory && (
            <div className="space-y-6">
              {/* Meta Info */}
              <div className="flex flex-wrap gap-3">
                <div className="flex items-center gap-2 px-3 py-2 bg-gray-800 rounded-lg">
                  <Hash className="w-4 h-4 text-gray-400" />
                  <span className="text-sm text-gray-300">ID: {selectedMemory.id}</span>
                </div>
                <div className="flex items-center gap-2 px-3 py-2 bg-gray-800 rounded-lg">
                  <Tag className="w-4 h-4 text-gray-400" />
                  <span className="text-sm text-gray-300">{selectedMemory.source}</span>
                </div>
                <div className="flex items-center gap-2 px-3 py-2 bg-gray-800 rounded-lg">
                  <span className="text-sm text-gray-300">
                    v{selectedMemory.version}
                  </span>
                </div>
                <div className={`flex items-center gap-2 px-3 py-2 rounded-lg ${getConfidenceBadge(selectedMemory.confidence).color}`}>
                  <span className="text-sm">
                    {(selectedMemory.confidence * 100).toFixed(0)}% confidence
                  </span>
                </div>
              </div>

              {/* Timestamp */}
              <div>
                <h4 className="text-sm font-medium text-gray-400 mb-2">Created</h4>
                <p className="text-white">{formatDate(selectedMemory.created_at)}</p>
              </div>

              {/* Content */}
              <div>
                <h4 className="text-sm font-medium text-gray-400 mb-2">Content</h4>
                <div className="p-4 bg-gray-800 rounded-lg max-h-80 overflow-y-auto">
                  <p className="text-gray-200 whitespace-pre-wrap leading-relaxed">
                    {selectedMemory.content}
                  </p>
                </div>
              </div>

              {/* Character Count */}
              <div className="text-xs text-gray-500 text-right">
                {selectedMemory.content.length.toLocaleString()} characters
              </div>
            </div>
          )}
        </Modal>
      </div>
    </div>
  );
}
