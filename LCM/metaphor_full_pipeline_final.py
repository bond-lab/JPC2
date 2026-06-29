"""
metaphor_full_pipeline_unified.py
-----
Unified pipeline combining four metaphor-mapping approaches:

  MODE 1 — chainnet   : ChainNet JSON + manual MML word list → WordNet lookup
  MODE 2 — wordnet    : Manual MML word list → WordNet lookup (no ChainNet)
  MODE 3 — thesaurus  : thesaurus.json → auto-extract MML words → WordNet lookup
  MODE 4 — discovery  : Auto-discover words that belong to BOTH colour AND
                        material/substance semantic domains via hypernym traversal

Usage
-----
Run interactively (prompts for mode):
    python metaphor_full_pipeline_unified.py

Run with a specific mode directly:
    python metaphor_full_pipeline_unified.py --mode chainnet
    python metaphor_full_pipeline_unified.py --mode wordnet
    python metaphor_full_pipeline_unified.py --mode thesaurus
    python metaphor_full_pipeline_unified.py --mode discovery

Required files (depending on mode):
    chainnet_metonymy.json  — needed for MODE 1
    thesaurus.json          — needed for MODE 3
    wn_cache.pkl            — auto-created on first run, reused afterwards
"""

import argparse
import csv
import json
import os
import pickle
import re
import sys

import wn

# ---------------------------------------------------------------------------
# PATHS
# ---------------------------------------------------------------------------

BASE_PATH = os.path.dirname(os.path.abspath(__file__))

CHAINNET_FILE  = os.path.join(BASE_PATH, "chainnet_metonymy.json")
THESAURUS_FILE = os.path.join(BASE_PATH, "thesaurus.json")
CACHE_FILE     = os.path.join(BASE_PATH, "wn_cache.pkl")

OUTPUT_FILES = {
    "chainnet"  : os.path.join(BASE_PATH, "mapping_results.csv"),
    "wordnet"   : os.path.join(BASE_PATH, "mapping_results_wordnet.csv"),
    "thesaurus" : os.path.join(BASE_PATH, "mapping_results_thesaurus.csv"),
    "discovery" : os.path.join(BASE_PATH, "mapping_results_colour_material.csv"),
}

# ---------------------------------------------------------------------------
# WORDNET — LOAD & CACHE
# ---------------------------------------------------------------------------

def load_wordnet():
    """Download (if needed) and index WordNet into plain dicts."""
    print("Loading WordNet via 'wn' library...")
    try:
        ewn = wn.Wordnet('omw-en:1.4')
    except Exception:
        print("WordNet data not found locally — downloading 'omw-en:1.4'...")
        wn.download('omw-en:1.4')
        ewn = wn.Wordnet('omw-en:1.4')

    synset_defs      = {}   # sid → definition string
    synset_relations = {}   # sid → [hypernym_sid, ...]
    lemma_to_synsets = {}   # lemma_str → [sid, ...]
    synset_lemmas    = {}   # sid → [lemma_str, ...]

    for synset in ewn.synsets():
        sid = synset.id
        synset_defs[sid]      = synset.definition()
        synset_lemmas[sid]    = [l.lower() for l in synset.lemmas()]
        synset_relations[sid] = [h.id for h in synset.hypernyms()]

        for lemma in synset.lemmas():
            lemma_lower = lemma.lower()
            lemma_to_synsets.setdefault(lemma_lower, [])
            if sid not in lemma_to_synsets[lemma_lower]:
                lemma_to_synsets[lemma_lower].append(sid)

    return synset_defs, synset_relations, lemma_to_synsets, synset_lemmas


def load_wordnet_cached():
    """Return cached WordNet dicts, building the cache on the first call."""
    if os.path.exists(CACHE_FILE):
        print("Loading WordNet from cache...")
        with open(CACHE_FILE, "rb") as f:
            return pickle.load(f)
    else:
        data = load_wordnet()
        with open(CACHE_FILE, "wb") as f:
            pickle.dump(data, f)
        print("WordNet cache saved.")
        return data

# ---------------------------------------------------------------------------
# SHARED HELPERS
# ---------------------------------------------------------------------------

