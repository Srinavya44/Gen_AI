# app.py
import os
import json
import re
import boto3
import streamlit as st

# -----------------------
# Configuration
# -----------------------
MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "meta.llama3-8b-instruct-v1:0")
REGION = os.environ.get("AWS_REGION", "ap-south-1")

# Create bedrock client
bedrock = boto3.client("bedrock-runtime", region_name=REGION)


# -----------------------
# Dietary rules & replacements
# -----------------------
# dietary_rules = {
#     "none": {
#         "blocked": [],
#         "replacement": {}
#     },
#     "vegan": {
#         "blocked": ["chicken", "fish", "beef", "pork", "egg", "milk", "cheese", "yogurt", "butter", "honey"],
#         "replacement": {
#             "chicken": "tofu",
#             "fish": "jackfruit",
#             "beef": "tempeh",
#             "pork": "jackfruit",
#             "egg": "flax egg",
#             "milk": "soy milk",
#             "cheese": "vegan cheese",
#             "yogurt": "coconut yogurt",
#             "butter": "vegan butter",
#             "honey": "maple syrup"
#         }
#     },
#     "vegetarian": {
#         "blocked": ["chicken", "fish", "beef", "pork"],
#         "replacement": {
#             "chicken": "paneer",
#             "fish": "mushrooms",
#             "beef": "soy chunks",
#             "pork": "jackfruit"
#         }
#     },
#     "pescatarian": {
#         "blocked": ["chicken", "beef", "pork"],
#         "replacement": {
#             "chicken": "salmon",
#             "beef": "tuna",
#             "pork": "salmon"
#         }
#     },
#     "gluten-free": {
#         "blocked": ["wheat", "barley", "rye", "pasta", "all-purpose flour", "breadcrumbs"],
#         "replacement": {
#             "wheat": "gluten-free flour",
#             "barley": "quinoa",
#             "rye": "buckwheat",
#             "pasta": "gluten-free pasta",
#             "all-purpose flour": "gluten-free flour",
#             "breadcrumbs": "crushed gluten-free crackers"
#         }
#     }
# }

# # -----------------------
# # Helpers
# # -----------------------
# def normalize_ingredient_name(s: str) -> str:
#     return s.strip().lower()

# def preprocess_ingredients(raw_ingredients: str, diet_key: str):
#     """Replace blocked ingredients automatically and return (cleaned_string, replacements_list)."""
#     items = [normalize_ingredient_name(i) for i in raw_ingredients.split(",") if i.strip()]
#     processed = []
#     replacements = []  # tuples (original, replaced)
#     rules = dietary_rules.get(diet_key, dietary_rules["none"])
#     blocked = set(rules["blocked"])
#     repl_map = rules["replacement"]

#     for it in items:
#         # exact match replacement first
#         if it in blocked:
#             if it in repl_map:
#                 processed.append(repl_map[it])
#                 replacements.append((it, repl_map[it]))
#             else:
#                 # drop it (no replacement)
#                 replacements.append((it, None))
#         else:
#             # also check partial matches (e.g., "chicken breast" -> "chicken")
#             matched = False
#             for b in blocked:
#                 if b in it:
#                     if b in repl_map:
#                         # replace the blocked substring with replacement
#                         new_it = it.replace(b, repl_map[b])
#                         processed.append(new_it)
#                         replacements.append((it, new_it))
#                     else:
#                         # drop the blocked substring entirely
#                         new_it = re.sub(r"\b" + re.escape(b) + r"\b", "", it).strip()
#                         if new_it:
#                             processed.append(new_it)
#                         replacements.append((it, None))
#                     matched = True
#                     break
#             if not matched:
#                 processed.append(it)

#     # dedupe while preserving order
#     seen = set()
#     processed_unique = []
#     for p in processed:
#         if p not in seen:
#             seen.add(p)
#             processed_unique.append(p)

#     return ", ".join(processed_unique), replacements

