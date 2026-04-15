import { Platform } from 'react-native';

export const theme = {
  colors: {
    primary: '#FF7A22',
    primarySoft: '#FFF1E7',
    background: '#FFFFFF',
    surface: '#F4F4F4',
    text: '#111111',
    muted: '#7B7B7B',
    border: '#ECECEC',
    white: '#FFFFFF',
    shadow: '#000000',
  },
  radius: {
    md: 20,
    lg: 24,
    xl: 30,
    round: 999,
  },
  spacing: {
    sm: 10,
    md: 16,
    lg: 20,
    xl: 24,
  },
};

export const shadows = {
  soft: Platform.select({
    ios: {
      shadowColor: theme.colors.shadow,
      shadowOffset: { width: 0, height: 8 },
      shadowOpacity: 0.08,
      shadowRadius: 16,
    },
    android: {
      elevation: 4,
    },
    default: {},
  }),
  card: Platform.select({
    ios: {
      shadowColor: theme.colors.shadow,
      shadowOffset: { width: 0, height: 4 },
      shadowOpacity: 0.1,
      shadowRadius: 8,
    },
    android: {
      elevation: 4,
    },
    default: {},
  }),
  floating: Platform.select({
    ios: {
      shadowColor: theme.colors.primary,
      shadowOffset: { width: 0, height: 8 },
      shadowOpacity: 0.28,
      shadowRadius: 12,
    },
    android: {
      elevation: 10,
    },
    default: {},
  }),
};
