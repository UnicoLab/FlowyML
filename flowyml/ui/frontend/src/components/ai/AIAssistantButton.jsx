import React from 'react';
import { motion } from 'framer-motion';
import { Sparkles, Brain } from 'lucide-react';
import { useAIAssistant } from '../../contexts/AIAssistantContext';

export function AIAssistantButton() {
    const { isOpen, setIsOpen, isLoading, isWebGPUSupported, isModelLoading } = useAIAssistant();

    // Don't render if WebGPU check is still loading
    if (isWebGPUSupported === null) return null;

    return (
        <motion.button
            initial={{ scale: 0, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ delay: 0.5, type: 'spring', stiffness: 300, damping: 20 }}
            onClick={() => setIsOpen(true)}
            className={`fixed bottom-6 right-6 z-30 group ${isOpen ? 'hidden' : ''}`}
        >
            {/* Animated glow effect */}
            <motion.div
                className="absolute inset-0 rounded-full bg-gradient-to-r from-purple-500 to-indigo-500 blur-xl opacity-50"
                animate={{
                    scale: isLoading || isModelLoading ? [1, 1.3, 1] : 1,
                    opacity: isLoading || isModelLoading ? [0.5, 0.8, 0.5] : 0.5
                }}
                transition={{
                    duration: 1.5,
                    repeat: isLoading || isModelLoading ? Infinity : 0,
                    ease: 'easeInOut'
                }}
            />

            {/* Main button */}
            <div className="relative w-14 h-14 rounded-full bg-gradient-to-br from-purple-600 to-indigo-600 shadow-xl shadow-purple-500/40 flex items-center justify-center transition-transform group-hover:scale-110">
                {isLoading || isModelLoading ? (
                    <motion.div
                        animate={{ rotate: 360 }}
                        transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
                    >
                        <Brain size={24} className="text-white" />
                    </motion.div>
                ) : (
                    <Sparkles size={24} className="text-white" />
                )}
            </div>

            {/* Tooltip */}
            <div className="absolute right-full mr-3 top-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none">
                <div className="bg-slate-800 text-white text-sm px-3 py-2 rounded-lg whitespace-nowrap shadow-lg border border-slate-700">
                    {!isWebGPUSupported
                        ? 'AI Assistant (WebGPU required)'
                        : isModelLoading
                            ? 'Loading AI...'
                            : 'Ask FlowyML Assistant'
                    }
                    <div className="absolute right-0 top-1/2 -translate-y-1/2 translate-x-1 w-2 h-2 bg-slate-800 rotate-45 border-r border-t border-slate-700" />
                </div>
            </div>

            {/* WebGPU warning indicator */}
            {!isWebGPUSupported && (
                <div className="absolute -top-1 -right-1 w-4 h-4 bg-amber-500 rounded-full flex items-center justify-center text-xs font-bold text-black">
                    !
                </div>
            )}
        </motion.button>
    );
}

export default AIAssistantButton;
