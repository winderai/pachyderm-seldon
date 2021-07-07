import argparse

import numpy as np
import pandas as pd
import json
from alibi_detect.utils.saving import load_detector

np.random.seed(112)

parser = argparse.ArgumentParser()
parser.add_argument('data_file_path', type=str)
parser.add_argument('detector_path', type=str)
args = parser.parse_args()


df = pd.read_csv(args.data_file_path, index_col=0)

print(df)
cd = load_detector(args.detector_path)

X = df.drop(columns='target').values

preds_drift = cd.predict(X, drift_type='batch', return_p_val=True, return_distance=True)
print(preds_drift)