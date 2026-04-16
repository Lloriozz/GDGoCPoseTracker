import React from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { shadows, theme } from '../../constants/theme';
import { ChatUiMessage } from '../../types/chat';

type ChatBubbleProps = {
  message: ChatUiMessage;
};

export function ChatBubble({ message }: ChatBubbleProps) {
  const isUser = message.role === 'user';

  return (
    <View style={[styles.wrapper, isUser ? styles.userWrapper : styles.assistantWrapper]}>
      <View style={[styles.bubble, isUser ? styles.userBubble : [styles.assistantBubble, shadows.soft]]}>
        <Text style={[styles.text, isUser ? styles.userText : styles.assistantText]}>{message.text}</Text>
      </View>
      {message.meta ? <Text style={[styles.meta, isUser ? styles.metaRight : styles.metaLeft]}>{message.meta}</Text> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  wrapper: {
    marginBottom: 14,
  },
  userWrapper: {
    alignItems: 'flex-end',
  },
  assistantWrapper: {
    alignItems: 'flex-start',
  },
  bubble: {
    maxWidth: '84%',
    borderRadius: 24,
    paddingHorizontal: 16,
    paddingVertical: 14,
  },
  userBubble: {
    backgroundColor: theme.colors.primary,
    borderBottomRightRadius: 8,
  },
  assistantBubble: {
    backgroundColor: '#1C1C1E',
    borderBottomLeftRadius: 8,
  },
  text: {
    fontSize: 16,
    lineHeight: 22,
  },
  userText: {
    color: '#FFF',
  },
  assistantText: {
    color: '#FFF',
  },
  meta: {
    marginTop: 4,
    fontSize: 12,
    color: theme.colors.muted,
  },
  metaLeft: {
    marginLeft: 8,
  },
  metaRight: {
    marginRight: 8,
  },
});
