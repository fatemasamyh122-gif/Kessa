
import json
import os
import time
from google import genai
from google.genai import types
from google.genai.errors import APIError, ServerError

# Set your free Gemini API key from Google AI Studio
API_KEY = os.getenv("GEMINI_API_KEY", "AQ.Ab8RN6LjSfnn8AcsUEro5vEnYZgWZhIsIiVf_Vx5tWBZ6I0UCA")

SYSTEM_PROMPT = """
You are an expert children's story editor and interactive game designer creating content for Egyptian children (ages 6-10).
You will receive a raw Arabic fable. Your goal is to generate a JSON response with the enhanced story, scene image descriptions, an alternate time-travel storyline, a tailored interactive post-story activity, and a wisdom keepsake prompt.

Follow these strict rules:
1. Language: Simplified Modern Standard Arabic with a warm, encouraging Egyptian storytelling tone.
2. Structure:
   - Enhance the original story into clear, engaging scenes.
   - Introduce a "Time Travel" branching point at the end asking: "تحب ترجع بالزمن وتغير القصة؟"
   - Create 1 alternate scenario based on 1 key character decision.
   - Choose 1 post-story activity from these types: ['drag_drop', 'word_puzzle', 'visual_counting', 'paint_by_number', 'real_life_quiz'].
   - ALWAYS include a "wisdom_keepsake" (a short Egyptian-friendly life lesson/quote + image prompt).
3. Image Descriptions: Provide highly detailed visual art prompts in English for 3D animated cartoon style (Disney/Pixar style).

You MUST output ONLY raw JSON matching this EXACT structure:
{
  "story_id": "unique_string_id",
  "title_ar": "اسم القصة بالعربية",
  "moral_ar": "الحكمة الأساسية من القصة",
  "cover_prompt": "English image prompt for story cover",
  "cover_image": "cover.jpg",
  "main_story": [
    {
      "scene_num": 1,
      "text_ar": "نص المشهد الأول...",
      "image_filename": "scene_1.jpg",
      "image_prompt": "English image prompt for scene 1..."
    }
  ],
  "time_travel": {
    "question_ar": "هل تحب نرجع بالزمن ونشوف إيه يحصل لو...",
    "alternate_story": [
      {
        "scene_num": 1,
        "text_ar": "نص المشهد البديل...",
        "image_filename": "alt_scene_1.jpg",
        "image_prompt": "English image prompt for alternate scene 1..."
      }
    ]
  },
  "post_activity": {
    "activity_type": "real_life_quiz",
    "title_ar": "عنوان النشاط",
    "instructions_ar": "تعليمات النشاط للطفل",
    "content": {}
  },
  "wisdom_keepsake": {
    "quote_ar": "مقولة الحكمة القابلة للتحميل",
    "image_filename": "wisdom_keepsake.jpg",
    "image_prompt": "English image prompt for wisdom wallpaper with text badge space"
  }
}
"""


def generate_with_fallback(client, prompt):
  """Tries active current Flash models with automatic retries on 503 capacity errors."""
  candidate_models = [
      "gemini-flash-latest",
      "gemini-3.8-flash",
      "gemini-3.5-flash",
      "gemini-3.5-flash-lite",
      "gemini-flash-lite-latest",
  ]

  for model_name in candidate_models:
    print(f"🔄 Trying model: {model_name}...")
    for attempt in range(1, 4):  # Retry up to 3 times per model if server is busy
      try:
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            ),
        )
        print(f"✅ Success using {model_name}!")
        return response.text
      except ServerError as e:
        if e.code == 503:
          print(
              f"⚠️ {model_name} busy (503). Waiting 5s... (Attempt {attempt}/3)"
          )
          time.sleep(5)
        else:
          print(f"❌ Server error on {model_name}: {e}")
          break
      except APIError as e:
        print(f"❌ API error on {model_name}: {e}")
        break
      except Exception as e:
        print(f"❌ Unexpected error on {model_name}: {e}")
        break

  raise RuntimeError(
      "All models are currently experiencing high server demand. Please wait 1"
      " minute and run the script again."
  )


def process_story(story_folder_path):
  raw_text_path = os.path.join(story_folder_path, "story_raw.txt")
  if not os.path.exists(raw_text_path):
    print(f"Error: {raw_text_path} not found.")
    return

  with open(raw_text_path, "r", encoding="utf-8") as f:
    raw_story = f.read()

  print("🤖 Starting Story Factory...")
  client = genai.Client(api_key=API_KEY)

  full_prompt = f"{SYSTEM_PROMPT}\n\nOriginal Raw Story:\n{raw_story}"
  raw_json_response = generate_with_fallback(client, full_prompt)

  json_data = json.loads(raw_json_response)

  # 1. Save story_data.json
  json_out_path = os.path.join(story_folder_path, "story_data.json")
  with open(json_out_path, "w", encoding="utf-8") as f:
    json.dump(json_data, f, ensure_ascii=False, indent=2)
  print(f"✅ Saved story data to {json_out_path}")

  # 2. Save prompts.txt for manual image generation
  prompts_out_path = os.path.join(story_folder_path, "prompts.txt")
  with open(prompts_out_path, "w", encoding="utf-8") as f:
    f.write(
        f"=== COVER IMAGE ===\nFilename:"
        f" {json_data['cover_image']}\nPrompt: {json_data['cover_prompt']}\n\n"
    )
    f.write("=== MAIN STORY SCENES ===\n")
    for scene in json_data["main_story"]:
      f.write(
          f"Filename: {scene['image_filename']}\nPrompt:"
          f" {scene['image_prompt']}\n\n"
      )
    f.write("=== TIME TRAVEL SCENES ===\n")
    for scene in json_data["time_travel"]["alternate_story"]:
      f.write(
          f"Filename: {scene['image_filename']}\nPrompt:"
          f" {scene['image_prompt']}\n\n"
      )
    f.write(
        f"=== WISDOM KEEPSAKE ===\nFilename:"
        f" {json_data['wisdom_keepsake']['image_filename']}\nPrompt:"
        f" {json_data['wisdom_keepsake']['image_prompt']}\n"
    )

  print(f"🎨 Saved image generation prompts to {prompts_out_path}")


if __name__ == "__main__":
  process_story("stories/sick_lion")