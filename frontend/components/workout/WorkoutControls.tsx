import React from 'react';
import { View, Pressable, StyleSheet } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

interface WorkoutControlsProps {
  isPaused: boolean;
  onPrevious: () => void;
  onSkip: () => void;
  onPauseToggle: () => void;
  canGoPrevious: boolean;
}

export const WorkoutControls: React.FC<WorkoutControlsProps> = ({
  isPaused,
  onPrevious,
  onSkip,
  onPauseToggle,
  canGoPrevious
}) => {
  return (
    <View style={styles.footer}>
      <View style={styles.controlsRow}>
        <Pressable 
          style={[styles.skipButton, !canGoPrevious && { opacity: 0.5 }]} 
          onPress={onPrevious}
          disabled={!canGoPrevious}
        >
          <Ionicons name="play-skip-back" size={24} color="#333" />
        </Pressable>
        <Pressable style={styles.pauseButton} onPress={onPauseToggle}>
          <Ionicons name={isPaused ? "play" : "pause"} size={32} color="#fff" />
        </Pressable>
        <Pressable style={styles.skipButton} onPress={onSkip}>
          <Ionicons name="play-skip-forward" size={24} color="#333" />
        </Pressable>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  footer: {
    padding: 20,
    alignItems: 'center',
    paddingBottom: 40,
  },
  controlsRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 24,
  },
  skipButton: {
    width: 50,
    height: 50,
    borderRadius: 25,
    backgroundColor: '#fff',
    justifyContent: 'center',
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 5,
    elevation: 3,
  },
  pauseButton: {
    backgroundColor: '#111',
    width: 70,
    height: 70,
    borderRadius: 35,
    justifyContent: 'center',
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 5 },
    shadowOpacity: 0.2,
    shadowRadius: 10,
    elevation: 5,
  },
});
