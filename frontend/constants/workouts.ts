import { WorkoutData } from '../types/workout';

export const BICEP_WORKOUT_DATA: WorkoutData = {
  workout_name: "Ultimate Bicep Builder",
  total_duration: "4 minutes",
  rounds: "1",
  exercises: [
    {
      name: "Dumbbell Bicep Curl",
      duration: 30,
      rest: 10,
      description: "Keep your elbows close to your torso and rotate the palms of your hands until they are facing forward.",
      muscles: ["Biceps brachii"],
      difficulty: "Beginner",
      animation_url: "https://fitnessprogramer.com/wp-content/uploads/2021/02/Dumbbell-Curl.gif"
    },
    {
      name: "Hammer Curl",
      duration: 30,
      rest: 10,
      description: "Hold the dumbbells with a neutral grip (palms facing each other) and curl the weights up.",
      muscles: ["Brachialis", "Brachioradialis"],
      difficulty: "Beginner",
      animation_url: "https://fitnessprogramer.com/wp-content/uploads/2021/02/Hammer-Curl.gif"
    },
    {
      name: "Concentration Curl",
      duration: 30,
      rest: 10,
      description: "Sit on a bench, rest your elbow on your inner thigh, and curl the weight upward, isolating the bicep.",
      muscles: ["Biceps brachii (short head)"],
      difficulty: "Intermediate",
      animation_url: "https://fitnessprogramer.com/wp-content/uploads/2021/02/Concentration-Curl.gif"
    },
    {
      name: "EZ Bar Preacher Curl",
      duration: 30,
      rest: 10,
      description: "Use a preacher bench to isolate the biceps completely and prevent the rest of your body from using momentum.",
      muscles: ["Biceps brachii (long head)"],
      difficulty: "Intermediate",
      animation_url: "https://fitnessprogramer.com/wp-content/uploads/2021/02/Z-Bar-Preacher-Curl.gif"
    }
  ]
};

export const CARDIO_WORKOUT_DATA: WorkoutData = {
  workout_name: "Quick Cardio Blast",
  total_duration: "3 minutes 20 seconds",
  rounds: "1",
  exercises: [
    {
      name: "Jumping Jacks",
      duration: 30,
      rest: 10,
      description: "A classic full-body move to get your heart rate up and blood flowing perfectly.",
      muscles: ["Shoulders", "Calves", "Quads", "Core"],
      difficulty: "Beginner",
      animation_guide: "Figure stands naturally, jumps up explosively while spreading legs wide and raising arms overhead, then returns to the starting position. Fast, rhythmic bounce. Light on the toes."
    },
    {
      name: "Bodyweight Squats",
      duration: 30,
      rest: 10,
      description: "Lower your hips just like sitting in a chair. Keep your chest up and power through your heels.",
      muscles: ["Quads", "Glutes", "Hamstrings"],
      difficulty: "Beginner",
      animation_guide: "Figure starts with feet shoulder-width apart, drops hips back and down until thighs are parallel to the floor, then smoothly stands back up straight. Moderate, controlled 2-second descending tempo."
    },
    {
      name: "High Knees",
      duration: 30,
      rest: 10,
      description: "Run perfectly in place, driving your knees as high up to your chest as possible to fire up the core.",
      muscles: ["Core", "Hip Flexors", "Calves", "Quads"],
      difficulty: "Intermediate",
      animation_guide: "Figure actively runs in place, driving knees up to exactly waist-level. Arms pump vigorously in sync with opposite legs. Fast, energetic upward tempo."
    },
    {
      name: "Mountain Climbers",
      duration: 30,
      rest: 10,
      description: "Start in a strong plank position and rapidly alternate bringing your knees to your chest.",
      muscles: ["Core", "Shoulders", "Chest", "Triceps"],
      difficulty: "Intermediate",
      animation_guide: "Figure holds a high plank (push-up) posture with a flat back. Alternates driving one knee aggressively toward the chest and quickly extending it back. Very fast, running-on-the-floor tempo."
    },
    {
      name: "Butt Kicks",
      duration: 30,
      rest: 10,
      description: "Jog rhythmically in place while actively flicking your heels all the way up to tap your glutes.",
      muscles: ["Hamstrings", "Glutes", "Calves"],
      difficulty: "Beginner",
      animation_guide: "Figure lightly jogs in place, emphasizing the back-kick so the heel of the trailing leg swings up to hit the glutes. Smooth, moderate-to-fast tempo. Upper body stays upright."
    }
  ]
};

export const SQUAT_WORKOUT_DATA: WorkoutData = {
  workout_name: "Ultimate Leg Day",
  total_duration: "4 minutes",
  rounds: "1",
  exercises: [
    {
      name: "Bodyweight Squat",
      duration: 30,
      rest: 10,
      description: "Keep your chest up and back straight while squatting down until your thighs are parallel to the floor.",
      muscles: ["Quads", "Glutes", "Hamstrings"],
      difficulty: "Beginner",
      animation_url: "https://fitnessprogramer.com/wp-content/uploads/2021/05/bodyweight-squat-full-version.gif"
    },
    {
      name: "Goblet Squat",
      duration: 30,
      rest: 10,
      description: "Hold a weight at chest level and maintain an upright torso as you drop your hips straight down.",
      muscles: ["Quads", "Core"],
      difficulty: "Intermediate",
      animation_url: "https://fitnessprogramer.com/wp-content/uploads/2021/05/bodyweight-squat-full-version.gif"
    },
    {
      name: "Bulgarian Split Squat",
      duration: 30,
      rest: 10,
      description: "Rest one foot behind you on an elevated surface and focus on dropping your back knee down.",
      muscles: ["Quads", "Glutes"],
      difficulty: "Advanced",
      animation_url: "https://fitnessprogramer.com/wp-content/uploads/2021/05/bodyweight-squat-full-version.gif"
    },
    {
      name: "Dumbbell Lunges",
      duration: 30,
      rest: 10,
      description: "Step forward into a lunge position, lowering your hips until both knees are bent at a 90-degree angle.",
      muscles: ["Quads", "Glutes", "Hamstrings"],
      difficulty: "Intermediate",
      animation_url: "https://fitnessprogramer.com/wp-content/uploads/2021/02/Dumbbell-Lunge.gif"
    }
  ]
};
