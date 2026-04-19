import { Platform } from 'react-native';

const DEFAULT_API_SCHEME = process.env.EXPO_PUBLIC_API_SCHEME ?? 'http';
const DEFAULT_BACKEND_PORT = process.env.EXPO_PUBLIC_BACKEND_PORT ?? '3000';
const DEFAULT_CHAT_PORT = process.env.EXPO_PUBLIC_CHAT_PORT ?? '8001';

const stripTrailingSlash = (value: string) => value.replace(/\/+$/, '');

const getConfiguredHost = () =>
  (process.env.EXPO_PUBLIC_API_HOST ?? process.env.EXPO_PUBLIC_API_IP ?? '').trim();

const getDefaultHost = () => {
  if (Platform.OS === 'android') {
    return '10.0.2.2';
  }

  return 'localhost';
};

const buildBaseUrl = (port: string, path = '') => {
  const host = getConfiguredHost() || getDefaultHost();
  return `${DEFAULT_API_SCHEME}://${host}:${port}${path}`;
};

const getApiBaseUrl = () => {
  const backendUrl = process.env.EXPO_PUBLIC_BACKEND_URL;
  if (backendUrl) {
    return stripTrailingSlash(backendUrl);
  }

  return stripTrailingSlash(buildBaseUrl(DEFAULT_BACKEND_PORT, '/api'));
};

const getChatApiBaseUrl = () => {
  const chatUrl = process.env.EXPO_PUBLIC_CHAT_URL;
  if (chatUrl) {
    return stripTrailingSlash(chatUrl);
  }

  return stripTrailingSlash(buildBaseUrl(DEFAULT_CHAT_PORT));
};

export const API_BASE_URL = getApiBaseUrl();
export const CHAT_API_BASE_URL = getChatApiBaseUrl();
export const CHAT_WS_BASE_URL = stripTrailingSlash(
  (process.env.EXPO_PUBLIC_CHAT_WS_URL ?? CHAT_API_BASE_URL).replace(/^http/i, 'ws')
);

export const API_CONFIG = {
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 10000,
};
