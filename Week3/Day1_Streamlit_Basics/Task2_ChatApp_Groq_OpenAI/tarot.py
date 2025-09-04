import os
import random

# 22 Major Arcana names in order
CARDS = [
    "fool", "magician", "high_priestess", "empress", "emperor",
    "hierophant", "lovers", "chariot", "strength", "hermit",
    "wheel_of_fortune", "justice", "hanged_man", "death",
    "temperance", "devil", "tower", "star", "moon", "sun",
    "judgement", "world"
]

MEANINGS_UPRIGHT = {
    "fool": "New beginnings, spontaneity, free spirit.",
    "magician": "Manifestation, resourcefulness, power.",
    "high_priestess": "Intuition, mystery, inner voice.",
    "empress": "Fertility, nurturing, abundance.",
    "emperor": "Authority, structure, control.",
    "hierophant": "Tradition, spiritual wisdom, guidance.",
    "lovers": "Love, harmony, relationships.",
    "chariot": "Determination, willpower, success.",
    "strength": "Courage, patience, compassion.",
    "hermit": "Introspection, inner guidance, solitude.",
    "wheel_of_fortune": "Fate, karma, cycles of life.",
    "justice": "Fairness, truth, law.",
    "hanged_man": "Pause, surrender, new perspective.",
    "death": "Transformation, endings, rebirth.",
    "temperance": "Balance, harmony, moderation.",
    "devil": "Addiction, materialism, bondage.",
    "tower": "Sudden change, chaos, revelation.",
    "star": "Hope, inspiration, renewal.",
    "moon": "Illusion, fear, intuition.",
    "sun": "Joy, success, positivity.",
    "judgement": "Reflection, reckoning, awakening.",
    "world": "Completion, wholeness, achievement."
}
MEANINGS_REVERSED = {
    "fool": "Hesitation, recklessness, fear of the leap.",
    "magician": "Manipulation, scattered energy, untapped power.",
    "high_priestess": "Secrets withheld, blocked intuition, confusion.",
    "empress": "Creative blocks, smothering, neglect of self.",
    "emperor": "Domination, rigidity, loss of control.",
    "hierophant": "Rebellion, stale tradition, empty ritual.",
    "lovers": "Disharmony, indecision, misaligned values.",
    "chariot": "Lack of direction, forcefulness, burnout.",
    "strength": "Self-doubt, impatience, inner imbalance.",
    "hermit": "Isolation, withdrawal, refusal to see within.",
    "wheel_of_fortune": "Resisting change, setbacks, cycles repeat.",
    "justice": "Bias, dishonesty, unfairness.",
    "hanged_man": "Stagnation, martyrdom, needless sacrifice.",
    "death": "Stagnation, clinging to the old, delayed endings.",
    "temperance": "Excess, imbalance, impatience.",
    "devil": "Breaking chains, awareness of bondage, temptation fades.",
    "tower": "Avoided disaster, lingering instability, denial.",
    "star": "Doubt, faith tested, dimmed hope.",
    "moon": "Deception revealed, anxiety, mixed signals.",
    "sun": "Temporary gloom, unrealistic optimism.",
    "judgement": "Self-criticism, avoidance, fear of change.",
    "world": "Incomplete cycles, delays, loose ends."
}

def draw_tarot_card():
    card_key = random.choice(CARDS)
    is_reversed = random.choice([True, False])  # 50% chance

    name = card_key.replace("_", " ").title()
    meaning = MEANINGS_REVERSED[card_key] if is_reversed else MEANINGS_UPRIGHT[card_key]

    return {
        "name": name,
        "meaning": meaning,
        "image": f"{card_key}.jpg",  # app joins with images/tarot/
        "reversed": is_reversed
    }