def get_hypernyms_indented(synset_id, relations, defs, lemmas_dict,
                           depth, level=0, visited=None):
    """
    Build an indented hypernym tree as a list of strings (one entry per line).
    Separator between lemma list and definition is ' — ' (em-dash style).
    Used by modes: chainnet, wordnet, thesaurus.
    """
    if visited is None:
        visited = set()
    if depth == 0 or synset_id in visited:
        return []

    visited.add(synset_id)
    lines = []

    for h in relations.get(synset_id, []):
        if h in defs:
            lemma_str  = ", ".join(lemmas_dict.get(h, []))
            definition = defs.get(h, "")
            lines.append("  " * level + f"{lemma_str} — {definition}")
            lines.extend(
                get_hypernyms_indented(h, relations, defs, lemmas_dict,
                                       depth - 1, level + 1, visited)
            )

    return lines


def get_hypernyms_colon(synset_id, relations, defs, lemmas_dict,
                        depth, level=0, visited=None):
    """
    Same tree, but separator is ': ' (colon).
    Used by mode: discovery (matches original metaphor_full_pipeline_thesaurus_2.py).
    """
    if visited is None:
        visited = set()
    if depth == 0 or synset_id in visited:
        return []

    visited.add(synset_id)
    lines = []

    for h in relations.get(synset_id, []):
        if h in defs:
            lemma_str  = ", ".join(lemmas_dict.get(h, []))
            definition = defs.get(h, "")
            lines.append("  " * level + f"{lemma_str}: {definition}")
            lines.extend(
                get_hypernyms_colon(h, relations, defs, lemmas_dict,
                                    depth - 1, level + 1, visited)
            )

    return lines


def save_csv(results, path, fieldnames):
    """Write results list-of-dicts to a CSV file."""
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)
    print(f"Results saved to: {path}")

# ---------------------------------------------------------------------------
# MODE 1 — CHAINNET
# (Original: Metaphor_full_pipeline_5.py)
# ---------------------------------------------------------------------------

def load_chainnet(path):
    """Load ChainNet JSON produced by the professor."""
    if not os.path.exists(path):
        print(f"Warning: {path} not found.")
        return []
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    entries = data.get("content", []) if isinstance(data, dict) else data

    results = []
    for item in entries:
        sense_id = item.get("from_sense", "")
        lemma    = item.get("wordform", "").lower()
        if not lemma and "%" in sense_id:
            lemma = sense_id.split("%")[0].lower()
        results.append({"lemma": lemma, "sense_id": sense_id})
    return results


def get_mml_chainnet():
    """Manual MML word lists for the ChainNet / direct-WordNet modes."""
    return {
        "COLOUR IS MINERAL": [
            "sapphire", "amethyst", "turquoise", "ruby",
            "amber", "emerald", "coral", "gold",
        ],
        "COLOUR IS PLANT": [
            "orchid", "sunflower", "daisy", "rose", "violet",
        ],
    }


def run_chainnet(s_defs, s_rels, l_to_s, s_lemmas):
    """MODE 1: ChainNet + manual MML → WordNet."""
    chainnet_data = load_chainnet(CHAINNET_FILE)
    if not chainnet_data:
        print(f"ERROR: {CHAINNET_FILE} is missing or empty — cannot run chainnet mode.")
        return

    mml_data   = get_mml_chainnet()
    mml_lookup = {
        word.lower().strip(): concept
        for concept, words in mml_data.items()
        for word in words
    }

    print("Linking data (strict ChainNet mode)...")
    results = []

    for entry in chainnet_data:
        lemma     = entry["lemma"].strip().lower()
        sense_key = entry["sense_id"]

        if lemma not in mml_lookup:
            continue

        concept        = mml_lookup[lemma]
        target_synsets = l_to_s.get(lemma, [])

        for synset_id in target_synsets:
            h_tree = get_hypernyms_indented(synset_id, s_rels, s_defs, s_lemmas, 5)
            results.append({
                "Lemma"      : lemma,
                "Sense_ID"   : sense_key,
                "Synset_ID"  : synset_id,
                "Definition" : s_defs.get(synset_id, ""),
                "Hypernyms"  : "\n".join(h_tree),
                "MML_Concept": concept,
            })

    print(f"Done. Found {len(results)} occurrences.")
    fieldnames = ["Lemma", "Sense_ID", "Synset_ID", "Definition", "Hypernyms", "MML_Concept"]
    save_csv(results, OUTPUT_FILES["chainnet"], fieldnames)

# ---------------------------------------------------------------------------
# MODE 2 — WORDNET DIRECT
# (Original: metaphor_full_pipeline_wordnet.py)
# ---------------------------------------------------------------------------

