"""OpenAI-compatible API client for generating structured image prompts.

Supports any OpenAI-compatible API endpoint (MiniMax, OpenAI, custom proxy, etc.)
Configuration priority (highest to lowest):
  1. Environment variables: OPENAI_BASE_URL / MINIMAX_BASE_URL, OPENAI_API_KEY / MINIMAX_API_KEY
  2. Plugin directory config.json (copy from config.json.example)
"""

import json
import os
import urllib.request
import urllib.error
from typing import Optional

# Cached config file content
_CONFIG_CACHE = None


def _get_plugin_dir() -> str:
    """Get the directory where this module is located."""
    return os.path.dirname(os.path.abspath(__file__))


def _load_config_file() -> dict:
    """Load config.json from plugin directory. Returns empty dict if not found."""
    global _CONFIG_CACHE
    if _CONFIG_CACHE is not None:
        return _CONFIG_CACHE
    
    config_path = os.path.join(_get_plugin_dir(), "config.json")
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            _CONFIG_CACHE = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        _CONFIG_CACHE = {}
    
    return _CONFIG_CACHE


def _get_config_value(env_vars: list, config_key: str, default: str = "") -> str:
    """Get config value with priority: env var > config.json > default.
    
    Args:
        env_vars: List of environment variable names to check in order
        config_key: Key name in config.json
        default: Fallback default value
    """
    # 1. Check environment variables
    for var in env_vars:
        val = os.environ.get(var)
        if val:
            return val
    
    # 2. Check config.json
    cfg = _load_config_file()
    val = cfg.get(config_key)
    if val:
        return str(val)
    
    # 3. Return default
    return default


def _get_base_url() -> str:
    """Get API base URL from environment variables or config.json."""
    return _get_config_value(
        ["OPENAI_BASE_URL", "MINIMAX_BASE_URL"],
        "base_url",
        "https://api.minimaxi.com"
    )


def _get_api_key() -> str:
    """Get API key from environment variables or config.json."""
    return _get_config_value(
        ["OPENAI_API_KEY", "MINIMAX_API_KEY"],
        "api_key"
    )

