import { ThemeProvider as NextThemesProvider } from "next-themes";
import { useTheme as useNextTheme } from "next-themes";
import { useEffect, useState } from "react";

// Export the useTheme hook
export const useTheme = () => {
  const { theme, setTheme, ...rest } = useNextTheme();
  return { theme, setTheme, ...rest };
};

export function ThemeProvider({ children, defaultTheme = "system", ...props }) {
  const [mounted, setMounted] = useState(false);

  // Prevent hydration mismatch by only rendering after mount
  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) {
    return <div className="hidden">{children}</div>;
  }

  return (
    <NextThemesProvider
      defaultTheme={defaultTheme}
      enableSystem
      attribute="class"
      {...props}
    >
      {children}
    </NextThemesProvider>
  );
} 