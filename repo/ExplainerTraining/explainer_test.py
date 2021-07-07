import argparse

import dill
import numpy as np
import pandas as pd
import joblib

np.random.seed(112)

parser = argparse.ArgumentParser()
parser.add_argument('data_file_path', type=str)
parser.add_argument('explainer_path', type=str)
parser.add_argument('detector_path', type=str)
args = parser.parse_args()

with open("{}/explainer.dill".format(args.explainer_path), 'rb') as in_strm:
    explainer = dill.load(in_strm)

print(explainer)

df = pd.read_csv(args.data_file_path, index_col=0)
X_test = df.drop(columns='target').values


clf = joblib.load(args.detector_path)
print(clf)
print()

for row in X_test[:10]:
    explanation = explainer.explain(
        row, 
        threshold=0.85, 
        coverage_samples=10, 
        batch_size=10
    )
    print('Anchor: %s' % (' AND '.join(explanation.anchor)))