# Mode 1: 普通扩写 —— 简单描述 → 丰富扩写 + 合规JSON
SYSTEM_PROMPT_EXPAND = """You are an elite creative prompt expansion engine for Ideogram 4, a state-of-the-art text-to-image model with a **strictly structured JSON prompting interface**.

The user provides a brief idea. Your job is to **EXPAND** it into a maximally rich, vivid, structured JSON caption that unlocks Ideogram 4's full creative potential. Be imaginative and artistic, but the **JSON format must be pixel-perfect compliant**.

## Expansion Rules (Be Bold and Creative)

Transform the user's simple idea into a visually stunning scene by adding:
1. **Atmospheric depth**: time of day, weather, air quality, humidity, mood, emotional resonance
2. **Lighting artistry**: key light direction, fill light, rim light, bounce light, color temperature shifts, caustics, volumetrics, god rays
3. **Compositional intelligence**: camera angle (low angle, bird's eye, Dutch tilt), lens characteristics, depth of field, bokeh quality, rule of thirds, leading lines, framing devices
4. **Textural richness**: material properties, surface imperfections, fabric weaves, skin pores, weathering, patina, reflections, subsurface scattering
5. **Color storytelling**: dominant palette, accent colors, color temperature gradients, complementary or analogous harmonies, atmospheric perspective color shifts
6. **Environmental narrative**: spatial depth cues, ambient life, background activity, architectural details, natural elements

**Be creative and imaginative.** Do not hold back on detail. The longer and richer your descriptions, the better the image quality.

## CRITICAL: Output Format Compliance

Return **ONLY** a single valid JSON object. No markdown fences, no explanations, no trailing commas.

### Exact Key Order (MANDATORY — deviation hurts quality)

**Photo captions** use this key order:
```json
{
  "high_level_description": "",
  "style_description": {
    "aesthetics": "",
    "lighting": "",
    "photo": "",
    "medium": "photograph",
    "color_palette": []
  },
  "compositional_deconstruction": {
    "background": "",
    "elements": [
      {
        "type": "obj",
        "bbox": [0, 0, 0, 0],
        "desc": "",
        "color_palette": []
      }
    ]
  }
}
```

**Non-photo captions** (illustration, painting, 3D render, etc.) use this key order:
```json
{
  "high_level_description": "",
  "style_description": {
    "aesthetics": "",
    "lighting": "",
    "medium": "",
    "art_style": "",
    "color_palette": []
  },
  "compositional_deconstruction": {
    "background": "",
    "elements": [
      {
        "type": "obj",
        "bbox": [0, 0, 0, 0],
        "desc": "",
        "color_palette": []
      }
    ]
  }
}
```

**Rules:**
- Choose **exactly ONE** of `photo` + `medium: "photograph"` **OR** `art_style` + non-photo `medium`. Never both.
- `color_palette` is optional but strongly recommended. If included, keep it in the **final position**.
- All keys must appear **exactly as spelled**. No extra keys. No renamed keys.

## Field Rules (Detailed)

### high_level_description
- 1-2 vivid sentences summarizing the entire scene, setting, subjects, and mood.

### style_description
- `aesthetics`: Overall visual style and treatment (e.g. "cinematic noir with crushed blacks and lifted shadows", "whimsical storybook illustration with hand-painted textures").
- `lighting`: Light source, direction, quality, color temperature (e.g. "warm tungsten key from camera-left, cool blue ambient fill, sharp rim light from behind").
- `photo`: Camera, lens, film stock, photographic treatment. Use **empty string `""`** if medium is not photographic.
- `medium`: `"photograph"`, `"illustration"`, `"oil_painting"`, `"3d_render"`, `"watercolor"`, `"digital_painting"`, `"graphic_design"`, etc.
- `art_style`: Specific art style for non-photo (e.g. "flat vector with bold outlines and limited palette", "oil painting with visible impasto brushstrokes"). Only use with non-photo medium.
- `color_palette`: Array of 3–6 (up to 16) dominant colors as uppercase hex `#RRGGBB`. Include background colors. Include highlight and shadow colors for controlled lighting.

### compositional_deconstruction.background
- Rich description of the environment **ONLY**. Do NOT describe subjects/elements here. Include depth cues, atmosphere, and ambient details.

### compositional_deconstruction.elements
- Array of 3–8 elements, listed roughly **background-to-foreground**.
- Each element:
  - `type`: Always `"obj"` (or `"text"` if the element contains rendered text).
  - `bbox`: **`[y_min, x_min, y_max, x_max]`** in 0–1000 normalized coordinates. Origin top-left. Must satisfy `0 ≤ y_min < y_max ≤ 1000` and `0 ≤ x_min < x_max ≤ 1000`. Match the prose description.
  - `desc`: **EXTREMELY DETAILED** natural description. Include: identity, pose/orientation, exact location in frame, relative size, key visual details (textures, markings, materials), gaze or motion direction, light interaction specific to this element, facial expression if human. Write like an art director briefing a master painter.
  - `color_palette`: Optional. Up to 5 colors as uppercase hex `#RRGGBB`. Should be harmonious with the overall `style_description.color_palette`.

## Hard Constraints

- Output **valid JSON only**. No markdown code blocks. No explanations.
- Use **ONLY** the keys defined above, **exactly as spelled**, in the **exact order** shown.
- All text in **English**.
- Hex colors: **uppercase** `#RRGGBB` only. No shorthand like `#fff`.
- `bbox` order is **`[y_min, x_min, y_max, x_max]`**. Not `[x_min, y_min, x_max, y_max]`.
- When serializing, use compact JSON: no extra spaces, no line breaks inside strings."""

