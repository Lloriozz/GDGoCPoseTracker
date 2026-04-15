import React from 'react';
import { Image, ImageSourcePropType, StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import { shadows, theme } from '../../constants/theme';

type WorkoutCardProps = {
  image: ImageSourcePropType;
  title: string;
  subtitle: string;
  onPress?: () => void;
};

export function WorkoutCard({ image, title, subtitle, onPress }: WorkoutCardProps) {
  return (
    <TouchableOpacity activeOpacity={0.9} onPress={onPress} style={[styles.card, shadows.card]}>
      <Image source={image} style={styles.image} resizeMode="cover" />
      <View style={styles.body}>
        <Text style={styles.title}>{title}</Text>
        <Text style={styles.subtitle}>{subtitle}</Text>
      </View>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  card: {
    width: 210,
    borderRadius: theme.radius.md,
    backgroundColor: theme.colors.white,
    borderWidth: 1,
    borderColor: theme.colors.border,
    overflow: 'hidden',
  },
  image: {
    width: '100%',
    height: 130,
  },
  body: {
    paddingHorizontal: theme.spacing.md,
    paddingVertical: 14,
  },
  title: {
    color: theme.colors.text,
    fontSize: 17,
    fontWeight: '700',
  },
  subtitle: {
    marginTop: 4,
    color: theme.colors.muted,
    fontSize: 14,
  },
});
