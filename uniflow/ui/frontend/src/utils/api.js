import { useState, useEffect } from 'react';

// Cache for config
let configCache = null;

export const getConfig = async () => {
  if (configCache) return configCache;
  try {
    const res = await fetch('/api/config');
    configCache = await res.json();
    return configCache;
  } catch (err) {
    console.error('Failed to fetch config:', err);
    return { execution_mode: 'local' };
  }
};

export const getBaseUrl = async () => {
  const config = await getConfig();
  if (config.execution_mode === 'remote' && config.remote_server_url) {
    return config.remote_server_url;
  }
  return '';
};

export const fetchApi = async (endpoint, options = {}) => {
  const baseUrl = await getBaseUrl();
  // Ensure endpoint starts with /
  const path = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
  const url = `${baseUrl}${path}`;

  return fetch(url, options);
};

export const useConfig = () => {
  const [config, setConfig] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getConfig().then(cfg => {
      setConfig(cfg);
      setLoading(false);
    });
  }, []);

  return { config, loading };
};