def build_prompt(ingredients: str, num_recipes: int, diet: str, difficulty: str, servings: int):
    # """
    # Ask model for a JSON array of recipe objects. Each object:
    # { "title", "servings", "ingredients": [...], "steps": [...], "difficulty", "estimated_time", "notes" }
    # """
    diet_wording = diet if diet != "none" else "no dietary restriction"
    difficulty_text = difficulty if difficulty != "Any" else "Any difficulty"

    prompt = f"""
You are a helpful, precise recipe generator.

Constraints:
- Diet: {diet_wording}. STRICTLY follow this; do NOT include disallowed ingredients.
- Difficulty: {difficulty_text}.
You are an expert chef and nutritionist. Create a recipe based on the user's input, following these rules:

1. INGREDIENTS:
   - Always include the user-provided ingredients.
   - If the user provided ingredients without quantities, assign realistic quantities using standard cooking measurements (grams, cups, tablespoons, teaspoons, etc.).
   - Add any additional ingredients necessary to make the recipe balanced, flavorful, and complete.
   - Respect the dietary preference strictly. If the preference conflicts with a given ingredient, replace it with a suitable alternative of the same function in the recipe, adjusting the quantity as needed.
   - Make sure ingredient list has no duplicates and is easy to read.

2. INSTRUCTIONS:
   - Provide step-by-step instructions.
   - Use clear, concise language.
   - Ensure cooking times and temperatures are specified when relevant.

3. NUTRITION FACTS:
   - Calculate approximate per-serving nutrition values: calories, protein (g), fat (g), carbs (g), and fiber (g).
   - Use standard food composition knowledge to estimate these values based on the ingredients and quantities.

4. OUTPUT FORMAT:
   Return the output in valid JSON with the structure:

Task:
JSON Schema:
[
  {{
    "title": "string",
    "servings": integer,
    "ingredients": [
       {"name": "ingredient name", "quantity": "amount with unit"},
       ...
     ],
    "steps": ["string", "string"],
    "difficulty": "Easy" | "Medium" | "Hard",
    "estimated_time": "string (e.g., '25 minutes')",
    "notes": "string"
     "nutrition_per_serving": {
       "calories": number,
       "protein_g": number,
       "fat_g": number,
       "carbs_g": number,
       "fiber_g": number
     }
  }}
]

Now generate exactly {num_recipes} recipes using only:
{ingredients}

Your entire response must be a single JSON array following the schema above, starting with '[' and ending with ']'.
"""
    return prompt.strip()
