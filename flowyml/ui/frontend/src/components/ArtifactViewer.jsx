import React, { useState, useEffect } from 'react';
import { fetchApi } from '../utils/api';
import { Light as SyntaxHighlighter } from 'react-syntax-highlighter';
import json from 'react-syntax-highlighter/dist/esm/languages/hljs/json';
import python from 'react-syntax-highlighter/dist/esm/languages/hljs/python';
import { docco } from 'react-syntax-highlighter/dist/esm/styles/hljs';
import {
    Image,
    FileText,
    Code,
    Table as TableIcon,
    AlertCircle
} from 'lucide-react';

SyntaxHighlighter.registerLanguage('json', json);
SyntaxHighlighter.registerLanguage('python', python);

export function ArtifactViewer({ artifact }) {
    const [content, setContent] = useState(null);
    const [contentType, setContentType] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    useEffect(() => {
        if (!artifact?.artifact_id) return;
        fetchContent();
    }, [artifact]);

    const fetchContent = async () => {
        setLoading(true);
        setError(null);
        try {
            // First try to infer type from artifact metadata
            let type = 'text';
            if (artifact.path) {
                const ext = artifact.path.split('.').pop().toLowerCase();
                if (['png', 'jpg', 'jpeg', 'svg', 'gif'].includes(ext)) type = 'image';
                else if (['json'].includes(ext)) type = 'json';
                else if (['csv', 'tsv'].includes(ext)) type = 'table';
            }

            // If it's a value-based artifact (no file path), use the value directly if possible
            if (!artifact.path && artifact.value) {
                // If value looks like a path to an image (unlikely but possible in some setups)
                // Otherwise assuming text/json
                try {
                    const parsed = JSON.parse(artifact.value);
                    setContent(parsed);
                    setContentType('json');
                } catch {
                    setContent(artifact.value);
                    setContentType('text');
                }
                setLoading(false);
                return;
            }

            // Fetch actual content from backend
            const res = await fetchApi(`/api/assets/${artifact.artifact_id}/content`);
            if (!res.ok) {
                // If content fetch fails, fallback to 'value' preview if available
                if (artifact.value) {
                    setContent(artifact.value);
                    setContentType('text');
                } else {
                    throw new Error('Failed to load artifact content');
                }
            } else {
                const blob = await res.blob();
                const mime = blob.type;

                if (mime.startsWith('image/') || type === 'image') {
                    const url = URL.createObjectURL(blob);
                    setContent(url);
                    setContentType('image');
                } else if (mime.includes('json') || type === 'json') {
                    const text = await blob.text();
                    setContent(JSON.parse(text));
                    setContentType('json');
                } else {
                    const text = await blob.text();
                    setContent(text);
                    setContentType('text');
                }
            }

        } catch (err) {
            console.error('Failed to load artifact:', err);
            setError('Could not load full content. Showing metadata only.');
        } finally {
            setLoading(false);
        }
    };

    if (loading) {
        return (
            <div className="flex flex-col items-center justify-center p-12 text-slate-400">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-500 mb-2"></div>
                <p className="text-sm">Loading content...</p>
            </div>
        );
    }

    if (error) {
        return (
            <div className="flex flex-col items-center justify-center p-8 text-rose-500 bg-rose-50 rounded-lg border border-rose-100">
                <AlertCircle size={24} className="mb-2" />
                <p className="text-sm font-medium">{error}</p>
            </div>
        );
    }

    if (contentType === 'image') {
        return (
            <div className="flex flex-col items-center">
                <div className="relative rounded-lg overflow-hidden border border-slate-200 shadow-sm bg-slate-50">
                    <img src={content} alt={artifact.name} className="max-w-full max-h-[60vh] object-contain" />
                </div>
                <p className="text-xs text-slate-500 mt-2 flex items-center gap-1">
                    <Image size={12} />
                    Image Preview
                </p>
            </div>
        );
    }

    if (contentType === 'json') {
        return (
            <div className="rounded-lg overflow-hidden border border-slate-200 shadow-sm">
                <div className="bg-slate-50 px-3 py-2 border-b border-slate-200 flex items-center gap-2">
                    <Code size={14} className="text-slate-500" />
                    <span className="text-xs font-semibold text-slate-600">JSON Viewer</span>
                </div>
                <div className="max-h-[50vh] overflow-y-auto">
                    <SyntaxHighlighter
                        language="json"
                        style={docco}
                        customStyle={{ margin: 0, padding: '1rem', fontSize: '0.85rem' }}
                    >
                        {JSON.stringify(content, null, 2)}
                    </SyntaxHighlighter>
                </div>
            </div>
        );
    }

    // Default Text Viewer
    return (
        <div className="rounded-lg overflow-hidden border border-slate-200 shadow-sm">
            <div className="bg-slate-50 px-3 py-2 border-b border-slate-200 flex items-center gap-2">
                <FileText size={14} className="text-slate-500" />
                <span className="text-xs font-semibold text-slate-600">Text Content</span>
            </div>
            <pre className="p-4 bg-white text-slate-800 text-xs font-mono overflow-x-auto whitespace-pre-wrap max-h-[50vh] overflow-y-auto">
                {typeof content === 'string' ? content : JSON.stringify(content, null, 2)}
            </pre>
        </div>
    );
}
