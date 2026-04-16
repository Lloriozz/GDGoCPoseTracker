import React from 'react';
import { StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import { shadows, theme } from '../../constants/theme';

type FloatingPtButtonProps = {
  onPress: () => void;
};

export function FloatingPtButton({ onPress }: FloatingPtButtonProps) {
  return (
    <View pointerEvents="box-none" style={styles.wrapper}>
      <TouchableOpacity activeOpacity={0.9} onPress={onPress} style={[styles.button, shadows.floating]}>
        <Text style={styles.label}>Pt</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  wrapper: {
    position: 'absolute',
    right: 14,
    bottom: 92,
  },
  button: {
    width: 54,
    height: 54,
    borderRadius: 27,
    backgroundColor: theme.colors.primary,
    borderWidth: 3,
    borderColor: theme.colors.white,
    alignItems: 'center',
    justifyContent: 'center',
  },
  label: {
    color: theme.colors.white,
    fontSize: 22,
    fontWeight: '700',
  },
});
