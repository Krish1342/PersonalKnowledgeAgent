"use client";

import React, { useState, useRef, useEffect } from "react";
import {
  Send,
  Loader2,
  User,
  Bot,
  ChevronDown,
  ChevronUp,
  FileText,
  Shield,
  Sparkles,
  MessageSquare,
} from "lucide-react";
import { queryKnowledgeBase, deriveAgentSteps } from "@/lib/api";
import type { QueryResponse, ContextItem, AgentStep } from "@/lib/api";
import { Card, CardContent } from "@/components/Card";
import { Alert } from "@/components/Alert";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  metadata?: {
    score: number | null;
    critique: string | null;
    context: ContextItem[];
    steps: AgentStep[];
  };
}

export default function QueryPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [expandedMessage, setExpandedMessage] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSubmit = async (e?: React.FormEvent) => {
    e?.preventDefault();

    const question = input.trim();
    if (!question || isLoading) return;

    const userMessage: Message = {
      id: `user-${Date.now()}`,
      role: "user",
      content: question,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsLoading(true);

    try {
      const response: QueryResponse = await queryKnowledgeBase({ question });
      const steps = deriveAgentSteps(response);

      const assistantMessage: Message = {
        id: `assistant-${Date.now()}`,
        role: "assistant",
        content: response.answer,
        timestamp: new Date(),
        metadata: {
          score: response.score,
          critique: response.critique,
          context: response.context,
          steps: steps,
        },
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err) {
      const errorMessage: Message = {
        id: `error-${Date.now()}`,
        role: "assistant",
        content: `Sorry, I encountered an error: ${err instanceof Error ? err.message : "Failed to process your question"}`,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
      inputRef.current?.focus();
    }
  };

  const getScoreInfo = (score: number | null) => {
    if (score === null) return { label: "Unknown", color: "text-gray-400", bg: "bg-gray-800" };
    if (score >= 0.8) return { label: "High Confidence", color: "text-green-400", bg: "bg-green-900/30" };
    if (score >= 0.6) return { label: "Medium Confidence", color: "text-yellow-400", bg: "bg-yellow-900/30" };
    return { label: "Low Confidence", color: "text-red-400", bg: "bg-red-900/30" };
  };

  const toggleExpanded = (id: string) => {
    setExpandedMessage(expandedMessage === id ? null : id);
  };

  return (
    <div className="min-h-screen bg-gray-950 flex flex-col">
      {/* Page Header */}
      <div className="border-b border-gray-800 bg-gray-900/50">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 py-3 sm:py-4">
          <h1 className="text-lg sm:text-xl font-bold text-white">Ask Your Knowledge Base</h1>
          <p className="text-xs sm:text-sm text-gray-400">Get answers grounded in your stored knowledge</p>
        </div>
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 py-4 sm:py-6">
          {messages.length === 0 ? (
            <div className="text-center py-12 sm:py-20 px-4">
              <div className="inline-flex p-4 rounded-full bg-gray-800 mb-4">
                <MessageSquare className="w-8 h-8 text-gray-500" />
              </div>
              <h2 className="text-lg sm:text-xl font-semibold text-white mb-2">
                Start a conversation
              </h2>
              <p className="text-sm sm:text-base text-gray-400 max-w-md mx-auto">
                Ask a question about your ingested knowledge. Your answers will be grounded in your actual data.
              </p>
              <div className="mt-6 flex flex-wrap justify-center gap-2">
                {["What do I know about...", "Summarize my notes on...", "Find information about..."].map((suggestion) => (
                  <button
                    key={suggestion}
                    onClick={() => setInput(suggestion)}
                    className="px-3 sm:px-4 py-2 bg-gray-800 hover:bg-gray-700 active:bg-gray-900 text-gray-300 text-xs sm:text-sm rounded-lg transition-colors touch-manipulation"
                  >
                    {suggestion}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="space-y-4 sm:space-y-6">
              {messages.map((message) => (
                <div key={message.id}>
                  {message.role === "user" ? (
                    // User Message
                    <div className="flex gap-3 sm:gap-4">
                      <div className="flex-shrink-0 w-7 h-7 sm:w-8 sm:h-8 bg-blue-600 rounded-full flex items-center justify-center">
                        <User className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-white" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-xs sm:text-sm text-gray-400 mb-1">You</p>
                        <p className="text-sm sm:text-base text-white break-words">{message.content}</p>
                      </div>
                    </div>
                  ) : (
                    // Assistant Message
                    <div className="flex gap-3 sm:gap-4">
                      <div className="flex-shrink-0 w-7 h-7 sm:w-8 sm:h-8 bg-green-600 rounded-full flex items-center justify-center">
                        <Bot className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-white" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 sm:gap-3 mb-1 flex-wrap">
                          <p className="text-xs sm:text-sm text-gray-400">Assistant</p>
                          {message.metadata?.score !== undefined && (
                            <span className={`text-xs px-2 py-0.5 rounded-full ${getScoreInfo(message.metadata.score).bg} ${getScoreInfo(message.metadata.score).color}`}>
                              <Shield className="w-3 h-3 inline mr-1" />
                              {message.metadata.score !== null ? `${(message.metadata.score * 100).toFixed(0)}%` : "N/A"}
                            </span>
                          )}
                        </div>
                        
                        <Card className="mb-3">
                          <CardContent>
                            <p className="text-sm sm:text-base text-gray-100 whitespace-pre-wrap leading-relaxed break-words">
                              {message.content}
                            </p>
                          </CardContent>
                        </Card>

                        {/* Expandable Details */}
                        {message.metadata && (message.metadata.context.length > 0 || message.metadata.critique) && (
                          <button
                            onClick={() => toggleExpanded(message.id)}
                            className="flex items-center gap-2 text-xs sm:text-sm text-gray-400 hover:text-white transition-colors touch-manipulation py-2"
                          >
                            {expandedMessage === message.id ? (
                              <ChevronUp className="w-4 h-4" />
                            ) : (
                              <ChevronDown className="w-4 h-4" />
                            )}
                            <span>
                              {expandedMessage === message.id ? "Hide" : "Show"} details
                              {message.metadata.context.length > 0 && ` (${message.metadata.context.length} sources)`}
                            </span>
                          </button>
                        )}

                        {/* Expanded Details */}
                        {expandedMessage === message.id && message.metadata && (
                          <div className="mt-4 space-y-4">
                            {/* Critique */}
                            {message.metadata.critique && (
                              <div className="p-3 bg-gray-800/50 rounded-lg">
                                <p className="text-xs text-gray-400 mb-1 flex items-center gap-1">
                                  <Sparkles className="w-3 h-3" />
                                  Quality Assessment
                                </p>
                                <p className="text-sm text-gray-300">{message.metadata.critique}</p>
                              </div>
                            )}

                            {/* Sources */}
                            {message.metadata.context.length > 0 && (
                              <div>
                                <p className="text-xs text-gray-400 mb-2 flex items-center gap-1">
                                  <FileText className="w-3 h-3" />
                                  Sources Used
                                </p>
                                <div className="space-y-2">
                                  {message.metadata.context.map((ctx, idx) => (
                                    <div key={idx} className="p-3 bg-gray-800/50 rounded-lg">
                                      <div className="flex items-center justify-between mb-2">
                                        <span className="text-xs text-blue-400 font-medium">
                                          {ctx.source}
                                        </span>
                                        {ctx.relevance_score !== null && (
                                          <span className="text-xs text-gray-500">
                                            {(ctx.relevance_score * 100).toFixed(0)}% match
                                          </span>
                                        )}
                                      </div>
                                      <p className="text-sm text-gray-400 line-clamp-3">
                                        {ctx.content}
                                      </p>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              ))}

              {/* Loading Indicator */}
              {isLoading && (
                <div className="flex gap-4">
                  <div className="flex-shrink-0 w-8 h-8 bg-green-600 rounded-full flex items-center justify-center">
                    <Bot className="w-4 h-4 text-white" />
                  </div>
                  <div className="flex items-center gap-2 text-gray-400">
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Searching knowledge base...</span>
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>
          )}
        </div>
      </div>

      {/* Input Area */}
      <div className="border-t border-gray-800 bg-gray-900/80 backdrop-blur-sm">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 py-3 sm:py-4">
          <form onSubmit={handleSubmit} className="flex gap-2 sm:gap-3">
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask a question..."
              className="
                flex-1 px-3 sm:px-4 py-2.5 sm:py-3 bg-gray-800 border border-gray-700 rounded-xl text-sm sm:text-base
                text-white placeholder-gray-500
                focus:outline-none focus:border-green-500 focus:ring-1 focus:ring-green-500
                touch-manipulation
              "
            />
            <button
              type="submit"
              disabled={isLoading || !input.trim()}
              className="
                px-4 sm:px-6 py-2.5 sm:py-3 bg-green-600 hover:bg-green-500 active:bg-green-700 disabled:bg-gray-700
                disabled:cursor-not-allowed text-white rounded-xl transition-colors
                flex items-center gap-2 touch-manipulation flex-shrink-0
              "
            >
              {isLoading ? (
                <Loader2 className="w-4 h-4 sm:w-5 sm:h-5 animate-spin" />
              ) : (
                <Send className="w-4 h-4 sm:w-5 sm:h-5" />
              )}
              <span className="hidden sm:inline">Send</span>
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
