import { API_BASE_URL } from '../config/api';

interface Workout {
  id: string;
  userId: string;
  workout_name: string;
  total_duration: string;
  rounds: string;
  exercises: Exercise[];
  createdAt: string;
  updatedAt: string;
}

interface Exercise {
  id: string;
  workoutId: string;
  name: string;
  duration: number;
  rest: number;
  description: string;
  muscles: string[];
  difficulty: string;
  animation_url?: string;
  animation_guide?: string;
}

export const workoutAPI = {
  async getUserWorkouts(token: string): Promise<Workout[]> {
    const response = await fetch(`${API_BASE_URL}/workouts`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!response.ok) throw new Error('Failed to fetch workouts');
    return response.json();
  },

  async getWorkoutById(token: string, id: string): Promise<Workout> {
    const response = await fetch(`${API_BASE_URL}/workouts/${id}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!response.ok) throw new Error('Failed to fetch workout');
    return response.json();
  },

  async createWorkout(token: string, data: Partial<Workout>): Promise<Workout> {
    const response = await fetch(`${API_BASE_URL}/workouts`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(data),
    });
    if (!response.ok) throw new Error('Failed to create workout');
    return response.json();
  },

  async updateWorkout(token: string, id: string, data: Partial<Workout>): Promise<Workout> {
    const response = await fetch(`${API_BASE_URL}/workouts/${id}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(data),
    });
    if (!response.ok) throw new Error('Failed to update workout');
    return response.json();
  },

  async deleteWorkout(token: string, id: string) {
    const response = await fetch(`${API_BASE_URL}/workouts/${id}`, {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!response.ok) throw new Error('Failed to delete workout');
    return response.json();
  },

  async getAllExercises(): Promise<Exercise[]> {
    const response = await fetch(`${API_BASE_URL}/workouts/exercises`);
    if (!response.ok) throw new Error('Failed to fetch exercises');
    return response.json();
  },

  async getWorkoutStats(token: string) {
    const response = await fetch(`${API_BASE_URL}/workouts/stats`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!response.ok) throw new Error('Failed to fetch workout stats');
    return response.json();
  },
};
