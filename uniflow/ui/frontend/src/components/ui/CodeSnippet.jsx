import React, { useState } from 'react';
import { Copy, Check } from 'lucide-react';

export function CodeSnippet({ code, language = 'python', title, className = '' }) {
    const [copied, setCopied] = useState(false);

    const copyToClipboard = () => {
        navigator.clipboard.writeText(code);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    return (
        <div className={`relative group ${className}`}>
            {title && (
                <div className="flex items-center justify-between px-4 py-2 bg-slate-800 dark:bg-slate-900 border-b border-slate-700 rounded-t-lg">
                    <span className="text-sm font-medium text-slate-300">{title}</span>
                    <span className="text-xs text-slate-500 uppercase font-mono">{language}</span>
                </div>
            )}
            <div className="relative">
                <pre className={`p-4 bg-slate-900 dark:bg-slate-950 text-slate-100 text-sm font-mono overflow-x-auto leading-relaxed ${title ? '' : 'rounded-t-lg'} rounded-b-lg`}>
                    <code className={`language-${language}`}>{code}</code>
                </pre>
                <button
                    onClick={copyToClipboard}
                    className="absolute top-3 right-3 p-2 bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-slate-200 rounded-md transition-all opacity-0 group-hover:opacity-100"
                    title="Copy to clipboard"
                >
                    {copied ? <Check size={14} /> : <Copy size={14} />}
                </button>
            </div>
        </div>
    );
}

// Example usage in CodeTab:
// <CodeSnippet code={sourceCode} language="python" title="Step Source Code" />
