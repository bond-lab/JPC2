import json
import numpy as np
import matplotlib.pyplot as plt

from collections import Counter
from wn.compat import sensekey
from sentence_transformers import SentenceTransformer
from nltk.corpus import wordnet

from sklearn.model_selection import (StratifiedKFold, cross_validate, cross_val_predict)
from sklearn.feature_extraction import DictVectorizer
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.calibration import calibration_curve
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.metrics import ConfusionMatrixDisplay

from sklearn.naive_bayes import GaussianNB
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier
from sklearn.neighbors import KNeighborsClassifier

sense_getter = sensekey.sense_getter('omw-en:2.0')
sentence_model= SentenceTransformer('all-MiniLM-L6-v2')  
le = LabelEncoder()

embedding_cache = {}

tropes_list = []
metaphor_f1 = []
metonymy_f1 = []
macro_precisions = []
macro_recalls = []
macro_f1s = []
accuracies = []
errors = []

skf = StratifiedKFold(
        n_splits=10,
        shuffle=True,
        random_state=42
    )

def tropes(metaphor, metonymy):
    for e in metaphor.get('content', []):
        if all(k in e for k in ('wordform', 'from_sense', 'to_sense')):
            tropes_list.append((
                'metaphor',
                e['wordform'],
                e['from_sense'],
                e['to_sense']
            ))

    for e in metonymy.get('content', []):
        if all(k in e for k in ('wordform', 'from_sense', 'to_sense')):
            tropes_list.append((
                'metonymy',
                e['wordform'],
                e['from_sense'],
                e['to_sense']
            ))

    return tropes_list

def hypernym_overlap(fs, ts):
    try:
        f = set(h for path in fs.hypernym_paths() for h in path)
        t = set(h for path in ts.hypernym_paths() for h in path)

        return len(f & t) / max(len(f | t), 1)

    except Exception:
        return 0

def get_text(syn):
    text = syn.definition() + " " + " ".join(syn.examples())

    return text

def get_embedding(text):
    if text not in embedding_cache:
        embedding_cache[text] = sentence_model.encode(text)

    return embedding_cache[text]

def extract_features(fs, ts):
    text_fs = get_text(fs)
    text_ts = get_text(ts)

    emb_fs = get_embedding(text_fs)
    emb_ts = get_embedding(text_ts)

    hyp_overlap = hypernym_overlap(fs, ts)

    path = fs.shortest_path(ts)
    distance = len(path)-1 if path else 100

    fs_depth = fs.max_depth()
    ts_depth = ts.max_depth()
    depth_diff = fs_depth - ts_depth

    lchs = fs.lowest_common_hypernyms(ts)
    lch_depth = (lchs[0].max_depth() if lchs else 0)

    sim = cosine_similarity([emb_fs], [emb_ts])[0][0]
    path_sim = 1/(distance+1)
    wup_sim = (2 * lch_depth /(fs_depth + ts_depth))

    if lch_depth == 0:
        wup_sim = 0

    from_lex = fs.lexfile()
    to_lex = ts.lexfile()
  
    path1 = set(h for p in fs.hypernym_paths() for h in p)
    path2 = set(h for p in ts.hypernym_paths() for h in p)
    union = path1 | path2
    jaccard = (len(path1 & path2) / len(union) if union else 0.0)

    from_def = fs.definition()
    to_def = ts.definition()
    def_emb_fs = get_embedding(from_def)
    def_emb_ts = get_embedding(to_def)
    def_sim = cosine_similarity([def_emb_fs],[def_emb_ts])[0][0]

    features = {
        "cos_sim": sim,
        "path_sim": path_sim,
        "wup_sim": wup_sim,
        "jaccard_hypernyms": jaccard,
        "semantic_gap": 1 - sim,
        "hypernym_overlap": hyp_overlap,
        "depth_diff": depth_diff,
        "semantic_distance": distance,
        "lch_depth": lch_depth,
        "transision_lex": f"{from_lex}-> {to_lex}",
        "from_pos": fs.pos,
        "from_lexfile": from_lex,
        "definition_sim": def_sim,
        "fs_definition": from_def,
        "emb": np.mean(emb_fs)

    }

    return features

