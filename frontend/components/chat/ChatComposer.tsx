import React from 'react';
import { ActivityIndicator, StyleSheet, TextInput, TouchableOpacity, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { theme } from '../../constants/theme';

type ChatComposerProps = {
  value: string;
  onChangeText: (text: string) => void;
  onSend: () => void;
  loading?: boolean;
};

export function ChatComposer({ value, onChangeText, onSend, loading = false }: ChatComposerProps) {
  const canSend = value.trim().length > 0 && !loading;

  return (
    <View style={styles.wrapper}>
      <TouchableOpacity activeOpacity={0.8} style={styles.sideButton}>
        <Ionicons name="add" size={34} color="#707070" />
      </TouchableOpacity>
      <View style={styles.inputShell}>
        <TextInput
          value={value}
          onChangeText={onChangeText}
          placeholder="Hỏi ChatBot"
          placeholderTextColor="#676767"
          style={styles.input}
          multiline
        />
        <TouchableOpacity activeOpacity={0.8} onPress={canSend ? onSend : undefined} style={styles.trailingButton}>
          {loading ? (
            <ActivityIndicator color={theme.colors.primary} size="small" />
          ) : canSend ? (
            <Ionicons name="send" size={22} color={theme.colors.primary} />
          ) : (
            <Ionicons name="mic-outline" size={28} color="#383838" />
          )}
        </TouchableOpacity>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  wrapper: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 10,
    paddingTop: 10,
    paddingBottom: 10,
    backgroundColor: theme.colors.white,
    borderTopWidth: 1,
    borderTopColor: theme.colors.border,
    gap: 10,
  },
  sideButton: {
    width: 42,
    height: 42,
    borderRadius: 21,
    backgroundColor: '#D9D9D9',
    alignItems: 'center',
    justifyContent: 'center',
  },
  inputShell: {
    flex: 1,
    minHeight: 50,
    maxHeight: 120,
    borderRadius: theme.radius.round,
    backgroundColor: theme.colors.surface,
    flexDirection: 'row',
    alignItems: 'flex-end',
    paddingLeft: 16,
    paddingRight: 10,
    paddingVertical: 4,
  },
  input: {
    flex: 1,
    paddingVertical: 10,
    fontSize: 18,
    color: theme.colors.text,
    maxHeight: 96,
  },
  trailingButton: {
    width: 40,
    height: 40,
    alignItems: 'center',
    justifyContent: 'center',
  },
});
