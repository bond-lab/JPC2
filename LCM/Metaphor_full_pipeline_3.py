import json
import gzip
import csv
import xml.etree.ElementTree as ET
import os
from difflib import get_close_matches

# Nastavení cest - nyní relativní k místu spuštění
BASE_PATH = os.path.dirname(os.path.abspath(__file__))
WORDNET_FILE = os.path.join(BASE_PATH, "omw-en_1.4_cn.xml.gz")
CHAINNET_FILE = os.path.join(BASE_PATH, "chainnet_metonymy.json")
OUTPUT_FILE = os.path.join(BASE_PATH, "mapping_results_fixed.csv")

HYPERNYM_DEPTH_LIMIT = 5 

def load_wordnet_xml(path):
    print(f"Načítání WordNet XML z {path}...")
    if not os.path.exists(path):
        print("CHYBA: Soubor WordNetu nebyl nalezen.")
        return {}, {}, {}, {}

    with gzip.open(path, 'rb') as f:
        xml_data = f.read()

    root = ET.fromstring(xml_data)

    synset_defs = {}
    synset_relations = {}
    lemma_to_synsets = {}
    sense_to_synset = {} 

    for synset in root.findall(".//Synset"):
        sid = synset.get("id")
        definition = ""
        def_elem = synset.find("Definition")
        if def_elem is not None and def_elem.text:
            definition = def_elem.text.strip()
        synset_defs[sid] = definition

        hypernyms = [rel.get("target") for rel in synset.findall("SynsetRelation") 
                     if rel.get("relType") == "hypernym"]
        synset_relations[sid] = hypernyms

    for lex_entry in root.findall(".//LexicalEntry"):
        lemma_elem = lex_entry.find("Lemma")
        if lemma_elem is None: continue
        lemma = lemma_elem.get("writtenForm", "").lower()

        for sense in lex_entry.findall("Sense"):
            synset_id = sense.get("synset")
            sense_key = sense.get("id") 

            if lemma not in lemma_to_synsets:
                lemma_to_synsets[lemma] = []
            lemma_to_synsets[lemma].append(synset_id)
            
            if sense_key:
                sense_to_synset[sense_key] = synset_id

    print(f"Načteno synsetů: {len(synset_defs)}, Indexováno lemat: {len(lemma_to_synsets)}")
    return synset_defs, synset_relations, lemma_to_synsets, sense_to_synset

def get_hypernyms_limited(synset_id, relations, defs, depth, visited=None):
    if visited is None: visited = set()
    if depth == 0 or synset_id in visited: return []
    visited.add(synset_id)

    hypernyms = []
    for h in relations.get(synset_id, []):
        if h in defs:
            hypernyms.append(defs[h])
            hypernyms.extend(get_hypernyms_limited(h, relations, defs, depth - 1, visited))
    return hypernyms

def load_chainnet(path):
    print("Načítání ChainNet JSON...")
    if not os.path.exists(path):
        print("CHYBA: Soubor ChainNet nebyl nalezen.")
        return []

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    entries = data.get("content", []) if isinstance(data, dict) else data

    results = []
    for item in entries:
        sense_id = item.get("from_sense", "")
        lemma = item.get("wordform", "").lower()
        if "%" in sense_id:
            lemma = sense_id.split("%")[0].lower()
        results.append({"lemma": lemma, "sense_id": sense_id})
    return results

def load_mml():
    return {
        "ARGUMENT IS WAR": ["attack", "defend", "fight", "target", "strategy", "force"],
        "IDEAS ARE FOOD": ["digest", "swallow", "cook", "bake", "spoon", "bite"],
        "UNDERSTANDING IS SEEING": ["see", "view", "focus", "vision", "clear", "sight"],
        "TIME IS MONEY": ["spend", "waste", "invest", "cost", "budget", "save", "speed"],
        "LIFE IS A JOURNEY": ["path", "road", "step", "crossroads", "guide"],
        "CONTROL IS UP": ["rise", "high", "top", "peak", "raise", "superior"],
        "SOCIETY IS A BODY": ["head", "heart", "arm", "brain", "member", "shoulder"]
    }

def link_data(chainnet, synset_defs, synset_relations, lemma_to_synsets, sense_to_synset, mml):
    print("Propojování metafor...")
    mml_lookup = {word: concept for concept, words in mml.items() for word in words}
    results = []
    seen_entries = set()

    for entry in chainnet:
        lemma = entry["lemma"]
        sense_key = entry["sense_id"]

        target_synsets = []
        if sense_key in sense_to_synset:
            target_synsets = [sense_to_synset[sense_key]]
        elif lemma in lemma_to_synsets:
            target_synsets = lemma_to_synsets[lemma]
        
        if not target_synsets: continue

        for synset_id in target_synsets:
            unique_key = (lemma, sense_key, synset_id)
            if unique_key in seen_entries: continue
            seen_entries.add(unique_key)

            definition = synset_defs.get(synset_id, "")
            hypernyms = get_hypernyms_limited(synset_id, synset_relations, synset_defs, HYPERNYM_DEPTH_LIMIT)
            hypernym_chain = " | ".join(hypernyms)

            concept = mml_lookup.get(lemma)
            if not concept:
                match = get_close_matches(lemma, list(mml_lookup.keys()), n=1, cutoff=0.85)
                if match: concept = mml_lookup[match[0]]

            if concept:
                results.append({
                    "Lemma": lemma,
                    "Sense_ID": sense_key,
                    "Synset_ID": synset_id,
                    "Definition": definition,
                    "Hypernyms": hypernym_chain,
                    "MML_Concept": concept
                })

    print(f"Nalezeno unikátních propojení: {len(results)}")
    return results

def save_csv(results, path):
    print(f"Ukládání do {path}...")
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["Lemma", "Sense_ID", "Synset_ID", "Definition", "Hypernyms", "MML_Concept"])
        writer.writeheader()
        writer.writerows(results)

if __name__ == "__main__":
    print("\n---- Start Metaphor Pipeline ----\n")
    s_defs, s_rels, l_to_s, sense_to_syn = load_wordnet_xml(WORDNET_FILE)
    chainnet_data = load_chainnet(CHAINNET_FILE)
    mml_data = load_mml()

    if s_defs and chainnet_data:
        final_results = link_data(chainnet_data, s_defs, s_rels, l_to_s, sense_to_syn, mml_data)
        save_csv(final_results, OUTPUT_FILE)
    
    print("\n--- Done ---")