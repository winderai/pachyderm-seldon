import argparse
import joblib
import numpy as np

import dill
import numpy as np
import pandas as pd
from alibi.explainers import AnchorTabular

np.random.seed(112)

parser = argparse.ArgumentParser(
    description='Create a model explainer for income classification.')
parser.add_argument('data_file_path', type=str,
                    help='Path to csv file containing training set')
parser.add_argument('detector_path', type=str,
                    help='Path to drift detector file')
parser.add_argument('explainer_path', type=str,
                    help='Path to output explainer file')
parser.add_argument('income_data_commit', type=str,
                    help='Commit hash of input income_data repo')
parser.add_argument('income_training_commit', type=str,
                    help='Commit hash of input income_training repo')
args = parser.parse_args()

print("income_data_commit: {}".format(args.income_data_commit))
print("income_training_commit: {}".format(args.income_training_commit))

print(f"Loading income model from {args.detector_path}")
clf = joblib.load(args.detector_path)
def predict_fn(x): return clf.predict_proba(x)

print(f"Loading data set from {args.data_file_path}")
income = pd.read_csv(args.data_file_path, index_col=0)
X_ref, Y_ref = income.drop(columns='target').values, income['target'].values
feature_names = income.drop(columns='target').columns

print(f"Training Explainer...")
explainer = AnchorTabular(predict_fn, feature_names=feature_names, seed=112)
explainer.fit(X_ref)
print("Explainer trained!")

print(f"Saving explainer in {args.explainer_path}")
dill.dump(explainer, open("{}/explainer.dill".format(args.explainer_path), "wb"))
print("Explainer saved!")