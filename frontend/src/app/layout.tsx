import type { Metadata } from 'next';
import './globals.css';
import { Providers } from './providers';

export const metadata: Metadata = {
  title: 'DepHealth - Predictive Dependency Health Monitoring',
  description: 'Predict future dependency risks before they become problems with AI-powered analysis',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body style={{ backgroundColor: '#0c0a09', color: '#f5f5f4', margin: 0, padding: 0 }}>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
