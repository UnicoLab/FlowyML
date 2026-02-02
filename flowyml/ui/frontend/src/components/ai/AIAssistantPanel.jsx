import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Send, Trash2, Loader2, AlertCircle, Cpu, Zap, ChevronDown, Sparkles, Eye, EyeOff, Layers, FileText, Terminal, BarChart2 } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { useAIAssistant } from '../../contexts/AIAssistantContext';

// Custom markdown components for chat messages
const MarkdownComponents = {
    code({ node, inline, className, children, ...props }) {
        const match = /language-(\w+)/.exec(className || '');
        const language = match ? match[1] : '';

        if (!inline && language) {
            return (
                <div className="relative group my-3">
                    <div className="absolute right-2 top-2 opacity-0 group-hover:opacity-100 transition-opacity">
                        <button
                            onClick={() => navigator.clipboard.writeText(String(children))}
                            className="px-2 py-1 text-xs bg-slate-700 hover:bg-slate-600 rounded text-slate-300"
                        >
                            Copy
                        </button>
                    </div>
                    <SyntaxHighlighter
                        style={oneDark}
                        language={language}
                        PreTag="div"
                        className="rounded-lg text-sm !my-0"
                        {...props}
                    >
                        {String(children).replace(/\n$/, '')}
                    </SyntaxHighlighter>
                </div>
            );
        }

        return (
            <code className="bg-slate-700/50 px-1.5 py-0.5 rounded text-sm text-purple-300" {...props}>
                {children}
            </code>
        );
    },
    p({ children }) {
        return <p className="mb-2 last:mb-0">{children}</p>;
    },
    ul({ children }) {
        return <ul className="list-disc list-inside mb-2 space-y-1">{children}</ul>;
    },
    ol({ children }) {
        return <ol className="list-decimal list-inside mb-2 space-y-1">{children}</ol>;
    },
    strong({ children }) {
        return <strong className="font-semibold text-white">{children}</strong>;
    },
    a({ href, children }) {
        return (
            <a href={href} className="text-purple-400 hover:text-purple-300 underline" target="_blank" rel="noopener noreferrer">
                {children}
            </a>
        );
    }
};

