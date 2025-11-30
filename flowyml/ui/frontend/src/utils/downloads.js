import { getBaseUrl } from './api';

export const downloadArtifactById = async (artifactId) => {
    if (!artifactId) {
        return;
    }

    const baseUrl = await getBaseUrl();
    const url = `${baseUrl}/api/assets/${artifactId}/download`;
    window.open(url, '_blank', 'noopener,noreferrer');
};
