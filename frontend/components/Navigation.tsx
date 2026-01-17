"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Brain, Upload, Search, Database, Home, Network, Settings } from "lucide-react";
import { UserButton, SignedIn, SignedOut, SignInButton } from "@clerk/nextjs";

const navItems = [
  { href: "/", label: "Home", icon: Home },
  { href: "/ingest", label: "Ingest", icon: Upload },
  { href: "/query", label: "Query", icon: Search },
  { href: "/memory", label: "Memory", icon: Database },
  { href: "/graph", label: "Graph", icon: Network },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function Navigation() {
  const pathname = usePathname();

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-gray-900/95 backdrop-blur-sm border-b border-gray-800">
      <div className="max-w-7xl mx-auto px-4">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link href="/" className="flex items-center gap-2 group">
            <Brain className="w-8 h-8 text-indigo-500 group-hover:text-indigo-400 transition-colors" />
            <span className="font-bold text-lg text-white hidden sm:block">
              Second Brain
            </span>
          </Link>

          {/* Nav Links */}
          <div className="flex items-center gap-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = pathname === item.href;

              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`
                    flex items-center gap-2 px-3 py-2 rounded-lg transition-all
                    ${
                      isActive
                        ? "bg-indigo-600 text-white"
                        : "text-gray-400 hover:text-white hover:bg-gray-800"
                    }
                  `}
                >
                  <Icon className="w-4 h-4" />
                  <span className="hidden md:block text-sm font-medium">
                    {item.label}
                  </span>
                </Link>
              );
            })}
          </div>

          {/* User Button */}
          <div className="flex items-center gap-3">
            <SignedIn>
              <UserButton 
                afterSignOutUrl="/"
                appearance={{
                  elements: {
                    avatarBox: "w-9 h-9",
                  }
                }}
              />
            </SignedIn>
            <SignedOut>
              <SignInButton mode="modal">
                <button className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium rounded-lg transition-colors">
                  Sign In
                </button>
              </SignInButton>
            </SignedOut>
          </div>
        </div>
      </div>
    </nav>
  );
}

export default Navigation;
