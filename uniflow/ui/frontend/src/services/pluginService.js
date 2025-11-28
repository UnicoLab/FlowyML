/**
 * Service for managing plugins and integrations.
 * Communicates with the backend API for plugin operations.
 */

const API_BASE_URL = '/api';

class PluginService {
    async getAvailablePlugins() {
        try {
            const response = await fetch(`${API_BASE_URL}/plugins/available`);
            if (!response.ok) throw new Error('Failed to fetch available plugins');
            return await response.json();
        } catch (error) {
            console.error('Error fetching available plugins:', error);
            return [];
        }
    }

    async getInstalledPlugins() {
        try {
            const response = await fetch(`${API_BASE_URL}/plugins/installed`);
            if (!response.ok) throw new Error('Failed to fetch installed plugins');
            return await response.json();
        } catch (error) {
            console.error('Error fetching installed plugins:', error);
            return [];
        }
    }

    async installPlugin(pluginId) {
        try {
            const response = await fetch(`${API_BASE_URL}/plugins/install`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ plugin_id: pluginId })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Installation failed');
            }

            return await response.json();
        } catch (error) {
            console.error('Error installing plugin:', error);
            throw error;
        }
    }

    async uninstallPlugin(pluginId) {
        try {
            const response = await fetch(`${API_BASE_URL}/plugins/uninstall/${pluginId}`, {
                method: 'POST'
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Uninstall failed');
            }

            return await response.json();
        } catch (error) {
            console.error('Error uninstalling plugin:', error);
            throw error;
        }
    }

    async importZenMLStack(stackName) {
        try {
            const response = await fetch(`${API_BASE_URL}/plugins/import-stack`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ stack_name: stackName })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Import failed');
            }

            return await response.json();
        } catch (error) {
            console.error('Error importing stack:', error);
            throw error;
        }
    }
}

export const pluginService = new PluginService();
