import React from 'react';
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { ToastProvider } from './context/ToastContext';
import AppLayout from './layouts/AppLayout';

import LandingPage from './pages/LandingPage';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import DashboardPage from './pages/DashboardPage';
import UnifiedSearchPage from './pages/UnifiedSearchPage';
import DiscoveryPage from './pages/DiscoveryPage';
import PaperDetailPage from './pages/PaperDetailPage';
import UniversityLibraryPage from './pages/UniversityLibraryPage';
import CollectionsPage from './pages/CollectionsPage';
import ResearchersPage from './pages/ResearchersPage';
import ResearcherProfilePage from './pages/ResearcherProfilePage';
import DiscussionsPage from './pages/DiscussionsPage';
import CreatePostPage from './pages/CreatePostPage';
import RecommendationsPage from './pages/RecommendationsPage';
import TrendsPage from './pages/TrendsPage';
import AssistantPage from './pages/AssistantPage';
import AnalyticsPage from './pages/AnalyticsPage';
import AdminPage from './pages/AdminPage';
import SettingsPage from './pages/SettingsPage';

function RequireAuth({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) {
    return (
      <div className="min-h-[50vh] flex items-center justify-center text-sm text-[#687386]">
        Loading your workspace...
      </div>
    );
  }
  if (!user) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

function RequireAdmin({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) {
    return (
      <div className="min-h-[50vh] flex items-center justify-center text-sm text-[#687386]">
        Verifying permissions...
      </div>
    );
  }
  if (!user) return <Navigate to="/login" replace />;
  if (user.role !== 'admin') return <Navigate to="/dashboard" replace />;
  return <>{children}</>;
}

export default function App() {
  return (
    <ToastProvider>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<LandingPage />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />

            <Route element={<AppLayout />}>
              <Route path="/dashboard" element={<DashboardPage />} />
              <Route path="/search" element={<UnifiedSearchPage />} />
              <Route path="/discover" element={<DiscoveryPage />} />
              <Route path="/papers/:id" element={<PaperDetailPage />} />
              <Route path="/library" element={<UniversityLibraryPage />} />
              <Route path="/collections" element={<RequireAuth><CollectionsPage /></RequireAuth>} />
              <Route path="/researchers" element={<ResearchersPage />} />
              <Route path="/researchers/:id" element={<ResearcherProfilePage />} />
              <Route path="/discussions" element={<DiscussionsPage />} />
              <Route path="/discussions/new" element={<RequireAuth><CreatePostPage /></RequireAuth>} />
              <Route path="/recommendations" element={<RequireAuth><RecommendationsPage /></RequireAuth>} />
              <Route path="/trends" element={<TrendsPage />} />
              <Route path="/assistant" element={<AssistantPage />} />
              <Route path="/analytics" element={<RequireAdmin><AnalyticsPage /></RequireAdmin>} />
              <Route path="/admin" element={<RequireAdmin><AdminPage /></RequireAdmin>} />
              <Route path="/settings" element={<RequireAuth><SettingsPage /></RequireAuth>} />
            </Route>

            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </ToastProvider>
  );
}
