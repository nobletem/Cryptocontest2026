import csv
import string

from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

upper = string.ascii_uppercase


def IC(text):
    text = "".join(c for c in text.upper() if c in upper)
    n = len(text)

    if n < 2:
        return 0

    counts = [text.count(c) for c in upper]
    return sum(count * (count - 1) for count in counts) / (n * (n - 1))


with open("training.csv", "r", newline="") as f:
    rows = list(csv.DictReader(f))

x = [[IC(row["ciphertext"])] for row in rows]
y = [1 if row["label"] == "c" else 0 for row in rows]

model = make_pipeline(StandardScaler(), LogisticRegression())
model.fit(x, y)

texts = [
    "NKRRUZNOYOYGIRGYYOIGRIOVNKXGTGREYOYVXUHRKSLUXZNKIXEVZGTGREYOYIUSVKZOZOUTIUTMXGZARGZOUTYUTMKZZOTMZNKIUXXKIZGTYCKX",
    "ROVVYDRSCSCKMVKCCSMKVMSZROBKXKVICSCZBYLVOWPYBDROMBIZDKXKVICSCMYWZODSDSYXMYXQBKDEVKDSYXCYXQODDSXQDROMYBBOMDKXCGOB",
    "DRKXUIYEPYBIYEBZKBDSMSZKDSYXGOGSCRIYEKVVDROLOCDSXIYEBPEDEBOOXNOKFYBC",
    "ZNGTQEUALUXEUAXVGXZOIOVGZOUTCKCOYNEUAGRRZNKHKYZOTEUAXLAZAXKKTJKGBUXY"
]

values = [[IC(text)] for text in texts]
predictions = model.predict(values)
probabilities = model.predict_proba(values)[:, 1]

for number, text in enumerate(texts, 1):
    value = IC(text)
    label = predictions[number - 1]
    probability = probabilities[number - 1]
    name = "Caesar" if label == 1 else "Vigenere"
    print(f"{number}: IC = {value:.6f}, P(c) = {probability:.6f}, class = {name}")
