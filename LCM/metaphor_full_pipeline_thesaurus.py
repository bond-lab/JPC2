import json
import csv
import os
import wn
import pickle
import re

# --- PATHS ---
BASE_PATH = os.path.dirname(os.path.abspath(__file__))
THESAURUS_FILE = os.path.join(BASE_PATH, "thesaurus.json")
OUTPUT_FILE = os.path.join(BASE_PATH, "mapping_results_thesaurus.csv")
CACHE_FILE = os.path.join(BASE_PATH, "wn_cache.pkl")

# --- WORDNET ---

def load_wordnet():
    print("Načítání WordNet přes knihovnu wn...")
    try:
        ewn = wn.Wordnet('omw-en:1.4')
    except:
        print("WordNet data nenalezena, stahuji...")
        wn.download('omw-en:1.4')
        ewn = wn.Wordnet('omw-en:1.4')

    synset_defs = {}
    synset_relations = {}
    lemma_to_synsets = {}
    synset_lemmas = {}

    for synset in ewn.synsets():
        sid = synset.id
        synset_defs[sid] = synset.definition()
        synset_lemmas[sid] = [l.lower() for l in synset.lemmas()]
        synset_relations[sid] = [h.id for h in synset.hypernyms()]

        for lemma in synset.lemmas():
            lemma_lower = lemma.lower()
            lemma_to_synsets.setdefault(lemma_lower, [])
            if sid not in lemma_to_synsets[lemma_lower]:
                lemma_to_synsets[lemma_lower].append(sid)

    return synset_defs, synset_relations, lemma_to_synsets, synset_lemmas


def load_wordnet_cached():
    if os.path.exists(CACHE_FILE):
        print("Načítání WordNet z cache...")
        with open(CACHE_FILE, "rb") as f:
            return pickle.load(f)
    else:
        data = load_wordnet()
        with open(CACHE_FILE, "wb") as f:
            pickle.dump(data, f)
        return data

# --- HYPERNYM TREE ---

def get_hypernyms_limited(synset_id, relations, defs, lemmas_dict, depth, level=0, visited=None):
    if visited is None:
        visited = set()
    if depth == 0 or synset_id in visited:
        return []

    visited.add(synset_id)
    hypernyms = []

    for h in relations.get(synset_id, []):
        if h in defs:
            lemma_str = ", ".join(lemmas_dict.get(h, []))
            definition = defs.get(h, "")
            hypernyms.append("  " * level + f"{lemma_str} — {definition}")
            hypernyms.extend(
                get_hypernyms_limited(h, relations, defs, lemmas_dict, depth - 1, level + 1, visited)
            )

    return hypernyms

# --- LOAD THESAURUS ---

def load_thesaurus(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

# --- EXTRACT WORDS AUTOMATICALLY ---

def clean_headword(word):
    word = word.lower()
    word = re.sub(r"\(.*?\)", "", word)  # remove brackets
    word = word.strip()
    return word


def extract_mml_from_thesaurus(data):
    mml = {}

    for part in data.get("parts", []):
        for theme in part.get("themes", []):
            concept = theme.get("name")

            if concept not in mml:
                mml[concept] = []

            for subsection in theme.get("subsections", []):
                for entry in subsection.get("entries", []):
                    raw_word = entry.get("headword", "")
                    word = clean_headword(raw_word)

                    if word:
                        mml[concept].append(word)

            # remove duplicates
            mml[concept] = list(set(mml[concept]))

    return mml

# --- LINK TO WORDNET ---

def link_data_direct_from_wn(synset_defs, synset_relations, lemma_to_synsets, synset_lemmas, mml):
    print("Propojování dat (WordNet lookup)...")
    results = []

    for concept, words in mml.items():
        for lemma in words:
            lemma = lemma.strip().lower()
            target_synsets = lemma_to_synsets.get(lemma, [])

            if not target_synsets:
                print(f" ! Slovo '{lemma}' nebylo ve WordNetu nalezeno.")
                continue

            for synset_id in target_synsets:
                definition = synset_defs.get(synset_id, "")
                h_tree = get_hypernyms_limited(
                    synset_id,
                    synset_relations,
                    synset_defs,
                    synset_lemmas,
                    5
                )

                results.append({
                    "Lemma": lemma,
                    "Synset_ID": synset_id,
                    "Definition": definition,
                    "Hypernyms": "\n".join(h_tree),
                    "MML_Concept": concept
                })

    return results

# --- SAVE CSV ---

def save_csv(results, path):
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        fieldnames = ["Lemma", "Synset_ID", "Definition", "Hypernyms", "MML_Concept"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

# --- MAIN ---

if __name__ == "__main__":
    # 1. WordNet
    s_defs, s_rels, l_to_s, s_lemmas = load_wordnet_cached()

    # 2. Thesaurus → automatic MML
    thesaurus_data = load_thesaurus(THESAURUS_FILE)
    mml_data = extract_mml_from_thesaurus(thesaurus_data)

    # 3. Link
    final_results = link_data_direct_from_wn(
        s_defs, s_rels, l_to_s, s_lemmas, mml_data
    )

    # 4. Save
    if final_results:
        save_csv(final_results, OUTPUT_FILE)
        print("-" * 30)
        print(f"HOTOVO! Nalezeno {len(final_results)} významů.")
        print(f"Výsledky uloženy do: {OUTPUT_FILE}")
    else:
        print("CHYBA: Nebyly nalezeny žádné shody.")