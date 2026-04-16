import React, { useCallback } from 'react';
import { View, Text, Pressable, Animated } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { router, useFocusEffect } from 'expo-router';

import { SQUAT_WORKOUT_DATA } from '../constants/workouts';
import { useWorkoutTimer } from '../hooks/useWorkoutTimer';
import { WorkoutTimer } from '../components/workout/WorkoutTimer';
import { ExerciseCard } from '../components/workout/ExerciseCard';
import { WorkoutControls } from '../components/workout/WorkoutControls';
import { workoutStyles } from '../styles/workout';

export default function SquatWorkoutScreen() {
  const insets = useSafeAreaInsets();

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
    resetWorkout,
    playSound
  } = useWorkoutTimer({ workoutData: SQUAT_WORKOUT_DATA });

  useFocusEffect(
    useCallback(() => {
      resetWorkout();
    }, [resetWorkout])
  );

  const handleQuitRequest = () => {
    router.replace('/(tabs)' as any);
  };

  const confirmQuit = () => {
    router.replace('/(tabs)' as any);
  };

  if (phase === 'start') {
    return (
      <View style={[workoutStyles.container, workoutStyles.finishedContainer, { paddingTop: insets.top }]}>
        <Ionicons name="barbell" size={100} color="#FF7A22" />
        <Text style={workoutStyles.titleText}>{SQUAT_WORKOUT_DATA.workout_name}</Text>
        <Text style={workoutStyles.subtitleText}>
          {SQUAT_WORKOUT_DATA.exercises.length} Exercises • {SQUAT_WORKOUT_DATA.total_duration}
        </Text>
        <Pressable 
          style={workoutStyles.primaryButton} 
          onPress={() => {
            setPhase('workout');
            playSound('start');
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
        <Ionicons name="trophy" size={100} color="#FFD700" />
        <Text style={workoutStyles.titleText}>Workout Complete!</Text>
        <Text style={workoutStyles.subtitleText}>You crushed {SQUAT_WORKOUT_DATA.workout_name}</Text>
        <Pressable style={workoutStyles.primaryButton} onPress={confirmQuit}>
          <Text style={workoutStyles.primaryButtonText}>Finish & Return Home</Text>
        </Pressable>
      </View>
    );
  }

  const currentExercise = SQUAT_WORKOUT_DATA.exercises[currentExerciseIndex];
  const nextExercise = currentExerciseIndex + 1 < SQUAT_WORKOUT_DATA.exercises.length
    ? SQUAT_WORKOUT_DATA.exercises[currentExerciseIndex + 1]
    : null;

  const barWidth = progressAnim.interpolate({
    inputRange: [0, 1],
    outputRange: ['0%', '100%']
  });

  return (
    <View style={[workoutStyles.container, phase === 'rest' && workoutStyles.restContainer, { paddingTop: insets.top }]}>
      {/* Header */}
      <View style={workoutStyles.header}>
        <View style={{ flex: 1 }}>
          <Text style={[workoutStyles.progressText, phase === 'rest' && { color: 'rgba(255,255,255,0.7)' }]}>
            Exercise {currentExerciseIndex + 1} of {SQUAT_WORKOUT_DATA.exercises.length}
          </Text>
        </View>
        <Pressable onPress={handleQuitRequest} hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}>
          <Ionicons name="close" size={28} color={phase === 'rest' ? '#fff' : '#333'} />
        </Pressable>
      </View>

      {/* Progress Bar */}
      <View style={[workoutStyles.progressBarBackground, phase === 'rest' && { backgroundColor: 'rgba(255,255,255,0.2)' }]}>
        <Animated.View style={[workoutStyles.progressBarFill, { width: barWidth, backgroundColor: phase === 'rest' ? '#4ADE80' : '#FF7A22' }]} />
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
    </View>
  );
}
