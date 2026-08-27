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

/**
 * Build an absolute WebSocket URL for an API path.
 *
 * Mirrors getBaseUrl(): in remote-execution mode the API lives on a different
 * origin than the page, and hardcoding window.location.host connected the
 * socket to the wrong server (which then fell back to polling).
 *
 * @param {string} endpoint - Path beginning with `/ws/`.
 * @returns {Promise<string>} Absolute ws:// or wss:// URL.
 */
export const getWebSocketUrl = async (endpoint) => {
    const path = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
    const baseUrl = await getBaseUrl();

    if (baseUrl) {
        // Reuse the configured API origin, swapping http(s) for ws(s).
        const url = new URL(path, baseUrl);
        url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
        return url.toString();
    }

    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    return `${wsProtocol}//${window.location.host}${path}`;
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
