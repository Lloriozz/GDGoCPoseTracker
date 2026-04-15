import { Request, Response } from 'express';
import prisma from '../config/prisma';

// Get all workouts for a user
export const getUserWorkouts = async (req: Request, res: Response) => {
  try {
    const userId = req.user?.userId;

    if (!userId) {
      return res.status(401).json({ error: 'Unauthorized' });
    }

    const workouts = await prisma.workout.findMany({
      where: { userId },
      include: {
        exercise: true
      },
      orderBy: {
        startedAt: 'desc'
      }
    });

    res.json(workouts);
  } catch (error) {
    console.error('Get workouts error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
};

// Get workout by ID
export const getWorkoutById = async (req: Request, res: Response) => {
  try {
    const { id } = req.params;
    const userId = req.user?.userId;

    if (!userId) {
      return res.status(401).json({ error: 'Unauthorized' });
    }

    const workout = await prisma.workout.findFirst({
      where: {
        id,
        userId
      },
      include: {
        exercise: true
      }
    });

    if (!workout) {
      return res.status(404).json({ error: 'Workout not found' });
    }

    res.json(workout);
  } catch (error) {
    console.error('Get workout error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
};

// Create new workout
export const createWorkout = async (req: Request, res: Response) => {
  try {
    const userId = req.user?.userId;

    if (!userId) {
      return res.status(401).json({ error: 'Unauthorized' });
    }

    const { exerciseId, duration } = req.body;

    const workout = await prisma.workout.create({
      data: {
        userId,
        exerciseId,
        duration,
        completed: false
      },
      include: {
        exercise: true
      }
    });

    res.status(201).json({
      message: 'Workout created successfully',
      workout
    });
  } catch (error) {
    console.error('Create workout error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
};

// Update workout
export const updateWorkout = async (req: Request, res: Response) => {
  try {
    const { id } = req.params;
    const userId = req.user?.userId;

    if (!userId) {
      return res.status(401).json({ error: 'Unauthorized' });
    }

    const { duration, score, completed } = req.body;

    const workout = await prisma.workout.updateMany({
      where: {
        id,
        userId
      },
      data: {
        duration,
        score,
        completed,
        completedAt: completed ? new Date() : null
      }
    });

    if (workout.count === 0) {
      return res.status(404).json({ error: 'Workout not found' });
    }

    const updatedWorkout = await prisma.workout.findFirst({
      where: { id },
      include: { exercise: true }
    });

    res.json({
      message: 'Workout updated successfully',
      workout: updatedWorkout
    });
  } catch (error) {
    console.error('Update workout error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
};

// Delete workout
export const deleteWorkout = async (req: Request, res: Response) => {
  try {
    const { id } = req.params;
    const userId = req.user?.userId;

    if (!userId) {
      return res.status(401).json({ error: 'Unauthorized' });
    }

    const workout = await prisma.workout.deleteMany({
      where: {
        id,
        userId
      }
    });

    if (workout.count === 0) {
      return res.status(404).json({ error: 'Workout not found' });
    }

    res.json({ message: 'Workout deleted successfully' });
  } catch (error) {
    console.error('Delete workout error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
};

// Get all exercise types
export const getAllExercises = async (req: Request, res: Response) => {
  try {
    const exercises = await prisma.exercise.findMany({
      orderBy: {
        name: 'asc'
      }
    });

    res.json(exercises);
  } catch (error) {
    console.error('Get exercises error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
};

// Get workout statistics
export const getWorkoutStats = async (req: Request, res: Response) => {
  try {
    const userId = req.user?.userId;

    if (!userId) {
      return res.status(401).json({ error: 'Unauthorized' });
    }

    const totalWorkouts = await prisma.workout.count({
      where: { userId }
    });

    const completedWorkouts = await prisma.workout.count({
      where: {
        userId,
        completed: true
      }
    });

    const totalDuration = await prisma.workout.aggregate({
      where: {
        userId,
        completed: true
      },
      _sum: {
        duration: true
      }
    });

    const averageScore = await prisma.workout.aggregate({
      where: {
        userId,
        completed: true,
        score: {
          not: null
        }
      },
      _avg: {
        score: true
      }
    });

    res.json({
      totalWorkouts,
      completedWorkouts,
      totalDuration: totalDuration._sum.duration || 0,
      averageScore: averageScore._avg.score || 0
    });
  } catch (error) {
    console.error('Get workout stats error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
};
