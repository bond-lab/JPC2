import json
import csv
import os
import wn
import pickle

# --- AUTOMATICKÉ NASTAVENÍ CEST ---
BASE_PATH = os.path.dirname(os.path.abspath(__file__))
# Chainnet už technicky pro hlavní logiku nepotřebujeme, ale nechávám cestu pro úplnost
CHAINNET_FILE = os.path.join(BASE_PATH, "chainnet_metonymy.json")
OUTPUT_FILE = os.path.join(BASE_PATH, "mapping_results_wordnet.csv")
CACHE_FILE = os.path.join(BASE_PATH, "wn_cache.pkl")

# --- FUNKCE PRO WORDNET ---

def load_wordnet():
    """Stáhne a připraví WordNet data do slovníků."""
    print("Načítání WordNet přes knihovnu wn...")
    try:
        ewn = wn.Wordnet('omw-en:1.4')
    except:
        print("WordNet data nenalezena, stahuji 'omw-en:1.4'...")
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
            if lemma_lower not in lemma_to_synsets:
                lemma_to_synsets[lemma_lower] = []
            if sid not in lemma_to_synsets[lemma_lower]:
                lemma_to_synsets[lemma_lower].append(sid)

    return synset_defs, synset_relations, lemma_to_synsets, synset_lemmas

def load_wordnet_cached():
    """Načte data z cache, nebo je vytvoří, pokud neexistují."""
    if os.path.exists(CACHE_FILE):
        print("Načítání WordNet z cache...")
        with open(CACHE_FILE, "rb") as f:
            return pickle.load(f)
    else:
        data = load_wordnet()
        with open(CACHE_FILE, "wb") as f:
            pickle.dump(data, f)
        return data

# --- FUNKCE PRO HIERARCHII ---

def get_hypernyms_limited(synset_id, relations, defs, lemmas_dict, depth, level=0, visited=None):
    """Vytvoří hezký textový 'strom' hierarchie pro CSV."""
    if visited is None: visited = set()
    if depth == 0 or synset_id in visited: return []
    visited.add(synset_id)

    hypernyms = []
    for h in relations.get(synset_id, []):
        if h in defs:
            lemma_str = ", ".join(lemmas_dict.get(h, []))
            definition = defs.get(h, "")
            hypernyms.append("  " * level + f"{lemma_str} — {definition}")
            hypernyms.extend(get_hypernyms_limited(h, relations, defs, lemmas_dict, depth - 1, level + 1, visited))
    return hypernyms

# --- DATA A PROPOJOVÁNÍ ---

def load_mml():
    """Definuje cílové konceptuální metafory (přidáno aquamarine)."""
    return {
        "COLOUR IS MINERAL": ["sapphire", "amethyst", "aquamarine", "turquoise", "ruby", "amber", "emerald", "coral", "gold"],
        "COLOUR IS PLANT": ["orchid", "sunflower", "daisy", "rose", "violet"]
    }

def link_data_direct_from_wn(synset_defs, synset_relations, lemma_to_synsets, synset_lemmas, mml):
    """Prohledává WordNet přímo podle seznamu slov v MML (ignoruje absenci v ChainNetu)."""
    print("Propojování dat (Hledání přímo ve WordNetu)...")
    results = []

    for concept, words in mml.items():
        for lemma in words:
            lemma = lemma.strip().lower()
            
            # Hledáme slovo přímo v indexu WordNetu
            target_synsets = lemma_to_synsets.get(lemma, [])
            
            if not target_synsets:
                print(f" ! Slovo '{lemma}' nebylo ve WordNetu nalezeno.")
                continue
            
            for synset_id in target_synsets:
                definition = synset_defs.get(synset_id, "")
                h_tree = get_hypernyms_limited(synset_id, synset_relations, synset_defs, synset_lemmas, 5)
                
                results.append({
                    "Lemma": lemma,
                    "Sense_ID": "DIRECT_WN_SEARCH", # Označení, že nejde o ID z ChainNetu
                    "Synset_ID": synset_id,
                    "Definition": definition,
                    "Hypernyms": "\n".join(h_tree),
                    "MML_Concept": concept
                })
            
    return results

def save_csv(results, path):
    """Uloží výsledky do CSV souboru."""
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        fieldnames = ["Lemma", "Sense_ID", "Synset_ID", "Definition", "Hypernyms", "MML_Concept"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

# --- SPOUŠTĚNÍ ---

if __name__ == "__main__":
    # 1. Načtení WordNetu
    s_defs, s_rels, l_to_s, s_lemmas = load_wordnet_cached()
    
    # 2. Načtení tvého seznamu hledaných slov
    mml_data = load_mml()

    # 3. Propojení (hledá přímo ve WordNetu podle tvého seznamu)
    final_results = link_data_direct_from_wn(s_defs, s_rels, l_to_s, s_lemmas, mml_data)
    
    # 4. Uložení
    if final_results:
        save_csv(final_results, OUTPUT_FILE)
        print("-" * 30)
        print(f"HOTOVO! Nalezeno {len(final_results)} významů pro tvá slova.")
        print(f"Výsledky uloženy do: {OUTPUT_FILE}")
    else:
        print("CHYBA: Nebyly nalezeny žádné shody.")