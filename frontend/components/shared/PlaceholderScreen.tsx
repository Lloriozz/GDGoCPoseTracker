import React from 'react';
import { SafeAreaView } from 'react-native-safe-area-context';
import { StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import { theme } from '../../constants/theme';

type PlaceholderScreenProps = {
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
};

export function PlaceholderScreen({
  title,
  description,
  actionLabel,
  onAction,
}: PlaceholderScreenProps) {
  return (
    <SafeAreaView style={styles.safe}>
      <View style={styles.container}>
        <Text style={styles.title}>{title}</Text>
        <Text style={styles.description}>{description}</Text>
        {actionLabel && onAction ? (
          <TouchableOpacity activeOpacity={0.88} onPress={onAction} style={styles.button}>
            <Text style={styles.buttonText}>{actionLabel}</Text>
          </TouchableOpacity>
        ) : null}
      </View>
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
    paddingHorizontal: 24,
    alignItems: 'center',
    justifyContent: 'center',
  },
  title: {
    fontSize: 30,
    fontWeight: '800',
    color: theme.colors.text,
    textAlign: 'center',
  },
  description: {
    marginTop: 12,
    fontSize: 16,
    lineHeight: 24,
    color: theme.colors.muted,
    textAlign: 'center',
  },
  button: {
    marginTop: 24,
    borderRadius: theme.radius.round,
    backgroundColor: theme.colors.primary,
    paddingHorizontal: 20,
    paddingVertical: 12,
  },
  buttonText: {
    color: theme.colors.white,
    fontSize: 15,
    fontWeight: '700',
  },
});
