import { createContext, useContext, useState, useCallback, useEffect, useRef } from 'react';
import * as webllm from '@mlc-ai/web-llm';

// FlowyML System Prompt - comprehensive knowledge base for the AI assistant
const FLOWYML_SYSTEM_PROMPT = `You are FlowyML Assistant, an expert AI advisor for the FlowyML ML pipeline framework. You help users optimize their pipelines, debug issues, and follow best practices.

## About FlowyML
FlowyML is an enterprise-grade ML pipeline framework that combines Python simplicity with powerful MLOps features:
- Zero-boilerplate orchestration with pure Python (no YAML/DSLs)
- Intelligent caching (code hash, input hash) to skip unchanged steps
- First-class Assets: Dataset, Model, Metrics, FeatureSet with auto-lineage
- Context auto-injection for parameters
- Step grouping for efficient execution
- Dynamic workflows with conditional logic (If/then/else)
- Human-in-the-loop approval gates
- Built-in experiment tracking and model leaderboard
- LLM/GenAI observability with @trace_llm decorator
- Data drift detection
- Pipeline scheduling and notifications

## Key Concepts
1. **Steps**: Use @step decorator with inputs/outputs. Cache with cache="input_hash" or cache="code_hash"
2. **Pipelines**: Create with Pipeline(name, context=ctx), add steps with .add_step()
3. **Context**: Define params with context(lr=0.01), auto-injected to steps
4. **Assets**: Dataset.create(), Model.create(), Metrics.create() - tracked automatically
5. **Execution Groups**: Group steps with execution_group="name" to share resources

## Best Practices
- Use caching strategically: input_hash for data processing, code_hash for model training
- Group related steps in execution_group for efficiency
- Use conditional execution (If/then/else) for dynamic workflows
- Track experiments with Experiment class
- Monitor data drift with detect_drift()
- Use @trace_llm for LLM observability

When users share logs, metrics, or pipeline context, analyze them and provide:
1. Specific, actionable recommendations
2. Code examples when helpful
3. Explanations of why certain optimizations work
4. Links to relevant FlowyML features

Be concise but thorough. Format responses with markdown for clarity.`;

const AIAssistantContext = createContext(null);

// Model configuration - using a smaller, faster model for WebGPU
const MODEL_ID = "Qwen2.5-1.5B-Instruct-q4f16_1-MLC"; // Fast, lightweight model