def clean_json_output(text: str):
    """Extracts JSON array from any text and returns as Python object."""
    match = re.search(r"\[.*\]", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return None
    return None

def call_bedrock(prompt: str, max_gen_len: int = 700, temperature: float = 0.25, top_p: float = 0.9) -> str:
    """Calls Bedrock and always returns raw text output from the model."""
    payload = {
        "prompt": prompt,
        "max_gen_len": max_gen_len,
        "temperature": temperature,
        "top_p": top_p
    }

    resp = bedrock.invoke_model(
        modelId=MODEL_ID,
        contentType="application/json",
        accept="application/json",
        body=json.dumps(payload).encode("utf-8")
    )

    body_text = resp["body"].read().decode("utf-8")

    try:
        parsed = json.loads(body_text)
        # Common Bedrock output patterns
        if isinstance(parsed, dict):
            if "outputs" in parsed and isinstance(parsed["outputs"], list):
                return parsed["outputs"][0].get("text", "")
            for k in ("generation", "output", "results", "text"):
                if k in parsed and isinstance(parsed[k], str):
                    return parsed[k]
        elif isinstance(parsed, list):
            # If the model directly gave a list, return it as JSON string
            return json.dumps(parsed)
    except json.JSONDecodeError:
        pass

    return body_text  # if parsing as JSON fails, just return raw string


def parse_model_output(raw_text: str):
    """Extracts and parses a JSON array of recipes from model output text."""
    if not raw_text:
        return None

    # Try direct JSON parsing
    try:
        parsed = json.loads(raw_text)
        if isinstance(parsed, list):
            return parsed
    except json.JSONDecodeError:
        pass

    # Try extracting JSON array from within the text
    match = re.search(r"\[\s*\{.*\}\s*\]", raw_text, re.DOTALL)
    if match:
        json_str = match.group(0)
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            # Try fixing trailing commas
            json_str = re.sub(r",\s*([\]}])", r"\1", json_str)
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                return None

    return None

# -----------------------
# Streamlit UI
# -----------------------
st.set_page_config(page_title="AI Recipe Generator", layout="centered", page_icon="🍳")
st.markdown(
    """
    <style>
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background-color: #f8f9fa;
    }

    /* Recipe card styling */
    .recipe-card {
        background: #ffffff;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 20px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        border: 1px solid #e0e0e0;
    }
    .recipe-title {
        font-size: 1.4rem;
        font-weight: bold;
        color: #2c3e50;
        margin-bottom: 10px;
    }
    .recipe-meta {
        font-size: 0.9rem;
        color: #555;
        margin-bottom: 15px;
    }
    .recipe-section-title {
        font-weight: bold;
        margin-top: 15px;
        color: #34495e;
    }
    .recipe-list {
        padding-left: 20px;
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.title("🍳 AI Recipe Generator")

# Sidebar controls
with st.sidebar:
    st.header("Options")
    num_recipes = st.slider("Number of recipes", 1, 5, 2)
    dietary_choice = st.selectbox("Dietary restriction", ["none", "vegan", "vegetarian", "pescatarian", "gluten-free"])
    difficulty = st.selectbox("Preferred difficulty", ["Any", "Easy", "Medium", "Hard"])
    servings = st.number_input("Servings (approx.)", min_value=1, max_value=10, value=2)

st.markdown("Enter the ingredients you have (comma-separated). Example: `tomato, chicken, rice, garlic`")
ingredients_input = st.text_area("Ingredients", value="", height=120)

generate = st.button("Generate recipes")

if generate:
    if not ingredients_input.strip():
        st.warning("Please enter at least one ingredient.")
    else:
        cleaned_ingredients, replacements = preprocess_ingredients(ingredients_input, dietary_choice)
        if replacements:
            for orig, repl in replacements:
                if repl is None:
                    st.warning(f"Removed '{orig}' because it is not allowed for {dietary_choice}.")
                elif repl != orig:
                    st.info(f"Replaced '{orig}' → '{repl}' to satisfy {dietary_choice} diet.")

        prompt = build_prompt(cleaned_ingredients, num_recipes, dietary_choice, difficulty, servings)
        with st.spinner("Generating recipes..."):
            raw = call_bedrock(prompt, max_gen_len=800, temperature=0.28, top_p=0.9)

        recipes = parse_model_output(raw)
        if not recipes:
            st.error("Couldn't parse model output. Showing raw response below for debugging.")
            st.code(raw if isinstance(raw, str) else json.dumps(raw, indent=2))
        
        else:
            for i, r in enumerate(recipes, start=1):
                recipe_html = f"""
                <div class="recipe-card">
                    <div class="recipe-title">{i}. {r.get('title', 'Untitled')}</div>
                    <div class="recipe-meta">
                        Servings: {r.get('servings', '-')} 
                        {' • Difficulty: ' + r.get('difficulty') if r.get('difficulty') else ''} 
                        {' • Time: ' + r.get('estimated_time') if r.get('estimated_time') else ''}
                    </div>
                    <div class="recipe-section-title">Ingredients</div>
                    <ul class="recipe-list">
                        {''.join(f'<li>{item}</li>' for item in r.get('ingredients', []))}
                    </ul>
                    <div class="recipe-section-title">Steps</div>
                    <ol class="recipe-list">
                        {''.join(f'<li>{step}</li>' for step in r.get('steps', []))}
                    </ol>
                    {f'<div class="recipe-section-title">Notes</div><p>{r.get("notes")}</p>' if r.get('notes') else ''}
                </div>
                """
                
                st.markdown(recipe_html, unsafe_allow_html=True)
            

