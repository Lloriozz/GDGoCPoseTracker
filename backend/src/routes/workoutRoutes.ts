import { Router } from 'express';
import {
  getUserWorkouts,
  getWorkoutById,
  createWorkout,
  updateWorkout,
  deleteWorkout,
  getAllExercises,
  getWorkoutStats
} from '../controllers/workoutController';
import { authenticate } from '../utils/auth';

const router = Router();

// Protected routes
router.get('/', authenticate, getUserWorkouts);
router.get('/stats', authenticate, getWorkoutStats);
router.get('/exercises', getAllExercises);
router.get('/:id', authenticate, getWorkoutById);
router.post('/', authenticate, createWorkout);
router.put('/:id', authenticate, updateWorkout);
router.delete('/:id', authenticate, deleteWorkout);

export default router;
