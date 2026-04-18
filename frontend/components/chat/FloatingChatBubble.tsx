import React from 'react';
import { StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { router } from 'expo-router';
import { theme } from '../../constants/theme';
import { useChatbot } from '../../contexts/ChatbotContext';

export function FloatingChatBubble() {
  const { messages } = useChatbot();

  return (
    <View pointerEvents="box-none" style={styles.bubbleContainer}>
      <TouchableOpacity
        activeOpacity={0.8}
        onPress={() => router.push('/chat')}
        style={styles.bubble}
      >
        <Ionicons name="chatbubble" size={28} color="#fff" />
        {messages.length > 0 ? (
          <View style={styles.badge}>
            <Text style={styles.badgeText}>{messages.length}</Text>
          </View>
        ) : null}
      </TouchableOpacity>
    </View>
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
});
