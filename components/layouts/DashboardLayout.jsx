import React, { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/router';
import { motion } from 'framer-motion';
import { Home, FileText, Box, MessageSquare, User, LogOut, Menu, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useAuth } from '@/utils/AuthContext';
import { ThemeToggle } from '@/components/ui/theme-toggle';
import TransitionLayout from '@/components/TransitionLayout';

export default function DashboardLayout({ children }) {
  const { user, logout } = useAuth();
  const router = useRouter();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  const navItems = [
    { label: 'Dashboard', href: '/dashboard', icon: <Home className="w-5 h-5" /> },
    { label: 'Text Processing', href: '/dashboard/text-processing', icon: <FileText className="w-5 h-5" /> },
    { label: 'AR Experience', href: '/dashboard/ar-experience', icon: <Box className="w-5 h-5" /> },
    { label: 'Feedback', href: '/dashboard/feedback', icon: <MessageSquare className="w-5 h-5" /> },
    { label: 'Profile', href: '/dashboard/profile', icon: <User className="w-5 h-5" /> },
  ];

  const isActive = (path) => router.pathname === path;

  const toggleMobileMenu = () => {
    setIsMobileMenuOpen(!isMobileMenuOpen);
  };

  const sidebarVariants = {
    hidden: { x: -300, opacity: 0 },
    visible: { 
      x: 0, 
      opacity: 1,
      transition: { 
        type: "spring", 
        stiffness: 300, 
        damping: 30,
        staggerChildren: 0.05,
        delayChildren: 0.05
      }
    }
  };

  const navItemVariants = {
    hidden: { x: -20, opacity: 0 },
    visible: { 
      x: 0, 
      opacity: 1, 
      transition: { 
        duration: 0.2 
      }
    }
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Mobile menu toggle */}
      <div className="block md:hidden fixed top-4 left-4 z-50">
        <Button
          variant="ghost"
          size="icon"
          onClick={toggleMobileMenu}
          aria-label={isMobileMenuOpen ? "Close menu" : "Open menu"}
          className="rounded-full"
        >
          {isMobileMenuOpen ? (
            <X className="h-5 w-5" />
          ) : (
            <Menu className="h-5 w-5" />
          )}
        </Button>
      </div>

      {/* Sidebar for desktop */}
      <motion.aside
        initial="hidden"
        animate="visible"
        variants={sidebarVariants}
        className="fixed hidden md:flex w-64 h-full bg-card/50 backdrop-blur-sm shadow-md flex-col border-r border-border z-10"
      >
        <div className="p-6">
          <motion.h1 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.2 }}
            className="text-2xl font-bold text-primary"
          >
            Aetherion AR
          </motion.h1>
        </div>

        <nav className="flex-1 px-4">
          <ul className="space-y-2">
            {navItems.map((item, index) => (
              <motion.li 
                key={item.href}
                variants={navItemVariants}
              >
                <Link href={item.href}>
                  <div
                    className={`flex items-center px-4 py-3 rounded-lg transition-all duration-200 hover:bg-accent hover:text-accent-foreground ${
                      isActive(item.href)
                        ? 'bg-accent text-accent-foreground font-medium'
                        : 'text-foreground/70'
                    }`}
                  >
                    {item.icon}
                    <span className="ml-3">{item.label}</span>
                  </div>
                </Link>
              </motion.li>
            ))}
          </ul>
        </nav>

        <div className="p-4 border-t border-border flex flex-col gap-2">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center">
              <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center text-primary-foreground">
                {user && user.name ? user.name.charAt(0).toUpperCase() : 'U'}
              </div>
              <div className="ml-3">
                <p className="text-sm font-medium">{user ? user.name : 'User'}</p>
                <p className="text-xs text-muted-foreground truncate max-w-[140px]">
                  {user ? user.email : 'user@example.com'}
                </p>
              </div>
            </div>
            <ThemeToggle />
          </div>
          <Button
            variant="outline"
            onClick={logout}
            className="w-full justify-start"
          >
            <LogOut className="w-4 h-4 mr-2" />
            Logout
          </Button>
        </div>
      </motion.aside>

      {/* Mobile sidebar overlay */}
      {isMobileMenuOpen && (
        <div
          className="fixed inset-0 bg-background/80 backdrop-blur-sm z-40 md:hidden"
          onClick={toggleMobileMenu}
        />
      )}

      {/* Mobile sidebar */}
      <motion.aside
        initial={{ x: -300 }}
        animate={{ x: isMobileMenuOpen ? 0 : -300 }}
        transition={{ duration: 0.3, ease: "easeInOut" }}
        className="fixed flex md:hidden w-64 h-full bg-card shadow-lg flex-col z-50"
      >
        <div className="p-6 flex items-center justify-between">
          <h1 className="text-2xl font-bold text-primary">Aetherion AR</h1>
          <ThemeToggle className="md:hidden" />
        </div>

        <nav className="flex-1 px-4">
          <ul className="space-y-2">
            {navItems.map((item) => (
              <li key={item.href}>
                <Link href={item.href}>
                  <div
                    className={`flex items-center px-4 py-3 rounded-lg transition-all duration-200 hover:bg-accent hover:text-accent-foreground ${
                      isActive(item.href)
                        ? 'bg-accent text-accent-foreground font-medium'
                        : 'text-foreground/70'
                    }`}
                    onClick={toggleMobileMenu}
                  >
                    {item.icon}
                    <span className="ml-3">{item.label}</span>
                  </div>
                </Link>
              </li>
            ))}
          </ul>
        </nav>

        <div className="p-4 border-t border-border">
          <div className="flex items-center mb-4">
            <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center text-primary-foreground">
              {user && user.name ? user.name.charAt(0).toUpperCase() : 'U'}
            </div>
            <div className="ml-3">
              <p className="text-sm font-medium">{user ? user.name : 'User'}</p>
              <p className="text-xs text-muted-foreground truncate max-w-[180px]">
                {user ? user.email : 'user@example.com'}
              </p>
            </div>
          </div>
          <Button
            variant="outline"
            onClick={logout}
            className="w-full justify-start"
          >
            <LogOut className="w-4 h-4 mr-2" />
            Logout
          </Button>
        </div>
      </motion.aside>

      {/* Main content */}
      <main className="md:ml-64 min-h-screen">
        <TransitionLayout variant="fadeIn" duration={0.3}>
          <div className="container max-w-7xl mx-auto py-8 px-4 md:px-8">
            {children}
          </div>
        </TransitionLayout>
      </main>
    </div>
  );
} 