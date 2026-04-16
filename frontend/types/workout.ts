export interface Exercise {
  name: string;
  duration: number;
  rest: number;
  description: string;
  muscles: string[];
  difficulty: string;
  animation_url?: string;
  animation_guide?: string;
}

export interface WorkoutData {
  workout_name: string;
  total_duration: string;
  rounds: string;
  exercises: Exercise[];
}

export type WorkoutPhase = 'start' | 'workout' | 'rest' | 'finished';
