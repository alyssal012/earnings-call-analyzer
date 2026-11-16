"""Word lists for earnings-call language.

Written for this project and tuned to how executives actually talk on calls.
General-purpose sentiment dictionaries misread finance: "liability" or "tax"
aren't negative here, and "challenging" is one of the strongest negative signals there is.
"""

POSITIVE = {
    "strong", "stronger", "strength", "record", "excellent", "outperform", "outperformed", "growth", "grew",
    "improved", "improvement", "expanded", "exceeded", "ahead", "momentum", "encouraging", "pleased",
    "confident", "robust", "accelerating", "accelerate", "healthy", "tailwind", "tailwinds", "raising",
    "raised", "beat", "highest", "bright", "faster", "gains", "favorable", "upside", "well positioned",
}
NEGATIVE = {
    "challenging", "softness", "softer", "soft", "weak", "weaker", "weakness", "decline", "declined",
    "decreased", "below", "headwind", "headwinds", "pressure", "pressures", "cautious", "lowering",
    "lowered", "cut", "miss", "missed", "disappointing", "difficult", "slowdown", "slower", "moderated",
    "promotional", "markdowns", "pausing", "down from", "paused", "cancellations", "uncertain", "aged", "deteriorated", "deteriorating",
}
HEDGING = {
    "may", "might", "could", "possibly", "uncertain", "uncertainty", "dynamic", "fluid", "prudent",
    "too early", "monitor", "monitoring", "believe", "approximately", "roughly", "reviewing",
    "evaluate", "evaluating", "depends", "visibility", "cautious", "at this point",
}
CONFIDENT = {"will", "confident", "committed", "certain", "clearly", "definitely", "expect", "plan", "on track"}

# Phrases that signal an executive is not answering the question
DEFLECTIONS = [
    "we don't break that out", "we do not break that out", "don't break out", "not going to comment",
    "won't comment", "too early to say", "too early to tell", "not productive to get into",
    "wouldn't be productive", "would be productive to get into", "get into specifics",
    "we'll provide more color", "provide more color", "more color when", "not in a position",
    "we're not going to", "we won't be providing", "i'd rather not", "dynamic environment",
    "we're comfortable with the overall",
]

GUIDANCE_WORDS = ("guidance", "outlook", "we now expect", "full-year", "full year", "forecast")
RAISE = ("raising", "raise", "increase our", "increasing our", "up from")
LOWER = ("lowering", "lower our", "reducing", "reduce our", "cut our", "down from")
REAFFIRM = ("reaffirm", "reiterate", "maintaining", "maintain our", "unchanged")