def models_configuration():
    lr = make_pipeline(
        StandardScaler(),
        LogisticRegression(
            class_weight='balanced'
        ) 
    )

    rf= RandomForestClassifier(
        class_weight='balanced',
        random_state=42,
     )

    xgb = XGBClassifier(
        n_estimators=100,
        max_depth=3,
        learning_rate=0.1,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        eval_metric="logloss"
        )

    nb = make_pipeline(
            StandardScaler(),
            GaussianNB()
            )
    
    knn = KNeighborsClassifier(
        n_neighbors=5,
        weights="distance",
        metric= "cosine" 
    )

    model = {
        "LRegression": lr,
        "Rforest": rf,
        "XGBoost": xgb,
        "GNaiveBayers": nb,
        "KNN": knn,
    }
    return model

def train_model(data):
    X = []
    y = []
    skipped = 0
    models = models_configuration()

    for label, word, fs, ts in data:
        try:
            syn_fs = sense_getter(fs).synset()
            syn_ts = sense_getter(ts).synset()
            
            ft = extract_features(syn_fs, syn_ts)

            X.append(ft)
            y.append(label)

        except Exception as e: 
            print("FAILED:", fs, ts)
            print(e)

            skipped += 1 

    print(f"\nSkipped: {skipped}")
    print(f"Valid samples: {len(X)}")
    print(Counter(y))

    if len(X) == 0:
        raise ValueError("No valid samples!")
    

    vectorizer = DictVectorizer(sparse=False)
    X = vectorizer.fit_transform(X)
    y = le.fit_transform(y)

    for name, model in models.items():
        evaluate(model, name, X,  y)

def evaluate(model, model_name, X, y): 
    cv = StratifiedKFold(
        n_splits=10,
        shuffle=True,
        random_state=42
    )

    print("-"*50) 
    print(model_name)
    print("-"*50) 

    param = {
        "estimator": model,
        "X": X,
        "y": y,
        "cv": cv,    }
    
    results = cross_validate(
       **param,
        scoring=[
            "accuracy",
            "precision_macro",
            "recall_macro",
            "f1_macro"
        ],
        return_train_score=True, 
    )

    print("TRAIN")
    print(f"Accuracy:  {results['train_accuracy'].mean():.2%}")
    print(f"Precision: {results['train_precision_macro'].mean():.2%}")
    print(f"Recall:    {results['train_recall_macro'].mean():.2%}")
    print(f"F1:        {results['train_f1_macro'].mean():.2%}")

    print("\nTEST")
    print(f"Accuracy:  {results['test_accuracy'].mean():.2%}")
    print(f"Precision: {results['test_precision_macro'].mean():.2%}")
    print(f"Recall:    {results['test_recall_macro'].mean():.2%}")
    print(f"F1:        {results['test_f1_macro'].mean():.2%}")

    pred_test = cross_val_predict(**param)

    ConfusionMatrixDisplay.from_predictions( 
        y,
        pred_test, 
        display_labels=["metaphor","metonomy"] 
    )
    plt.title("Test confusion matrix")
    plt.show()

    print("\nComputing confidence score...")

    metaphor_id = le.transform(['metaphor'])[0]
    metonymy_id = le.transform(['metonymy'])[0]

    probs = cross_val_predict(**param, method="predict_proba")

    probs_meta = probs[:, metaphor_id]
    probs_meto = probs[:, metonymy_id]

    y_meta = (y == metaphor_id).astype(int)
    y_meto = (y == metonymy_id).astype(int)

    fraction_meta, mean_meta = calibration_curve(
        y_meta,
        probs_meta,
        )

    plt.figure(figsize=(6, 6))

    plt.plot(
        mean_meta,
        fraction_meta,
        marker='o',
        label='Model'
        )

    plt.plot(
        [0, 1],
        [0, 1],
        '--',
        label='Perfect calibration'
        )

    plt.xlabel('Mean predicted probability')
    plt.ylabel('Fraction positive')
    plt.title('Calibration curve — metaphor')
    plt.legend()
    plt.show()

    fraction_meto, mean_meto = calibration_curve(
        y_meto,
        probs_meto,
        )

    plt.figure(figsize=(6, 6))

    plt.plot(
        mean_meto,
        fraction_meto,
        marker='o',
        label='Model'
        )

    plt.plot(
        [0, 1],
        [0, 1],
         '--',
    label='Perfect calibration'
        )

    plt.xlabel('Mean predicted probability')
    plt.ylabel('Fraction positive')
    plt.title('Calibration curve — metonymy')
    plt.legend()
    plt.show()
 
def main():

    with open("chainnet_metaphor.json","r",encoding="utf-8") as fp:
        metaphor = json.load(fp)

    with open("chainnet_metonymy.json","r",encoding="utf-8") as fp:
        metonymy = json.load(fp)

    data = tropes(metaphor,metonymy)
    train_model(data)

if __name__ == "__main__":
    main()
