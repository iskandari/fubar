import os
import subprocess
import re
import cv2
from PIL import Image
import numpy as np
import argparse
import sys
import glob
sys.path.append('/home/ubuntu/fubar')
# sys.path.append('/Users/kjczarne/Desktop/Coding/Python/DSR/fubar')
from fubar_CONF import label_dict, labels_of_images_to_be_cropped, tf_s_conf, hprm, path_conf


def fubar_benchmark_function(thresh_linspace_div=10,
                             iou_thresh=0.5,
                             metrics=['map'],
                             optimization=['max'],
                             return_val=None):
    """
    benchmarking function
    :param thresh_linspace_div: number of buckets between 0 and 1 to set for confidence threshold
    :param iou_thresh: iou threshold for mAP calculation
    :param metrics: list of metrics to be used for evaluation, can be:
        * precision
        * recall
        * F1
        * TP
        * FP
        * FN
        * TP_<class name>
        * FP_<class name>
        * ap_<class name>
        * map
    :param optimization: list of functions to be used for evaluation, allows two strings: 'min' and 'max' or any
                         arbitrary function returning numpy array index
                         order must reflect order of metrics being
                         evaluated, e.g. if your metrics=['map', 'FN'] and you want to maximize mAP and minimize
                         false negatives, use ['max', 'min']
    :param return_val: set to anything but None if you want the function to return the data apart from only printing it
    :return: None or final_out dict ({metrics: {confidence_threshold, value}})
    """
    cwd = os.getcwd()
    os.chdir(path_conf['yolo_darknet_app'])
    thresholds = np.linspace(0, 1, thresh_linspace_div)

    patterns = {
        'precision': r'(?<=precision = )\d\.\d+',
        'recall': r'(?<=recall = )\d\.\d+',
        'F1': r'(?<=F1-score = )\d\.\d+',
        'TP': r'(?<=[^\(]TP = )\d+',
        'FP': r'(?<=FP = )\d+(?=,)',
        'FN': r'(?<=[^\(]FN = )\d+',
        'TP_': r'(?<=\(TP = )\d+',
        'FP_': r'(?<=FP = )\d+(?=\))',
        'ap_': r'(?<=ap = )\d+\.\d+',
        'iou_thresh': r'(?<=IoU threshold = )\d+',
        'thresh': r'(?<=thresh = )\d+\.\d+',
        'class_names': r'(?<=name = )\w+',
        'map': r'(?<=\(mAP@\d.\d\d\) = )\d\.\d+'
    }

    runs_dict = {}

    for i in thresholds:
        result = subprocess.run(['./darknet',
                                 'detector',
                                 'map',
                                 path_conf['yolo_obj.data'],
                                 path_conf['yolo_cfg'],
                                 path_conf['yolo_weights'],
                                 '-thresh',
                                 str(i),
                                 '-iou-thresh',
                                 str(iou_thresh)], stdout=subprocess.PIPE)
        result = result.stdout.decode('utf-8')
#         result = "calculation mAP (mean average precision)...\
# 408\
#  detections_count = 1276, unique_truth_count = 701\
# class_id = 0, name = lock, ap = 86.82%           (TP = 279, FP = 9)\
# class_id = 1, name = rack, ap = 80.40%           (TP = 225, FP = 23)\
# \
#  for thresh = 0.50, precision = 0.94, recall = 0.72, F1-score = 0.81\
#  for thresh = 0.50, TP = 504, FP = 32, FN = 197, average IoU = 70.68 %\
# \
#  IoU threshold = 50 %, used Area-Under-Curve for each unique Recall\
#  mean average precision (mAP@0.50) = 0.836113, or 83.61 %\
# Total Detection Time: 33.000000 Seconds"
        # per-class TP, FP and NP are sorted 0 to n, where n is number of classes

        results = {k: re.findall(v, result) for k, v in patterns.items()}

        # convert types in the results
        # if single element in list change to scalar
        copy_results = {k: v for k, v in results.items()}
        for k, v in results.items():
            repl_list = []
            if type(v) is list:
                for j in v:
                    try:
                        repl_list.append(int(j))
                    except ValueError:  # converting to int when there's a dot in a string raises a ValueError
                        try:
                            repl_list.append(float(j))
                        except ValueError:
                            repl_list.append(j)  # finally it can be just a string
            v = repl_list
            if len(v) == 1:
                copy_results[k] = v[0]
            else:
                for idx, val in enumerate(v):
                    if k == 'thresh':
                        copy_results[k] = val[0]  # right now YOLO doesn't allow to separately manipulate thresholds
                                             # for each class, so we just select the first element of the list
                    else:
                        new_key = k + f'_{results["class_names"][idx]}'
                        copy_results[new_key] = val

        runs_dict[i] = copy_results  # throw in results dict into dict collecting all the runs

    """{0: 
            {'precision': 0.94, 
            'recall': 0.72, 
            'F1': 0.81, 
            'TP': 504, 
            'FP': 32, 
            'FN': 197, 
            'TP_lock': 279
            'TP_rack': 225,
            'FP_lock': 9, 
            'FP_rack': 23, 
            'ap_lock': 86.82
            'ap_rack': 80.4, 
            'iou_thresh': 50, 
            'thresh': [0.5, 0.5],
            'class_names': ['lock', 'rack'], 
            'map': 0.836113}
        }"""

    metrics_dict = {k: [] for k in metrics}  # initialize dict with empty lists for metrics
    for run, result_dict in runs_dict.items():
        for k, v in result_dict.items():
            if k in metrics:
                metrics_dict[k].append(v)
    """{
        'map': [0.83, 0.98, 0.45],
        'FP_per_class': [[9, 23], [9, 23], [9, 23]]
    }"""
    temp = []
    for i in optimization:  # make min/max strings to correspond to np.argmin/np.argmax
        if i == 'max':
            temp.append(np.argmax)
        elif i == 'min':
            temp.append(np.argmin)
        else:
            if callable(i):
                temp.append(i)
            else:
                raise TypeError('optimization methods should be functions or "min"/"max" strings')
    optimization_dict = dict(zip(metrics, temp))
    """
    {
        'map': np.argmax
        'FP_per_class': np.argmin
    }    
    """
    final_out = {}
    for metric, list_of_vals in metrics_dict.items():
        func = optimization_dict[metric]
        idx = func(list_of_vals)
        print(f'Confidence threshold {idx} is optimal with respect to metric {metric}.')
        print(f'Value of metric {metric} for threshold {idx} is {list_of_vals[idx]}')
        print(f'Function used for evaluation: {func}')
        final_out[metric] = dict(confidence_threshold=idx, value=list_of_vals[idx])

    os.chdir(cwd)  # get back to original working directory

    if return_val is not None:
        return final_out
    else:
        return None


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument("-t", "--thresh",
                    help="confidence threshold bucket size, default is 10")
    ap.add_argument("-i", "--iou_thresh", default='draw.jpg',
                    help="IoU threshold to check mAP at, default is 0.5")
    ap.add_argument('-m', '--metrics', nargs='+',
                    help='metrics keys to be used for optimization')
    ap.add_argument('-o', '--optimization', nargs='+',
                    help='function names to be used for optimization, usually min/max')
    args = vars(ap.parse_args())
    ret = fubar_benchmark_function(args['thresh'], args['iou_thresh'])
    print(ret)
