import unittest

from core.model_brand import get_model_brand


class ModelBrandTests(unittest.TestCase):
    def test_qwen_models_are_attributed_to_alibaba_cloud(self):
        brand = get_model_brand("qwen3.8:27b")
        self.assertEqual(brand.display_name, "Qwen")
        self.assertEqual(brand.company, "Alibaba Cloud")
        self.assertEqual(brand.app_title, "Alibaba Cloud AI Assistant")
        self.assertEqual(brand.assistant_name, "Alibaba Cloud")

    def test_deepseek_model_changes_brand(self):
        brand = get_model_brand("deepseek-r1:14b")
        self.assertEqual(brand.display_name, "DeepSeek")
        self.assertEqual(brand.company, "DeepSeek")
        self.assertEqual(brand.app_title, "DeepSeek AI Assistant")
        self.assertEqual(brand.assistant_name, "DeepSeek")

    def test_meta_llama_model(self):
        brand = get_model_brand("llama3.2:3b")
        self.assertEqual(brand.display_name, "Llama")
        self.assertEqual(brand.company, "Meta")
        self.assertEqual(brand.app_title, "Meta AI Assistant")

    def test_google_gemma_model(self):
        brand = get_model_brand("gemma3:12b")
        self.assertEqual(brand.company, "Google")

    def test_huggingface_namespace_is_supported(self):
        brand = get_model_brand("hf.co/library/qwen3:8b")
        self.assertEqual(brand.company, "Alibaba Cloud")

    def test_unknown_model_uses_neutral_brand(self):
        brand = get_model_brand("my-private-model:latest")
        self.assertEqual(brand.app_title, "Local AI Assistant")
        self.assertEqual(brand.company, "Разработчик не определён")


if __name__ == "__main__":
    unittest.main()
