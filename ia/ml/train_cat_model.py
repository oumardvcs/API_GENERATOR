import os
import pandas as pd
from sklearn.preprocessing import LabelEncoder
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
import joblib

print("🔹 Début du script d'entraînement")

BASE_DIR = os.path.dirname(__file__)
CSV_PATH = os.path.join(BASE_DIR, "column_data_from_db.csv")
MODEL_PATH = os.path.join(BASE_DIR, "categ_model.pkl")

def train_categ_model():
    # 1️⃣ Charger le CSV
    df = pd.read_csv(CSV_PATH)
    df["is_categ_target"] = df["semantic_type"].apply(lambda x: 1 if x == "categorical" else 0)


    # 2️⃣ Encoder dtype
    le = LabelEncoder()
    df["dtype_enc"] = le.fit_transform(df["dtype"])

    # 3️⃣ Features et cible
    X = df[["dtype_enc", "n_unique", "avg_length", "is_numeric"]]
    y = df["is_categ"]

    # 4️⃣ Split train/test
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # 5️⃣ Créer le modèle
    clf = RandomForestClassifier(n_estimators=100, random_state=42)
    clf.fit(X_train, y_train)

    # 6️⃣ Évaluer
    score = clf.score(X_test, y_test)
    print(f"Accuracy sur le test set : {score:.2f}")

    # 7️⃣ Sauvegarder le modèle
    joblib.dump(clf, MODEL_PATH)
    print(f"Modèle sauvegardé dans {MODEL_PATH}")

if __name__ == "__main__":
    train_categ_model()

