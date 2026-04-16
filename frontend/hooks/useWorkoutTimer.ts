import { useState, useEffect, useRef, useCallback } from 'react';
import { Animated, Easing } from 'react-native';
import { WorkoutPhase, WorkoutData } from '../types/workout';

interface UseWorkoutTimerProps {
  workoutData: WorkoutData;
  onPhaseChange?: (phase: WorkoutPhase) => void;
  onExerciseChange?: (exerciseIndex: number) => void;
}

export const useWorkoutTimer = ({ workoutData, onPhaseChange, onExerciseChange }: UseWorkoutTimerProps) => {
  const [currentExerciseIndex, setCurrentExerciseIndex] = useState(0);
  const [phase, setPhase] = useState<WorkoutPhase>('start');
  const [timeLeft, setTimeLeft] = useState(workoutData.exercises[0].duration);
  const [isPaused, setIsPaused] = useState(false);
  
  const progressAnim = useRef(new Animated.Value(0)).current;
  const pulseAnim = useRef(new Animated.Value(1)).current;
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const playSound = useCallback((type: 'start' | 'halfway' | 'countdown') => {
    console.log(`[Audio Cue]: ${type.toUpperCase()}`);
  }, []);

  const resetWorkout = useCallback(() => {
    setCurrentExerciseIndex(0);
    setPhase('start');
    setTimeLeft(workoutData.exercises[0].duration);
    setIsPaused(false);
    progressAnim.setValue(0);
  }, [workoutData, progressAnim]);

  useEffect(() => {
    if (phase === 'finished' || phase === 'start') return;

    const currentMaxTime = phase === 'workout'
      ? workoutData.exercises[currentExerciseIndex].duration
      : workoutData.exercises[currentExerciseIndex].rest;

    Animated.timing(progressAnim, {
      toValue: 1 - (timeLeft / currentMaxTime),
      duration: 1000,
      easing: Easing.linear,
      useNativeDriver: false,
    }).start();

    if (isPaused) return;

    if (timeLeft === 0) {
      if (phase === 'workout') {
        const hasRest = workoutData.exercises[currentExerciseIndex].rest > 0;
        const isLastExercise = currentExerciseIndex === workoutData.exercises.length - 1;

        if (hasRest && !isLastExercise) {
          setPhase('rest');
          setTimeLeft(workoutData.exercises[currentExerciseIndex].rest);
          playSound('start');
        } else if (isLastExercise) {
          setPhase('finished');
          playSound('start');
        } else {
          setCurrentExerciseIndex((prev: number) => prev + 1);
          setTimeLeft(workoutData.exercises[currentExerciseIndex + 1].duration);
          playSound('start');
          onExerciseChange?.(currentExerciseIndex + 1);
        }
      } else if (phase === 'rest') {
        setPhase('workout');
        setCurrentExerciseIndex((prev: number) => prev + 1);
        setTimeLeft(workoutData.exercises[currentExerciseIndex + 1].duration);
        playSound('start');
        progressAnim.setValue(0);
        onExerciseChange?.(currentExerciseIndex + 1);
      }
      return;
    }

    if (phase === 'workout') {
      const half = Math.floor(workoutData.exercises[currentExerciseIndex].duration / 2);
      if (timeLeft === half) playSound('halfway');
      if (timeLeft <= 3 && timeLeft > 0) playSound('countdown');
    } else {
      if (timeLeft <= 3 && timeLeft > 0) playSound('countdown');
    }

    timerRef.current = setInterval(() => {
      setTimeLeft((prev: number) => prev - 1);
    }, 1000);

    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    };
  }, [timeLeft, isPaused, phase, currentExerciseIndex, workoutData, progressAnim, playSound, onExerciseChange]);

  useEffect(() => {
    if (phase === 'rest') {
      Animated.loop(
        Animated.sequence([
          Animated.timing(pulseAnim, { toValue: 1.05, duration: 800, useNativeDriver: true }),
          Animated.timing(pulseAnim, { toValue: 1, duration: 800, useNativeDriver: true })
        ])
      ).start();
    } else {
      pulseAnim.stopAnimation();
      pulseAnim.setValue(1);
    }
  }, [phase, pulseAnim]);

  const handlePrevious = useCallback(() => {
    if (currentExerciseIndex > 0) {
      setPhase('workout');
      setCurrentExerciseIndex((prev: number) => prev - 1);
      setTimeLeft(workoutData.exercises[currentExerciseIndex - 1].duration);
      playSound('start');
      progressAnim.setValue(0);
      onExerciseChange?.(currentExerciseIndex - 1);
    } else {
      setTimeLeft(workoutData.exercises[0].duration);
      progressAnim.setValue(0);
    }
  }, [currentExerciseIndex, workoutData, progressAnim, playSound, onExerciseChange]);

  const handleSkip = useCallback(() => {
    const isLastExercise = currentExerciseIndex === workoutData.exercises.length - 1;
    if (isLastExercise) {
      setPhase('finished');
      playSound('start');
    } else {
      setPhase('workout');
      setCurrentExerciseIndex((prev: number) => prev + 1);
      setTimeLeft(workoutData.exercises[currentExerciseIndex + 1].duration);
      playSound('start');
      progressAnim.setValue(0);
      onExerciseChange?.(currentExerciseIndex + 1);
    }
  }, [currentExerciseIndex, workoutData, progressAnim, playSound, onExerciseChange]);

  return {
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
  };
};
