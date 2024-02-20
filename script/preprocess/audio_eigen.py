# -*- coding: utf-8 -*-

"""模块功能描述

详细描述

"""

from setting import *
import json
import pandas as pd
import numpy as np


def audioWordSeg(
    eigen_list: dict = None, reduced_noise: np.ndarray = None, sr: int = None
) -> dict:
    """按照getWordInfoList的结果列表，以词为单位，将音频时域信息序列进行切割，eg："来"的时间间隔为1.3秒，要获取这个时间间隔内的音频信息。

    eigen_list：
        传入需要提取的JSON文件，字典文件中包括start_time,end_time,word。
    reduced_noise:
        降噪后音频的时域信息。
    sr：
        采样率。

    返回：
        eigen_list：
            在传入的JSON文件中，增加了以词为单位的时间间隔和该时间段内的时域信息。eg：
    {'eigen_list': [{'word': '起来',
       'eigen': {'start_time': 13.0,
        'end_time': 14.39,
        'audio_segment': array([ 8.5642641e-05, -5.3360149e-05, -2.1816693e-05, ...,
                2.0035163e-02,  2.3617115e-02,  1.1252311e-02], dtype=float32),
        'times': 1.3900000000000006}} ,..., {'word'....}]}

    """

    eigen_list = eigen_list["eigen_list"]

    eigen_segments = []  # 用来存储子字典eigen_segment
    """遍历JSON文件中的子字典eigen_list，获取其中的每个词的起始和结束时间，并按时间段进行切割音频，返回出np.ndarray类型"""
    for item in eigen_list:
        start_time = item["eigen"]["start_time"]
        end_time = item["eigen"]["end_time"]
        word = item["word"]
        times = end_time - start_time
        times = round(times, 3)

        # 将时间转换为样本索引
        start_sample = int(start_time * sr)
        end_sample = int(end_time * sr)

        # 根据样本索引切割时域信号
        audio_segment = reduced_noise[start_sample:end_sample]

        # 构建新的子字典
        eigen_segment = {
            "word": word,
            "eigen": {
                "start_time": start_time,
                "end_time": end_time,
                "seg_seq": audio_segment,
                "times": times,
            },
        }

        eigen_segments.append(eigen_segment)
    eigen_list = {"eigen_list": eigen_segments}

    return eigen_list
