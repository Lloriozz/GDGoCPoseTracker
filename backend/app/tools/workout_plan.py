from app.schemas.user_profile import UserProfile


def generate_workout_plan(profile: UserProfile) -> dict[str, object]:
    if (
        profile.goal is None
        or profile.workout_days_per_week is None
        or profile.train_location is None
    ):
        return {}

    split = _choose_split(profile.workout_days_per_week)
    injuries = [injury.lower() for injury in profile.injuries]
    is_home = profile.train_location == "home"

    if split == "full_body":
        days = [
            _build_day("Day 1", "Full Body A", _full_body_a(is_home, injuries)),
            _build_day("Day 2", "Full Body B", _full_body_b(is_home, injuries)),
            _build_day("Day 3", "Full Body C", _full_body_c(is_home, injuries)),
        ][: profile.workout_days_per_week]
    elif split == "upper_lower":
        days = [
            _build_day("Day 1", "Upper", _upper_day(is_home, injuries)),
            _build_day("Day 2", "Lower", _lower_day(is_home, injuries)),
            _build_day("Day 3", "Upper", _upper_day_two(is_home, injuries)),
            _build_day("Day 4", "Lower", _lower_day_two(is_home, injuries)),
        ]
    else:
        days = [
            _build_day("Day 1", "Push", _push_day(is_home, injuries)),
            _build_day("Day 2", "Pull", _pull_day(is_home, injuries)),
            _build_day("Day 3", "Legs", _legs_day(is_home, injuries)),
            _build_day("Day 4", "Upper", _upper_day_two(is_home, injuries)),
            _build_day("Day 5", "Lower", _lower_day_two(is_home, injuries)),
        ][: profile.workout_days_per_week]

    notes = [
        f"Selected {split} because user trains {profile.workout_days_per_week} days per week",
        "Exercise selection is adapted to training location",
    ]
    if profile.experience_level:
        notes.append(f"Program framing is adjusted for {profile.experience_level} level adherence and recovery")
    if profile.goal_detail:
        notes.append(f"Goal detail to keep in mind: {profile.goal_detail}")
    if any("knee" in injury or "goi" in injury for injury in injuries):
        notes.append("Reduced knee-stress exercise selection")
    if any("shoulder" in injury or "vai" in injury for injury in injuries):
        notes.append("Reduced overhead and unstable shoulder loading")

    return {
        "split": split,
        "goal": profile.goal,
        "train_location": profile.train_location,
        "days": days,
        "notes": notes,
    }


def _choose_split(workout_days_per_week: int) -> str:
    if workout_days_per_week <= 3:
        return "full_body"
    if workout_days_per_week == 4:
        return "upper_lower"
    return "push_pull_legs"


def _build_day(day: str, focus: str, exercises: list[dict[str, str | int]]) -> dict[str, object]:
    return {
        "day": day,
        "focus": focus,
        "exercises": exercises,
    }


def _exercise(name: str, sets: int, reps: str, note: str | None = None) -> dict[str, str | int]:
    payload: dict[str, str | int] = {"name": name, "sets": sets, "reps": reps}
    if note is not None:
        payload["note"] = note
    return payload


def _press_variation(is_home: bool, shoulder_sensitive: bool) -> dict[str, str | int]:
    if shoulder_sensitive:
        return _exercise("Incline Push-Up" if is_home else "Machine Chest Press", 3, "8-12")
    return _exercise("Dumbbell Bench Press" if is_home else "Barbell Bench Press", 3, "6-10")


def _row_variation(is_home: bool) -> dict[str, str | int]:
    return _exercise("One-Arm Dumbbell Row" if is_home else "Cable Row", 3, "8-12")


def _hinge_variation(is_home: bool) -> dict[str, str | int]:
    return _exercise("Dumbbell Romanian Deadlift" if is_home else "Romanian Deadlift", 3, "8-10")


def _knee_dominant_variation(is_home: bool, knee_sensitive: bool) -> dict[str, str | int]:
    if knee_sensitive:
        name = "Box Squat" if is_home else "Leg Press"
        return _exercise(name, 3, "10-12", "Keep pain low and range controlled")
    name = "Goblet Squat" if is_home else "Back Squat"
    return _exercise(name, 3, "6-10")


def _shoulder_press_variation(is_home: bool, shoulder_sensitive: bool) -> dict[str, str | int]:
    if shoulder_sensitive:
        return _exercise("Lateral Raise", 3, "12-15")
    return _exercise("Seated Dumbbell Shoulder Press" if is_home else "Machine Shoulder Press", 3, "8-12")


def _full_body_a(is_home: bool, injuries: list[str]) -> list[dict[str, str | int]]:
    knee_sensitive = any("knee" in injury or "goi" in injury for injury in injuries)
    shoulder_sensitive = any("shoulder" in injury or "vai" in injury for injury in injuries)
    return [
        _knee_dominant_variation(is_home, knee_sensitive),
        _press_variation(is_home, shoulder_sensitive),
        _row_variation(is_home),
        _hinge_variation(is_home),
        _exercise("Plank", 3, "30-45 sec"),
    ]


