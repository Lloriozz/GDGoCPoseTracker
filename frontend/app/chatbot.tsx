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
import { SafeAreaView, useSafeAreaInsets } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { router } from 'expo-router';
import { ChatBubble } from '../components/chat/ChatBubble';
import { ChatComposer } from '../components/chat/ChatComposer';
import { QuickActionButton } from '../components/chat/QuickActionButton';
import { LinearGradient } from 'expo-linear-gradient';
import { theme } from '../constants/theme';
import { sendChatMessage } from '../services/chat';
import { ChatUiMessage } from '../types/chat';
import { useAuth } from '../contexts/AuthContext';

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
  const { user } = useAuth();
  const [messages, setMessages] = useState<ChatUiMessage[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef<ScrollView | null>(null);
  const sessionId = useMemo(() => `mobile-session-${Date.now()}`, []);
  const userId = useMemo(() => user?.id || 'guest-user', [user?.id]);
  
  // Lấy insets của điện thoại (Tai thỏ, Dynamic Island, viền dưới) để tính toán chuẩn xác
  const insets = useSafeAreaInsets();

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
    // Cách giải quyết 1: Chỉ lấy insets top, bỏ bottom đi vì KeyboardAvoidingView sẽ lo việc đẩy nội dung lên
    <SafeAreaView style={styles.safe} edges={['top']}>
      <KeyboardAvoidingView
        style={styles.container}
        // Cách giải quyết 2: Thêm offset để iOS không đẩy quá tay
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
        keyboardVerticalOffset={Platform.OS === 'ios' ? 10 : 0}
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
          // Cách giải quyết 3: Đảm bảo khoảng trống dưới cùng cuộn đủ rộng để không bị che
          contentContainerStyle={[styles.scrollContent, { paddingBottom: Math.max(20, insets.bottom + 10) }]}
          keyboardShouldPersistTaps="handled"
          onContentSizeChange={() => scrollRef.current?.scrollToEnd({ animated: true })}
          showsVerticalScrollIndicator={false}
        >
          <Text style={styles.greeting}>Xin chào {user?.username || user?.email?.split('@')[0] || 'bạn'}!</Text>
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

        {/* Khung chat composer giờ sẽ được đẩy lên một cách an toàn */}
        <ChatComposer value={input} onChangeText={setInput} onSend={() => sendMessage()} loading={loading} />

        {/* Cách giải quyết 4: Đệm thêm không gian cho phần bottom (thanh home bar của iPhone) nếu chưa mở bàn phím */}
        {Platform.OS === 'ios' && <View style={{ height: insets.bottom }} />}
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: {
    flex: 1,
    backgroundColor: '#0F0F0F', // Chỉnh lại background thành màu cố định thay vì dựa vào theme để tránh viền sáng
  },
  container: {
    flex: 1,
  },
  header: {
    height: 60, // Giảm bớt chiều cao header một chút để có thêm không gian cho màn nhỏ
    paddingHorizontal: 12,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    zIndex: 10, // Đảm bảo header đè lên gradient
  },
  headerIcon: {
    width: 36,
    height: 36, // Xác định rõ kích thước vùng bấm
    alignItems: 'center',
    justifyContent: 'center',
  },
  headerTitle: {
    color: theme.colors.text,
    fontSize: 18, // Giảm một xíu để nhìn thanh thoát hơn
    fontWeight: '700',
  },
  scroll: {
    flex: 1,
  },
  scrollContent: {
    paddingHorizontal: 16, // Căn lề rộng ra một chút
    paddingTop: 10,
    flexGrow: 1, // Quan trọng: Đảm bảo nội dung luôn push xuống nếu ít tin nhắn
  },
  greeting: {
    fontSize: 20,
    color: theme.colors.text,
    fontWeight: '400',
  },
  hero: {
    marginTop: 8,
    color: theme.colors.text,
    fontSize: 26, // Chỉnh lại size chữ một xíu cho màn nhỏ
    fontWeight: '800',
    lineHeight: 34,
    maxWidth: '90%', // Đừng fix cứng kích thước, dùng % cho linh hoạt
  },
  quickActionGroup: {
    marginTop: 24,
  },
  messageList: {
    marginTop: 16,
    paddingBottom: 10,
  },
  resetButton: {
    alignSelf: 'center', // Đưa ra giữa nhìn sẽ cân đối hơn
    marginTop: 20,
    marginBottom: 10, // Cho thêm margin bottom
    paddingHorizontal: 20,
    paddingVertical: 12,
    borderRadius: 24,
    backgroundColor: 'rgba(255, 94, 14, 0.15)', // Sửa lại màu nền nút reset xíu cho hợp với gradient
  },
  resetText: {
    color: '#FF5E0E', // Thay bằng màu chính xác
    fontSize: 14,
    fontWeight: '700',
  },
});