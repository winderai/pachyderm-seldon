import argparse

import numpy as np
import pandas as pd

from alibi_detect.cd import KSDrift
from alibi_detect.utils.saving import save_detector

np.random.seed(112)

parser = argparse.ArgumentParser(
    description='Create a drift detector for income classification.')
parser.add_argument('data_file_path', type=str,
                    help='Path to csv file containing training set')
parser.add_argument('detector_path', type=str,
                    help='Path to output drift detector file')
args = parser.parse_args()

print(f"Loading data set from {args.data_file_path}")
income = pd.read_csv(args.data_file_path, index_col=0)
X_ref, Y_ref = income.drop(columns='target').values, income['target'].values

print("Creating drift detector...")
cd = KSDrift(p_val=.05, X_ref=X_ref, preprocess_X_ref=False,
             preprocess_fn=lambda x: x, data_type='tabular')

print(f"Saving drift detector in {args.detector_path}")
save_detector(cd, args.detector_path)
print("Drift detector saved!")