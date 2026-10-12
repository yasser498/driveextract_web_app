import './globals.css';
import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'DriveExtract',
  description: 'تحويل روابط Google Drive Viewer إلى صور وPDF',
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="ar" dir="rtl">
      <body>{children}</body>
    </html>
  );
}
