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

/**
 * Fetch an API endpoint and return its parsed JSON body, throwing on failure.
 *
 * `fetchApi` returns the raw Response, and most call sites went straight to
 * `.json()` without checking `.ok`. An error body then parsed cleanly, the
 * expected field came back `undefined`, and the page rendered its empty state -
 * so a failing backend was indistinguishable from an account with no data.
 *
 * @param {string} endpoint - API path.
 * @param {RequestInit} [options] - Passed through to fetch.
 * @returns {Promise<any>} Parsed response body.
 * @throws {ApiError} When the response status is not ok.
 */
export const fetchJson = async (endpoint, options = {}) => {
    const response = await fetchApi(endpoint, options);

    if (!response.ok) {
        let detail = `Request failed with status ${response.status}`;
        try {
            const body = await response.json();
            // FastAPI uses `detail`; the app-wide handler uses `message`.
            detail = body?.detail || body?.message || detail;
            if (typeof detail !== 'string') detail = JSON.stringify(detail);
        } catch {
            // Non-JSON body: keep the status-based message.
        }
        throw new ApiError(detail, response.status);
    }

    // 204 and other empty bodies must not blow up the caller.
    if (response.status === 204) return null;

    return response.json();
};

/** Error carrying the HTTP status alongside the server's message. */
export class ApiError extends Error {
    constructor(message, status) {
        super(message);
        this.name = 'ApiError';
        this.status = status;
    }
}

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
