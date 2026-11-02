"""Infer a model family and its creator from common Ollama model names.

Ollama's local tags API does not consistently expose the model publisher, so
this module uses a conservative name-to-brand map and a neutral fallback.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelBrand:
    display_name: str
    company: str

    @property
    def assistant_name(self) -> str:
        if self.company == "Разработчик не определён":
            return "Local AI"
        return self.company

    @property
    def app_title(self) -> str:
        if self.company == "Разработчик не определён":
            return "Local AI Assistant"
        return f"{self.company} AI Assistant"


# Prefixes are checked longest-first where names overlap.
_MODEL_BRANDS = (
    ("gpt-oss", "GPT-OSS", "OpenAI"),
    ("deepseek", "DeepSeek", "DeepSeek"),
    ("qwen", "Qwen", "Alibaba Cloud"),
    ("llama", "Llama", "Meta"),
    ("gemma", "Gemma", "Google"),
    ("codegemma", "CodeGemma", "Google"),
    ("codestral", "Codestral", "Mistral AI"),
    ("mixtral", "Mixtral", "Mistral AI"),
    ("mistral", "Mistral", "Mistral AI"),
    ("phi", "Phi", "Microsoft"),
    ("command-r", "Command R", "Cohere"),
    ("command", "Command", "Cohere"),
    ("aya", "Aya", "Cohere"),
    ("granite", "Granite", "IBM"),
    ("nemotron", "Nemotron", "NVIDIA"),
    ("glm", "GLM", "Z.ai"),
    ("chatglm", "ChatGLM", "Z.ai"),
    ("internlm", "InternLM", "Shanghai AI Laboratory"),
    ("minicpm", "MiniCPM", "OpenBMB"),
    ("yi", "Yi", "01.AI"),
    ("solar", "Solar", "Upstage"),
    ("stablelm", "StableLM", "Stability AI"),
    ("stable-code", "Stable Code", "Stability AI"),
    ("falcon", "Falcon", "Technology Innovation Institute"),
    ("olmo", "OLMo", "Allen Institute for AI"),
    ("jamba", "Jamba", "AI21 Labs"),
    ("exaone", "EXAONE", "LG AI Research"),
    ("dbrx", "DBRX", "Databricks"),
    ("nous-hermes", "Nous Hermes", "Nous Research"),
    ("hermes", "Hermes", "Nous Research"),
    ("starcoder", "StarCoder", "BigCode"),
    ("smollm", "SmolLM", "Hugging Face"),
    ("tinyllama", "TinyLlama", "TinyLlama Project"),
)


def get_model_brand(model_name: str) -> ModelBrand:
    """Return a friendly model label and likely creator for an Ollama tag."""
    value = (model_name or "").strip().lower().replace("\\", "/")
    if not value:
        return ModelBrand("Ассистент", "Разработчик не определён")

    # Handle names such as hf.co/organization/model:tag.
    model_id = value.rsplit("/", 1)[-1].split(":", 1)[0]
    model_id = model_id.replace("_", "-")

    for prefix, display_name, company in _MODEL_BRANDS:
        if model_id == prefix or model_id.startswith(prefix + "-") or model_id.startswith(prefix + ".") or model_id.startswith(prefix) and prefix in {"qwen", "llama", "gemma", "deepseek", "mistral", "mixtral", "phi", "granite", "nemotron", "glm", "internlm", "minicpm", "solar", "falcon", "olmo", "jamba", "exaone", "dbrx", "starcoder", "smollm", "tinyllama"}:
            return ModelBrand(display_name, company)

    return ModelBrand("Local AI", "Разработчик не определён")
