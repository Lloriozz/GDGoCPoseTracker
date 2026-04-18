import React from 'react';
import { Stack } from 'expo-router';
import { AuthProvider } from '../contexts/AuthContext';
import { FloatingChatBubble } from '../components/chat/FloatingChatBubble';

export default function RootLayout() {
  return (
    <AuthProvider>
      <Stack screenOptions={{ headerShown: false }}>
        <Stack.Screen name="index" options={{ headerShown: false }} />
        <Stack.Screen name="login" />
        <Stack.Screen name="signup" />
        <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
        <Stack.Screen name="bicep-workout" />
        <Stack.Screen name="squat-workout" />
        <Stack.Screen name="workout" />
        <Stack.Screen name="pose-tracker" />
      </Stack>
      <FloatingChatBubble />
    </AuthProvider>
  );
}