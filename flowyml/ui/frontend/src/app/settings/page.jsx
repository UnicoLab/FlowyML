import React, { useState, useEffect } from 'react';
import { fetchApi } from '../../utils/api';
import {
    Settings as SettingsIcon,
    Palette,
    Bell,
    Database,
    Shield,
    Globe,
    Zap,
    Clock,
    Save,
    RefreshCw,
    CheckCircle2,
    Moon,
    Sun,
    Monitor
} from 'lucide-react';
import { Card } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { Badge } from '../../components/ui/Badge';

export function Settings() {
    const [settings, setSettings] = useState({
        theme: 'system',
        notificationsEnabled: true,
        emailAlerts: false,
        autoRefresh: true,
        refreshInterval: 30,
        timezone: 'auto',
        dataRetention: 30,
        artifactUpload: false,
        debugMode: false
    });
    const [saved, setSaved] = useState(false);
    const [serverInfo, setServerInfo] = useState(null);

    useEffect(() => {
        fetchServerInfo();
    }, []);

    const fetchServerInfo = async () => {
        try {
            const response = await fetchApi('/api/execution/info');
            if (response.ok) {
                const data = await response.json();
                setServerInfo(data);
            }
        } catch (error) {
            console.error('Failed to fetch server info:', error);
        }
    };

    const handleSettingChange = (key, value) => {
        setSettings(prev => ({ ...prev, [key]: value }));
        setSaved(false);
    };

    const saveSettings = () => {
        // In a real app, this would save to the backend
        localStorage.setItem('flowyml_settings', JSON.stringify(settings));
        setSaved(true);
        setTimeout(() => setSaved(false), 3000);
    };

    const ThemeButton = ({ theme, icon: Icon, label }) => (
        <button
            onClick={() => handleSettingChange('theme', theme)}
            className={`flex flex-col items-center justify-center p-4 rounded-xl border-2 transition-all ${settings.theme === theme
                ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20'
                : 'border-slate-200 dark:border-slate-700 hover:border-slate-300 dark:hover:border-slate-600'
                }`}
        >
            <Icon size={24} className={settings.theme === theme ? 'text-primary-600' : 'text-slate-500'} />
            <span className={`mt-2 text-sm font-medium ${settings.theme === theme ? 'text-primary-600' : 'text-slate-600 dark:text-slate-400'
                }`}>
                {label}
            </span>
        </button>
    );

    return (
        <div className="p-6 max-w-4xl mx-auto space-y-6">
            {/* Header */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div>
                    <h1 className="text-3xl font-bold text-slate-900 dark:text-white flex items-center gap-3">
                        <div className="p-3 bg-gradient-to-br from-slate-600 to-slate-800 rounded-xl text-white">
                            <SettingsIcon size={28} />
                        </div>
                        Settings
                    </h1>
                    <p className="text-slate-500 dark:text-slate-400 mt-2">
                        Configure your FlowyML dashboard preferences
                    </p>
                </div>
                <Button
                    onClick={saveSettings}
                    className="flex items-center gap-2 bg-gradient-to-r from-primary-600 to-purple-600 hover:from-primary-700 hover:to-purple-700"
                >
                    {saved ? <CheckCircle2 size={16} /> : <Save size={16} />}
                    {saved ? 'Saved!' : 'Save Settings'}
                </Button>
            </div>

            {/* Appearance */}
            <Card>
                <div className="flex items-center gap-3 mb-6">
                    <div className="p-2 bg-purple-100 dark:bg-purple-900/20 rounded-lg">
                        <Palette className="text-purple-600 dark:text-purple-400" size={20} />
                    </div>
                    <div>
                        <h2 className="text-lg font-semibold text-slate-900 dark:text-white">Appearance</h2>
                        <p className="text-sm text-slate-500 dark:text-slate-400">Customize the look and feel</p>
                    </div>
                </div>

                <div className="grid grid-cols-3 gap-4">
                    <ThemeButton theme="light" icon={Sun} label="Light" />
                    <ThemeButton theme="dark" icon={Moon} label="Dark" />
                    <ThemeButton theme="system" icon={Monitor} label="System" />
                </div>
            </Card>

            {/* Notifications */}
            <Card>
                <div className="flex items-center gap-3 mb-6">
                    <div className="p-2 bg-blue-100 dark:bg-blue-900/20 rounded-lg">
                        <Bell className="text-blue-600 dark:text-blue-400" size={20} />
                    </div>
                    <div>
                        <h2 className="text-lg font-semibold text-slate-900 dark:text-white">Notifications</h2>
                        <p className="text-sm text-slate-500 dark:text-slate-400">Manage alert preferences</p>
                    </div>
                </div>

                <div className="space-y-4">
                    <label className="flex items-center justify-between cursor-not-allowed opacity-60">
                        <div>
                            <div className="font-medium text-slate-900 dark:text-white flex items-center gap-2">
                                Push Notifications
                                <Badge variant="secondary" className="text-xs">Coming Soon</Badge>
                            </div>
                            <div className="text-sm text-slate-500">Get notified about pipeline completions</div>
                        </div>
                        <input
                            type="checkbox"
                            checked={settings.notificationsEnabled}
                            disabled
                            className="w-5 h-5 rounded text-slate-400 cursor-not-allowed"
                        />
                    </label>

                    <label className="flex items-center justify-between cursor-not-allowed opacity-60">
                        <div>
                            <div className="font-medium text-slate-900 dark:text-white flex items-center gap-2">
                                Email Alerts
                                <Badge variant="secondary" className="text-xs">Coming Soon</Badge>
                            </div>
                            <div className="text-sm text-slate-500">Receive email for failed pipelines</div>
                        </div>
                        <input
                            type="checkbox"
                            checked={settings.emailAlerts}
                            disabled
                            className="w-5 h-5 rounded text-slate-400 cursor-not-allowed"
                        />
                    </label>
                </div>
            </Card>

            {/* Data & Storage */}
            <Card>
                <div className="flex items-center gap-3 mb-6">
                    <div className="p-2 bg-green-100 dark:bg-green-900/20 rounded-lg">
                        <Database className="text-green-600 dark:text-green-400" size={20} />
                    </div>
                    <div>
                        <h2 className="text-lg font-semibold text-slate-900 dark:text-white">Data & Storage</h2>
                        <p className="text-sm text-slate-500 dark:text-slate-400">Configure data handling</p>
                    </div>
                </div>

                <div className="space-y-4">
                    <label className="flex items-center justify-between cursor-not-allowed opacity-60">
                        <div>
                            <div className="font-medium text-slate-900 dark:text-white flex items-center gap-2">
                                Auto-upload Artifacts
                                <Badge variant="secondary" className="text-xs">Coming Soon</Badge>
                            </div>
                            <div className="text-sm text-slate-500">Automatically upload artifacts to remote storage</div>
                        </div>
                        <input
                            type="checkbox"
                            checked={settings.artifactUpload}
                            disabled
                            className="w-5 h-5 rounded text-slate-400 cursor-not-allowed"
                        />
                    </label>

                    <div className="opacity-60">
                        <div className="flex items-center justify-between mb-2">
                            <div>
                                <div className="font-medium text-slate-900 dark:text-white flex items-center gap-2">
                                    Data Retention
                                    <Badge variant="secondary" className="text-xs">Coming Soon</Badge>
                                </div>
                                <div className="text-sm text-slate-500">Days to keep run history</div>
                            </div>
                            <Badge variant="secondary">{settings.dataRetention} days</Badge>
                        </div>
                        <input
                            type="range"
                            min="7"
                            max="365"
                            value={settings.dataRetention}
                            disabled
                            className="w-full h-2 bg-slate-200 dark:bg-slate-700 rounded-lg appearance-none cursor-not-allowed"
                        />
                    </div>
                </div>
            </Card>

            {/* Performance */}
            <Card>
                <div className="flex items-center gap-3 mb-6">
                    <div className="p-2 bg-amber-100 dark:bg-amber-900/20 rounded-lg">
                        <Zap className="text-amber-600 dark:text-amber-400" size={20} />
                    </div>
                    <div>
                        <h2 className="text-lg font-semibold text-slate-900 dark:text-white">Performance</h2>
                        <p className="text-sm text-slate-500 dark:text-slate-400">Dashboard behavior settings</p>
                    </div>
                </div>

                <div className="space-y-4">
                    <label className="flex items-center justify-between cursor-pointer">
                        <div>
                            <div className="font-medium text-slate-900 dark:text-white">Auto-refresh Data</div>
                            <div className="text-sm text-slate-500">Automatically refresh dashboard data</div>
                        </div>
                        <input
                            type="checkbox"
                            checked={settings.autoRefresh}
                            onChange={(e) => handleSettingChange('autoRefresh', e.target.checked)}
                            className="w-5 h-5 rounded text-primary-600 focus:ring-primary-500"
                        />
                    </label>

                    {settings.autoRefresh && (
                        <div>
                            <div className="flex items-center justify-between mb-2">
                                <div>
                                    <div className="font-medium text-slate-900 dark:text-white">Refresh Interval</div>
                                    <div className="text-sm text-slate-500">Seconds between refreshes</div>
                                </div>
                                <Badge variant="secondary">{settings.refreshInterval}s</Badge>
                            </div>
                            <input
                                type="range"
                                min="10"
                                max="120"
                                step="10"
                                value={settings.refreshInterval}
                                onChange={(e) => handleSettingChange('refreshInterval', parseInt(e.target.value))}
                                className="w-full h-2 bg-slate-200 dark:bg-slate-700 rounded-lg appearance-none cursor-pointer"
                            />
                        </div>
                    )}

                    <label className="flex items-center justify-between cursor-pointer">
                        <div>
                            <div className="font-medium text-slate-900 dark:text-white">Debug Mode</div>
                            <div className="text-sm text-slate-500">Show verbose logging in console</div>
                        </div>
                        <input
                            type="checkbox"
                            checked={settings.debugMode}
                            onChange={(e) => handleSettingChange('debugMode', e.target.checked)}
                            className="w-5 h-5 rounded text-primary-600 focus:ring-primary-500"
                        />
                    </label>
                </div>
            </Card>

            {/* Server Info */}
            <Card className="bg-slate-50 dark:bg-slate-800/50">
                <div className="flex items-center gap-3 mb-6">
                    <div className="p-2 bg-slate-200 dark:bg-slate-700 rounded-lg">
                        <Globe className="text-slate-600 dark:text-slate-400" size={20} />
                    </div>
                    <div>
                        <h2 className="text-lg font-semibold text-slate-900 dark:text-white">Server Information</h2>
                        <p className="text-sm text-slate-500 dark:text-slate-400">FlowyML backend details</p>
                    </div>
                </div>

                <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                        <div className="text-slate-500 dark:text-slate-400">Version</div>
                        <div className="font-medium text-slate-900 dark:text-white">{serverInfo?.version || '0.1.0'}</div>
                    </div>
                    <div>
                        <div className="text-slate-500 dark:text-slate-400">Environment</div>
                        <div className="font-medium text-slate-900 dark:text-white">{serverInfo?.environment || 'Development'}</div>
                    </div>
                    <div>
                        <div className="text-slate-500 dark:text-slate-400">Database</div>
                        <div className="font-medium text-slate-900 dark:text-white">{serverInfo?.database || 'PostgreSQL'}</div>
                    </div>
                    <div>
                        <div className="text-slate-500 dark:text-slate-400">Uptime</div>
                        <div className="font-medium text-slate-900 dark:text-white">{serverInfo?.uptime || 'N/A'}</div>
                    </div>
                </div>
            </Card>

            {/* Footer Branding */}
            <div className="text-center pt-8 pb-4 border-t border-slate-200 dark:border-slate-700">
                <div className="flex items-center justify-center gap-2 text-slate-500 dark:text-slate-400">
                    <span className="text-sm">Made with ❤️ by</span>
                    <span className="font-semibold text-primary-600 dark:text-primary-400">UnicoLab</span>
                </div>
                <p className="text-xs text-slate-400 dark:text-slate-500 mt-1">
                    FlowyML - Next-generation MLOps Platform
                </p>
            </div>
        </div>
    );
}
