import json
import csv
import os
import wn
import pickle

# --- AUTOMATICKÉ NASTAVENÍ CEST ---
# Toto zajistí, že skript najde soubory, i když ho spouštíš z jiného adresáře
BASE_PATH = os.path.dirname(os.path.abspath(__file__))
CHAINNET_FILE = os.path.join(BASE_PATH, "chainnet_metonymy.json")
OUTPUT_FILE = os.path.join(BASE_PATH, "mapping_results.csv")
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
        # Uložíme si lemmata jako čistý seznam stringů
        synset_lemmas[sid] = [l.lower() for l in synset.lemmas()]

        # Relace: přímé hypernymy
        synset_relations[sid] = [h.id for h in synset.hypernyms()]

        # Mapování slovo -> ID synsetu
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

def get_ancestor_lemmas(synset_id, relations, lemmas_dict, depth, visited=None):
    """Najde všechna slova (lemmata) v nadřazených kategoriích do hloubky X."""
    if visited is None: visited = set()
    if depth == 0 or synset_id in visited: return []
    visited.add(synset_id)

    ancestors = []
    for h_id in relations.get(synset_id, []):
        ancestors.extend(lemmas_dict.get(h_id, []))
        ancestors.extend(get_ancestor_lemmas(h_id, relations, lemmas_dict, depth - 1, visited))
    return list(set(ancestors))

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

def load_chainnet(path):
    """Načte vstupní data od profesora."""
    if not os.path.exists(path):
        print(f"Upozornění: Soubor {path} nebyl nalezen.")
        return []
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    entries = data.get("content", []) if isinstance(data, dict) else data
    
    results = []
    for item in entries:
        sense_id = item.get("from_sense", "")
        lemma = item.get("wordform", "").lower()
        if not lemma and "%" in sense_id:
            lemma = sense_id.split("%")[0].lower()
        results.append({"lemma": lemma, "sense_id": sense_id})
    return results

def load_mml():
    """Definuje cílové konceptuální metafory."""
    return {
        "COLOUR IS MINERAL": ["sapphire", "amethyst", "turquoise", "ruby", "amber", "emerald", "coral", "gold"],
        "COLOUR IS PLANT": ["orchid", "sunflower", "daisy", "rose", "violet"]
    }

def link_data(chainnet, synset_defs, synset_relations, lemma_to_synsets, synset_lemmas, mml):
    print("Propojování dat (Striktní režim)...")
    # Vytvoříme si jednoduchou tabulku pro rychlé hledání
    mml_lookup = {word.lower().strip(): concept for concept, words in mml.items() for word in words}

    results = []
    for entry in chainnet:
        lemma = entry["lemma"].strip().lower()
        sense_key = entry["sense_id"]
        
        # STRIKTNÍ FILTR: Pokud slovo není přímo v tvém seznamu, rovnou ho přeskoč
        if lemma not in mml_lookup:
            continue
            
        concept = mml_lookup[lemma]
        target_synsets = lemma_to_synsets.get(lemma, [])
        
        for synset_id in target_synsets:
            definition = synset_defs.get(synset_id, "")
            h_tree = get_hypernyms_limited(synset_id, synset_relations, synset_defs, synset_lemmas, 5)
            
            results.append({
                "Lemma": lemma,
                "Sense_ID": sense_key,
                "Synset_ID": synset_id,
                "Definition": definition,
                "Hypernyms": "\n".join(h_tree),
                "MML_Concept": concept
            })
            
    print(f"Hotovo. Nalezeno {len(results)} výskytů tvých vybraných slov.")
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
    # Načtení WordNetu (pokud není cache, vytvoří se)
    s_defs, s_rels, l_to_s, s_lemmas = load_wordnet_cached()
    
    # Načtení vstupních dat
    chainnet_data = load_chainnet(CHAINNET_FILE)
    mml_data = load_mml()

    if not chainnet_data:
        print(f"CHYBA: Soubor {CHAINNET_FILE} chybí nebo je prázdný!")
    else:
        # Finální propojení
        final_results = link_data(chainnet_data, s_defs, s_rels, l_to_s, s_lemmas, mml_data)
        
        # Uložení
        save_csv(final_results, OUTPUT_FILE)
        
        print("-" * 30)
        print(f"HOTOVO! Nalezeno {len(final_results)} shod.")
        print(f"Výsledky uloženy do: {OUTPUT_FILE}")