import argparse

import numpy as np
import pandas as pd
from alibi_detect.od import Mahalanobis
from alibi_detect.utils.data import create_outlier_batch
from alibi_detect.utils.saving import load_detector


np.random.seed(112)

parser = argparse.ArgumentParser()
parser.add_argument('data_file_path', type=str)
parser.add_argument('outlier_detector_path', type=str)
args = parser.parse_args()

df = pd.read_csv(args.data_file_path, index_col=0)
X = df.drop(columns='target').values

od = load_detector(args.outlier_detector_path)
print(od)

preds = od.predict(
    X,
    return_instance_score=True
)

df_detections = pd.DataFrame(preds['data'])
perc_outl = df_detections[df_detections['is_outlier'] == 1]['is_outlier'].count() / df_detections['is_outlier'].count() * 100
print("% outliers: {}".format(perc_outl))