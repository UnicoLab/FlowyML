import { useState, useEffect } from 'react';

/**
 * Hook to detect WebGPU support in the browser.
 * Returns loading state while checking and final support status.
 */
export function useWebGPU() {
    const [isSupported, setIsSupported] = useState(null);
    const [isLoading, setIsLoading] = useState(true);
    const [gpuInfo, setGpuInfo] = useState(null);

    useEffect(() => {
        const checkWebGPU = async () => {
            try {
                // Check if WebGPU API is available
                if (!navigator.gpu) {
                    setIsSupported(false);
                    setIsLoading(false);
                    return;
                }

                // Try to get an adapter
                const adapter = await navigator.gpu.requestAdapter();
                if (!adapter) {
                    setIsSupported(false);
                    setIsLoading(false);
                    return;
                }

                // Get adapter info for debugging
                const info = await adapter.requestAdapterInfo?.() || {};
                setGpuInfo({
                    vendor: info.vendor || 'Unknown',
                    architecture: info.architecture || 'Unknown',
                    device: info.device || 'Unknown',
                    description: info.description || 'WebGPU Available'
                });

                setIsSupported(true);
            } catch (error) {
                console.warn('WebGPU detection error:', error);
                setIsSupported(false);
            } finally {
                setIsLoading(false);
            }
        };

        checkWebGPU();
    }, []);

    return { isSupported, isLoading, gpuInfo };
}

export default useWebGPU;
