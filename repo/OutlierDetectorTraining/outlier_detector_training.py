import argparse

import numpy as np
import pandas as pd
from alibi_detect.od import Mahalanobis
from alibi_detect.utils.data import create_outlier_batch
from alibi_detect.utils.saving import save_detector


np.random.seed(112)

parser = argparse.ArgumentParser(
    description='Train an outlider detector for income dataset.')
parser.add_argument('data_file_path', type=str,
                    help='Path to csv file containing training set')
parser.add_argument('outlier_detector_path', type=str,
                    help='Path to output detector file')
args = parser.parse_args()


print(f"Loading data set from {args.data_file_path}")
income = pd.read_csv(args.data_file_path, index_col=0)

X_train, Y_train = income.drop(
    columns='target').values, income['target'].values
mean, stdev = X_train.mean(axis=0), X_train.std(axis=0)


od = Mahalanobis(n_components=2, data_type='tabular')

print("Warming up detector...")

perc_outlier=2
od.infer_threshold(X_train, threshold_perc=100-perc_outlier)

print(f"Saving outlier detector in {args.outlier_detector_path}")
save_detector(od, args.outlier_detector_path)
print("Outlier detector saved!")