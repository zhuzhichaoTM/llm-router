import { createContext, useContext, useState, useCallback, ReactNode } from 'react';

interface ConfigContextType {
  apiKey: string | null;
  adminApiKey: string | null;
  setApiKey: (key: string | null) => void;
  setAdminApiKey: (key: string | null) => void;
}

const ConfigContext = createContext<ConfigContextType | undefined>(undefined);

export function ConfigProvider({ children }: { children: ReactNode }) {
  const [apiKey, setApiKey] = useState<string | null>(null);
  const [adminApiKey, setAdminApiKey] = useState<string | null>(null);

  const handleSetApiKey = useCallback((key: string | null) => {
    setApiKey(key);
    if (key) {
      localStorage.setItem('llm_router_api_key', key);
    } else {
      localStorage.removeItem('llm_router_api_key');
    }
  }, []);

  const handleSetAdminApiKey = useCallback((key: string | null) => {
    setAdminApiKey(key);
    if (key) {
      localStorage.setItem('llm_router_admin_api_key', key);
    } else {
      localStorage.removeItem('llm_router_admin_api_key');
    }
  }, []);

  return (
    <ConfigContext.Provider
      value={{
        apiKey,
        adminApiKey,
        setApiKey: handleSetApiKey,
        setAdminApiKey: handleSetAdminApiKey,
      }}
    >
      {children}
    </ConfigContext.Provider>
  );
}

export function useConfig() {
  const context = useContext(ConfigContext);
  if (context === undefined) {
    throw new Error('useConfig must be used within a ConfigProvider');
  }
  return context;
}
