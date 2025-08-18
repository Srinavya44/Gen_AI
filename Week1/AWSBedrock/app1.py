# app.py
import os
import json
import re
import requests
import boto3
import streamlit as st
from dotenv import load_dotenv

# -----------------------
# Load env & config
# -----------------------
load_dotenv()

MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "meta.llama3-8b-instruct-v1:0")
REGION = os.environ.get("AWS_REGION", "ap-south-1")
SPOONACULAR_API_KEY = os.environ.get("SPOONACULAR_API_KEY")

# Create Bedrock client
bedrock = boto3.client("bedrock-runtime", region_name=REGION)

# -----------------------
# Dietary rules & replacements
# -----------------------
dietary_rules = {
    "none": {"blocked": [], "replacement": {}},
    "vegan": {
        "blocked": ["chicken", "fish", "beef", "pork", "egg", "milk", "cheese", "yogurt", "butter", "honey"],
        "replacement": {
            "chicken": "tofu",
            "fish": "jackfruit",
            "beef": "tempeh",
            "pork": "jackfruit",
            "egg": "flax egg",
            "milk": "soy milk",
            "cheese": "vegan cheese",
            "yogurt": "coconut yogurt",
            "butter": "vegan butter",
            "honey": "maple syrup",
        },
    },
    "vegetarian": {
        "blocked": ["chicken", "fish", "beef", "pork"],
        "replacement": {
            "chicken": "paneer",
            "fish": "mushrooms",
            "beef": "soy chunks",
            "pork": "jackfruit",
        },
    },
    "pescatarian": {
        "blocked": ["chicken", "beef", "pork"],
        "replacement": {
            "chicken": "salmon",
            "beef": "tuna",
            "pork": "salmon",
        },
    },
    "gluten-free": {
        "blocked": ["wheat", "barley", "rye", "pasta", "all-purpose flour", "breadcrumbs"],
        "replacement": {
            "wheat": "gluten-free flour",
            "barley": "quinoa",
            "rye": "buckwheat",
            "pasta": "gluten-free pasta",
            "all-purpose flour": "gluten-free flour",
            "breadcrumbs": "crushed gluten-free crackers",
        },
    },
}

# -----------------------
# Helpers
# -----------------------
def normalize_ingredient_name(s: str) -> str:
    return s.strip().lower()

def preprocess_ingredients(raw_ingredients: str, diet_key: str):
    items = [normalize_ingredient_name(i) for i in raw_ingredients.split(",") if i.strip()]
    processed = []
    replacements = []
    rules = dietary_rules.get(diet_key, dietary_rules["none"])
    blocked = set(rules["blocked"])
    repl_map = rules["replacement"]

    for it in items:
        replaced_any = False
        for b in blocked:
            if re.search(rf"\b{re.escape(b)}\b", it):
                if b in repl_map:
                    new_it = re.sub(rf"\b{re.escape(b)}\b", repl_map[b], it)
                    processed.append(new_it)
                    replacements.append((it, new_it))
                else:
                    replacements.append((it, None))
                replaced_any = True
                break
        if not replaced_any:
            processed.append(it)

    seen = set()
    processed_unique = []
    for p in processed:
        if p not in seen and p is not None:
            seen.add(p)
            processed_unique.append(p)

    return ", ".join(processed_unique), replacements

def build_prompt(ingredients: str, num_recipes: int, diet: str, difficulty: str, servings: int):
    diet_wording = diet if diet != "none" else "no dietary restriction"
    difficulty_text = difficulty if difficulty != "Any" else "Any"

    prompt = f"""
You are an expert chef.

GOAL:
Create complete, practical recipes from the provided main ingredients.

RULES:
- Diet: {diet_wording}. STRICTLY follow this; do NOT include disallowed ingredients.
- Difficulty target: {difficulty_text}.
- Servings target: approximately {servings} per recipe.
- Treat the provided ingredients as the main components. You may add common/necessary items.
- Replace blocked ingredients with alternatives if needed.
- EVERY ingredient in the output must have a clear quantity and unit.
- Deduplicate ingredients.
- Output MUST be valid JSON ONLY.

JSON SCHEMA (array of objects):
[
  {{
    "title": "string",
    "servings": integer,
    "ingredients": [
      {{"name": "string", "quantity": "string"}}
    ],
    "steps": ["string", "string"],
    "difficulty": "Easy" | "Medium" | "Hard",
    "estimated_time": "string",
    "notes": "string"
  }}
]

Now generate EXACTLY {num_recipes} recipes using these main ingredients:
{ingredients}

Return ONLY the JSON array.
"""
    return prompt.strip()