export function AIAssistantProvider({ children }) {
    const [isOpen, setIsOpen] = useState(false);
    const [messages, setMessages] = useState([]);
    const [isLoading, setIsLoading] = useState(false);
    const [isModelLoading, setIsModelLoading] = useState(false);
    const [loadProgress, setLoadProgress] = useState(0);
    const [loadStatus, setLoadStatus] = useState('');
    const [error, setError] = useState(null);
    const [isWebGPUSupported, setIsWebGPUSupported] = useState(null);
    const [pipelineContext, setPipelineContext] = useState(null);
    const [contextEnabled, setContextEnabled] = useState(true); // User toggle for context sharing

    const engineRef = useRef(null);
    const abortControllerRef = useRef(null);

    // Check WebGPU support on mount
    useEffect(() => {
        const checkWebGPU = async () => {
            try {
                if (!navigator.gpu) {
                    setIsWebGPUSupported(false);
                    return;
                }
                const adapter = await navigator.gpu.requestAdapter();
                setIsWebGPUSupported(!!adapter);
            } catch (e) {
                console.warn('WebGPU check failed:', e);
                setIsWebGPUSupported(false);
            }
        };
        checkWebGPU();
    }, []);

    // Initialize WebLLM engine
    const initEngine = useCallback(async () => {
        if (engineRef.current || !isWebGPUSupported) return;

        setIsModelLoading(true);
        setError(null);
        setLoadStatus('Initializing...');

        try {
            const engine = await webllm.CreateMLCEngine(MODEL_ID, {
                initProgressCallback: (progress) => {
                    setLoadProgress(Math.round(progress.progress * 100));
                    setLoadStatus(progress.text || 'Loading model...');
                }
            });

            engineRef.current = engine;
            setLoadStatus('Model ready!');
            setIsModelLoading(false);

            // Add welcome message
            setMessages([{
                role: 'assistant',
                content: `👋 Hi! I'm your FlowyML AI Assistant, running **locally** in your browser using WebGPU.

I have access to your current pipeline context and can help you:
- 🔧 **Optimize** your pipelines for better performance
- 🐛 **Debug** failing steps and understand errors
- 📊 **Analyze** run metrics and suggest improvements
- 💡 **Learn** FlowyML best practices and features

What would you like help with today?`
            }]);

        } catch (e) {
            console.error('Failed to initialize WebLLM:', e);
            setError(e.message || 'Failed to load AI model');
            setIsModelLoading(false);
        }
    }, [isWebGPUSupported]);

    // Send message and get streaming response
    const sendMessage = useCallback(async (content) => {
        if (!engineRef.current || isLoading) return;

        // Add user message
        const userMessage = { role: 'user', content };
        setMessages(prev => [...prev, userMessage]);
        setIsLoading(true);

        // Create abort controller for cancellation
        abortControllerRef.current = new AbortController();

        try {
            // Build context-aware prompt (only if enabled and context exists)
            let contextInfo = '';
            if (contextEnabled && pipelineContext) {
                contextInfo = `\n\n## Current Page Context\nThe user is currently viewing: ${pipelineContext.pageType || 'unknown page'}\n\n### Context Data\n${JSON.stringify(pipelineContext, null, 2)}\n\nUse this context to provide specific, actionable advice about the current pipeline run.\n`;
            }

            const systemMessage = FLOWYML_SYSTEM_PROMPT + contextInfo;

            // Build message history for context
            const chatMessages = [
                { role: 'system', content: systemMessage },
                ...messages.slice(-6), // Keep last 6 messages for context
                userMessage
            ];

            // Add placeholder for assistant response
            const assistantMessage = { role: 'assistant', content: '' };
            setMessages(prev => [...prev, assistantMessage]);

            // Stream the response
            const asyncGenerator = await engineRef.current.chat.completions.create({
                messages: chatMessages,
                temperature: 0.7,
                max_tokens: 1024,
                stream: true
            });

            let fullContent = '';
            for await (const chunk of asyncGenerator) {
                if (abortControllerRef.current?.signal.aborted) break;

                const delta = chunk.choices[0]?.delta?.content || '';
                fullContent += delta;

                // Update the last message with streamed content
                setMessages(prev => {
                    const updated = [...prev];
                    updated[updated.length - 1] = { role: 'assistant', content: fullContent };
                    return updated;
                });
            }

        } catch (e) {
            if (e.name !== 'AbortError') {
                console.error('Chat error:', e);
                setMessages(prev => [...prev, {
                    role: 'assistant',
                    content: `❌ Error: ${e.message || 'Failed to generate response'}`
                }]);
            }
        } finally {
            setIsLoading(false);
            abortControllerRef.current = null;
        }
    }, [messages, pipelineContext, contextEnabled, isLoading]);

    // Cancel current generation
    const cancelGeneration = useCallback(() => {
        if (abortControllerRef.current) {
            abortControllerRef.current.abort();
        }
    }, []);

    // Clear chat history
    const clearChat = useCallback(() => {
        setMessages([{
            role: 'assistant',
            content: '🗑️ Chat cleared. How can I help you with FlowyML?'
        }]);
    }, []);

    // Update pipeline context (called from other components)
    const updateContext = useCallback((context) => {
        setPipelineContext(context);
    }, []);

    const value = {
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
        updateContext,
        pipelineContext,
        contextEnabled,
        setContextEnabled
    };

    return (
        <AIAssistantContext.Provider value={value}>
            {children}
        </AIAssistantContext.Provider>
    );
}

export function useAIAssistant() {
    const context = useContext(AIAssistantContext);
    if (!context) {
        throw new Error('useAIAssistant must be used within AIAssistantProvider');
    }
    return context;
}