# Mode 2: 详细描述 —— 保留所有细节，只做结构转换
SYSTEM_PROMPT_CONVERT = """You are an expert prompt converter for Ideogram 4, a state-of-the-art text-to-image model with a **strictly structured JSON prompting interface**.

The user provides a detailed description (possibly a long paragraph or a reverse-engineered prompt from another platform like Midjourney, DALL-E, or MiniMax web).

Your job: Convert it into a strictly valid Ideogram4 structured JSON while **PRESERVING EVERY SINGLE DETAIL** from the original.

## Preservation Rules (Mandatory)

1. **Do NOT add** elements, objects, or details not mentioned by the user.
2. **Do NOT remove** any detail from the original description. Every color, texture, pose, lighting note, and compositional cue must survive the conversion.
3. **Do NOT change** the artistic style, mood, or medium implied by the user.
4. **Do NOT expand** beyond what the user wrote. If they described 3 elements, you output 3 elements. No more, no less.
5. Structure the user's existing details into the JSON format. Do not invent new descriptions.

## CRITICAL: Output Format Compliance

Return **ONLY** a single valid JSON object. No markdown fences, no explanations, no trailing commas.

### Exact Key Order (MANDATORY)

**Photo:** `high_level_description` → `style_description` (`aesthetics`, `lighting`, `photo`, `medium`, `color_palette`) → `compositional_deconstruction` (`background`, `elements`)

**Non-photo:** `high_level_description` → `style_description` (`aesthetics`, `lighting`, `medium`, `art_style`, `color_palette`) → `compositional_deconstruction` (`background`, `elements`)

**Rules:**
- Choose **exactly ONE** of `photo` + `medium: "photograph"` **OR** `art_style` + non-photo `medium`.
- `color_palette` optional but keep in final position if included.

## Field Rules

- `high_level_description`: 1-2 sentences summarizing the user's scene.
- `style_description`: Extract style, lighting, camera, medium from user's text. Use `""` for fields the user didn't specify.
- `style_description.color_palette`: 3–6 (up to 16) colors as uppercase hex `#RRGGBB`. Only include if user mentioned colors or clearly implied.
- `compositional_deconstruction.background`: Environment behind subjects. Must NOT overlap with element descriptions.
- `compositional_deconstruction.elements`: One object per visual element the user described.
  - `type`: `"obj"` (or `"text"` for rendered text)
  - `bbox`: **`[y_min, x_min, y_max, x_max]`**, 0–1000. Infer positions from compositional cues.
  - `desc`: Use the user's **OWN words** as much as possible. Preserve their exact visual details.
  - `color_palette`: Up to 5 colors as uppercase hex `#RRGGBB`, only if mentioned.

## Hard Constraints

- Valid JSON only. No markdown. No explanations.
- ONLY specified keys, exact spelling, exact order.
- All text in English.
- Hex: uppercase `#RRGGBB` only.
- `bbox`: `[y_min, x_min, y_max, x_max]`."""

# Mode 3: JSON修复 —— 纯修复格式，不改内容
SYSTEM_PROMPT_FIX = """You are an expert JSON repair assistant for Ideogram 4.

The user provides a JSON object (partial, malformed, or with subtle errors). Your job is to repair it into strictly valid Ideogram4 JSON.

## Repair Rules (Mandatory)

1. **Keep ALL existing content UNCHANGED** unless it violates a hard format rule.
2. **Fix bbox values**: Must be **`[y_min, x_min, y_max, x_max]`** with integers `0 ≤ y_min < y_max ≤ 1000` and `0 ≤ x_min < x_max ≤ 1000`.
3. **Fix hex colors**: Must be uppercase `#RRGGBB`. No shorthand.
4. **Fix color_palette**: Must be array of strings. `style_description.color_palette` up to 16 entries. Per-element `color_palette` up to 5 entries.
5. **Fill missing required keys** with reasonable defaults inferred from context. Do NOT invent creative content.
6. **Remove extra keys** not in the spec.
7. **Do NOT rewrite descriptions** unless they are empty or broken. Preserve original wording.
8. If input is natural language, convert to structured JSON preserving every detail.

## CRITICAL: Output Format Compliance

Return **ONLY** a single valid JSON object. No markdown fences, no explanations.

### Exact Key Order (MANDATORY)

**Photo:** `high_level_description` → `style_description` (`aesthetics`, `lighting`, `photo`, `medium`, `color_palette`) → `compositional_deconstruction` (`background`, `elements`)

**Non-photo:** `high_level_description` → `style_description` (`aesthetics`, `lighting`, `medium`, `art_style`, `color_palette`) → `compositional_deconstruction` (`background`, `elements`)

Each element key order: `"obj"`: `type`, `bbox`, `desc`, `color_palette`. `"text"`: `type`, `bbox`, `text`, `desc`, `color_palette`.

## Hard Constraints

- Valid JSON only. No markdown. No explanations.
- ONLY specified keys, exact spelling, exact order.
- All text in English.
- Hex: uppercase `#RRGGBB` only.
- `bbox`: `[y_min, x_min, y_max, x_max]`."""


def _strip_think_tags(content: str) -> str:
    """Strip MiniMax <think> tags from response."""
    while "<think>" in content and "</think>" in content:
        start = content.find("<think>")
        end = content.find("</think>") + len("</think>")
        content = content[:start] + content[end:]
    return content.strip()


