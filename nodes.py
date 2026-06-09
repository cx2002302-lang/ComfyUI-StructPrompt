"""ComfyUI custom node for MiniMax Ideogram4 prompt generation."""

import json
import os
import sys

# Handle both relative import (ComfyUI plugin loading) and absolute import (direct execution)
try:
    from .llm_client import call_minimax_chat
except ImportError:
    from llm_client import call_minimax_chat


class LLMJsonPrompt:
    """Generate structured Ideogram4 prompt using MiniMax API. (Legacy single-mode node)
    
    SECURITY: api_key is read ONLY from MINIMAX_API_KEY environment variable.
    It is NEVER exposed as a frontend widget to prevent PNG metadata leaks.
    """
    
    CATEGORY = "prompt"
    FUNCTION = "generate_prompt"
    RETURN_TYPES = ("STRING", "STRING",)
    RETURN_NAMES = ("ideogram4_prompt", "simple_prompt",)
    OUTPUT_IS_LIST = (False, False,)
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "user_prompt": ("STRING", {
                    "multiline": True,
                    "default": "a beautiful sunset over mountains, digital art",
                    "placeholder": "Describe what you want to generate...",
                }),
            },
            "optional": {
                "model": ("STRING", {
                    "default": "MiniMax-M3",
                    "placeholder": "任意模型名，如 gpt-4o, claude-3-5-sonnet...",
                }),
                "temperature": ("FLOAT", {
                    "default": 0.7,
                    "min": 0.0,
                    "max": 2.0,
                    "step": 0.1,
                }),
                "max_tokens": ("INT", {
                    "default": 4096,
                    "min": 512,
                    "max": 8192,
                    "step": 256,
                }),
            },
        }
    
    def generate_prompt(self, user_prompt: str, model: str = "MiniMax-M3",
                       temperature: float = 0.7, max_tokens: int = 4096):
        """Generate Ideogram4 structured prompt via MiniMax API."""
        if not user_prompt.strip():
            return ("", "")
        
        try:
            ideogram4_json = call_minimax_chat(
                user_prompt=user_prompt,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return (ideogram4_json, user_prompt)
        except Exception as e:
            error_msg = f"ERROR: {str(e)}"
            return (error_msg, user_prompt)


class LLMJsonPromptAdvanced:
    """Advanced MiniMax Ideogram4 prompt with 3 modes: expand, detailed, JSON fix.
    
    SECURITY: api_key is read ONLY from MINIMAX_API_KEY environment variable.
    It is NEVER exposed as a frontend widget to prevent PNG metadata leaks.
    """
    
    CATEGORY = "prompt"
    FUNCTION = "generate_prompt"
    RETURN_TYPES = ("STRING", "STRING",)
    RETURN_NAMES = ("ideogram4_prompt", "mode_used",)
    OUTPUT_IS_LIST = (False, False,)
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "user_prompt": ("STRING", {
                    "multiline": True,
                    "default": "",
                    "placeholder": "输入你的描述或JSON...",
                }),
                "mode": (["普通扩写", "详细描述", "JSON修复"], {
                    "default": "普通扩写",
                }),
                "seed": ("INT", {
                    "default": 0,
                    "min": 0,
                    "max": 999999,
                    "step": 1,
                }),
            },
            "optional": {
                "model": ("STRING", {
                    "default": "MiniMax-M3",
                    "placeholder": "任意模型名，如 gpt-4o, claude-3-5-sonnet...",
                }),
                "temperature": ("FLOAT", {
                    "default": 0.6,
                    "min": 0.0,
                    "max": 2.0,
                    "step": 0.1,
                }),
                "max_tokens": ("INT", {
                    "default": 4096,
                    "min": 512,
                    "max": 8192,
                    "step": 256,
                }),
            },
        }
    
    def generate_prompt(self, user_prompt: str, mode: str = "普通扩写", seed: int = 0,
                       model: str = "MiniMax-M3",
                       temperature: float = 0.6, max_tokens: int = 4096):
        """Generate Ideogram4 structured prompt via MiniMax API with selected mode."""
        if not user_prompt.strip():
            return ("", mode)
        
        try:
            ideogram4_json = call_minimax_chat(
                user_prompt=user_prompt,
                mode=mode,
                seed=seed,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return (ideogram4_json, mode)
        except Exception as e:
            error_msg = f"ERROR: {str(e)}"
            return (error_msg, mode)


class Ideogram4ParamBuilder:
    """Build ComfyUI API parameters for Ideogram4 workflow."""
    
    CATEGORY = "prompt"
    FUNCTION = "build_params"
    RETURN_TYPES = ("STRING", "INT", "INT", "INT", "FLOAT", "FLOAT",)
    RETURN_NAMES = ("preset_json", "steps", "width", "height", "mu", "std",)
    
    @classmethod
    def INPUT_TYPES(cls):
        presets = ["Default", "Quality", "Turbo"]
        return {
            "required": {
                "preset": (presets, {"default": "Default"}),
                "width": ("INT", {"default": 1024, "min": 256, "max": 2048, "step": 16}),
                "height": ("INT", {"default": 1024, "min": 256, "max": 2048, "step": 16}),
            },
        }
    
    def build_params(self, preset: str, width: int, height: int):
        """Return preset parameters."""
        presets = {
            "Default": {"num_steps": 20, "mu": 0.0, "std": 1.75, "preset_id": "V4_DEFAULT_20"},
            "Quality": {"num_steps": 48, "mu": 0.0, "std": 1.5,  "preset_id": "V4_QUALITY_48"},
            "Turbo":   {"num_steps": 12, "mu": 0.5, "std": 1.75, "preset_id": "V4_TURBO_12"},
        }
        p = presets.get(preset, presets["Default"])
        preset_json = json.dumps(p, ensure_ascii=False)
        return (preset_json, p["num_steps"], width, height, p["mu"], p["std"])


NODE_CLASS_MAPPINGS = {
    "LLMJsonPrompt": LLMJsonPrompt,
    "LLMJsonPromptAdvanced": LLMJsonPromptAdvanced,
    "Ideogram4ParamBuilder": Ideogram4ParamBuilder,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "LLMJsonPrompt": "LLM JSON Prompt",
    "LLMJsonPromptAdvanced": "LLM JSON Prompt (Advanced)",
    "Ideogram4ParamBuilder": "Ideogram4 Param Builder",
}
