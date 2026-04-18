import React from 'react';
import { Stack, usePathname } from 'expo-router';
import { FloatingChatBubble } from '../components/chat/FloatingChatBubble';
import { AuthProvider } from '../contexts/AuthContext';
import { ChatbotProvider } from '../contexts/ChatbotContext';

export default function RootLayout() {
  const pathname = usePathname();
  const shouldShowFloatingChat = pathname !== '/chat';

  return (
    <AuthProvider>
      <ChatbotProvider>
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
        {shouldShowFloatingChat ? <FloatingChatBubble /> : null}
      </ChatbotProvider>
    </AuthProvider>
  );
}
