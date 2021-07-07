import argparse

import numpy as np
import joblib
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score


np.random.seed(112)

parser = argparse.ArgumentParser(
    description='Train a model for income classification.')
parser.add_argument('data_file_path', type=str,
                    help='Path to csv file containing training set')
parser.add_argument('model_path', type=str, help='Path to output joblib file')
args = parser.parse_args()

print(f"Loading data set from {args.data_file_path}")
income = pd.read_csv(args.data_file_path, index_col=0)
X_train, Y_train = income.drop(
    columns='target').values, income['target'].values

print("Training model...")
clf = LogisticRegression(
    random_state=112,
    max_iter=1000,
)
clf.fit(X_train, Y_train)
print("Model trained!")

df_coeff = pd.DataFrame({'feature': income.drop(
    columns='target').columns, 'coefficient': clf.coef_[0]})
df_coeff = df_coeff.sort_values(by='coefficient', ascending=False)
print("model coefficients:")
print(df_coeff)


def predict_fn(x): return clf.predict(x)


print('Train accuracy: ', accuracy_score(Y_train, predict_fn(X_train)))

print(f"Saving model in {args.model_path}")
joblib.dump(clf, args.model_path)
print("Model saved!")
