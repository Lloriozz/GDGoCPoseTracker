import React, { useMemo, useRef, useState } from 'react';
import {
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { router } from 'expo-router';
import { ChatBubble } from '../components/chat/ChatBubble';
import { ChatComposer } from '../components/chat/ChatComposer';
import { QuickActionButton } from '../components/chat/QuickActionButton';
import { LinearGradient } from 'expo-linear-gradient';
import { theme } from '../constants/theme';
import { sendChatMessage } from '../services/chat';
import { ChatUiMessage } from '../types/chat';

const quickActions = [
  {
    label: 'Tạo lịch tập',
    prompt: 'Tạo lịch tập cho tôi.',
  },
  {
    label: 'Tạo thực đơn',
    prompt: 'Tạo thực đơn cho tôi.',
  },
  {
    label: 'Tính calo giúp tôi',
    prompt: 'Tính calo giúp tôi.',
  },
];

function buildMessage(role: 'assistant' | 'user', text: string, meta?: string): ChatUiMessage {
  return {
    id: `${role}-${Date.now()}-${Math.random().toString(16).slice(2)}`,
    role,
    text,
    meta,
  };
}

export default function ChatbotScreen() {
  const [messages, setMessages] = useState<ChatUiMessage[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef<ScrollView | null>(null);
  const sessionId = useMemo(() => `mobile-session-${Date.now()}`, []);
  const userId = useMemo(() => 'mobile-user-001', []);

  const sendMessage = async (rawText?: string) => {
    const nextText = (rawText ?? input).trim();
    if (!nextText || loading) {
      return;
    }

    const userMessage = buildMessage('user', nextText);
    setMessages((current) => [...current, userMessage]);
    setInput('');
    setLoading(true);

    try {
      const response = await sendChatMessage({
        user_id: userId,
        session_id: sessionId,
        message: nextText,
      });

      const meta = response.missing_fields.length
        ? `Cần thêm: ${response.missing_fields.join(', ')}`
        : response.intent.replaceAll('_', ' ');

      setMessages((current) => [
        ...current,
        buildMessage('assistant', response.reply, meta),
      ]);
    } catch (error) {
      const fallback =
        error instanceof Error && error.message
          ? error.message
          : 'Hiện chưa kết nối được backend chat.';

      setMessages((current) => [
        ...current,
        buildMessage(
          'assistant',
          `Mình chưa gửi được tin nhắn tới backend. ${fallback}`,
          'Lỗi kết nối'
        ),
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <SafeAreaView style={styles.safe} edges={['top', 'bottom']}>
      <KeyboardAvoidingView
        style={styles.container}
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      >
        <LinearGradient
          colors={['rgba(255, 94, 14, 0.25)', '#0F0F0F', '#0F0F0F']}
          locations={[0, 0.35, 1]}
          style={StyleSheet.absoluteFillObject}
        />
        <View style={styles.header}>
          <TouchableOpacity activeOpacity={0.8} onPress={() => router.back()} style={styles.headerIcon}>
            <Ionicons name="arrow-back-outline" size={28} color={theme.colors.text} />
          </TouchableOpacity>
          <Text style={styles.headerTitle}>PoseTracker</Text>
          <TouchableOpacity activeOpacity={0.8} style={styles.headerIcon}>
            <Ionicons name="menu-outline" size={30} color={theme.colors.text} />
          </TouchableOpacity>
        </View>

        <ScrollView
          ref={scrollRef}
          style={styles.scroll}
          contentContainerStyle={styles.scrollContent}
          keyboardShouldPersistTaps="handled"
          onContentSizeChange={() => scrollRef.current?.scrollToEnd({ animated: true })}
          showsVerticalScrollIndicator={false}
        >
          <Text style={styles.greeting}>Xin chào Huy!</Text>
          <Text style={styles.hero}>Chúng ta nên bắt đầu từ đâu nhỉ?</Text>

          {messages.length === 0 ? (
            <View style={styles.quickActionGroup}>
              {quickActions.map((item) => (
                <QuickActionButton key={item.label} label={item.label} onPress={() => sendMessage(item.prompt)} />
              ))}
            </View>
          ) : (
            <View style={styles.messageList}>
              {messages.map((message) => (
                <ChatBubble key={message.id} message={message} />
              ))}
            </View>
          )}

          {messages.length > 0 ? (
            <TouchableOpacity activeOpacity={0.88} onPress={() => setMessages([])} style={styles.resetButton}>
              <Text style={styles.resetText}>Bắt đầu lại</Text>
            </TouchableOpacity>
          ) : null}
        </ScrollView>

        <ChatComposer value={input} onChangeText={setInput} onSend={() => sendMessage()} loading={loading} />
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: {
    flex: 1,
    backgroundColor: theme.colors.background,
  },
  container: {
    flex: 1,
    backgroundColor: 'transparent',
  },
  header: {
    height: 68,
    paddingHorizontal: 12,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  headerIcon: {
    width: 36,
    alignItems: 'center',
    justifyContent: 'center',
  },
  headerTitle: {
    color: theme.colors.text,
    fontSize: 20,
    fontWeight: '700',
  },
  scroll: {
    flex: 1,
  },
  scrollContent: {
    paddingHorizontal: 14,
    paddingTop: 18,
    paddingBottom: 20,
  },
  greeting: {
    fontSize: 20,
    color: theme.colors.text,
    fontWeight: '400',
  },
  hero: {
    marginTop: 8,
    color: theme.colors.text,
    fontSize: 28,
    fontWeight: '800',
    lineHeight: 38,
    maxWidth: 290,
  },
  quickActionGroup: {
    marginTop: 22,
  },
  messageList: {
    marginTop: 24,
  },
  resetButton: {
    alignSelf: 'flex-start',
    marginTop: 14,
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderRadius: theme.radius.round,
    backgroundColor: theme.colors.primarySoft,
  },
  resetText: {
    color: theme.colors.primary,
    fontSize: 14,
    fontWeight: '700',
  },
});
