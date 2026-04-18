import { Platform } from 'react-native';

const getApiBaseUrl = () => {
  // Check for environment variable override (production or dev)
  const backendUrl = process.env.EXPO_PUBLIC_BACKEND_URL;
  if (backendUrl) {
    return backendUrl;
  }

  // Check for manual IP override via environment variable
  if (__DEV__) {
    const manualIp = process.env.EXPO_PUBLIC_API_IP;
    if (manualIp) {
      return `http://${manualIp}:3000/api`;
    }
  }

  // For Android emulator
  if (__DEV__ && Platform.OS === 'android') {
    return 'http://124.197.18.178:3000/api';
  }
  // For iOS simulator and web
  return 'http://124.197.18.178:3000/api';
};

const getChatApiBaseUrl = () => {
  // Check for environment variable override (production or dev)
  const chatUrl = process.env.EXPO_PUBLIC_CHAT_URL;
  if (chatUrl) {
    return chatUrl;
  }

  // Check for manual IP override via environment variable
  if (__DEV__) {
    const manualIp = process.env.EXPO_PUBLIC_API_IP;
    if (manualIp) {
      return `http://${manualIp}:8000`;
    }
  }

  // For Android device/emulator
  if (__DEV__ && Platform.OS === 'android') {
    return 'http://124.197.18.178:8000';
  }
  // For iOS simulator and web
  return 'http://124.197.18.178:8000';
};

export const API_BASE_URL = getApiBaseUrl();
export const CHAT_API_BASE_URL = getChatApiBaseUrl();

export const API_CONFIG = {
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 10000,
};