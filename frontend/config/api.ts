import { Platform } from 'react-native';

const getApiBaseUrl = () => {
  // Check for manual override via environment variable
  if (__DEV__) {
    const manualIp = process.env.EXPO_PUBLIC_API_IP;
    if (manualIp) {
      return `http://${manualIp}:3000/api`;
    }
  }

  // For Android emulator
  if (__DEV__ && Platform.OS === 'android') {
    return 'http://10.0.2.2:3000/api';
  }
  // For iOS simulator and web
  return 'http://192.168.2.58:3000/api';
};

export const API_BASE_URL = getApiBaseUrl();

export const API_CONFIG = {
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 10000,
};

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
