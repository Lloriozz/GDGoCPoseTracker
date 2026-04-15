import { Platform } from 'react-native';

const DEFAULT_PORT = '8000';

function buildBaseUrl() {
  const manualHost = process.env.EXPO_PUBLIC_API_HOST?.trim();
  const manualPort = process.env.EXPO_PUBLIC_API_PORT?.trim() || DEFAULT_PORT;

  if (manualHost) {
    return `http://${manualHost}:${manualPort}`;
  }

  if (Platform.OS === 'web' && typeof window !== 'undefined') {
    const host = window.location.hostname || 'localhost';
    return `http://${host}:${DEFAULT_PORT}`;
  }

  if (__DEV__ && Platform.OS === 'android') {
    return `http://10.0.2.2:${DEFAULT_PORT}`;
  }

  return `http://localhost:${DEFAULT_PORT}`;
}

export const API_BASE_URL = buildBaseUrl();
