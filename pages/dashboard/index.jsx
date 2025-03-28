import React, { useState, useEffect, useContext } from 'react';
import Head from 'next/head';
import Link from 'next/link';
import { useRouter } from 'next/router';
import { AuthContext } from '@/utils/AuthContext';
import { userAPI } from '@/utils/api';

export default function DashboardPage() {
  const router = useRouter();
  const { user, logout } = useContext(AuthContext);
  const [dashboardStats, setDashboardStats] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        setIsLoading(true);
        const stats = await userAPI.getDashboardStats();
        setDashboardStats(stats);
        setError(null);
      } catch (err) {
        console.error('Failed to fetch dashboard stats:', err);
        setError('Using fallback data. API server may be offline.');
        // Always use fallback data to avoid errors disrupting the UI
        setDashboardStats({
          projects: 12,
          arSessions: 48,
          textProcesses: 156,
          hoursUsed: 24,
          recentProjects: [
            { id: 1, name: 'Virtual Assistant', date: '2023-12-15' },
            { id: 2, name: 'AR Office Tour', date: '2023-12-10' },
            { id: 3, name: 'Text Analysis Demo', date: '2023-12-05' },
          ]
        });
      } finally {
        setIsLoading(false);
      }
    };

    fetchDashboardData();
  }, []);

  const handleLogout = async () => {
    try {
      await logout();
      // The AuthContext's logout function will handle the redirect
    } catch (error) {
      console.error('Logout error:', error);
    }
  };

  // Format stats for display
  const stats = dashboardStats ? [
    { title: 'Projects', value: dashboardStats.projects.toString(), icon: '📁' },
    { title: 'AR Sessions', value: dashboardStats.arSessions.toString(), icon: '🥽' },
    { title: 'Text Processes', value: dashboardStats.textProcesses.toString(), icon: '📝' },
    { title: 'Hours Used', value: dashboardStats.hoursUsed.toString(), icon: '⏱️' },
  ] : [];

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50">
        <div className="text-center">
          <p className="text-lg text-slate-600">Loading dashboard...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50">
      <Head>
        <title>Dashboard | Aetherion AR</title>
        <meta name="description" content="Aetherion AR user dashboard" />
      </Head>

      {/* Header */}
      <header className="bg-slate-800 text-white">
        <div className="container mx-auto px-4 py-4 flex justify-between items-center">
          <div className="flex items-center space-x-8">
            <h1 className="text-xl font-bold">Aetherion AR</h1>
            <nav>
              <ul className="flex space-x-6">
                <li>
                  <Link href="/dashboard" className="text-white hover:text-sky-300 transition font-medium">
                    Dashboard
                  </Link>
                </li>
                <li>
                  <Link href="/dashboard/text-processing" className="text-slate-300 hover:text-sky-300 transition">
                    Text Processing
                  </Link>
                </li>
                <li>
                  <Link href="/dashboard/ar-experience" className="text-slate-300 hover:text-sky-300 transition">
                    AR Experience
                  </Link>
                </li>
                <li>
                  <Link href="/dashboard/feedback" className="text-slate-300 hover:text-sky-300 transition">
                    Feedback
                  </Link>
                </li>
              </ul>
            </nav>
          </div>
          <div className="flex items-center space-x-4">
            <span className="text-sm">{user?.name || 'User'}</span>
            <button
              onClick={handleLogout}
              className="px-3 py-1 text-sm bg-slate-700 hover:bg-slate-600 rounded transition"
            >
              Logout
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-8">
        {error && (
          <div className="mb-4 p-3 bg-red-100 border border-red-200 text-red-800 rounded">
            {error}
          </div>
        )}
        
        <div className="mb-8">
          <h2 className="text-2xl font-bold text-slate-800 mb-2">Welcome, {user?.name || 'User'}</h2>
          <p className="text-slate-600">Here's an overview of your Aetherion AR activity</p>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-10">
          {stats.map((stat, index) => (
            <div key={index} className="bg-white p-6 rounded-lg shadow-sm border border-slate-100">
              <div className="flex items-center space-x-4">
                <div className="text-3xl">{stat.icon}</div>
                <div>
                  <div className="text-2xl font-bold text-slate-800">{stat.value}</div>
                  <div className="text-sm text-slate-500">{stat.title}</div>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Quick Access Section */}
        <div className="grid md:grid-cols-2 gap-8 mb-8">
          <div className="bg-white p-6 rounded-lg shadow-sm border border-slate-100">
            <h3 className="text-lg font-semibold mb-4">Quick Access</h3>
            <div className="grid grid-cols-2 gap-4">
              <Link 
                href="/dashboard/text-processing" 
                className="p-4 bg-sky-50 rounded-lg border border-sky-100 hover:bg-sky-100 transition text-center"
              >
                <div className="text-3xl mb-2">📝</div>
                <div className="font-medium">Text Processing</div>
              </Link>
              <Link 
                href="/dashboard/ar-experience" 
                className="p-4 bg-emerald-50 rounded-lg border border-emerald-100 hover:bg-emerald-100 transition text-center"
              >
                <div className="text-3xl mb-2">🥽</div>
                <div className="font-medium">AR Experience</div>
              </Link>
              <Link 
                href="#" 
                className="p-4 bg-amber-50 rounded-lg border border-amber-100 hover:bg-amber-100 transition text-center"
              >
                <div className="text-3xl mb-2">🗃️</div>
                <div className="font-medium">Documents</div>
              </Link>
              <Link 
                href="/dashboard/feedback" 
                className="p-4 bg-purple-50 rounded-lg border border-purple-100 hover:bg-purple-100 transition text-center"
              >
                <div className="text-3xl mb-2">📊</div>
                <div className="font-medium">Feedback</div>
              </Link>
            </div>
          </div>

          {/* Recent Projects */}
          <div className="bg-white p-6 rounded-lg shadow-sm border border-slate-100">
            <h3 className="text-lg font-semibold mb-4">Recent Projects</h3>
            <div className="divide-y">
              {dashboardStats?.recentProjects?.map((project) => (
                <div key={project.id} className="py-3 flex justify-between items-center">
                  <div>
                    <div className="font-medium">{project.name}</div>
                    <div className="text-sm text-slate-500">
                      Last modified: {new Date(project.date).toLocaleDateString()}
                    </div>
                  </div>
                  <Link 
                    href={`/projects/${project.id}`}
                    className="px-3 py-1 text-sm bg-slate-100 hover:bg-slate-200 rounded transition"
                  >
                    Open
                  </Link>
                </div>
              ))}
              {(!dashboardStats?.recentProjects || dashboardStats.recentProjects.length === 0) && (
                <div className="py-3 text-slate-500 text-center">No recent projects found</div>
              )}
            </div>
            <div className="mt-4 text-center">
              <Link 
                href="/projects" 
                className="text-sm text-sky-600 hover:text-sky-700 transition"
              >
                View all projects →
              </Link>
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="bg-slate-800 text-slate-400 py-6 mt-auto">
        <div className="container mx-auto px-4 text-center text-sm">
          <p>© 2023 Aetherion AR Project. All rights reserved.</p>
        </div>
      </footer>
    </div>
  );
} 