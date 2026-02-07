import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ConfigProvider, useConfig } from '@/hooks/useConfig';
import Layout from '@/components/Layout';
import Dashboard from '@/pages/Dashboard';
import Providers from '@/pages/Providers';
import Routing from '@/pages/Routing';
import Cost from '@/pages/Cost';
import ApiDocs from '@/pages/ApiDocs';
import QuickStart from '@/pages/QuickStart';
import Monitor from '@/pages/Monitor';
import ApiKeyModal from '@/components/ApiKeyModal';

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { apiKey } = useConfig();
  if (!apiKey) {
    return <Navigate to="/quick-start" replace />;
  }
  return <>{children}</>;
}

function App() {
  const { setApiKey } = useConfig();

  // Load API key from localStorage on mount
  React.useEffect(() => {
    const savedKey = localStorage.getItem('llm_router_api_key');
    if (savedKey) {
      setApiKey(savedKey);
    }
  }, [setApiKey]);

  return (
    <ConfigProvider>
      <BrowserRouter>
        <Layout>
          <Routes>
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/providers" element={
              <ProtectedRoute>
                <Providers />
              </ProtectedRoute>
            } />
            <Route path="/routing" element={
              <ProtectedRoute>
                <Routing />
              </ProtectedRoute>
            } />
            <Route path="/cost" element={
              <ProtectedRoute>
                <Cost />
              </ProtectedRoute>
            } />
            <Route path="/api-docs" element={<ApiDocs />} />
            <Route path="/quick-start" element={<QuickStart />} />
            <Route path="/monitor" element={
              <ProtectedRoute>
                <Monitor />
              </ProtectedRoute>
            } />
          </Routes>
          <ApiKeyModal />
        </Layout>
      </BrowserRouter>
    </ConfigProvider>
  );
}

export default App;
