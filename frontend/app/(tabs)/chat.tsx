import React, { useRef } from 'react';
import {
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { SafeAreaView, useSafeAreaInsets } from 'react-native-safe-area-context';
import { ChatBubble } from '../../components/chat/ChatBubble';
import { ChatComposer } from '../../components/chat/ChatComposer';
import { QuickActionButton } from '../../components/chat/QuickActionButton';
import { theme } from '../../constants/theme';
import { useAuth } from '../../contexts/AuthContext';
import { useChatbot } from '../../contexts/ChatbotContext';

export default function ChatScreen() {
  const { user } = useAuth();
  const { input, loading, messages, quickActions, resetConversation, sendMessage, setInput } =
    useChatbot();
  const insets = useSafeAreaInsets();
  const scrollRef = useRef<ScrollView | null>(null);
  const greetingName = user?.username || user?.email?.split('@')[0] || 'bạn';

  return (
    <SafeAreaView style={styles.safe} edges={['top']}>
      <KeyboardAvoidingView
        style={styles.container}
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
        keyboardVerticalOffset={Platform.OS === 'ios' ? 10 : 0}
      >
        <LinearGradient
          colors={['rgba(255, 94, 14, 0.25)', '#0F0F0F', '#0F0F0F']}
          locations={[0, 0.35, 1]}
          style={StyleSheet.absoluteFillObject}
        />

        <View style={styles.header}>
          <Text style={styles.headerTitle}>PoseTracker Chat</Text>
        </View>

        <ScrollView
          ref={scrollRef}
          style={styles.scroll}
          contentContainerStyle={[
            styles.scrollContent,
            { paddingBottom: Math.max(20, insets.bottom + 10) },
          ]}
          keyboardShouldPersistTaps="handled"
          onContentSizeChange={() => scrollRef.current?.scrollToEnd({ animated: true })}
          showsVerticalScrollIndicator={false}
        >
          <Text style={styles.greeting}>{`Xin chào ${greetingName}!`}</Text>
          <Text style={styles.hero}>Chúng ta nên bắt đầu từ đâu nhỉ?</Text>

          {messages.length === 0 ? (
            <View style={styles.quickActionGroup}>
              {quickActions.map((item) => (
                <QuickActionButton
                  key={item.label}
                  label={item.label}
                  onPress={() => void sendMessage(item.prompt)}
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
              onPress={resetConversation}
              style={styles.resetButton}
            >
              <Text style={styles.resetText}>Bắt đầu lại</Text>
            </TouchableOpacity>
          ) : null}
        </ScrollView>

        <ChatComposer
          value={input}
          onChangeText={setInput}
          onSend={() => void sendMessage()}
          loading={loading}
        />

        {Platform.OS === 'ios' ? <View style={{ height: insets.bottom }} /> : null}
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: {
    flex: 1,
    backgroundColor: '#0F0F0F',
  },
  container: {
    flex: 1,
  },
  header: {
    height: 60,
    paddingHorizontal: 16,
    justifyContent: 'center',
  },
  headerTitle: {
    color: theme.colors.text,
    fontSize: 18,
    fontWeight: '700',
    textAlign: 'center',
  },
  scroll: {
    flex: 1,
  },
  scrollContent: {
    paddingHorizontal: 16,
    paddingTop: 10,
    flexGrow: 1,
  },
  greeting: {
    fontSize: 20,
    color: theme.colors.text,
    fontWeight: '400',
  },
  hero: {
    marginTop: 8,
    color: theme.colors.text,
    fontSize: 26,
    fontWeight: '800',
    lineHeight: 34,
    maxWidth: '90%',
  },
  quickActionGroup: {
    marginTop: 24,
  },
  messageList: {
    marginTop: 16,
    paddingBottom: 10,
  },
  resetButton: {
    alignSelf: 'center',
    marginTop: 20,
    marginBottom: 10,
    paddingHorizontal: 20,
    paddingVertical: 12,
    borderRadius: 24,
    backgroundColor: 'rgba(255, 94, 14, 0.15)',
  },
  resetText: {
    color: '#FF5E0E',
    fontSize: 14,
    fontWeight: '700',
  },
});
