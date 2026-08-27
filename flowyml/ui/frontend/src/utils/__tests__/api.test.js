import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

/**
 * `fetchApi` and `getWebSocketUrl` decide which origin every request reaches.
 * In remote-execution mode the API lives on a different host than the page, so
 * a helper that ignores the configured base URL silently talks to the wrong
 * server.
 */
describe('api helpers', () => {
    let api;

    const loadFresh = async (config) => {
        // The module caches the config, so each case needs a clean instance.
        vi.resetModules();
        global.fetch = vi.fn().mockResolvedValue({
            json: async () => config,
            ok: true,
        });
        api = await import('../api');
        return api;
    };

    beforeEach(() => {
        global.window = { location: { protocol: 'http:', host: 'localhost:5173' } };
    });

    afterEach(() => {
        vi.restoreAllMocks();
    });

    describe('local mode', () => {
        it('uses a relative URL so requests stay on the page origin', async () => {
            const { fetchApi } = await loadFresh({ execution_mode: 'local' });
            await fetchApi('/api/runs/');
            expect(global.fetch).toHaveBeenLastCalledWith('/api/runs/', {});
        });

        it('normalises an endpoint that is missing its leading slash', async () => {
            const { fetchApi } = await loadFresh({ execution_mode: 'local' });
            await fetchApi('api/runs/');
            expect(global.fetch).toHaveBeenLastCalledWith('/api/runs/', {});
        });

        it('builds a ws:// URL from the page host', async () => {
            const { getWebSocketUrl } = await loadFresh({ execution_mode: 'local' });
            expect(await getWebSocketUrl('/ws/runs/abc/logs')).toBe(
                'ws://localhost:5173/ws/runs/abc/logs',
            );
        });

        it('uses wss:// when the page is served over https', async () => {
            global.window.location.protocol = 'https:';
            const { getWebSocketUrl } = await loadFresh({ execution_mode: 'local' });
            expect(await getWebSocketUrl('/ws/runs/abc/logs')).toBe(
                'wss://localhost:5173/ws/runs/abc/logs',
            );
        });
    });

    describe('remote mode', () => {
        const remote = {
            execution_mode: 'remote',
            remote_server_url: 'https://api.example.com',
        };

        it('prefixes requests with the configured server URL', async () => {
            const { fetchApi } = await loadFresh(remote);
            await fetchApi('/api/runs/');
            expect(global.fetch).toHaveBeenLastCalledWith('https://api.example.com/api/runs/', {});
        });

        it('points WebSockets at the API origin, not the page origin', async () => {
            const { getWebSocketUrl } = await loadFresh(remote);
            // Previously built from window.location.host, which connected to
            // the wrong server and fell back to polling.
            expect(await getWebSocketUrl('/ws/runs/abc/logs')).toBe(
                'wss://api.example.com/ws/runs/abc/logs',
            );
        });

        it('forwards request options unchanged', async () => {
            const { fetchApi } = await loadFresh(remote);
            const options = { method: 'POST', body: '{}' };
            await fetchApi('/api/runs/', options);
            expect(global.fetch).toHaveBeenLastCalledWith(
                'https://api.example.com/api/runs/',
                options,
            );
        });
    });

    describe('when the config request fails', () => {
        it('falls back to local mode instead of throwing', async () => {
            vi.resetModules();
            global.fetch = vi.fn().mockRejectedValue(new Error('offline'));
            vi.spyOn(console, 'error').mockImplementation(() => {});
            const { getConfig } = await import('../api');
            expect(await getConfig()).toEqual({ execution_mode: 'local' });
        });
    });
});
