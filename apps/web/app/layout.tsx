import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Sortwise | Waste Classification',
  description: 'Upload one waste item and receive responsible sorting guidance.',
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

