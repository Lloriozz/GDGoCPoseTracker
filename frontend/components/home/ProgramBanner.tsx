import React from 'react';
import {
  ImageBackground,
  ImageSourcePropType,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import { shadows, theme } from '../../constants/theme';

type ProgramBannerProps = {
  category: string;
  title: string;
  image: ImageSourcePropType;
  onPress?: () => void;
};

export function ProgramBanner({ category, title, image, onPress }: ProgramBannerProps) {
  return (
    <View style={[styles.wrapper, shadows.card]}>
      <ImageBackground source={image} resizeMode="cover" imageStyle={styles.image} style={styles.image}>
        <View style={styles.overlay} />
        <View style={styles.content}>
          <Text style={styles.category}>{category}</Text>
          <Text style={styles.title}>{title}</Text>
          <TouchableOpacity activeOpacity={0.88} onPress={onPress} style={styles.button}>
            <Text style={styles.buttonText}>Start Program</Text>
          </TouchableOpacity>
        </View>
      </ImageBackground>
    </View>
  );
}

const styles = StyleSheet.create({
  wrapper: {
    height: 200,
    borderRadius: 22,
    overflow: 'hidden',
    marginBottom: 18,
  },
  image: {
    flex: 1,
    borderRadius: 22,
    justifyContent: 'flex-end',
  },
  overlay: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: 'rgba(0,0,0,0.46)',
  },
  content: {
    padding: theme.spacing.lg,
  },
  category: {
    color: 'rgba(255,255,255,0.72)',
    fontSize: 13,
    fontWeight: '500',
  },
  title: {
    marginTop: 4,
    marginBottom: 14,
    color: theme.colors.white,
    fontSize: 30,
    fontWeight: '800',
    lineHeight: 34,
  },
  button: {
    alignSelf: 'flex-start',
    backgroundColor: theme.colors.primary,
    borderRadius: theme.radius.round,
    paddingHorizontal: 18,
    paddingVertical: 10,
  },
  buttonText: {
    color: theme.colors.white,
    fontSize: 14,
    fontWeight: '700',
  },
});
