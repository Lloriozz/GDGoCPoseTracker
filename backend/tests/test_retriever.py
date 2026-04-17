from __future__ import annotations

import shutil
import unittest
from pathlib import Path
from uuid import uuid4

from app.core.config import settings
from app.rag.retriever import KnowledgeRetriever
from app.rag.wiki_retriever import WikiKnowledgeRetriever
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

class WikiKnowledgeRetrieverTestCase(unittest.TestCase):
    _temp_root = Path("data") / "_tmp_tests"

    @classmethod
    def setUpClass(cls) -> None:
        cls._original_wiki_path = settings.wiki_path
        cls._original_wiki_enabled = settings.wiki_enabled
        cls._temp_root.mkdir(parents=True, exist_ok=True)

    @classmethod
    def tearDownClass(cls) -> None:
        settings.wiki_path = cls._original_wiki_path
        settings.wiki_enabled = cls._original_wiki_enabled

    def setUp(self) -> None:
        self.temp_dir = self._temp_root / f"wiki_case_{uuid4().hex}"
        (self.temp_dir / "nutrition").mkdir(parents=True, exist_ok=True)
        (self.temp_dir.parent / "raw").mkdir(parents=True, exist_ok=True)
        settings.wiki_enabled = True
        settings.wiki_path = str(self.temp_dir)

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_prefers_concept_pages_over_source_summary_pages(self) -> None:
        self._write_page(
            self.temp_dir / "nutrition" / "muscle-gain-principles.md",
            "# Nguyên Tắc Tăng Cơ\n\n"
            "**Summary**: Trang concept về nguyên tắc tăng cơ và protein.\n\n"
            "**Page type**: concept\n\n"
            "**Sources**:\n- raw/source-a.md\n\n"
            "**Last updated**: 2026-04-16\n\n"
            "---\n\n"
            "## Key Points\n\n"
            "- Tăng cơ cần đủ protein và tổng năng lượng phù hợp.\n\n"
            "## Practical Notes\n\n"
            "- Có thể xoay tua món Việt giàu protein.\n\n"
            "## Related Pages\n\n"
            "- [[nutrition/nutrition-home]]\n",
        )
        self._write_page(
            self.temp_dir / "nutrition" / "source-summary-blog-a.md",
            "# Tóm Tắt Nguồn A\n\n"
            "**Summary**: Trang source-summary nhắc lại thực phẩm tăng cơ và protein.\n\n"
            "**Page type**: source-summary\n\n"
            "**Sources**:\n- raw/source-a.md\n\n"
            "**Last updated**: 2026-04-16\n\n"
            "---\n\n"
            "## Key Points\n\n"
            "- Bài blog nhắc đến thực phẩm tăng cơ, protein và carb.\n\n"
            "## Practical Notes\n\n"
            "- Claim còn yếu.\n\n"
            "## Related Pages\n\n"
            "- [[nutrition/muscle-gain-principles]]\n",
        )

        retriever = WikiKnowledgeRetriever(wiki_path=str(self.temp_dir), top_k=2, min_score=1)
        results = retriever.retrieve(
            message="nguyen tac tang co va protein la gi",
            intent="general_fitness_qa",
            profile=UserProfile(goal="muscle_gain"),
        )

        self.assertGreaterEqual(len(results), 1)
        self.assertEqual(results[0]["page_type"], "concept")
        self.assertEqual(results[0]["id"], "nutrition/muscle-gain-principles")

    def test_general_out_of_domain_question_does_not_pull_wiki(self) -> None:
        self._write_page(
            self.temp_dir / "nutrition" / "muscle-gain-principles.md",
            "# Nguyên Tắc Tăng Cơ\n\n"
            "**Summary**: Trang concept về nguyên tắc tăng cơ.\n\n"
            "**Page type**: concept\n\n"
            "**Sources**:\n- raw/source-a.md\n\n"
            "**Last updated**: 2026-04-16\n\n"
            "---\n\n"
            "## Key Points\n\n"
            "- Tăng cơ cần đủ protein.\n\n"
            "## Practical Notes\n\n"
            "- Theo dõi bữa ăn.\n\n"
            "## Related Pages\n\n"
            "- [[nutrition/nutrition-home]]\n",
        )

        retriever = WikiKnowledgeRetriever(wiki_path=str(self.temp_dir), top_k=2, min_score=1)
        results = retriever.retrieve(
            message="cach tao tai khoan ngan hang",
            intent="general_fitness_qa",
            profile=UserProfile(),
        )

        self.assertEqual(results, [])

    def test_reloads_wiki_pages_after_new_ingest_without_reinstantiating(self) -> None:
        retriever = WikiKnowledgeRetriever(wiki_path=str(self.temp_dir), top_k=2, min_score=1)
        self.assertEqual(
            retriever.retrieve(
                message="nguyen tac tang co la gi",
                intent="general_fitness_qa",
                profile=UserProfile(goal="muscle_gain"),
            ),
            [],
        )

        self._write_page(
            self.temp_dir / "nutrition" / "muscle-gain-principles.md",
            "# Nguyên Tắc Tăng Cơ\n\n"
            "**Summary**: Trang concept về nguyên tắc tăng cơ.\n\n"
            "**Page type**: concept\n\n"
            "**Sources**:\n- raw/source-a.md\n\n"
            "**Last updated**: 2026-04-16\n\n"
            "---\n\n"
            "## Key Points\n\n"
            "- Tăng cơ cần đủ protein.\n\n"
            "## Practical Notes\n\n"
            "- Ưu tiên món Việt dễ bám.\n\n"
            "## Related Pages\n\n"
            "- [[nutrition/nutrition-home]]\n",
        )

        results = retriever.retrieve(
            message="nguyen tac tang co la gi",
            intent="general_fitness_qa",
            profile=UserProfile(goal="muscle_gain"),
        )
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], "nutrition/muscle-gain-principles")

    def _write_page(self, path: Path, content: str) -> None:
        path.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
