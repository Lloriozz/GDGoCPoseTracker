from typing import Literal

from pydantic import BaseModel, Field


GoalType = Literal["fat_loss", "muscle_gain", "maintenance", "recomp"]
SexType = Literal["male", "female", "other"]
ActivityLevelType = Literal["low", "light", "moderate", "high"]
TrainLocationType = Literal["home", "gym"]
ExperienceLevelType = Literal["beginner", "intermediate", "advanced"]
BudgetLevelType = Literal["low", "medium", "high"]
CookTimePreferenceType = Literal["quick", "moderate", "flexible"]


class UserProfile(BaseModel):
    age: int | None = Field(default=None, ge=10, le=100)
    sex: SexType | None = None
    height_cm: float | None = Field(default=None, ge=100, le=250)
    weight_kg: float | None = Field(default=None, ge=25, le=350)
    goal: GoalType | None = None
    activity_level: ActivityLevelType | None = None
    workout_days_per_week: int | None = Field(default=None, ge=1, le=14)
    train_location: TrainLocationType | None = None
    experience_level: ExperienceLevelType | None = None
    budget_level: BudgetLevelType | None = None
    cook_time_preference: CookTimePreferenceType | None = None
    goal_detail: str | None = Field(default=None, min_length=3, max_length=300)
    injuries: list[str] = Field(default_factory=list)
    diet_preferences: list[str] = Field(default_factory=list)
    allergies: list[str] = Field(default_factory=list)
    preferred_foods: list[str] = Field(default_factory=list)
    disliked_foods: list[str] = Field(default_factory=list)


class UserProfilePatch(BaseModel):
    age: int | None = Field(default=None, ge=10, le=100)
    sex: SexType | None = None
    height_cm: float | None = Field(default=None, ge=100, le=250)
    weight_kg: float | None = Field(default=None, ge=25, le=350)
    goal: GoalType | None = None
    activity_level: ActivityLevelType | None = None
    workout_days_per_week: int | None = Field(default=None, ge=1, le=14)
    train_location: TrainLocationType | None = None
    experience_level: ExperienceLevelType | None = None
    budget_level: BudgetLevelType | None = None
    cook_time_preference: CookTimePreferenceType | None = None
    goal_detail: str | None = Field(default=None, min_length=3, max_length=300)
    injuries: list[str] | None = None
    diet_preferences: list[str] | None = None
    allergies: list[str] | None = None
    preferred_foods: list[str] | None = None
    disliked_foods: list[str] | None = None
