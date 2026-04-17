from __future__ import annotations

import unittest

from app.tools.nutrition_calculator import NutritionCalculator, looks_like_nutrition_request


class NutritionToolTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.calculator = NutritionCalculator()

    def test_detects_nutrition_request_from_multiple_items(self) -> None:
        self.assertTrue(
            looks_like_nutrition_request("200g uc ga, 100g gao song, 2 qua trung")
        )
        self.assertFalse(looks_like_nutrition_request("Lap lich tap cho toi"))
        self.assertFalse(
            looks_like_nutrition_request(
                "Toi nam 24 tuoi, cao 175cm, nang 72kg, tap 4 buoi moi tuan o gym. Hay tinh TDEE va macro cho toi."
            )
        )

    def test_parser_reads_precise_items(self) -> None:
        items = self.calculator.parse_message("200g uc ga, 100g gao song, 2 qua trung")
        self.assertEqual(len(items), 3)
        self.assertEqual([item.unit for item in items], ["g", "g", "qua"])
        self.assertEqual([item.name for item in items], ["uc ga", "gao song", "trung"])

    def test_precise_calculation_uses_catalog_numbers(self) -> None:
        result = self.calculator.build_estimate("200g uc ga, 100g gao song, 2 qua trung")
        estimate = result["tool_results"]["nutrition_estimate"]
        self.assertEqual(estimate["mode"], "precise")
        self.assertFalse(result["needs_clarification"])
        self.assertEqual(len(estimate["items"]), 3)
        self.assertAlmostEqual(estimate["totals"]["calories"], 743.0)
        self.assertAlmostEqual(estimate["totals"]["protein_g"], 64.4)
        self.assertAlmostEqual(estimate["totals"]["carb_g"], 80.4)
        self.assertAlmostEqual(estimate["totals"]["fat_g"], 15.3)

    def test_estimate_mode_uses_portion_templates(self) -> None:
        result = self.calculator.build_estimate("1 bat com, 1 phan pho", mode="estimated")
        estimate = result["tool_results"]["nutrition_estimate"]
        self.assertEqual(estimate["mode"], "estimated")
        self.assertFalse(result["needs_clarification"])
        self.assertAlmostEqual(estimate["totals"]["calories"], 688.0)
        self.assertAlmostEqual(estimate["totals"]["protein_g"], 32.3)
        self.assertAlmostEqual(estimate["totals"]["carb_g"], 100.1)
        self.assertAlmostEqual(estimate["totals"]["fat_g"], 16.5)

    def test_ambiguous_portions_ask_for_clarification_first(self) -> None:
        result = self.calculator.build_estimate("1 bat com, 1 phan pho")
        self.assertTrue(result["needs_clarification"])
        self.assertIn("khau phan pho bien", result["reply"].lower())

    def test_partial_unmatched_items_are_reported(self) -> None:
        result = self.calculator.build_estimate("200g uc ga, 100g rong bien la")
        estimate = result["tool_results"]["nutrition_estimate"]
        self.assertEqual(len(estimate["items"]), 1)
        self.assertEqual(estimate["unmatched_items"], ["rong bien la"])
        self.assertEqual(estimate["unmatched_inputs"], ["100g rong bien la"])
        self.assertAlmostEqual(estimate["totals"]["calories"], 240.0)


if __name__ == "__main__":
    unittest.main()
