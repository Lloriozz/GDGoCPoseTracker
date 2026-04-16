import React from 'react';
import { StyleSheet, Text, TouchableOpacity } from 'react-native';
import { shadows, theme } from '../../constants/theme';

type QuickActionButtonProps = {
  label: string;
  onPress: () => void;
};

export function QuickActionButton({ label, onPress }: QuickActionButtonProps) {
  return (
    <TouchableOpacity activeOpacity={0.9} onPress={onPress} style={[styles.button, shadows.soft]}>
      <Text style={styles.label}>{label}</Text>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  button: {
    alignSelf: 'flex-start',
    backgroundColor: theme.colors.white,
    borderRadius: theme.radius.round,
    paddingHorizontal: 20,
    paddingVertical: 14,
    marginBottom: 16,
  },
  label: {
    color: '#333333',
    fontSize: 18,
    fontWeight: '500',
  },
});
