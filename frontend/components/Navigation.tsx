"use client";

import React, { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Brain, Upload, Search, Database, Home, Network, Settings, Menu, X } from "lucide-react";
import { UserButton, SignedIn, SignedOut, SignInButton, useAuth } from "@clerk/nextjs";

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
  const { isSignedIn } = useAuth();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  // On landing page, show sign in button for signed out users
  const isLandingPage = pathname === "/";

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

          {/* Desktop Nav Links - Only show if signed in */}
          {isSignedIn && (
            <div className="hidden md:flex items-center gap-1">
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
                    <span className="text-sm font-medium">
                      {item.label}
                    </span>
                  </Link>
                );
              })}
            </div>
          )}

          {/* Right side - Auth buttons */}
          <div className="flex items-center gap-3">
            <SignedIn>
              {/* Mobile menu button */}
              <button
                onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
                className="md:hidden p-2 text-gray-400 hover:text-white hover:bg-gray-800 rounded-lg transition-colors"
              >
                {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
              </button>
              
              <UserButton 
                afterSignOutUrl="/"
                appearance={{
                  elements: {
                    avatarBox: "w-9 h-9",
                  }
                }}
              />
            </SignedIn>
            
            {/* Only show sign in on landing page when signed out */}
            {isLandingPage && (
              <SignedOut>
                <SignInButton mode="modal">
                  <button className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium rounded-lg transition-colors">
                    Sign In
                  </button>
                </SignInButton>
              </SignedOut>
            )}
          </div>
        </div>

        {/* Mobile Menu - Only show if signed in */}
        {isSignedIn && mobileMenuOpen && (
          <div className="md:hidden border-t border-gray-800 py-4">
            <div className="flex flex-col gap-2">
              {navItems.map((item) => {
                const Icon = item.icon;
                const isActive = pathname === item.href;

                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    onClick={() => setMobileMenuOpen(false)}
                    className={`
                      flex items-center gap-3 px-4 py-3 rounded-lg transition-all
                      ${
                        isActive
                          ? "bg-indigo-600 text-white"
                          : "text-gray-400 hover:text-white hover:bg-gray-800"
                      }
                    `}
                  >
                    <Icon className="w-5 h-5" />
                    <span className="text-base font-medium">
                      {item.label}
                    </span>
                  </Link>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </nav>
  );
}

export default Navigation;
