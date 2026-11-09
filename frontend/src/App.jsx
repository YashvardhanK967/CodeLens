import React, { useState } from 'react';
import LandingPage from './components/LandingPage';
import AnalyticsDashboard from './components/AnalyticsDashboard';
import { fetchUserAnalytics } from './api';
import { Code2, Github } from 'lucide-react';

export default function App() {
  const [formData, setFormData] = useState(null);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleFetch = async (form) => {
    setLoading(true);
    setError(null);
    try {
      setFormData(form);
      const result = await fetchUserAnalytics(form);
      setData(result);
    } catch (err) {
      console.error(err);
      setError(
        err.response?.data?.detail ||
          err.message ||
          'Failed to retrieve analytics. Please verify handle names and network connectivity.'
      );
    } finally {
      setLoading(false);
    }
  };

  const handleRefresh = () => {
    if (formData) {
      handleFetch(formData);
    }
  };

  const handleReset = () => {
    setData(null);
    setError(null);
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col justify-between selection:bg-indigo-500 selection:text-white">
      {/* Top Global Bar */}
      <nav className="border-b border-slate-900 bg-slate-950/80 backdrop-blur-md sticky top-0 z-50 px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div 
            onClick={handleReset}
            className="flex items-center gap-2.5 cursor-pointer group"
          >
            <div className="w-8 h-8 rounded-xl bg-indigo-600 flex items-center justify-center text-white shadow-lg shadow-indigo-600/30 group-hover:scale-105 transition">
              <Code2 size={18} />
            </div>
            <div>
              <span className="font-extrabold text-base tracking-tight text-white group-hover:text-indigo-300 transition">
                CodePulse
              </span>
              <span className="text-[10px] text-slate-500 block leading-none font-mono">
                Analytics Engine v2.0
              </span>
            </div>
          </div>

          <div className="flex items-center gap-3 text-xs text-slate-400">
            <span className="hidden sm:inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-slate-900 border border-slate-800">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              API Connected
            </span>
          </div>
        </div>
      </nav>

      {/* Main Body */}
      <main className="max-w-7xl mx-auto w-full px-4 sm:px-6 py-6 flex-1">
        {!data ? (
          <LandingPage
            onSubmit={handleFetch}
            loading={loading}
            error={error}
          />
        ) : (
          <AnalyticsDashboard
            data={data}
            onReset={handleReset}
            onRefresh={handleRefresh}
            loading={loading}
          />
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-900 py-6 px-6 text-center text-xs text-slate-500">
        <p>
          CodePulse &copy; {new Date().getFullYear()} — Multi-Platform Competitive Programming & DSA Analytics.
        </p>
      </footer>
    </div>
  );
}