def call_bedrock(prompt: str, max_gen_len: int = 900, temperature: float = 0.25, top_p: float = 0.9) -> str:
    payload = {
        "prompt": prompt,
        "max_gen_len": max_gen_len,
        "temperature": temperature,
        "top_p": top_p,
    }
    resp = bedrock.invoke_model(
        modelId=MODEL_ID,
        contentType="application/json",
        accept="application/json",
        body=json.dumps(payload).encode("utf-8"),
    )
    body_text = resp["body"].read().decode("utf-8")
    try:
        parsed = json.loads(body_text)
        if isinstance(parsed, dict):
            if "outputs" in parsed and isinstance(parsed["outputs"], list):
                return parsed["outputs"][0].get("text", "")
        elif isinstance(parsed, list):
            return json.dumps(parsed)
    except json.JSONDecodeError:
        pass
    return body_text

def parse_model_output(raw_text: str):
    if not raw_text:
        return None
    try:
        parsed = json.loads(raw_text)
        if isinstance(parsed, list):
            return parsed
    except json.JSONDecodeError:
        pass
    match = re.search(r"\[\s*?\{.*?\}\s*?\]", raw_text, re.DOTALL)
    if match:
        json_str = match.group(0)
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            json_str = re.sub(r",\s*([\]}])", r"\1", json_str)
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                return None
    return None

# -----------------------
# Spoonacular Nutrition
# -----------------------
def _quantifiable(qty: str) -> bool:
    NON_QUANTIFIABLE = {"to taste", "as needed", "as required", "pinch", "dash"}
    if not qty:
        return False
    q = qty.strip().lower()
    if q in NON_QUANTIFIABLE:
        return False
    return bool(re.search(r"\d", q)) or any(u in q for u in ["g", "gram", "ml", "cup", "tbsp", "tsp", "clove", "piece", "pcs", "oz"])

def ingredients_for_spoonacular(ingredients_obj_list):
    lines = []
    for ing in ingredients_obj_list or []:
        if isinstance(ing, dict):
            name = (ing.get("name") or "").strip()
            qty = (ing.get("quantity") or "").strip()
            if name and _quantifiable(qty):
                qty_clean = qty.replace("pcs", "piece")
                lines.append(f"{qty_clean} {name}")
    return lines

def fetch_spoonacular_nutrition(ing_lines, title: str = "Recipe", servings: int = 1):
    if not SPOONACULAR_API_KEY:
        return {"error": "Missing SPOONACULAR_API_KEY in environment."}

    if not ing_lines:
        return {"error": "No ingredients to analyze."}

    url = "https://api.spoonacular.com/recipes/analyze"
    params = {"apiKey": SPOONACULAR_API_KEY}
    payload = {
        "title": title,
        "servings": servings,
        "ingredients": ing_lines
    }

    try:
        r = requests.post(url, params=params, json=payload, timeout=20)
        if r.status_code != 200:
            return {"error": f"Spoonacular error {r.status_code}: {r.text[:200]}"}
        data = r.json()
    except Exception as e:
        return {"error": f"Spoonacular request failed: {e}"}

    try:
        nutrition = data.get("nutrition", {})
        nutrients = {n["name"]: n for n in nutrition.get("nutrients", [])}
        return {
            "servings": servings,
            "calories": nutrients.get("Calories", {}).get("amount", "-"),
            "protein_g": nutrients.get("Protein", {}).get("amount", "-"),
            "carbs_g": nutrients.get("Carbohydrates", {}).get("amount", "-"),
            "fat_g": nutrients.get("Fat", {}).get("amount", "-"),
            "fiber_g": nutrients.get("Fiber", {}).get("amount", "-")
        }
    except Exception:
        return {"error": "Could not parse Spoonacular nutrition response."}

