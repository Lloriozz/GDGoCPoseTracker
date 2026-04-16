import React from 'react';
import { Text, StyleSheet, View, Pressable, Alert } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useAuth } from '../../contexts/AuthContext';
import { router } from 'expo-router';
import { LinearGradient } from 'expo-linear-gradient';

export default function ProfileScreen() {
  const { user, token, logout } = useAuth();

  const handleLogout = () => {
    Alert.alert(
      'Logout',
      'Are you sure you want to logout?',
      [
        { text: 'Cancel', style: 'cancel' },
        { text: 'Logout', style: 'destructive', onPress: async () => {
          await logout();
          router.replace('/login' as any);
        }}
      ]
    );
  };

  if (!token) {
    return (
      <SafeAreaView style={styles.container}>
        <LinearGradient
          colors={['rgba(255, 94, 14, 0.25)', '#0F0F0F', '#0F0F0F']}
          locations={[0, 0.35, 1]}
          style={StyleSheet.absoluteFillObject}
        />
        <View style={styles.content}>
          <Ionicons name="person-circle-outline" size={100} color="#FF5E0E" />
          <Text style={styles.title}>Welcome to PoseTracker</Text>
          <Text style={styles.subtitle}>Sign in to access your profile</Text>
          <Pressable style={styles.button} onPress={() => router.push('/login' as any)}>
            <Text style={styles.buttonText}>Sign In</Text>
          </Pressable>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <LinearGradient
        colors={['rgba(255, 94, 14, 0.25)', '#0F0F0F', '#0F0F0F']}
        locations={[0, 0.35, 1]}
        style={StyleSheet.absoluteFillObject}
      />
      <View style={styles.content}>
        <View style={styles.avatar}>
          <Text style={styles.avatarText}>{user?.username?.[0] || user?.email?.[0] || 'U'}</Text>
        </View>
        <Text style={styles.title}>{user?.username || 'User'}</Text>
        <Text style={styles.email}>{user?.email}</Text>

        <View style={styles.menu}>
          <Pressable style={styles.menuItem} onPress={handleLogout}>
            <Ionicons name="log-out-outline" size={24} color="#FF5E0E" />
            <Text style={styles.menuItemText}>Logout</Text>
          </Pressable>
        </View>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { 
    flex: 1, 
    backgroundColor: '#0F0F0F',
  },
  content: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 24,
  },
  avatar: {
    width: 100,
    height: 100,
    borderRadius: 50,
    backgroundColor: '#FF5E0E',
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 16,
  },
  avatarText: {
    color: '#fff',
    fontSize: 40,
    fontWeight: '700',
  },
  title: { 
    fontSize: 28, 
    fontWeight: '800', 
    color: '#FFF',
    marginBottom: 8,
  },
  email: {
    fontSize: 16,
    color: '#A1A1A1',
    marginBottom: 40,
  },
  subtitle: {
    fontSize: 16,
    color: '#A1A1A1',
    marginBottom: 24,
    textAlign: 'center',
  },
  button: {
    backgroundColor: '#FF5E0E',
    paddingHorizontal: 32,
    paddingVertical: 14,
    borderRadius: 12,
  },
  buttonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '700',
  },
  menu: {
    width: '100%',
    gap: 12,
  },
  menuItem: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#1C1C1E',
    paddingVertical: 16,
    paddingHorizontal: 20,
    borderRadius: 12,
    gap: 12,
  },
  menuItemText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#FFF',
  }
});