def _clear_proxy_env():
    """Clear broken proxy env vars that block direct HTTPS."""
    cleared = {}
    for var in ["HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"]:
        val = os.environ.pop(var, None)
        if val is not None:
            cleared[var] = val
    return cleared


def _restore_proxy_env(cleared: dict):
    """Restore previously cleared proxy env vars."""
    for var, val in cleared.items():
        if val is not None:
            os.environ[var] = val


def _get_variation_hint(seed: int) -> str:
    """Generate a variation hint based on seed for 'gacha' effect in expand mode."""
    variations = [
        "In this variation, emphasize dramatic cinematic lighting and atmospheric depth with rich volumetric effects.",
        "In this variation, focus on rich surface textures, material details, and tactile qualities across all elements.",
        "In this variation, emphasize vibrant color harmony, bold contrasts, and dynamic compositional energy.",
        "In this variation, focus on ethereal, dreamy mood with soft diffusion, gentle bokeh, and magical atmosphere.",
        "In this variation, emphasize sharp architectural precision, geometric framing, and strong perspective lines.",
        "In this variation, focus on naturalistic botanical detail, organic forms, and rich environmental storytelling.",
        "In this variation, emphasize golden-hour warmth, lens flare, nostalgic film tone, and emotional resonance.",
        "In this variation, focus on moody chiaroscuro lighting, deep shadow contrast, and noir atmosphere.",
        "In this variation, emphasize futuristic sleekness, holographic reflections, and high-tech material surfaces.",
        "In this variation, focus on rustic warmth, handcrafted imperfections, and intimate small-scale details.",
        "In this variation, emphasize surreal juxtaposition, impossible perspectives, and dreamlike spatial logic.",
        "In this variation, focus on minimalist restraint, generous negative space, and precise focal points.",
    ]
    return variations[seed % len(variations)]


def call_minimax_chat(
    user_prompt: str,
    mode: str = "普通扩写",
    seed: int = 0,
    api_key: Optional[str] = None,
    model: str = "MiniMax-M3",
    base_url: Optional[str] = None,
    temperature: float = 0.6,
    max_tokens: int = 4096,
) -> str:
    """Call LLM API to generate structured prompt."""
    key = api_key or _get_api_key()
    if not key:
        raise ValueError(
            "API key not provided. Set OPENAI_API_KEY or MINIMAX_API_KEY environment variable."
        )
    
    url_base = base_url or _get_base_url()
    
    if mode == "普通扩写":
        system_content = SYSTEM_PROMPT_EXPAND
        variation = _get_variation_hint(seed)
        user_content = f"Expand the following simple idea into a maximally rich Ideogram4 structured prompt. {variation}\n\nUser's idea:\n{user_prompt}"
    elif mode == "详细描述":
        system_content = SYSTEM_PROMPT_CONVERT
        user_content = f"Convert the following detailed description into Ideogram4 structured JSON. Preserve every detail. Do not add or remove anything.\n\nDescription:\n{user_prompt}"
    elif mode == "JSON修复":
        system_content = SYSTEM_PROMPT_FIX
        user_content = f"Repair the following JSON into strictly valid Ideogram4 format. Keep all original content. Only fix format errors.\n\nContent:\n{user_prompt}"
    else:
        raise ValueError(f"Unknown mode: {mode}")
    
    cleared_proxies = _clear_proxy_env()
    try:
        url = f"{url_base}/v1/chat/completions"
        
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_content},
                {"role": "user", "content": user_content}
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }
        
        # MiniMax-specific: disable thinking if using MiniMax endpoint
        if "minimaxi" in url_base.lower():
            payload["thinking"] = {"type": "disabled"}
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}",
        }
        
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            content = data["choices"][0]["message"]["content"]
            content = _strip_think_tags(content)
            content = content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            parsed = json.loads(content)
            # Compact JSON format closer to training distribution
            return json.dumps(parsed, ensure_ascii=False, separators=(",", ":"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8") if hasattr(e, "read") else ""
        raise RuntimeError(f"API HTTP {e.code}: {body}")
    except json.JSONDecodeError as e:
        raise RuntimeError(f"API returned invalid JSON: {e}")
    except Exception as e:
        raise RuntimeError(f"API error: {e}")
    finally:
        _restore_proxy_env(cleared_proxies)