def _full_body_b(is_home: bool, injuries: list[str]) -> list[dict[str, str | int]]:
    shoulder_sensitive = any("shoulder" in injury or "vai" in injury for injury in injuries)
    return [
        _hinge_variation(is_home),
        _exercise("Lat Pulldown" if not is_home else "Band Pulldown", 3, "8-12"),
        _shoulder_press_variation(is_home, shoulder_sensitive),
        _exercise("Split Squat" if is_home else "Leg Curl", 3, "10-12"),
        _exercise("Dead Bug", 3, "10-12 each side"),
    ]


def _full_body_c(is_home: bool, injuries: list[str]) -> list[dict[str, str | int]]:
    knee_sensitive = any("knee" in injury or "goi" in injury for injury in injuries)
    return [
        _knee_dominant_variation(is_home, knee_sensitive),
        _row_variation(is_home),
        _exercise("Push-Up" if is_home else "Incline Dumbbell Press", 3, "8-12"),
        _exercise("Hip Thrust" if is_home else "Glute Bridge", 3, "10-15"),
        _exercise("Farmer Carry", 3, "20-30 m"),
    ]


def _upper_day(is_home: bool, injuries: list[str]) -> list[dict[str, str | int]]:
    shoulder_sensitive = any("shoulder" in injury or "vai" in injury for injury in injuries)
    return [
        _press_variation(is_home, shoulder_sensitive),
        _exercise("Lat Pulldown" if not is_home else "Band Row", 3, "8-12"),
        _shoulder_press_variation(is_home, shoulder_sensitive),
        _row_variation(is_home),
        _exercise("Biceps Curl", 2, "12-15"),
        _exercise("Triceps Extension", 2, "12-15"),
    ]


def _upper_day_two(is_home: bool, injuries: list[str]) -> list[dict[str, str | int]]:
    shoulder_sensitive = any("shoulder" in injury or "vai" in injury for injury in injuries)
    return [
        _exercise("Incline Dumbbell Press" if is_home else "Machine Chest Press", 3, "8-12"),
        _exercise("Chest-Supported Row" if not is_home else "One-Arm Dumbbell Row", 3, "8-12"),
        _shoulder_press_variation(is_home, shoulder_sensitive),
        _exercise("Face Pull" if not is_home else "Band Pull-Apart", 3, "12-15"),
        _exercise("Hammer Curl", 2, "12-15"),
        _exercise("Cable Pushdown" if not is_home else "Bench Dip", 2, "12-15"),
    ]


def _lower_day(is_home: bool, injuries: list[str]) -> list[dict[str, str | int]]:
    knee_sensitive = any("knee" in injury or "goi" in injury for injury in injuries)
    return [
        _hinge_variation(is_home),
        _knee_dominant_variation(is_home, knee_sensitive),
        _exercise("Leg Curl" if not is_home else "Sliding Leg Curl", 3, "10-15"),
        _exercise("Glute Bridge", 3, "10-15"),
        _exercise("Standing Calf Raise", 3, "12-20"),
    ]


def _lower_day_two(is_home: bool, injuries: list[str]) -> list[dict[str, str | int]]:
    knee_sensitive = any("knee" in injury or "goi" in injury for injury in injuries)
    return [
        _knee_dominant_variation(is_home, knee_sensitive),
        _hinge_variation(is_home),
        _exercise("Reverse Lunge" if not knee_sensitive else "Step-Up", 3, "8-12"),
        _exercise("Hip Thrust", 3, "8-12"),
        _exercise("Seated Calf Raise" if not is_home else "Single-Leg Calf Raise", 3, "12-20"),
    ]


def _push_day(is_home: bool, injuries: list[str]) -> list[dict[str, str | int]]:
    shoulder_sensitive = any("shoulder" in injury or "vai" in injury for injury in injuries)
    return [
        _press_variation(is_home, shoulder_sensitive),
        _exercise("Incline Press" if not is_home else "Feet-Elevated Push-Up", 3, "8-12"),
        _shoulder_press_variation(is_home, shoulder_sensitive),
        _exercise("Lateral Raise", 3, "12-15"),
        _exercise("Triceps Pushdown" if not is_home else "Overhead Triceps Extension", 3, "12-15"),
    ]


def _pull_day(is_home: bool, injuries: list[str]) -> list[dict[str, str | int]]:
    return [
        _row_variation(is_home),
        _exercise("Lat Pulldown" if not is_home else "Band Pulldown", 3, "8-12"),
        _exercise("Rear Delt Fly", 3, "12-15"),
        _hinge_variation(is_home),
        _exercise("Biceps Curl", 3, "10-15"),
    ]


def _legs_day(is_home: bool, injuries: list[str]) -> list[dict[str, str | int]]:
    knee_sensitive = any("knee" in injury or "goi" in injury for injury in injuries)
    return [
        _knee_dominant_variation(is_home, knee_sensitive),
        _hinge_variation(is_home),
        _exercise("Leg Curl" if not is_home else "Sliding Leg Curl", 3, "10-15"),
        _exercise("Glute Bridge", 3, "10-15"),
        _exercise("Standing Calf Raise", 3, "12-20"),
    ]
