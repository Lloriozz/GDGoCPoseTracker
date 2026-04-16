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
    return 'http://192.168.0.109:3000/api';
  }
  // For iOS simulator and web
  return 'http://192.168.2.58:3000/api';
};

const getChatApiBaseUrl = () => {
  // Check for manual override via environment variable
  if (__DEV__) {
    const manualIp = process.env.EXPO_PUBLIC_API_IP;
    if (manualIp) {
      return `http://${manualIp}:8000`;
    }
  }

  // For Android device/emulator
  if (__DEV__ && Platform.OS === 'android') {
    return 'http://192.168.0.109:8000';
  }
  // For iOS simulator and web
  return 'http://127.0.0.1:8000';
};

export const API_BASE_URL = getApiBaseUrl();
export const CHAT_API_BASE_URL = getChatApiBaseUrl();

export const API_CONFIG = {
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 10000,
};