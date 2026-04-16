from __future__ import annotations

import unittest

from app.rag.retriever import KnowledgeRetriever
from app.schemas.user_profile import UserProfile


class KnowledgeRetrieverTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.retriever = KnowledgeRetriever(top_k=3, min_score=1)

    def test_retrieves_budget_and_quick_meal_context(self) -> None:
        profile = UserProfile(
            goal="muscle_gain",
            budget_level="low",
            cook_time_preference="quick",
        )
        results = self.retriever.retrieve(
            message="minh can bua an nhanh va tiet kiem de tang co",
            intent="request_meal_guidance",
            profile=profile,
        )
        ids = {item["id"] for item in results}
        self.assertIn("meal_budget_protein", ids)
        self.assertIn("meal_quick_prep", ids)

    def test_retrieves_constraint_specific_meal_context(self) -> None:
        profile = UserProfile(
            diet_preferences=["vegetarian"],
            allergies=["milk"],
        )
        results = self.retriever.retrieve(
            message="toi an chay va khong dung sua nen chon nguon protein nao",
            intent="general_fitness_qa",
            profile=profile,
        )
        ids = {item["id"] for item in results}
        self.assertIn("vegetarian_protein_sources", ids)
        self.assertIn("dairy_free_substitutions", ids)

    def test_retrieves_injury_specific_workout_context(self) -> None:
        profile = UserProfile(
            injuries=["knee"],
            train_location="gym",
        )
        results = self.retriever.retrieve(
            message="dau goi hoi dau thi nen tap chan sao cho an toan",
            intent="request_workout_plan",
            profile=profile,
        )
        ids = {item["id"] for item in results}
        self.assertIn("knee_friendly_training", ids)

    def test_meal_retrieval_excludes_workout_categories_even_with_injury_profile(self) -> None:
        profile = UserProfile(
            goal="muscle_gain",
            budget_level="low",
            cook_time_preference="quick",
            injuries=["knee"],
        )
        results = self.retriever.retrieve(
            message="goi y lich an nhanh va tiet kiem cho toi",
            intent="request_meal_guidance",
            profile=profile,
        )
        categories = {item["category"] for item in results}
        ids = {item["id"] for item in results}
        self.assertTrue(categories)
        self.assertTrue(all(category.startswith("meal_") for category in categories))
        self.assertNotIn("knee_friendly_training", ids)

    def test_workout_retrieval_excludes_meal_categories_even_with_budget_profile(self) -> None:
        profile = UserProfile(
            goal="muscle_gain",
            train_location="gym",
            injuries=["knee"],
            budget_level="low",
            cook_time_preference="quick",
            preferred_foods=["pho"],
        )
        results = self.retriever.retrieve(
            message="lap lich tap 4 buoi cho toi va luu y dau goi",
            intent="request_workout_plan",
            profile=profile,
        )
        categories = {item["category"] for item in results}
        self.assertTrue(categories)
        self.assertTrue(
            all(category.startswith(("workout_", "recovery_")) for category in categories)
        )


if __name__ == "__main__":
    unittest.main()