// Chat message component
function ChatMessage({ message, isStreaming }) {
    const isUser = message.role === 'user';

    return (
        <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4`}
        >
            <div className={`max-w-[85%] ${isUser ? 'order-2' : 'order-1'}`}>
                {!isUser && (
                    <div className="flex items-center gap-2 mb-1">
                        <div className="w-6 h-6 rounded-full bg-gradient-to-br from-purple-500 to-indigo-600 flex items-center justify-center">
                            <Sparkles size={12} className="text-white" />
                        </div>
                        <span className="text-xs font-medium text-slate-400">FlowyML Assistant</span>
                    </div>
                )}
                <div
                    className={`rounded-2xl px-4 py-3 ${isUser
                        ? 'bg-gradient-to-r from-purple-600 to-indigo-600 text-white'
                        : 'bg-slate-800/80 text-slate-200 border border-slate-700/50'
                        }`}
                >
                    {isUser ? (
                        <p className="text-sm">{message.content}</p>
                    ) : (
                        <div className="text-sm prose prose-invert prose-sm max-w-none">
                            <ReactMarkdown
                                remarkPlugins={[remarkGfm]}
                                components={MarkdownComponents}
                            >
                                {message.content}
                            </ReactMarkdown>
                            {isStreaming && (
                                <span className="inline-block w-2 h-4 bg-purple-400 animate-pulse ml-1" />
                            )}
                        </div>
                    )}
                </div>
            </div>
        </motion.div>
    );
}

// Model loading progress component
function LoadingProgress({ progress, status }) {
    return (
        <div className="p-6 text-center">
            <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-gradient-to-br from-purple-500/20 to-indigo-500/20 flex items-center justify-center">
                <Loader2 className="w-8 h-8 text-purple-400 animate-spin" />
            </div>
            <h3 className="text-lg font-semibold text-white mb-2">Loading AI Model</h3>
            <p className="text-sm text-slate-400 mb-4">{status}</p>
            <div className="w-full bg-slate-700 rounded-full h-2 overflow-hidden">
                <motion.div
                    className="h-full bg-gradient-to-r from-purple-500 to-indigo-500"
                    initial={{ width: 0 }}
                    animate={{ width: `${progress}%` }}
                    transition={{ duration: 0.3 }}
                />
            </div>
            <p className="text-xs text-slate-500 mt-2">{progress}% complete</p>
        </div>
    );
}

// WebGPU not supported fallback
function WebGPUNotSupported() {
    return (
        <div className="p-6 text-center">
            <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-amber-500/20 flex items-center justify-center">
                <AlertCircle className="w-8 h-8 text-amber-400" />
            </div>
            <h3 className="text-lg font-semibold text-white mb-2">WebGPU Not Available</h3>
            <p className="text-sm text-slate-400 mb-4">
                Your browser doesn't support WebGPU, which is required for local AI inference.
            </p>
            <div className="bg-slate-800/50 rounded-lg p-4 text-left text-sm">
                <p className="text-slate-300 font-medium mb-2">Try one of these browsers:</p>
                <ul className="text-slate-400 space-y-1">
                    <li>• Chrome 113+ (recommended)</li>
                    <li>• Edge 113+</li>
                    <li>• Safari 18.2+ (macOS/iOS)</li>
                </ul>
            </div>
        </div>
    );
}

// Context indicator component
function ContextIndicator({ context, enabled, onToggle }) {
    if (!context) return null;

    const pageType = context.pageType || 'page';
    const icons = {
        run: <Layers size={12} />,
        pipeline: <FileText size={12} />,
        logs: <Terminal size={12} />,
        metrics: <BarChart2 size={12} />
    };

    return (
        <div className="px-4 py-2 bg-gradient-to-r from-purple-900/40 to-indigo-900/40 border-b border-slate-700/50">
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-xs">
                    <span className="text-slate-400">Context:</span>
                    <div className={`flex items-center gap-1.5 px-2 py-1 rounded-full ${enabled ? 'bg-purple-500/20 text-purple-300' : 'bg-slate-700/50 text-slate-500'}`}>
                        {icons[pageType] || <Eye size={12} />}
                        <span className="font-medium capitalize">{pageType}</span>
                        {context.pipelineName && (
                            <span className="text-slate-400">• {context.pipelineName}</span>
                        )}
                    </div>
                </div>
                <button
                    onClick={onToggle}
                    className={`flex items-center gap-1.5 px-2 py-1 rounded-lg text-xs font-medium transition-all ${enabled
                        ? 'bg-purple-500/20 text-purple-300 hover:bg-purple-500/30'
                        : 'bg-slate-700/50 text-slate-400 hover:bg-slate-700'
                        }`}
                    title={enabled ? 'Disable context sharing' : 'Enable context sharing'}
                >
                    {enabled ? <Eye size={12} /> : <EyeOff size={12} />}
                    {enabled ? 'Sharing' : 'Off'}
                </button>
            </div>
            {enabled && context.totalSteps !== undefined && (
                <div className="flex items-center gap-3 mt-2 text-xs text-slate-400">
                    <span>{context.totalSteps} steps</span>
                    {context.failedSteps > 0 && (
                        <span className="text-red-400">{context.failedSteps} failed</span>
                    )}
                    {context.metrics?.length > 0 && (
                        <span>{context.metrics.length} metrics</span>
                    )}
                </div>
            )}
        </div>
    );
}

// Main panel component
export function AIAssistantPanel() {
    const {
        isOpen,
        setIsOpen,
        messages,
        isLoading,
        isModelLoading,
        loadProgress,
        loadStatus,
        error,
        isWebGPUSupported,
        initEngine,
        sendMessage,
        cancelGeneration,
        clearChat,
        pipelineContext,
        contextEnabled,
        setContextEnabled
    } = useAIAssistant();

    const [input, setInput] = useState('');
    const messagesEndRef = useRef(null);
    const inputRef = useRef(null);

    // Initialize engine when panel opens
    useEffect(() => {
        if (isOpen && isWebGPUSupported && !isModelLoading) {
            initEngine();
        }
    }, [isOpen, isWebGPUSupported, isModelLoading, initEngine]);

    // Auto-scroll to bottom
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    // Focus input when panel opens
    useEffect(() => {
        if (isOpen && !isModelLoading && isWebGPUSupported) {
            setTimeout(() => inputRef.current?.focus(), 100);
        }
    }, [isOpen, isModelLoading, isWebGPUSupported]);

    // Handle send
    const handleSend = () => {
        if (!input.trim() || isLoading) return;
        sendMessage(input.trim());
        setInput('');
    };

    // Handle keyboard shortcuts
    const handleKeyDown = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    // Escape to close
    useEffect(() => {
        const handleEscape = (e) => {
            if (e.key === 'Escape' && isOpen) {
                setIsOpen(false);
            }
        };
        window.addEventListener('keydown', handleEscape);
        return () => window.removeEventListener('keydown', handleEscape);
    }, [isOpen, setIsOpen]);

    return (
        <AnimatePresence>
            {isOpen && (
                <>
                    {/* Backdrop */}
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        onClick={() => setIsOpen(false)}
                        className="fixed inset-0 bg-black/40 backdrop-blur-sm z-40"
                    />

                    {/* Panel */}
                    <motion.div
                        initial={{ opacity: 0, x: 400, scale: 0.95 }}
                        animate={{ opacity: 1, x: 0, scale: 1 }}
                        exit={{ opacity: 0, x: 400, scale: 0.95 }}
                        transition={{ type: 'spring', damping: 25, stiffness: 300 }}
                        className="fixed right-4 top-4 bottom-4 w-[420px] max-w-[calc(100vw-32px)] bg-slate-900/95 backdrop-blur-xl rounded-2xl shadow-2xl border border-slate-700/50 z-50 flex flex-col overflow-hidden"
                    >
                        {/* Header */}
                        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-700/50 bg-gradient-to-r from-purple-900/30 to-indigo-900/30">
                            <div className="flex items-center gap-3">
                                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-purple-500/30">
                                    <Sparkles size={20} className="text-white" />
                                </div>
                                <div>
                                    <h2 className="font-semibold text-white">FlowyML Assistant</h2>
                                    <div className="flex items-center gap-1.5 text-xs text-slate-400">
                                        <Cpu size={10} />
                                        <span>Powered by WebGPU</span>
                                        <span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
                                    </div>
                                </div>
                            </div>
                            <div className="flex items-center gap-2">
                                <button
                                    onClick={clearChat}
                                    className="p-2 hover:bg-slate-700/50 rounded-lg transition-colors"
                                    title="Clear chat"
                                >
                                    <Trash2 size={18} className="text-slate-400" />
                                </button>
                                <button
                                    onClick={() => setIsOpen(false)}
                                    className="p-2 hover:bg-slate-700/50 rounded-lg transition-colors"
                                >
                                    <X size={18} className="text-slate-400" />
                                </button>
                            </div>
                        </div>

                        {/* Context Indicator */}
                        <ContextIndicator
                            context={pipelineContext}
                            enabled={contextEnabled}
                            onToggle={() => setContextEnabled(!contextEnabled)}
                        />

                        {/* Content */}
                        <div className="flex-1 overflow-y-auto">
                            {isWebGPUSupported === false ? (
                                <WebGPUNotSupported />
                            ) : isModelLoading ? (
                                <LoadingProgress progress={loadProgress} status={loadStatus} />
                            ) : error ? (
                                <div className="p-6 text-center">
                                    <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-red-500/20 flex items-center justify-center">
                                        <AlertCircle className="w-8 h-8 text-red-400" />
                                    </div>
                                    <h3 className="text-lg font-semibold text-white mb-2">Error Loading Model</h3>
                                    <p className="text-sm text-slate-400">{error}</p>
                                    <button
                                        onClick={initEngine}
                                        className="mt-4 px-4 py-2 bg-purple-600 hover:bg-purple-500 rounded-lg text-sm font-medium transition-colors"
                                    >
                                        Retry
                                    </button>
                                </div>
                            ) : (
                                <div className="p-4">
                                    {messages.map((msg, idx) => (
                                        <ChatMessage
                                            key={idx}
                                            message={msg}
                                            isStreaming={isLoading && idx === messages.length - 1 && msg.role === 'assistant'}
                                        />
                                    ))}
                                    <div ref={messagesEndRef} />
                                </div>
                            )}
                        </div>

                        {/* Input area */}
                        {isWebGPUSupported && !isModelLoading && !error && (
                            <div className="p-4 border-t border-slate-700/50 bg-slate-800/50">
                                <div className="flex items-end gap-2">
                                    <div className="flex-1 relative">
                                        <textarea
                                            ref={inputRef}
                                            value={input}
                                            onChange={(e) => setInput(e.target.value)}
                                            onKeyDown={handleKeyDown}
                                            placeholder="Ask about FlowyML, pipelines, optimization..."
                                            rows={1}
                                            className="w-full bg-slate-700/50 border border-slate-600/50 rounded-xl px-4 py-3 text-sm text-white placeholder-slate-400 resize-none focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all"
                                            style={{ minHeight: '44px', maxHeight: '120px' }}
                                        />
                                    </div>
                                    <button
                                        onClick={isLoading ? cancelGeneration : handleSend}
                                        disabled={!input.trim() && !isLoading}
                                        className={`p-3 rounded-xl transition-all ${isLoading
                                            ? 'bg-red-500 hover:bg-red-400'
                                            : input.trim()
                                                ? 'bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 shadow-lg shadow-purple-500/30'
                                                : 'bg-slate-700/50 cursor-not-allowed'
                                            }`}
                                    >
                                        {isLoading ? (
                                            <X size={20} className="text-white" />
                                        ) : (
                                            <Send size={20} className="text-white" />
                                        )}
                                    </button>
                                </div>
                                <p className="text-xs text-slate-500 mt-2 text-center">
                                    <Zap size={10} className="inline mr-1" />
                                    Running locally • Your data never leaves this device
                                </p>
                            </div>
                        )}
                    </motion.div>
                </>
            )}
        </AnimatePresence>
    );
}

export default AIAssistantPanel;
