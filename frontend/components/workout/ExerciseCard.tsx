import React from 'react';
import { View, Text, StyleSheet, Image } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { Exercise } from '../../types/workout';

interface ExerciseCardProps {
  exercise: Exercise;
  timeLeft?: number;
}

export const ExerciseCard: React.FC<ExerciseCardProps> = ({ exercise, timeLeft }) => {
  return (
    <View style={styles.card}>
      <View style={styles.animationPlaceholder}>
        {exercise.animation_url ? (
          <Image 
            source={{ uri: exercise.animation_url }} 
            style={styles.animation}
            resizeMode="contain"
          />
        ) : (
          <>
            <Ionicons name="fitness-outline" size={80} color="#ccc" />
            <Text style={styles.placeholderText}>Animation</Text>
          </>
        )}
      </View>
      <Text style={styles.exerciseName}>{exercise.name}</Text>
      <Text style={styles.description}>{exercise.description}</Text>
      <View style={styles.badgeContainer}>
        <View style={styles.badge}>
          <Text style={styles.badgeText}>{exercise.difficulty}</Text>
        </View>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  card: {
    backgroundColor: '#1C1C1E',
    borderRadius: 24,
    padding: 24,
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 10 },
    shadowOpacity: 0.1,
    shadowRadius: 20,
    elevation: 5,
  },
  animationPlaceholder: {
    width: '100%',
    height: 200,
    backgroundColor: '#0F0F0F',
    borderRadius: 16,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 20,
  },
  animation: {
    width: '100%',
    height: '100%',
    borderRadius: 16,
  },
  placeholderText: {
    marginTop: 10,
    color: '#999',
    fontWeight: '500',
  },
  exerciseName: {
    fontSize: 28,
    fontWeight: '800',
    color: '#FFF',
    textAlign: 'center',
    marginBottom: 5,
  },
  description: {
    fontSize: 16,
    color: '#A1A1A1',
    textAlign: 'center',
    lineHeight: 22,
    marginBottom: 15,
  },
  badgeContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'center',
    gap: 8,
  },
  badge: {
    backgroundColor: '#331B10',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 20,
  },
  badgeText: {
    color: '#FF5E0E',
    fontSize: 12,
    fontWeight: '700',
    textTransform: 'uppercase',
  },
});
