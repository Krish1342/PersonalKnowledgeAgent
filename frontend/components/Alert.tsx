"use client";

import React from "react";
import { CheckCircle2, AlertCircle, Info, X } from "lucide-react";

type AlertType = "success" | "error" | "info";

interface AlertProps {
  type: AlertType;
  message: string;
  onClose?: () => void;
}

const alertConfig = {
  success: {
    icon: CheckCircle2,
    bg: "bg-green-900/30",
    border: "border-green-700",
    text: "text-green-400",
  },
  error: {
    icon: AlertCircle,
    bg: "bg-red-900/30",
    border: "border-red-700",
    text: "text-red-400",
  },
  info: {
    icon: Info,
    bg: "bg-blue-900/30",
    border: "border-blue-700",
    text: "text-blue-400",
  },
};

export function Alert({ type, message, onClose }: AlertProps) {
  const config = alertConfig[type];
  const Icon = config.icon;

  return (
    <div
      className={`
        flex items-start gap-3 p-4 rounded-lg border
        ${config.bg} ${config.border}
      `}
    >
      <Icon className={`w-5 h-5 mt-0.5 flex-shrink-0 ${config.text}`} />
      <p className={`flex-1 text-sm ${config.text}`}>{message}</p>
      {onClose && (
        <button
          onClick={onClose}
          className="p-1 hover:bg-white/10 rounded transition-colors"
        >
          <X className={`w-4 h-4 ${config.text}`} />
        </button>
      )}
    </div>
  );
}

export default Alert;
