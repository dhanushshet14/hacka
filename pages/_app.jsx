import { Toaster } from '@/components/ui/toaster';
import '@/app/globals.css';
import { AuthProvider } from '@/utils/AuthContext';
import { ThemeProvider } from '@/components/ThemeProvider';

export default function App({ Component, pageProps }) {
  return (
    <ThemeProvider defaultTheme="system">
      <AuthProvider>
        <Component {...pageProps} />
        <Toaster />
      </AuthProvider>
    </ThemeProvider>
  );
} 