import React from 'react';
import { router } from 'expo-router';
import { PlaceholderScreen } from '../../components/shared/PlaceholderScreen';

export default function ChatTabScreen() {
  return (
    <PlaceholderScreen
      title="Chat"
      description="Luồng chatbot chính đã được tách thành screen riêng theo Figma. Bạn có thể mở từ nút PT nổi ở Home hoặc từ đây."
      actionLabel="Open ChatBot"
      onAction={() => router.push('/chatbot')}
    />
  );
}
