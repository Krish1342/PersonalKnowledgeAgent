'use client';

import React, { useState, useEffect } from 'react';
import { 
  Settings as SettingsIcon, 
  Download, 
  Upload, 
  Trash2, 
  Database, 
  HardDrive,
  Shield,
  Moon,
  Sun,
  Bell,
  Key
} from 'lucide-react';
import { useUser } from '@clerk/nextjs';
import { Card, CardHeader, CardContent } from '@/components/Card';
import { Button } from '@/components/Button';
import { Alert } from '@/components/Alert';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface StorageStats {
  total_memories: number;
  bookmarked_count: number;
  total_original_bytes: number;
  total_compressed_bytes: number;
  storage_saved_bytes: number;
  storage_saved_percent: number;
  average_compression_ratio: number;
  sources: Record<string, number>;
}

export default function SettingsPage() {
  const { user, isLoaded } = useUser();
  const [stats, setStats] = useState<StorageStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState(false);
  const [importing, setImporting] = useState(false);
  const [alert, setAlert] = useState<{ type: 'success' | 'error'; message: string } | null>(null);
  const [theme, setTheme] = useState<'dark' | 'light'>('dark');

  useEffect(() => {
    fetchStats();
  }, []);

  const fetchStats = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/v2/memory/stats`);
      if (response.ok) {
        const data = await response.json();
        setStats(data);
      }
    } catch (error) {
      console.error('Failed to fetch stats:', error);
    } finally {
      setLoading(false);
    }
  };

  const formatBytes = (bytes: number): string => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const handleExport = async () => {
    setExporting(true);
    try {
      const response = await fetch(`${API_BASE_URL}/api/v2/memory/export`);
      if (!response.ok) throw new Error('Export failed');
      
      const data = await response.json();
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `second-brain-backup-${new Date().toISOString().split('T')[0]}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      
      setAlert({ type: 'success', message: 'Data exported successfully!' });
    } catch (error) {
      setAlert({ type: 'error', message: 'Failed to export data' });
    } finally {
      setExporting(false);
    }
  };

  const handleImport = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setImporting(true);
    try {
      const text = await file.text();
      const data = JSON.parse(text);
      
      const response = await fetch(`${API_BASE_URL}/api/v2/memory/import`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ data }),
      });
      
      if (!response.ok) throw new Error('Import failed');
      
      const result = await response.json();
      setAlert({ 
        type: 'success', 
        message: `Imported ${result.imported} memories (${result.skipped_duplicates} duplicates skipped)` 
      });
      fetchStats();
    } catch (error) {
      setAlert({ type: 'error', message: 'Failed to import data. Make sure the file is valid.' });
    } finally {
      setImporting(false);
      e.target.value = '';
    }
  };

  return (
    <div className="min-h-[calc(100vh-4rem)] p-4 md:p-6">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <SettingsIcon className="w-7 h-7 text-indigo-500" />
            Settings
          </h1>
          <p className="text-gray-400 mt-1">
            Manage your Second Brain preferences and data
          </p>
        </div>

        {alert && (
          <Alert type={alert.type} onClose={() => setAlert(null)} className="mb-6">
            {alert.message}
          </Alert>
        )}

        <div className="space-y-6">
          {/* Account Section */}
          <Card>
            <CardHeader>
              <h2 className="text-lg font-semibold text-white flex items-center gap-2">
                <Shield className="w-5 h-5 text-indigo-500" />
                Account
              </h2>
            </CardHeader>
            <CardContent>
              {isLoaded && user ? (
                <div className="flex items-center gap-4">
                  <img 
                    src={user.imageUrl} 
                    alt="Profile" 
                    className="w-16 h-16 rounded-full"
                  />
                  <div>
                    <p className="text-white font-medium">
                      {user.fullName || user.username || 'User'}
                    </p>
                    <p className="text-gray-400 text-sm">
                      {user.primaryEmailAddress?.emailAddress}
                    </p>
                    <p className="text-gray-500 text-xs mt-1">
                      Member since {new Date(user.createdAt || Date.now()).toLocaleDateString()}
                    </p>
                  </div>
                </div>
              ) : (
                <div className="text-gray-400">
                  <p>Sign in to sync your data across devices</p>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Storage Stats */}
          <Card>
            <CardHeader>
              <h2 className="text-lg font-semibold text-white flex items-center gap-2">
                <HardDrive className="w-5 h-5 text-indigo-500" />
                Storage
              </h2>
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="animate-pulse space-y-3">
                  <div className="h-4 bg-gray-800 rounded w-1/2"></div>
                  <div className="h-4 bg-gray-800 rounded w-3/4"></div>
                  <div className="h-4 bg-gray-800 rounded w-2/3"></div>
                </div>
              ) : stats ? (
                <div className="space-y-4">
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div className="bg-gray-800/50 rounded-lg p-3">
                      <p className="text-xs text-gray-400">Total Memories</p>
                      <p className="text-xl font-bold text-white">{stats.total_memories}</p>
                    </div>
                    <div className="bg-gray-800/50 rounded-lg p-3">
                      <p className="text-xs text-gray-400">Bookmarked</p>
                      <p className="text-xl font-bold text-yellow-500">{stats.bookmarked_count}</p>
                    </div>
                    <div className="bg-gray-800/50 rounded-lg p-3">
                      <p className="text-xs text-gray-400">Original Size</p>
                      <p className="text-xl font-bold text-white">{formatBytes(stats.total_original_bytes)}</p>
                    </div>
                    <div className="bg-gray-800/50 rounded-lg p-3">
                      <p className="text-xs text-gray-400">Compressed</p>
                      <p className="text-xl font-bold text-green-500">{formatBytes(stats.total_compressed_bytes)}</p>
                    </div>
                  </div>
                  
                  {/* Compression savings bar */}
                  <div className="bg-gray-800/50 rounded-lg p-4">
                    <div className="flex justify-between text-sm mb-2">
                      <span className="text-gray-400">Storage Efficiency</span>
                      <span className="text-green-500 font-medium">
                        {stats.storage_saved_percent}% saved
                      </span>
                    </div>
                    <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
                      <div 
                        className="h-full bg-gradient-to-r from-indigo-500 to-green-500 rounded-full transition-all"
                        style={{ width: `${100 - (stats.total_compressed_bytes / stats.total_original_bytes * 100)}%` }}
                      />
                    </div>
                    <p className="text-xs text-gray-500 mt-2">
                      Compression ratio: {stats.average_compression_ratio}x
                    </p>
                  </div>

                  {/* Sources breakdown */}
                  {Object.keys(stats.sources).length > 0 && (
                    <div>
                      <p className="text-sm text-gray-400 mb-2">By Source</p>
                      <div className="flex flex-wrap gap-2">
                        {Object.entries(stats.sources).map(([source, count]) => (
                          <span 
                            key={source}
                            className="px-3 py-1 bg-gray-800 rounded-full text-sm text-gray-300"
                          >
                            {source}: {count}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <p className="text-gray-400">No storage data available</p>
              )}
            </CardContent>
          </Card>

          {/* Data Management */}
          <Card>
            <CardHeader>
              <h2 className="text-lg font-semibold text-white flex items-center gap-2">
                <Database className="w-5 h-5 text-indigo-500" />
                Data Management
              </h2>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="flex flex-col sm:flex-row gap-3">
                  <Button
                    onClick={handleExport}
                    loading={exporting}
                    variant="secondary"
                    className="flex-1"
                  >
                    <Download className="w-4 h-4 mr-2" />
                    Export All Data
                  </Button>
                  
                  <label className="flex-1">
                    <input
                      type="file"
                      accept=".json"
                      onChange={handleImport}
                      className="hidden"
                      disabled={importing}
                    />
                    <Button
                      as="span"
                      loading={importing}
                      variant="secondary"
                      className="w-full cursor-pointer"
                    >
                      <Upload className="w-4 h-4 mr-2" />
                      Import Data
                    </Button>
                  </label>
                </div>
                
                <p className="text-xs text-gray-500">
                  Export your data as JSON for backup. Import restores your memories while skipping duplicates.
                </p>
              </div>
            </CardContent>
          </Card>

          {/* Preferences */}
          <Card>
            <CardHeader>
              <h2 className="text-lg font-semibold text-white flex items-center gap-2">
                <Moon className="w-5 h-5 text-indigo-500" />
                Preferences
              </h2>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-white font-medium">Theme</p>
                    <p className="text-sm text-gray-400">Choose your preferred color scheme</p>
                  </div>
                  <div className="flex items-center gap-2 bg-gray-800 rounded-lg p-1">
                    <button
                      onClick={() => setTheme('dark')}
                      className={`p-2 rounded-lg transition-colors ${
                        theme === 'dark' ? 'bg-indigo-600 text-white' : 'text-gray-400 hover:text-white'
                      }`}
                    >
                      <Moon className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => setTheme('light')}
                      className={`p-2 rounded-lg transition-colors ${
                        theme === 'light' ? 'bg-indigo-600 text-white' : 'text-gray-400 hover:text-white'
                      }`}
                    >
                      <Sun className="w-4 h-4" />
                    </button>
                  </div>
                </div>
                
                <div className="border-t border-gray-800 pt-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-white font-medium">Auto-tagging</p>
                      <p className="text-sm text-gray-400">Automatically tag ingested content</p>
                    </div>
                    <label className="relative inline-flex items-center cursor-pointer">
                      <input type="checkbox" defaultChecked className="sr-only peer" />
                      <div className="w-11 h-6 bg-gray-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-indigo-600"></div>
                    </label>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* API Keys (for future integration) */}
          <Card>
            <CardHeader>
              <h2 className="text-lg font-semibold text-white flex items-center gap-2">
                <Key className="w-5 h-5 text-indigo-500" />
                API Configuration
              </h2>
            </CardHeader>
            <CardContent>
              <p className="text-gray-400 text-sm mb-4">
                Configure API keys for enhanced features. These are stored securely in your environment.
              </p>
              <div className="space-y-3">
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Groq API Key</label>
                  <input
                    type="password"
                    placeholder="gsk_..."
                    className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                  />
                </div>
                <p className="text-xs text-gray-500">
                  Get your API key from{' '}
                  <a href="https://console.groq.com" target="_blank" rel="noopener noreferrer" className="text-indigo-400 hover:underline">
                    console.groq.com
                  </a>
                </p>
              </div>
            </CardContent>
          </Card>

          {/* Danger Zone */}
          <Card className="border-red-900/50">
            <CardHeader>
              <h2 className="text-lg font-semibold text-red-400 flex items-center gap-2">
                <Trash2 className="w-5 h-5" />
                Danger Zone
              </h2>
            </CardHeader>
            <CardContent>
              <p className="text-gray-400 text-sm mb-4">
                These actions are irreversible. Please be certain.
              </p>
              <Button
                variant="secondary"
                className="border-red-900 text-red-400 hover:bg-red-900/20"
                onClick={() => {
                  if (confirm('Are you sure you want to delete all your data? This cannot be undone.')) {
                    // Implement delete all
                    setAlert({ type: 'error', message: 'Delete functionality not implemented yet' });
                  }
                }}
              >
                <Trash2 className="w-4 h-4 mr-2" />
                Delete All Data
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
