"use client";

import React, { useState, useCallback } from "react";
import {
  Upload,
  FileText,
  Loader2,
  CheckCircle2,
  X,
  HelpCircle,
} from "lucide-react";
import { ingestContent } from "@/lib/api";
import { Card, CardContent, CardHeader } from "@/components/Card";
import { Button } from "@/components/Button";
import { Alert } from "@/components/Alert";

interface UploadResult {
  success: boolean;
  message: string;
  chunks: number;
}

export default function IngestPage() {
  const [textContent, setTextContent] = useState("");
  const [source, setSource] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<UploadResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const [fileName, setFileName] = useState<string | null>(null);

  const handleSubmit = async () => {
    if (!textContent.trim()) {
      setError("Please enter some content to ingest");
      return;
    }

    setIsLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await ingestContent({
        content: textContent,
        source: source || "manual_input",
      });

      setResult({
        success: response.success,
        message: response.message,
        chunks: response.chunks_ingested,
      });

      if (response.success) {
        setTextContent("");
        setFileName(null);
        setSource("");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to ingest content");
    } finally {
      setIsLoading(false);
    }
  };

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    const files = e.dataTransfer.files;
    if (files && files[0]) {
      handleFile(files[0]);
    }
  }, []);

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files[0]) {
      handleFile(files[0]);
    }
  };

  const handleFile = (file: File) => {
    if (!file.type.startsWith("text/") && !file.name.endsWith(".md") && !file.name.endsWith(".txt")) {
      setError("Please upload a text file (.txt, .md)");
      return;
    }

    setFileName(file.name);
    if (!source) {
      setSource(file.name.replace(/\.[^/.]+$/, ""));
    }

    const reader = new FileReader();
    reader.onload = (e) => {
      const content = e.target?.result as string;
      setTextContent(content);
      setError(null);
    };
    reader.onerror = () => {
      setError("Failed to read file");
    };
    reader.readAsText(file);
  };

  const clearFile = () => {
    setFileName(null);
    setTextContent("");
  };

  return (
    <div className="min-h-screen bg-gray-950 py-8">
      <div className="max-w-3xl mx-auto px-4">
        {/* Page Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-white mb-2">
            Add Knowledge
          </h1>
          <p className="text-gray-400">
            Upload documents or paste text to add to your knowledge base
          </p>
        </div>

        {/* Status Messages */}
        {result && (
          <div className="mb-6">
            <Alert
              type="success"
              message={`${result.message} (${result.chunks} chunks created)`}
              onClose={() => setResult(null)}
            />
          </div>
        )}

        {error && (
          <div className="mb-6">
            <Alert
              type="error"
              message={error}
              onClose={() => setError(null)}
            />
          </div>
        )}

        {/* Main Form */}
        <Card>
          <CardHeader>
            <h2 className="text-lg font-semibold text-white">Content Input</h2>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* File Upload */}
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Upload File
              </label>
              <div
                className={`
                  relative border-2 border-dashed rounded-lg p-8 text-center transition-all
                  ${dragActive
                    ? "border-green-500 bg-green-500/10"
                    : "border-gray-700 hover:border-gray-600"
                  }
                `}
                onDragEnter={handleDrag}
                onDragLeave={handleDrag}
                onDragOver={handleDrag}
                onDrop={handleDrop}
              >
                <input
                  type="file"
                  accept=".txt,.md,text/*"
                  onChange={handleFileInput}
                  className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                />

                {fileName ? (
                  <div className="flex items-center justify-center gap-3">
                    <FileText className="w-8 h-8 text-green-500" />
                    <span className="text-green-400 font-medium">{fileName}</span>
                    <button
                      onClick={(e) => {
                        e.preventDefault();
                        clearFile();
                      }}
                      className="p-1 hover:bg-gray-800 rounded"
                    >
                      <X className="w-4 h-4 text-gray-500 hover:text-red-400" />
                    </button>
                  </div>
                ) : (
                  <>
                    <Upload className="w-10 h-10 text-gray-600 mx-auto mb-3" />
                    <p className="text-gray-300 mb-1">
                      Drag and drop a file here, or click to browse
                    </p>
                    <p className="text-gray-500 text-sm">
                      Supports .txt and .md files
                    </p>
                  </>
                )}
              </div>
            </div>

            {/* Divider */}
            <div className="flex items-center gap-4">
              <div className="flex-1 h-px bg-gray-800" />
              <span className="text-gray-500 text-sm">or paste text directly</span>
              <div className="flex-1 h-px bg-gray-800" />
            </div>

            {/* Text Input */}
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Content
              </label>
              <textarea
                value={textContent}
                onChange={(e) => setTextContent(e.target.value)}
                placeholder="Paste or type your knowledge here..."
                className="
                  w-full h-48 px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg
                  text-white placeholder-gray-500 text-sm
                  focus:outline-none focus:border-green-500 focus:ring-1 focus:ring-green-500
                  resize-none
                "
              />
              <div className="flex justify-between mt-2 text-xs text-gray-500">
                <span>{textContent.length.toLocaleString()} characters</span>
                <span>~{Math.ceil(textContent.length / 1000)} chunks will be created</span>
              </div>
            </div>

            {/* Source Tag */}
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                <span>Source Label</span>
                <span className="text-gray-500 font-normal ml-2">(optional)</span>
              </label>
              <input
                type="text"
                value={source}
                onChange={(e) => setSource(e.target.value)}
                placeholder="e.g., research-notes, meeting-2024-01"
                className="
                  w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg
                  text-white placeholder-gray-500 text-sm
                  focus:outline-none focus:border-green-500 focus:ring-1 focus:ring-green-500
                "
              />
              <p className="mt-2 text-xs text-gray-500 flex items-start gap-1">
                <HelpCircle className="w-3 h-3 mt-0.5 flex-shrink-0" />
                A label to help you identify where this knowledge came from
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Submit Button */}
        <div className="mt-6">
          <Button
            onClick={handleSubmit}
            disabled={isLoading || !textContent.trim()}
            isLoading={isLoading}
            size="lg"
            className="w-full"
          >
            {isLoading ? "Processing..." : "Add to Knowledge Base"}
          </Button>
        </div>

        {/* Help Text */}
        <div className="mt-8 p-4 bg-gray-900/50 border border-gray-800 rounded-lg">
          <h3 className="text-sm font-medium text-gray-300 mb-2 flex items-center gap-2">
            <HelpCircle className="w-4 h-4" />
            How it works
          </h3>
          <ul className="text-sm text-gray-500 space-y-1">
            <li>• Your content is split into smaller chunks for better retrieval</li>
            <li>• Each chunk is converted into a searchable embedding</li>
            <li>• When you ask questions, relevant chunks are retrieved automatically</li>
          </ul>
        </div>
      </div>
    </div>
  );
}