def get_mml_wordnet():
    """Manual MML word lists for direct WordNet mode (extended list)."""
    return {
        "COLOUR IS MINERAL": [
            "sapphire", "amethyst", "aquamarine", "turquoise",
            "ruby", "amber", "emerald", "coral", "gold",
        ],
        "COLOUR IS MATERIAL": [
            "gold", "silver", "cobalt", "ochre",
            "gunmetal", "copper", "cobalt blue",
        ],
    }


def run_wordnet(s_defs, s_rels, l_to_s, s_lemmas):
    """MODE 2: Manual MML list → WordNet (no ChainNet)."""
    mml_data = get_mml_wordnet()
    print("Linking data (direct WordNet search)...")
    results = []

    for concept, words in mml_data.items():
        for lemma in words:
            lemma          = lemma.strip().lower()
            target_synsets = l_to_s.get(lemma, [])

            if not target_synsets:
                print(f"  ! '{lemma}' not found in WordNet.")
                continue

            for synset_id in target_synsets:
                h_tree = get_hypernyms_indented(synset_id, s_rels, s_defs, s_lemmas, 5)
                results.append({
                    "Lemma"      : lemma,
                    "Sense_ID"   : "DIRECT_WN_SEARCH",
                    "Synset_ID"  : synset_id,
                    "Definition" : s_defs.get(synset_id, ""),
                    "Hypernyms"  : "\n".join(h_tree),
                    "MML_Concept": concept,
                })

    print(f"Done. Found {len(results)} senses for your words.")
    fieldnames = ["Lemma", "Sense_ID", "Synset_ID", "Definition", "Hypernyms", "MML_Concept"]
    save_csv(results, OUTPUT_FILES["wordnet"], fieldnames)

# ---------------------------------------------------------------------------
# MODE 3 — THESAURUS
# (Original: metaphor_full_pipeline_thesaurus.py)
# ---------------------------------------------------------------------------

