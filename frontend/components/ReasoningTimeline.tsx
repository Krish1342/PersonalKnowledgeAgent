"use client";

import React from "react";
import {
  Lightbulb,
  Search,
  Brain,
  ShieldCheck,
  CheckCircle2,
  Loader2,
  AlertCircle,
  Clock,
} from "lucide-react";
import type { AgentStep } from "@/lib/api";

// ============================================================================
// Types
// ============================================================================

interface ReasoningTimelineProps {
  steps: AgentStep[];
  className?: string;
}

interface StepIconProps {
  name: string;
  status: AgentStep["status"];
}

interface StepCardProps {
  step: AgentStep;
  isLast: boolean;
}

// ============================================================================
// Icon Mapping
// ============================================================================

const STEP_ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  Plan: Lightbulb,
  Retrieve: Search,
  Reason: Brain,
  Critique: ShieldCheck,
};

const STATUS_COLORS: Record<AgentStep["status"], string> = {
  pending: "text-gray-400 bg-gray-100 dark:bg-gray-800",
  running: "text-blue-600 bg-blue-100 dark:bg-blue-900",
  completed: "text-green-600 bg-green-100 dark:bg-green-900",
  error: "text-red-600 bg-red-100 dark:bg-red-900",
};

const STATUS_BORDER_COLORS: Record<AgentStep["status"], string> = {
  pending: "border-gray-300 dark:border-gray-700",
  running: "border-blue-500",
  completed: "border-green-500",
  error: "border-red-500",
};

// ============================================================================
// Sub-components
// ============================================================================

function StepIcon({ name, status }: StepIconProps) {
  const IconComponent = STEP_ICONS[name] || Brain;

  if (status === "running") {
    return <Loader2 className="w-5 h-5 animate-spin" />;
  }

  if (status === "completed") {
    return <CheckCircle2 className="w-5 h-5" />;
  }

  if (status === "error") {
    return <AlertCircle className="w-5 h-5" />;
  }

  return <IconComponent className="w-5 h-5" />;
}

function StepMetadata({ metadata }: { metadata?: Record<string, unknown> }) {
  if (!metadata || Object.keys(metadata).length === 0) {
    return null;
  }

  return (
    <div className="mt-2 space-y-1">
      {Object.entries(metadata).map(([key, value]) => {
        if (value === null || value === undefined) return null;

        // Format key from camelCase to readable
        const label = key
          .replace(/([A-Z])/g, " $1")
          .replace(/^./, (str) => str.toUpperCase());

        // Format value
        let displayValue: string;
        if (typeof value === "number") {
          displayValue =
            key.toLowerCase().includes("score")
              ? `${(value * 100).toFixed(0)}%`
              : value.toString();
        } else if (typeof value === "string") {
          displayValue = value.length > 100 ? `${value.slice(0, 100)}...` : value;
        } else {
          displayValue = JSON.stringify(value);
        }

        return (
          <div key={key} className="flex items-center text-xs">
            <span className="text-gray-500 dark:text-gray-400 mr-2">
              {label}:
            </span>
            <span className="text-gray-700 dark:text-gray-300 font-medium">
              {displayValue}
            </span>
          </div>
        );
      })}
    </div>
  );
}

function StepCard({ step, isLast }: StepCardProps) {
  const statusColor = STATUS_COLORS[step.status];
  const borderColor = STATUS_BORDER_COLORS[step.status];

  return (
    <div className="flex items-start">
      {/* Icon and connector line */}
      <div className="flex flex-col items-center mr-4">
        <div
          className={`
            flex items-center justify-center w-10 h-10 rounded-full border-2
            ${statusColor} ${borderColor}
          `}
        >
          <StepIcon name={step.name} status={step.status} />
        </div>
        {!isLast && (
          <div
            className={`
              w-0.5 h-16 mt-2
              ${step.status === "completed" ? "bg-green-300 dark:bg-green-700" : "bg-gray-200 dark:bg-gray-700"}
            `}
          />
        )}
      </div>

      {/* Content */}
      <div className="flex-1 pb-8">
        <div className="flex items-center justify-between">
          <h3 className="font-semibold text-gray-900 dark:text-white">
            {step.name}
          </h3>
          {step.duration !== undefined && (
            <span className="flex items-center text-xs text-gray-500 dark:text-gray-400">
              <Clock className="w-3 h-3 mr-1" />
              {step.duration}ms
            </span>
          )}
        </div>

        <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
          {getStepDescription(step)}
        </p>

        <StepMetadata metadata={step.metadata} />
      </div>
    </div>
  );
}

// ============================================================================
// Helpers
// ============================================================================

function getStepDescription(step: AgentStep): string {
  const descriptions: Record<string, Record<AgentStep["status"], string>> = {
    Plan: {
      pending: "Waiting to optimize query...",
      running: "Optimizing query for retrieval...",
      completed: "Query optimized successfully",
      error: "Failed to optimize query",
    },
    Retrieve: {
      pending: "Waiting to search knowledge base...",
      running: "Searching knowledge base...",
      completed: `Retrieved ${step.metadata?.documentsRetrieved ?? 0} relevant documents`,
      error: "Failed to retrieve documents",
    },
    Reason: {
      pending: "Waiting to generate answer...",
      running: "Synthesizing answer from context...",
      completed: "Answer generated from knowledge base",
      error: "Failed to generate answer",
    },
    Critique: {
      pending: "Waiting to verify groundedness...",
      running: "Checking answer groundedness...",
      completed: `Verified with ${((step.metadata?.groundednessScore as number) * 100 || 0).toFixed(0)}% confidence`,
      error: "Failed to verify answer",
    },
  };

  return descriptions[step.name]?.[step.status] || "Processing...";
}

// ============================================================================
// Main Component
// ============================================================================

export function ReasoningTimeline({
  steps,
  className = "",
}: ReasoningTimelineProps) {
  if (!steps || steps.length === 0) {
    return (
      <div className={`text-gray-500 dark:text-gray-400 text-sm ${className}`}>
        No reasoning steps to display
      </div>
    );
  }

  return (
    <div className={`${className}`}>
      <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center">
        <Brain className="w-5 h-5 mr-2 text-blue-600" />
        Agent Reasoning
      </h2>

      <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-4">
        {steps.map((step, index) => (
          <StepCard
            key={`${step.name}-${index}`}
            step={step}
            isLast={index === steps.length - 1}
          />
        ))}
      </div>
    </div>
  );
}

export default ReasoningTimeline;
