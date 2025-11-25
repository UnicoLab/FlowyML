import React, { useState } from 'react';
import { Settings as SettingsIcon, Moon, Sun, Bell, Shield, Key, Save } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent } from './ui/Card';
import { Button } from './ui/Button';
import { motion } from 'framer-motion';

export function Settings() {
    const [theme, setTheme] = useState('light');
    const [notifications, setNotifications] = useState(true);
    const [apiKey, setApiKey] = useState('sk-........................');

    const container = {
        hidden: { opacity: 0 },
        show: {
            opacity: 1,
            transition: {
                staggerChildren: 0.1
            }
        }
    };

    const item = {
        hidden: { opacity: 0, y: 20 },
        show: { opacity: 1, y: 0 }
    };

    return (
        <motion.div
            initial="hidden"
            animate="show"
            variants={container}
            className="space-y-6 max-w-4xl mx-auto"
        >
            {/* Header */}
            <motion.div variants={item}>
                <div className="flex items-center gap-3 mb-2">
                    <div className="p-2 bg-gradient-to-br from-slate-700 to-slate-900 rounded-lg">
                        <SettingsIcon className="text-white" size={24} />
                    </div>
                    <h2 className="text-3xl font-bold text-slate-900 tracking-tight">Settings</h2>
                </div>
                <p className="text-slate-500 mt-2">Manage your workspace preferences and configurations.</p>
            </motion.div>

            {/* Appearance */}
            <motion.div variants={item}>
                <Card>
                    <CardHeader>
                        <div className="flex items-center gap-2">
                            <Sun size={20} className="text-slate-400" />
                            <CardTitle>Appearance</CardTitle>
                        </div>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div className="flex items-center justify-between">
                            <div>
                                <h4 className="font-medium text-slate-900">Theme</h4>
                                <p className="text-sm text-slate-500">Select your preferred interface theme.</p>
                            </div>
                            <div className="flex gap-2 bg-slate-100 p-1 rounded-lg">
                                <button
                                    onClick={() => setTheme('light')}
                                    className={`px-3 py-1.5 rounded-md text-sm font-medium transition-all ${theme === 'light'
                                            ? 'bg-white text-slate-900 shadow-sm'
                                            : 'text-slate-500 hover:text-slate-700'
                                        }`}
                                >
                                    <div className="flex items-center gap-2">
                                        <Sun size={14} />
                                        Light
                                    </div>
                                </button>
                                <button
                                    onClick={() => setTheme('dark')}
                                    className={`px-3 py-1.5 rounded-md text-sm font-medium transition-all ${theme === 'dark'
                                            ? 'bg-slate-800 text-white shadow-sm'
                                            : 'text-slate-500 hover:text-slate-700'
                                        }`}
                                >
                                    <div className="flex items-center gap-2">
                                        <Moon size={14} />
                                        Dark
                                    </div>
                                </button>
                            </div>
                        </div>
                    </CardContent>
                </Card>
            </motion.div>

            {/* Notifications */}
            <motion.div variants={item}>
                <Card>
                    <CardHeader>
                        <div className="flex items-center gap-2">
                            <Bell size={20} className="text-slate-400" />
                            <CardTitle>Notifications</CardTitle>
                        </div>
                    </CardHeader>
                    <CardContent>
                        <div className="flex items-center justify-between">
                            <div>
                                <h4 className="font-medium text-slate-900">Pipeline Alerts</h4>
                                <p className="text-sm text-slate-500">Receive notifications when pipelines fail or succeed.</p>
                            </div>
                            <label className="relative inline-flex items-center cursor-pointer">
                                <input
                                    type="checkbox"
                                    className="sr-only peer"
                                    checked={notifications}
                                    onChange={() => setNotifications(!notifications)}
                                />
                                <div className="w-11 h-6 bg-slate-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary-600"></div>
                            </label>
                        </div>
                    </CardContent>
                </Card>
            </motion.div>

            {/* API Configuration */}
            <motion.div variants={item}>
                <Card>
                    <CardHeader>
                        <div className="flex items-center gap-2">
                            <Key size={20} className="text-slate-400" />
                            <CardTitle>API Configuration</CardTitle>
                        </div>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div>
                            <label className="block text-sm font-medium text-slate-700 mb-1">
                                Flowy API Key
                            </label>
                            <div className="flex gap-2">
                                <input
                                    type="password"
                                    value={apiKey}
                                    onChange={(e) => setApiKey(e.target.value)}
                                    className="flex-1 px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent font-mono text-sm"
                                />
                                <Button variant="outline">Regenerate</Button>
                            </div>
                            <p className="text-xs text-slate-500 mt-1">
                                Used for authenticating CLI and SDK requests.
                            </p>
                        </div>
                    </CardContent>
                </Card>
            </motion.div>

            {/* Save Button */}
            <motion.div variants={item} className="flex justify-end pt-4">
                <Button className="flex items-center gap-2 px-6">
                    <Save size={18} />
                    Save Changes
                </Button>
            </motion.div>
        </motion.div>
    );
}
