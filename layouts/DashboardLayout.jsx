import React, { useState, useContext } from 'react';
import Head from 'next/head';
import Link from 'next/link';
import { useRouter } from 'next/router';
import { motion, AnimatePresence } from 'framer-motion';
import { AuthContext } from '@/utils/AuthContext';
import {
  ChevronLeft,
  ChevronRight,
  Home,
  FileText,
  Glasses,
  MessageSquare,
  Settings,
  Bell,
  User,
  LogOut,
  Menu,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';

const navItems = [
  { 
    path: '/dashboard', 
    label: 'Dashboard', 
    icon: Home,
    exact: true
  },
  { 
    path: '/dashboard/text-processing', 
    label: 'Text Processing', 
    icon: FileText 
  },
  { 
    path: '/dashboard/ar-experience', 
    label: 'AR Experience', 
    icon: Glasses 
  },
  { 
    path: '/dashboard/feedback', 
    label: 'Feedback', 
    icon: MessageSquare 
  },
  { 
    path: '/dashboard/settings', 
    label: 'Settings', 
    icon: Settings 
  },
];

export default function DashboardLayout({ children, title, description }) {
  const router = useRouter();
  const { user, logout } = useContext(AuthContext);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const toggleSidebar = () => {
    setSidebarOpen(!sidebarOpen);
  };

  const toggleMobileMenu = () => {
    setMobileMenuOpen(!mobileMenuOpen);
  };

  const handleLogout = async () => {
    await logout();
    router.push('/login');
  };

  // Check if the path matches the current route
  const isActive = (path, exact = false) => {
    if (exact) {
      return router.pathname === path;
    }
    return router.pathname.startsWith(path);
  };

  return (
    <div className="flex h-screen bg-slate-50 dark:bg-slate-900">
      <Head>
        <title>{title ? `${title} | Aetherion AR` : 'Aetherion AR'}</title>
        <meta 
          name="description" 
          content={description || 'Aetherion AR platform dashboard'}
        />
      </Head>

      {/* Desktop Sidebar */}
      <aside 
        className={`fixed inset-y-0 z-50 flex-shrink-0 ${
          sidebarOpen ? 'w-64' : 'w-20'
        } flex-col hidden md:flex transition-all duration-300 bg-white dark:bg-slate-800 border-r border-slate-200 dark:border-slate-700`}
      >
        {/* Sidebar header */}
        <div className="h-16 flex items-center justify-between px-4 border-b border-slate-200 dark:border-slate-700">
          {sidebarOpen && (
            <Link href="/dashboard" className="flex items-center space-x-2">
              <div className="h-8 w-8 rounded-full bg-gradient-to-tr from-sky-500 to-indigo-500 flex items-center justify-center text-white font-bold">
                A
              </div>
              <span className="text-xl font-semibold dark:text-white">Aetherion</span>
            </Link>
          )}
          <Button 
            variant="ghost" 
            size="icon" 
            onClick={toggleSidebar}
            className="ml-auto text-slate-500 hover:text-slate-600 dark:text-slate-400 dark:hover:text-slate-300"
          >
            {sidebarOpen ? <ChevronLeft /> : <ChevronRight />}
          </Button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 overflow-y-auto py-4">
          <ul className="space-y-1 px-2">
            {navItems.map((item) => (
              <li key={item.path}>
                <Link 
                  href={item.path}
                  className={`flex items-center ${
                    sidebarOpen ? 'px-4' : 'justify-center px-2'
                  } py-3 rounded-md transition-colors ${
                    isActive(item.path, item.exact) 
                      ? 'bg-sky-50 text-sky-600 dark:bg-sky-900/30 dark:text-sky-400' 
                      : 'text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-700/50'
                  }`}
                >
                  <item.icon className={`${sidebarOpen ? 'mr-3' : ''} h-5 w-5`} />
                  {sidebarOpen && <span>{item.label}</span>}
                </Link>
              </li>
            ))}
          </ul>
        </nav>

        {/* User section */}
        {sidebarOpen && (
          <div className="p-4 border-t border-slate-200 dark:border-slate-700">
            <div className="flex items-center space-x-3">
              <Avatar>
                <AvatarImage src={user?.avatar} />
                <AvatarFallback className="bg-sky-500 text-white">
                  {user?.name?.charAt(0) || 'U'}
                </AvatarFallback>
              </Avatar>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-slate-900 dark:text-white truncate">
                  {user?.name || 'User'}
                </p>
                <p className="text-xs text-slate-500 dark:text-slate-400 truncate">
                  {user?.email || 'user@example.com'}
                </p>
              </div>
            </div>
          </div>
        )}
      </aside>

      {/* Mobile sidebar */}
      <AnimatePresence>
        {mobileMenuOpen && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 0.5 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 z-40 bg-black md:hidden"
              onClick={toggleMobileMenu}
            />
            <motion.aside
              initial={{ x: -280 }}
              animate={{ x: 0 }}
              exit={{ x: -280 }}
              transition={{ ease: "easeOut", duration: 0.25 }}
              className="fixed inset-y-0 left-0 z-50 w-64 flex flex-col md:hidden bg-white dark:bg-slate-800 shadow-xl"
            >
              {/* Mobile sidebar header */}
              <div className="h-16 flex items-center justify-between px-4 border-b border-slate-200 dark:border-slate-700">
                <Link href="/dashboard" className="flex items-center space-x-2">
                  <div className="h-8 w-8 rounded-full bg-gradient-to-tr from-sky-500 to-indigo-500 flex items-center justify-center text-white font-bold">
                    A
                  </div>
                  <span className="text-xl font-semibold dark:text-white">Aetherion</span>
                </Link>
                <Button 
                  variant="ghost" 
                  size="icon" 
                  onClick={toggleMobileMenu}
                  className="text-slate-500 hover:text-slate-600 dark:text-slate-400 dark:hover:text-slate-300"
                >
                  <ChevronLeft />
                </Button>
              </div>

              {/* Mobile navigation */}
              <nav className="flex-1 overflow-y-auto py-4">
                <ul className="space-y-1 px-2">
                  {navItems.map((item) => (
                    <li key={item.path}>
                      <Link 
                        href={item.path}
                        className={`flex items-center px-4 py-3 rounded-md transition-colors ${
                          isActive(item.path, item.exact) 
                            ? 'bg-sky-50 text-sky-600 dark:bg-sky-900/30 dark:text-sky-400' 
                            : 'text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-700/50'
                        }`}
                        onClick={toggleMobileMenu}
                      >
                        <item.icon className="mr-3 h-5 w-5" />
                        <span>{item.label}</span>
                      </Link>
                    </li>
                  ))}
                </ul>
              </nav>

              {/* Mobile user section */}
              <div className="p-4 border-t border-slate-200 dark:border-slate-700">
                <div className="flex items-center space-x-3">
                  <Avatar>
                    <AvatarImage src={user?.avatar} />
                    <AvatarFallback className="bg-sky-500 text-white">
                      {user?.name?.charAt(0) || 'U'}
                    </AvatarFallback>
                  </Avatar>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-slate-900 dark:text-white truncate">
                      {user?.name || 'User'}
                    </p>
                    <p className="text-xs text-slate-500 dark:text-slate-400 truncate">
                      {user?.email || 'user@example.com'}
                    </p>
                  </div>
                </div>
              </div>
            </motion.aside>
          </>
        )}
      </AnimatePresence>

      {/* Main content area */}
      <div className={`flex-1 flex flex-col md:ml-${sidebarOpen ? '64' : '20'} transition-all duration-300`}>
        {/* Top navigation */}
        <header className="h-16 flex items-center justify-between px-4 md:px-6 border-b border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800">
          {/* Mobile menu button */}
          <Button 
            variant="ghost" 
            size="icon" 
            onClick={toggleMobileMenu}
            className="md:hidden text-slate-500 hover:text-slate-600 dark:text-slate-400 dark:hover:text-slate-300"
          >
            <Menu />
          </Button>

          {/* Page title - could be dynamic based on current route */}
          <h1 className="text-lg font-semibold text-slate-900 dark:text-white md:ml-0 ml-3">
            {navItems.find(item => 
              isActive(item.path, item.exact)
            )?.label || 'Dashboard'}
          </h1>

          {/* Right side actions */}
          <div className="flex items-center space-x-4">
            {/* Notifications */}
            <div className="relative">
              <Button 
                variant="ghost" 
                size="icon"
                className="text-slate-500 hover:text-slate-600 dark:text-slate-400 dark:hover:text-slate-300"
              >
                <Bell className="h-5 w-5" />
                <Badge className="absolute -top-1 -right-1 h-5 w-5 flex items-center justify-center p-0 text-xs bg-sky-500">
                  3
                </Badge>
              </Button>
            </div>

            {/* User menu */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button 
                  variant="ghost" 
                  size="sm" 
                  className="flex items-center space-x-2 hover:bg-slate-100 dark:hover:bg-slate-700/50"
                >
                  <Avatar className="h-8 w-8">
                    <AvatarImage src={user?.avatar} />
                    <AvatarFallback className="bg-sky-500 text-white">
                      {user?.name?.charAt(0) || 'U'}
                    </AvatarFallback>
                  </Avatar>
                  <span className="text-sm font-medium text-slate-700 dark:text-slate-200 hidden sm:inline-block">
                    {user?.name || 'User'}
                  </span>
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-56">
                <DropdownMenuLabel>My Account</DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItem>
                  <User className="mr-2 h-4 w-4" />
                  <span>Profile</span>
                </DropdownMenuItem>
                <DropdownMenuItem>
                  <Settings className="mr-2 h-4 w-4" />
                  <span>Settings</span>
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={handleLogout}>
                  <LogOut className="mr-2 h-4 w-4" />
                  <span>Log out</span>
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </header>

        {/* Main content */}
        <main className="flex-1 overflow-y-auto p-4 md:p-6 bg-slate-50 dark:bg-slate-900">
          <Card className="bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700 shadow-sm">
            <div className="p-6">{children}</div>
          </Card>
        </main>
      </div>
    </div>
  );
} 