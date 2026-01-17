'use client';

import { ClerkProvider } from '@clerk/nextjs';
import { ReactNode } from 'react';

interface ProvidersProps {
  children: ReactNode;
}

export function Providers({ children }: ProvidersProps) {
  return (
    <ClerkProvider
      appearance={{
        elements: {
          formButtonPrimary: 
            'bg-indigo-600 hover:bg-indigo-700 text-white',
          card: 'bg-gray-900 border border-gray-800',
          headerTitle: 'text-white',
          headerSubtitle: 'text-gray-400',
          socialButtonsBlockButton: 
            'bg-gray-800 border-gray-700 text-white hover:bg-gray-700',
          formFieldLabel: 'text-gray-300',
          formFieldInput: 
            'bg-gray-800 border-gray-700 text-white',
          footerActionLink: 'text-indigo-400 hover:text-indigo-300',
          identityPreviewEditButton: 'text-indigo-400',
          formFieldAction: 'text-indigo-400',
          alertText: 'text-gray-300',
          userButtonPopoverCard: 'bg-gray-900 border-gray-800',
          userButtonPopoverActionButton: 'text-gray-300 hover:bg-gray-800',
          userButtonPopoverActionButtonText: 'text-gray-300',
          userButtonPopoverFooter: 'hidden',
        },
        variables: {
          colorPrimary: '#6366f1',
          colorBackground: '#111827',
          colorText: '#ffffff',
          colorTextSecondary: '#9ca3af',
          colorInputBackground: '#1f2937',
          colorInputText: '#ffffff',
        },
      }}
    >
      {children}
    </ClerkProvider>
  );
}
