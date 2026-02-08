import React, { useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ConfigProvider, useConfig } from '@/hooks/useConfig';
import LayoutComponent from '@/components/Layout';
import Dashboard from '@/pages/Dashboard';
import Providers from '@/pages/Providers';
import Routing from '@/pages/Routing';
import Cost from '@/pages/Cost';
import ApiDocs from '@/pages/ApiDocs';
import QuickStart from '@/pages/QuickStart';
import Monitor from '@/pages/Monitor';
import Analytics from '@/pages/Analytics';
import ApiKeyModal from '@/components/ApiKeyModal';

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { apiKey } = useConfig();
  if (!apiKey) {
    return <Navigate to="/quick-start" replace />;
  }
  return <>{children}</>;
}

function AppContent() {
  let config;
  try {
    config = useConfig();
  } catch (error) {
    return <div style={{padding: '20px'}}>Error: {String(error)}</div>;
  }

  if (!config) {
    return <div style={{padding: '20px'}}>Config not available</div>;
  }

  const { setApiKey } = config;

  useEffect(() => {
    const savedKey = localStorage.getItem('llm_router_api_key');
    if (savedKey) {
      setApiKey(savedKey);
    }
  }, [setApiKey]);

  return (
    <>
      <Routes>
        <Route path="/" element={<LayoutComponent />}>
          <Route index element={<Navigate to="/quick-start" replace />} />
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="providers" element={
            <ProtectedRoute>
              <Providers />
            </ProtectedRoute>
          } />
          <Route path="routing" element={
            <ProtectedRoute>
              <Routing />
            </ProtectedRoute>
          } />
          <Route path="cost" element={
            <ProtectedRoute>
              <Cost />
            </ProtectedRoute>
          } />
          <Route path="api-docs" element={<ApiDocs />} />
          <Route path="quick-start" element={<QuickStart />} />
          <Route path="monitor" element={
            <ProtectedRoute>
              <Monitor />
            </ProtectedRoute>
          } />
          <Route path="analytics" element={
            <ProtectedRoute>
              <Analytics />
            </ProtectedRoute>
          } />
        </Route>
      </Routes>
      <ApiKeyModal />
    </>
  );
}

function App() {
  return (
    <ConfigProvider>
      <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <AppContent />
      </BrowserRouter>
    </ConfigProvider>
  );
}

export default App;
