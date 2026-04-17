import React, { useState, useCallback } from 'react';
import { View, Text, StyleSheet, Pressable, Modal, Animated } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { router, useFocusEffect } from 'expo-router';
import { LinearGradient } from 'expo-linear-gradient';

import { CARDIO_WORKOUT_DATA } from '../constants/workouts';
import { useWorkoutTimer } from '../hooks/useWorkoutTimer';
import { WorkoutTimer } from '../components/workout/WorkoutTimer';
import { ExerciseCard } from '../components/workout/ExerciseCard';
import { WorkoutControls } from '../components/workout/WorkoutControls';
import { workoutStyles } from '../styles/workout';

export default function WorkoutScreen() {
  const insets = useSafeAreaInsets();
  const [showQuitModal, setShowQuitModal] = useState(false);

  const {
    currentExerciseIndex,
    phase,
    timeLeft,
    isPaused,
    setIsPaused,
    setPhase,
    progressAnim,
    pulseAnim,
    handlePrevious,
    handleSkip,
    resetWorkout
  } = useWorkoutTimer({ workoutData: CARDIO_WORKOUT_DATA });

  useFocusEffect(
    useCallback(() => {
      resetWorkout();
    }, [resetWorkout])
  );

  const handleQuitRequest = () => {
    setIsPaused(true);
    setShowQuitModal(true);
  };

  const cancelQuit = () => {
    setShowQuitModal(false);
    setIsPaused(false);
  };

  const confirmQuit = () => {
    setShowQuitModal(false);
    router.replace('/(tabs)' as any);
  };

  if (phase === 'start') {
    return (
      <View style={[workoutStyles.container, workoutStyles.finishedContainer, { paddingTop: insets.top }]}>
        <LinearGradient
          colors={['rgba(255, 94, 14, 0.25)', '#0F0F0F', '#0F0F0F']}
          locations={[0, 0.35, 1]}
          style={StyleSheet.absoluteFillObject}
        />
        <Ionicons name="heart" size={100} color="#FF5E0E" />
        <Text style={workoutStyles.titleText}>{CARDIO_WORKOUT_DATA.workout_name}</Text>
        <Text style={workoutStyles.subtitleText}>
          {CARDIO_WORKOUT_DATA.exercises.length} Exercises • {CARDIO_WORKOUT_DATA.total_duration}
        </Text>
        <Pressable 
          style={workoutStyles.primaryButton} 
          onPress={() => {
            setPhase('workout');
            setIsPaused(false);
          }}
        >
          <Text style={workoutStyles.primaryButtonText}>Start Workout</Text>
        </Pressable>
      </View>
    );
  }

  if (phase === 'finished') {
    return (
      <View style={[workoutStyles.container, workoutStyles.finishedContainer, { paddingTop: insets.top }]}>
        <LinearGradient
          colors={['rgba(255, 94, 14, 0.25)', '#0F0F0F', '#0F0F0F']}
          locations={[0, 0.35, 1]}
          style={StyleSheet.absoluteFillObject}
        />
        <Ionicons name="trophy" size={100} color="#FFD700" />
        <Text style={workoutStyles.titleText}>Workout Complete!</Text>
        <Text style={workoutStyles.subtitleText}>You crushed {CARDIO_WORKOUT_DATA.workout_name}</Text>
        <Pressable style={workoutStyles.primaryButton} onPress={confirmQuit}>
          <Text style={workoutStyles.primaryButtonText}>Finish & Return Home</Text>
        </Pressable>
      </View>
    );
  }

  const currentExercise = CARDIO_WORKOUT_DATA.exercises[currentExerciseIndex];
  const nextExercise = currentExerciseIndex + 1 < CARDIO_WORKOUT_DATA.exercises.length
    ? CARDIO_WORKOUT_DATA.exercises[currentExerciseIndex + 1]
    : null;

  const barWidth = progressAnim.interpolate({
    inputRange: [0, 1],
    outputRange: ['0%', '100%']
  });

  return (
    <View style={[workoutStyles.container, phase === 'rest' && workoutStyles.restContainer, { paddingTop: insets.top }]}>
      <LinearGradient
        colors={['rgba(255, 94, 14, 0.25)', '#0F0F0F', '#0F0F0F']}
        locations={[0, 0.35, 1]}
        style={StyleSheet.absoluteFillObject}
      />
      {/* Header */}
      <View style={workoutStyles.header}>
        <View style={{ flex: 1 }}>
          <Text style={[workoutStyles.progressText, phase === 'rest' && { color: 'rgba(255,255,255,0.7)' }]}>
            Exercise {currentExerciseIndex + 1} of {CARDIO_WORKOUT_DATA.exercises.length}
          </Text>
        </View>
        <Pressable onPress={handleQuitRequest} hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}>
          <Ionicons name="close" size={28} color="#FFF" />
        </Pressable>
      </View>

      {/* Progress Bar */}
      <View style={[workoutStyles.progressBarBackground, phase === 'rest' && { backgroundColor: 'rgba(255,255,255,0.2)' }]}>
        <Animated.View style={[workoutStyles.progressBarFill, { width: barWidth, backgroundColor: phase === 'rest' ? '#4ADE80' : '#FF5E0E' }]} />
      </View>

      {/* Main Content */}
      <View style={workoutStyles.content}>
        {phase === 'workout' ? (
          <ExerciseCard exercise={currentExercise} />
        ) : (
          <Animated.View style={[workoutStyles.restCard, { transform: [{ scale: pulseAnim }] }]}>
            <Text style={workoutStyles.restTitle}>REST</Text>
            <WorkoutTimer timeLeft={timeLeft} phase="rest" />

            {nextExercise && (
              <View style={workoutStyles.nextBox}>
                <Text style={workoutStyles.nextLabel}>Up Next:</Text>
                <Text style={workoutStyles.nextTitle}>{nextExercise.name}</Text>
                <Text style={workoutStyles.nextDesc} numberOfLines={2}>{nextExercise.description}</Text>
              </View>
            )}
          </Animated.View>
        )}
      </View>

      {/* Footer Controls */}
      <WorkoutControls
        isPaused={isPaused}
        onPrevious={handlePrevious}
        onSkip={handleSkip}
        onPauseToggle={() => setIsPaused(!isPaused)}
        canGoPrevious={currentExerciseIndex > 0}
      />

      {/* Quit Modal */}
      <Modal transparent visible={showQuitModal} animationType="fade">
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <Text style={styles.modalTitle}>Pause Workout</Text>
            <Text style={styles.modalBody}>You&apos;re crushing it! Are you sure you want to end early?</Text>
            <View style={styles.modalActions}>
              <Pressable style={[styles.modalBtn, styles.btnResume]} onPress={cancelQuit}>
                <Text style={styles.btnResumeText}>Resume</Text>
              </Pressable>
              <Pressable style={[styles.modalBtn, styles.btnQuit]} onPress={confirmQuit}>
                <Text style={styles.btnQuitText}>End Workout</Text>
              </Pressable>
            </View>
          </View>
        </View>
      </Modal>

    </View>
  );
}

const styles = StyleSheet.create({
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.5)',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  modalContent: {
    backgroundColor: '#1C1C1E',
    width: '90%',
    borderRadius: 24,
    padding: 24,
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 10 },
    shadowOpacity: 0.1,
    shadowRadius: 20,
    elevation: 5,
  },
  modalTitle: {
    fontSize: 22,
    fontWeight: '800',
    color: '#FFF',
    marginBottom: 10,
  },
  modalBody: {
    fontSize: 16,
    color: '#A1A1A1',
    textAlign: 'center',
    marginBottom: 24,
    lineHeight: 22,
  },
  modalActions: {
    flexDirection: 'row',
    gap: 12,
    width: '100%',
  },
  modalBtn: {
    flex: 1,
    paddingVertical: 14,
    borderRadius: 12,
    alignItems: 'center',
    justifyContent: 'center',
  },
  btnResume: {
    backgroundColor: '#FF5E0E',
  },
  btnQuit: {
    backgroundColor: '#331B10',
  },
  btnResumeText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '700',
  },
  btnQuitText: {
    color: '#FF5E0E',
    fontSize: 16,
    fontWeight: '700',
  },
});
