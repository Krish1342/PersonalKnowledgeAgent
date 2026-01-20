"use client";

import Link from "next/link";
import { Upload, Search, Database, ArrowRight, Zap, Shield, Brain } from "lucide-react";
import { Card, CardContent } from "@/components/Card";

const features = [
  {
    icon: Upload,
    title: "Ingest Knowledge",
    description: "Add documents, notes, or any text to your personal knowledge base",
    href: "/ingest",
    color: "text-blue-400",
    bgColor: "bg-blue-500/10",
  },
  {
    icon: Search,
    title: "Ask Questions",
    description: "Query your knowledge with AI-powered semantic search",
    href: "/query",
    color: "text-green-400",
    bgColor: "bg-green-500/10",
  },
  {
    icon: Database,
    title: "Browse Memory",
    description: "View and manage all your stored knowledge entries",
    href: "/memory",
    color: "text-purple-400",
    bgColor: "bg-purple-500/10",
  },
];

const highlights = [
  {
    icon: Zap,
    title: "RAG-Powered",
    description: "Answers grounded in your actual data, not hallucinations",
  },
  {
    icon: Shield,
    title: "Local & Private",
    description: "Your data stays on your machine, fully under your control",
  },
  {
    icon: Brain,
    title: "Agent Workflow",
    description: "Multi-step reasoning with planning, retrieval, and verification",
  },
];

export default function Home() {
  return (
    <div className="min-h-screen bg-gray-950">
      {/* Hero Section */}
      <section className="relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-b from-green-500/5 to-transparent" />
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-12 sm:py-20 relative">
          <div className="text-center max-w-3xl mx-auto">
            <div className="inline-flex items-center gap-2 px-4 py-2 bg-green-500/10 rounded-full text-green-400 text-sm mb-6">
              <Brain className="w-4 h-4" />
              Your Second Brain
            </div>
            <h1 className="text-3xl sm:text-4xl md:text-5xl font-bold text-white mb-4 sm:mb-6 leading-tight px-2">
              Personal Knowledge Base
              <span className="text-green-400"> Agent</span>
            </h1>
            <p className="text-base sm:text-lg md:text-xl text-gray-400 mb-6 sm:mb-8 leading-relaxed px-2">
              Store your knowledge, ask questions, and get answers grounded in your own data. 
              Powered by AI agents that never hallucinate.
            </p>
            <div className="flex flex-col sm:flex-row gap-3 sm:gap-4 justify-center px-4">
              <Link
                href="/ingest"
                className="inline-flex items-center justify-center gap-2 px-6 py-3 sm:py-3.5 bg-green-600 hover:bg-green-500 active:bg-green-700 text-white font-medium rounded-lg transition-colors touch-manipulation"
              >
                Get Started
                <ArrowRight className="w-4 h-4" />
              </Link>
              <Link
                href="/query"
                className="inline-flex items-center justify-center gap-2 px-6 py-3 sm:py-3.5 bg-gray-800 hover:bg-gray-700 active:bg-gray-900 text-white font-medium rounded-lg border border-gray-700 transition-colors touch-manipulation"
              >
                Ask a Question
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Main Actions */}
      <section className="max-w-6xl mx-auto px-4 sm:px-6 py-8 sm:py-12">
        <h2 className="text-xl sm:text-2xl font-bold text-white mb-6 sm:mb-8 text-center px-2">
          What would you like to do?
        </h2>
        <div className="grid sm:grid-cols-2 md:grid-cols-3 gap-4 sm:gap-6">
          {features.map((feature) => {
            const Icon = feature.icon;
            return (
              <Link key={feature.href} href={feature.href}>
                <Card hoverable className="h-full">
                  <CardContent className="py-8">
                    <div
                      className={`inline-flex p-3 rounded-xl ${feature.bgColor} mb-4`}
                    >
                      <Icon className={`w-6 h-6 ${feature.color}`} />
                    </div>
                    <h3 className="text-lg font-semibold text-white mb-2">
                      {feature.title}
                    </h3>
                    <p className="text-gray-400 text-sm leading-relaxed">
                      {feature.description}
                    </p>
                    <div className="mt-4 flex items-center gap-2 text-green-400 text-sm font-medium">
                      Open
                      <ArrowRight className="w-4 h-4" />
                    </div>
                  </CardContent>
                </Card>
              </Link>
            );
          })}
        </div>
      </section>

      {/* Highlights */}
      <section className="max-w-6xl mx-auto px-4 sm:px-6 py-8 sm:py-12 border-t border-gray-800">
        <div className="grid sm:grid-cols-2 md:grid-cols-3 gap-6 sm:gap-8">
          {highlights.map((highlight, index) => {
            const Icon = highlight.icon;
            return (
              <div key={index} className="text-center">
                <div className="inline-flex p-3 rounded-full bg-gray-800 mb-4">
                  <Icon className="w-6 h-6 text-green-400" />
                </div>
                <h3 className="text-lg font-semibold text-white mb-2">
                  {highlight.title}
                </h3>
                <p className="text-gray-400 text-sm">{highlight.description}</p>
              </div>
            );
          })}
        </div>
      </section>
    </div>
  );
}
