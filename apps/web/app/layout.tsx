import type { Metadata } from 'next';
import { Toaster } from 'sonner';
import './globals.css';

export const metadata: Metadata = {
  title: 'Chief',
  description: 'Your life, under management.',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" data-theme="chief">
      <body>
        {children}
        <Toaster
          theme="dark"
          toastOptions={{
            style: {
              background: 'var(--v2-panel)',
              border: '1px solid var(--v2-border)',
              color: 'var(--v2-text)',
            },
          }}
        />
      </body>
    </html>
  );
}
