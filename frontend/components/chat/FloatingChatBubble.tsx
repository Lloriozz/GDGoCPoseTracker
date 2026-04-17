import React, { useMemo, useRef, useState } from 'react';
import {
  KeyboardAvoidingView,
  Modal,
  Platform,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
  Animated,
  PanResponder,
  Dimensions,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { ChatBubble } from './ChatBubble';
import { ChatComposer } from './ChatComposer';
import { QuickActionButton } from './QuickActionButton';
import { LinearGradient } from 'expo-linear-gradient';
import { theme } from '../../constants/theme';
import { sendChatMessage } from '../../services/chat';
import { ChatUiMessage } from '../../types/chat';

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

export function FloatingChatBubble() {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<ChatUiMessage[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef<ScrollView | null>(null);
  const sessionId = useMemo(() => `mobile-session-${Date.now()}`, []);
  const userId = useMemo(() => 'mobile-user-001', []);

  const pan = useRef(new Animated.ValueXY()).current;
  const panResponder = useRef(
    PanResponder.create({
      onMoveShouldSetPanResponder: (_, gestureState) => {
        return Math.abs(gestureState.dx) > 5 || Math.abs(gestureState.dy) > 5;
      },
      onPanResponderGrant: () => {
        pan.setOffset({
          x: (pan.x as any)._value,
          y: (pan.y as any)._value,
        });
        pan.setValue({ x: 0, y: 0 });
      },
      onPanResponderMove: Animated.event(
        [null, { dx: pan.x, dy: pan.y }],
        { useNativeDriver: false }
      ),
      onPanResponderRelease: () => {
        pan.flattenOffset();
        const SCREEN_WIDTH = Dimensions.get('window').width;
        const SCREEN_HEIGHT = Dimensions.get('window').height;
        const BUBBLE_SIZE = 60;
        const INITIAL_RIGHT = 20;
        const INITIAL_BOTTOM = 100;

        const originalX = SCREEN_WIDTH - INITIAL_RIGHT - BUBBLE_SIZE;
        const currentAbsoluteX = originalX + (pan.x as any)._value;
        const isLeftHalf = currentAbsoluteX + BUBBLE_SIZE / 2 < SCREEN_WIDTH / 2;

        let targetX = 0;
        if (isLeftHalf) {
          targetX = 20 - originalX;
        } else {
          targetX = 0;
        }

        // Limit the Y bounds
        const originalY = SCREEN_HEIGHT - INITIAL_BOTTOM - BUBBLE_SIZE;
        let targetY = (pan.y as any)._value;
        const currentAbsoluteY = originalY + targetY;

        if (currentAbsoluteY < 60) {
          targetY = 60 - originalY;
        } else if (currentAbsoluteY > SCREEN_HEIGHT - 120) {
          targetY = (SCREEN_HEIGHT - 120) - originalY;
        }

        Animated.spring(pan, {
          toValue: { x: targetX, y: targetY },
          friction: 6,
          tension: 40,
          useNativeDriver: false,
        }).start();
      },
    })
  ).current;

  const handleOpenModal = () => {
    setIsOpen(true);
    setLoading(false);
  };

  const sendMessage = async (rawText?: string) => {
    const nextText = (rawText ?? input).trim();
    console.log('sendMessage called with:', nextText, 'loading:', loading);
    if (!nextText || loading) {
      console.log('sendMessage aborted: empty or loading');
      return;
    }

    const userMessage = buildMessage('user', nextText);
    setMessages((current) => [...current, userMessage]);
    setInput('');
    setLoading(true);
    console.log('Sending to backend...');

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
    <>
      {/* Floating Bubble Button */}
      <Animated.View
        style={[
          styles.bubbleContainer,
          { transform: [{ translateX: pan.x }, { translateY: pan.y }] },
        ]}
        {...panResponder.panHandlers}
      >
        <TouchableOpacity
          activeOpacity={0.8}
          onPress={handleOpenModal}
          style={styles.bubble}
        >
          <Ionicons name="chatbubble" size={28} color="#fff" />
          {messages.length > 0 && (
            <View style={styles.badge}>
              <Text style={styles.badgeText}>{messages.length}</Text>
            </View>
          )}
        </TouchableOpacity>
      </Animated.View>

      {/* Chat Modal */}
      <Modal
        visible={isOpen}
        animationType="slide"
        onRequestClose={() => setIsOpen(false)}
      >
        <SafeAreaView style={styles.modalContainer}>
          {/* Header */}
          <View style={styles.header}>
            <TouchableOpacity
              activeOpacity={0.8}
              onPress={() => setIsOpen(false)}
              style={styles.closeButton}
            >
              <Ionicons name="close" size={28} color={theme.colors.text} />
            </TouchableOpacity>
            <Text style={styles.headerTitle}>PoseTracker Chat</Text>
            <View style={styles.headerSpacer} />
          </View>

          {/* Chat Content */}
          <KeyboardAvoidingView
            style={styles.chatContainer}
            behavior={Platform.OS === 'ios' ? 'padding' : undefined}
          >
            <LinearGradient
              colors={['rgba(255, 94, 14, 0.25)', '#0F0F0F', '#0F0F0F']}
              locations={[0, 0.35, 1]}
              style={StyleSheet.absoluteFillObject}
            />
            <ScrollView
              ref={scrollRef}
              style={styles.scroll}
              contentContainerStyle={styles.scrollContent}
              keyboardShouldPersistTaps="handled"
              onContentSizeChange={() => scrollRef.current?.scrollToEnd({ animated: true })}
              showsVerticalScrollIndicator={false}
            >
              <Text style={styles.greeting}>Xin chào!</Text>
              <Text style={styles.hero}>Chúng ta nên bắt đầu từ đâu nhỉ?</Text>

              {messages.length === 0 ? (
                <View style={styles.quickActionGroup}>
                  {quickActions.map((item) => (
                    <QuickActionButton
                      key={item.label}
                      label={item.label}
                      onPress={() => sendMessage(item.prompt)}
                    />
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
                <TouchableOpacity
                  activeOpacity={0.88}
                  onPress={() => setMessages([])}
                  style={styles.resetButton}
                >
                  <Text style={styles.resetText}>Bắt đầu lại</Text>
                </TouchableOpacity>
              ) : null}
            </ScrollView>

            <ChatComposer
              value={input}
              onChangeText={setInput}
              onSend={() => sendMessage()}
              loading={loading}
            />
          </KeyboardAvoidingView>
        </SafeAreaView>
      </Modal>
    </>
  );
}

const styles = StyleSheet.create({
  bubbleContainer: {
    position: 'absolute',
    bottom: 100,
    right: 20,
    zIndex: 1000,
  },
  bubble: {
    width: 60,
    height: 60,
    borderRadius: 30,
    backgroundColor: theme.colors.primary,
    justifyContent: 'center',
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 8,
  },
  badge: {
    position: 'absolute',
    top: -5,
    right: -5,
    minWidth: 20,
    height: 20,
    borderRadius: 10,
    backgroundColor: '#FF3B30',
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 6,
  },
  badgeText: {
    color: '#fff',
    fontSize: 12,
    fontWeight: '700',
  },
  modalContainer: {
    flex: 1,
    backgroundColor: theme.colors.background,
  },
  header: {
    height: 60,
    paddingHorizontal: 16,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: 'transparent',
    borderBottomWidth: 1,
    borderBottomColor: '#333',
  },
  closeButton: {
    width: 40,
    height: 40,
    alignItems: 'center',
    justifyContent: 'center',
  },
  headerTitle: {
    color: theme.colors.text,
    fontSize: 18,
    fontWeight: '700',
  },
  headerSpacer: {
    width: 40,
  },
  chatContainer: {
    flex: 1,
    backgroundColor: 'transparent',
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
    fontSize: 18,
    color: theme.colors.text,
    fontWeight: '400',
  },
  hero: {
    marginTop: 8,
    color: theme.colors.text,
    fontSize: 24,
    fontWeight: '800',
    lineHeight: 32,
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