# -----------------------
# Streamlit UI
# -----------------------
st.set_page_config(page_title="AI Recipe Generator", layout="centered", page_icon="🍳")
st.title("🍳 AI Recipe Generator")

with st.sidebar:
    st.header("Options")
    num_recipes = st.slider("Number of recipes", 1, 5, 2)
    dietary_choice = st.selectbox("Dietary restriction", ["none", "vegan", "vegetarian", "pescatarian", "gluten-free"])
    difficulty = st.selectbox("Preferred difficulty", ["Any", "Easy", "Medium", "Hard"])
    servings = st.number_input("Servings (approx.)", min_value=1, max_value=10, value=2)

st.markdown("Enter ingredients you have (comma-separated). Example: `200g chicken, 1 cup rice, tomato`")
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
            raw = call_bedrock(prompt, max_gen_len=1000, temperature=0.28, top_p=0.9)

        recipes = parse_model_output(raw)
        if not recipes:
            st.error("Couldn't parse model output. Raw response:")
            st.code(raw if isinstance(raw, str) else json.dumps(raw, indent=2))
        else:
            for i, r in enumerate(recipes, start=1):
                title = r.get("title", f"Recipe {i}")
                ing_list = r.get("ingredients", [])
                steps = r.get("steps", [])
                r_servings = r.get("servings", servings)
                r_diff = r.get("difficulty")
                r_time = r.get("estimated_time")
                notes = r.get("notes")

                ingredients_html = ''.join(
                    (f"<li>{ing.get('name','')} - {ing.get('quantity','')}</li>" if isinstance(ing, dict) else f"<li>{ing}</li>")
                    for ing in ing_list
                )
                recipe_html = f"""
                <div style="background:#fff;padding:20px;border-radius:12px;margin-bottom:20px;box-shadow:0 4px 12px rgba(0,0,0,0.08)">
                    <div style="font-size:1.4rem;font-weight:bold;">{i}. {title}</div>
                    <div style="font-size:0.9rem;color:#555;margin-bottom:15px;">
                        Servings: {r_servings if r_servings else '-'}
                        {" • Difficulty: " + r_diff if r_diff else ""}
                        {" • Time: " + r_time if r_time else ""}
                    </div>
                    <div style="font-weight:bold;">Ingredients</div>
                    <ul>{ingredients_html}</ul>
                    <div style="font-weight:bold;">Steps</div>
                    <ol>{''.join(f'<li>{step}</li>' for step in steps)}</ol>
                    {f'<div style="font-weight:bold;">Notes</div><p>{notes}</p>' if notes else ''}
                </div>
                """
                st.markdown(recipe_html, unsafe_allow_html=True)

                with st.spinner("Calculating nutrition (Spoonacular)..."):
                    spoon_lines = ingredients_for_spoonacular(ing_list)
                    nut = fetch_spoonacular_nutrition(spoon_lines, title=title, servings=r_servings)

                if isinstance(nut, dict) and nut.get("error"):
                    st.warning(f"Nutrition note: {nut['error']}")
                else:
                    nutrition_html = f"""
                    <div style="background:#f9f9f9;padding:15px;border-radius:8px;">
                        <div style="font-weight:bold;">Nutrition per Serving</div>
                        <ul>
                            <li>Calories: {nut.get('calories','-')} kcal</li>
                            <li>Protein: {nut.get('protein_g','-')} g</li>
                            <li>Carbs: {nut.get('carbs_g','-')} g</li>
                            <li>Fat: {nut.get('fat_g','-')} g</li>
                            <li>Fiber: {nut.get('fiber_g','-')} g</li>
                        </ul>
                    </div>
                    """
                    st.markdown(nutrition_html, unsafe_allow_html=True)
