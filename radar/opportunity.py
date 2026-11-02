"""What kind of thing a lead is, and whether it is worth building a tool around.

Five habits of people who build tool sites for a living:
- the format sets the ceiling of what a visitor will pay for: video > voice > image > text;
- a manual workflow that people pass around (a tutorial, a prompt recipe, a trend everyone
  copies) is a tool nobody has built yet: "anything done by hand across a broken chain can
  be one button";
- `can_charge`: the evidence points to paid demand, not only free traffic;
- `online_gap`: the evidence points to a local script, prompt, manual workflow or download,
  with no obvious usable online product for that exact job;
- `decay_risk`: high for a meme, model release or short-lived trend; low for a durable job.
The fields are read from the lead's own words (its name, the posts, the examples, the maker's
own description) by keyword rules. Cheap, and right often enough to sort a list; read the
posts before acting on a tag.
"""
from __future__ import annotations

import re

FORMATS = [
    ("video", re.compile(r"\b(?:videos?|clips?|animat\w*|film|movie|veo|sora|kling|hailuo|runway|seedance|"
                         r"lip ?sync|text[- ]to[- ]video|image[- ]to[- ]video|i2v|t2v)\b", re.I)),
    ("voice", re.compile(r"\b(?:voices?|tts|text[- ]to[- ]speech|speech|audio|music|songs?|singing|podcasts?|"
                         r"dubbing|transcri\w+|asr|sound)\b", re.I)),
    ("image", re.compile(r"\b(?:images?|photos?|pictures?|pics?|art|drawings?|illustrations?|portraits?|headshots?|"
                         r"logos?|stickers?|figurines?|anime|upscal\w*|backgrounds?|text[- ]to[- ]image|t2i|edit\w* photos?)\b",
                         re.I)),
]
RANK = {"video": 0, "voice": 1, "image": 2, "text": 3}
TUTORIAL = re.compile(r"\b(?:how to|step[- ]by[- ]step|step 1\b|tutorial|walkthrough|here'?s how|full prompt|"
                      r"prompts? (?:below|inside|included)|copy (?:this|my) prompt|prompt:)|🧵", re.I)
TREND = re.compile(r"\b(?:trend(?:ing)?|viral|everyone(?:'s| is) (?:making|doing|using|posting)|going viral|memes?)\b", re.I)
CHARGE = re.compile(r"\b(?:paid|payment|pricing|price|subscription|subscribe|credits?|api|saas|license|enterprise|"
                    r"pro plan|upgrade|buy|purchase|revenue|earn|monetiz\w*)\b", re.I)
ONLINE_GAP = re.compile(r"\b(?:local(?:ly)?|offline|script|prompt|github|repo|repository|self[- ]hosted|"
                        r"manual(?:ly)?|command[- ]line|cli|desktop app|download|\.exe|workflow)\b", re.I)
ONLINE = re.compile(r"\b(?:online|web app|website|api|saas|cloud|hosted|browser|one[- ]click|extension)\b", re.I)
NO_ONLINE = re.compile(r"\b(?:no|not|without)\s+(?:an?\s+)?(?:obvious\s+)?(?:usable\s+)?online\b", re.I)
DURABLE = re.compile(r"\b(?:api|integration|automation|workflow|productivity|business|team|enterprise|developer|"
                     r"database|security|compliance|monitor|backup|conversion)\b", re.I)
RELEASE = re.compile(r"\b(?:model|release|launch|version|v\d|gpt|claude|gemini|qwen|llama|veo|sora|kling|hailuo|"
                     r"openrouter)\b", re.I)
DECAY_RANK = {"low": 0, "medium": 1, "high": 2}
OPPORTUNITY_BOOLS = ("can_charge", "manual_workflow", "online_gap")
OPPORTUNITY_FIELDS = (*OPPORTUNITY_BOOLS, "decay_risk")
VIRAL = 1000                # likes: a tutorial nobody shared is not a demand signal
SHARE = 0.25                # a format named in at least this share of the posts (and two of them) counts


def own_words(lead: dict) -> str:
    """The thing's own words: its name, the examples, its maker's description."""
    about = lead.get("about") or ("", "")
    return " ".join([lead.get("term", ""), *lead.get("examples", []), about[1] if isinstance(about, (list, tuple)) else ""])


def fmt(lead: dict) -> str:
    """video, voice, image or text. Its own words decide first ("veo 3.1", "ai headshot"); otherwise the
    format the posts name most, if at least a quarter of them (and two) do; ties go to the costlier format."""
    mine = own_words(lead)
    for name, rx in FORMATS:
        if rx.search(mine):
            return name
    posts = lead.get("posts", [])
    counts = [(sum(1 for p in posts if rx.search(p.get("text", ""))), -RANK[name], name) for name, rx in FORMATS]
    n, _, name = max(counts)
    return name if n >= max(2, SHARE * len(posts)) else "text"


def one_click(posts: list[dict]) -> str | None:
    """"tutorial" when a post that walks through a manual workflow drew VIRAL likes, "trend" when a post
    riding a trend did; else None."""
    shared = [p.get("text", "") for p in posts if (p.get("likes") or 0) >= VIRAL]
    return "tutorial" if any(TUTORIAL.search(x) for x in shared) else "trend" if any(TREND.search(x) for x in shared) else None


def _all_words(lead: dict) -> str:
    posts = " ".join(p.get("text", "") for p in lead.get("posts", []))
    return own_words(lead) + " " + posts


def can_charge(lead: dict) -> bool:
    return bool(CHARGE.search(_all_words(lead)))


def manual_workflow(lead: dict) -> bool:
    return bool(lead.get("one_click") or TUTORIAL.search(_all_words(lead)) or TREND.search(_all_words(lead)))


def online_gap(lead: dict) -> bool:
    text = _all_words(lead)
    return bool(ONLINE_GAP.search(text)) and (not bool(ONLINE.search(text)) or bool(NO_ONLINE.search(text)))


def decay_risk(lead: dict) -> str:
    text = _all_words(lead)
    if lead.get("one_click") == "trend" or TREND.search(text) or RELEASE.search(text):
        return "high"
    return "low" if DURABLE.search(text) else "medium"


def assess(lead: dict) -> dict:
    return {"can_charge": can_charge(lead), "manual_workflow": manual_workflow(lead),
            "online_gap": online_gap(lead), "decay_risk": decay_risk(lead)}


def merge(*leads: dict) -> dict:
    """Combine opportunity fields from several views of the same lead.

    A yes on one useful job is a yes for the lead; decay uses the riskiest view.
    """
    out: dict = {}
    for field in OPPORTUNITY_BOOLS:
        vals = [r.get(field) for r in leads if r.get(field) is not None]
        if vals:
            out[field] = any(vals)
    risks = [r.get("decay_risk") for r in leads if r.get("decay_risk") in DECAY_RANK]
    if risks:
        out["decay_risk"] = max(risks, key=lambda x: DECAY_RANK[x])
    return out


def tag(lead: dict) -> dict:
    lead["format"], lead["one_click"] = fmt(lead), one_click(lead.get("posts", []))
    for key, value in assess(lead).items():
        lead.setdefault(key, value)
    return lead
