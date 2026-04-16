import React from 'react';
import { Text, StyleSheet } from 'react-native';
import { formatTime } from '../../utils/formatters';

interface WorkoutTimerProps {
  timeLeft: number;
  phase: 'workout' | 'rest';
}

export const WorkoutTimer: React.FC<WorkoutTimerProps> = ({ timeLeft, phase }) => {
  return (
    <Text style={[styles.timer, phase === 'rest' && styles.restTimer]}>
      {formatTime(timeLeft)}
    </Text>
  );
};

const styles = StyleSheet.create({
  timer: {
    fontSize: 64,
    fontWeight: '900',
    color: '#FF7A22',
    marginVertical: 10,
    fontVariant: ['tabular-nums'],
  },
  restTimer: {
    color: '#4ADE80',
  },
});