def load_thesaurus(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def clean_headword(word):
    word = word.lower()
    word = re.sub(r"\(.*?\)", "", word)   # strip parenthetical notes
    return word.strip()


def extract_mml_from_thesaurus(data):
    """Walk thesaurus JSON structure and collect headwords per concept theme."""
    mml = {}
    for part in data.get("parts", []):
        for theme in part.get("themes", []):
            concept = theme.get("name")
            mml.setdefault(concept, [])

            for subsection in theme.get("subsections", []):
                for entry in subsection.get("entries", []):
                    word = clean_headword(entry.get("headword", ""))
                    if word:
                        mml[concept].append(word)

            mml[concept] = list(set(mml[concept]))   # deduplicate
    return mml


def run_thesaurus(s_defs, s_rels, l_to_s, s_lemmas):
    """MODE 3: thesaurus.json → auto MML → WordNet."""
    if not os.path.exists(THESAURUS_FILE):
        print(f"ERROR: {THESAURUS_FILE} not found — cannot run thesaurus mode.")
        return

    thesaurus_data = load_thesaurus(THESAURUS_FILE)
    mml_data       = extract_mml_from_thesaurus(thesaurus_data)

    print("Linking data (thesaurus → WordNet)...")
    results = []

    for concept, words in mml_data.items():
        for lemma in words:
            lemma          = lemma.strip().lower()
            target_synsets = l_to_s.get(lemma, [])

            if not target_synsets:
                print(f"  ! '{lemma}' not found in WordNet.")
                continue

            for synset_id in target_synsets:
                h_tree = get_hypernyms_indented(synset_id, s_rels, s_defs, s_lemmas, 5)
                results.append({
                    "Lemma"      : lemma,
                    "Synset_ID"  : synset_id,
                    "Definition" : s_defs.get(synset_id, ""),
                    "Hypernyms"  : "\n".join(h_tree),
                    "MML_Concept": concept,
                })

    if results:
        print(f"Done. Found {len(results)} senses.")
        fieldnames = ["Lemma", "Synset_ID", "Definition", "Hypernyms", "MML_Concept"]
        save_csv(results, OUTPUT_FILES["thesaurus"], fieldnames)
    else:
        print("ERROR: No matches found.")

# ---------------------------------------------------------------------------
# MODE 4 — DISCOVERY (auto colour+material)
# (Original: metaphor_full_pipeline_thesaurus_2.py)
# ---------------------------------------------------------------------------

def is_descendant_of(synset_id, target_keywords, relations, lemmas_dict, visited=None):
    """Return True if synset_id has any ancestor whose lemmas include a keyword."""
    if visited is None:
        visited = set()
    if synset_id in visited:
        return False
    visited.add(synset_id)

    if any(k in lemmas_dict.get(synset_id, []) for k in target_keywords):
        return True

    for h_id in relations.get(synset_id, []):
        if is_descendant_of(h_id, target_keywords, relations, lemmas_dict, visited):
            return True

    return False


def discover_mapping_words(l_to_s, s_rels, s_lemmas):
    """Find lemmas that are descendants of BOTH colour AND substance/material."""
    print("Discovering words that map to both colour and material domains...")
    colour_roots    = ["color", "colour"]
    substance_roots = ["substance", "material", "matter"]
    found = []

    for lemma, synsets in l_to_s.items():
        has_colour    = any(is_descendant_of(sid, colour_roots,    s_rels, s_lemmas) for sid in synsets)
        has_substance = any(is_descendant_of(sid, substance_roots, s_rels, s_lemmas) for sid in synsets)
        if has_colour and has_substance:
            found.append(lemma)

    return list(set(found))


def run_discovery(s_defs, s_rels, l_to_s, s_lemmas):
    """MODE 4: Auto-discover colour+material words → WordNet."""
    target_words = discover_mapping_words(l_to_s, s_rels, s_lemmas)
    print(f"  Found {len(target_words)} candidate lemmas.")

    filter_roots = ["color", "colour", "substance", "material"]
    results = []

    for lemma in target_words:
        for sid in l_to_s.get(lemma, []):
            if is_descendant_of(sid, filter_roots, s_rels, s_lemmas):
                h_tree = get_hypernyms_colon(sid, s_rels, s_defs, s_lemmas, 5)
                results.append({
                    "Lemma"      : lemma,
                    "Synset_ID"  : sid,
                    "Definition" : s_defs.get(sid, ""),
                    "Hypernyms"  : "\n".join(h_tree),
                    "MML_Concept": "COLOUR IS MATERIAL",
                })

    print(f"Done. Found {len(results)} senses.")
    fieldnames = ["Lemma", "Synset_ID", "Definition", "Hypernyms", "MML_Concept"]
    save_csv(results, OUTPUT_FILES["discovery"], fieldnames)

# ---------------------------------------------------------------------------
# ENTRY POINT
# ---------------------------------------------------------------------------

MODES = {
    "chainnet"  : run_chainnet,
    "wordnet"   : run_wordnet,
    "thesaurus" : run_thesaurus,
    "discovery" : run_discovery,
}

MODE_DESCRIPTIONS = {
    "chainnet"  : "ChainNet JSON + manual MML word list → WordNet  →  mapping_results.csv",
    "wordnet"   : "Manual MML word list → WordNet (no ChainNet)    →  mapping_results_wordnet.csv",
    "thesaurus" : "thesaurus.json → auto-extract MML → WordNet     →  mapping_results_thesaurus.csv",
    "discovery" : "Auto-discover colour+material words via WordNet  →  mapping_results_colour_material.csv",
}


def choose_mode_interactively():
    print("\n=== Metaphor Full Pipeline — Unified ===\n")
    print("Available modes:\n")
    for i, (key, desc) in enumerate(MODE_DESCRIPTIONS.items(), start=1):
        print(f"  [{i}] {key:12s}  {desc}")
    print()

    while True:
        raw = input("Enter mode number or name: ").strip().lower()
        # Accept numeric shorthand
        if raw in ("1", "2", "3", "4"):
            key = list(MODES.keys())[int(raw) - 1]
            return key
        if raw in MODES:
            return raw
        print(f"  Unrecognised input '{raw}'. Please enter 1–4 or a mode name.")


def main():
    parser = argparse.ArgumentParser(
        description="Unified metaphor mapping pipeline (chainnet / wordnet / thesaurus / discovery)"
    )
    parser.add_argument(
        "--mode",
        choices=list(MODES.keys()),
        default=None,
        help="Pipeline mode to run. Omit to choose interactively.",
    )
    args = parser.parse_args()

    mode = args.mode if args.mode else choose_mode_interactively()

    print(f"\n→ Running mode: {mode}")
    print(f"  {MODE_DESCRIPTIONS[mode]}\n")

    # Load WordNet once; all modes share the same cache
    s_defs, s_rels, l_to_s, s_lemmas = load_wordnet_cached()

    # Dispatch to the selected mode
    MODES[mode](s_defs, s_rels, l_to_s, s_lemmas)

    print("\nAll done.")


if __name__ == "__main__":
    main()