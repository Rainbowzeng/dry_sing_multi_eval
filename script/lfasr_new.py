# -*- coding: utf-8 -*-
import base64
import hashlib
import hmac
import json
import os
import time
import requests
import urllib
import sys
import re
from pydub import AudioSegment
from pypinyin import pinyin, lazy_pinyin, Style

lfasr_host = 'https://raasr.xfyun.cn/v2/api'
# 请求的接口名
api_upload = '/upload'
api_get_result = '/getResult'


class RequestApi(object):
    def __init__(self, appid, secret_key, upload_file_path, hotword):
        self.appid = appid
        self.secret_key = secret_key
        self.upload_file_path = upload_file_path
        self.ts = str(int(time.time()))
        self.signa = self.get_signa()
        self.hotword = hotword

    def get_signa(self):
        appid = self.appid
        secret_key = self.secret_key
        m2 = hashlib.md5()
        m2.update((appid + self.ts).encode('utf-8'))
        md5 = m2.hexdigest()
        md5 = bytes(md5, encoding='utf-8')
        # 以secret_key为key, 上面的md5为msg， 使用hashlib.sha1加密结果为signa
        signa = hmac.new(
            secret_key.encode('utf-8'),
            md5,
            hashlib.sha1).digest()
        signa = base64.b64encode(signa)
        signa = str(signa, 'utf-8')
        return signa

    def upload(self):
        print("upload part：")
        upload_file_path = self.upload_file_path
        file_len = os.path.getsize(upload_file_path)
        file_name = os.path.basename(upload_file_path)

        param_dict = {}
        param_dict['appId'] = self.appid
        param_dict['signa'] = self.signa
        param_dict['ts'] = self.ts
        param_dict["fileSize"] = file_len
        param_dict["fileName"] = file_name
        param_dict["duration"] = "200"
        param_dict["language"] = "cn"
        param_dict["hotWord"] = self.hotword
        """
        以下为部分额外可选的传入参数，可根据需要以此形式添加参数
        可选参数详见https://www.xfyun.cn/doc/asr/ifasr_new/API.html
        """
        # param_dict["candidate"] = ""
        # param_dict["roleType"] = ""
        # param_dict["roleNum"] = ""
        # param_dict["roleNum"] = ""
        # param_dict["pd"] = ""
        # param_dict["audioMode"] = ""
        print("upload param：", param_dict)
        data = open(upload_file_path, 'rb').read(file_len)

        response = requests.post(
            url=lfasr_host +
            api_upload +
            "?" +
            urllib.parse.urlencode(param_dict),
            headers={
                "Content-type": "application/json"},
            data=data)
        print("upload_url:", response.request.url)
        upload_result = json.loads(response.text)
        print("upload resp:", upload_result)
        return upload_result

    def get_result(self):
        uploadresp = self.upload()
        orderId = uploadresp['content']['orderId']
        param_dict = {}
        param_dict['appId'] = self.appid
        param_dict['signa'] = self.signa
        param_dict['ts'] = self.ts
        param_dict['orderId'] = orderId
        param_dict['resultType'] = "transfer"
        print("")
        print("get_result part：")
        print("get_result parm：", param_dict)
        status = 3
        # 建议使用回调的方式查询结果，查询接口有请求频率限制
        while status == 3:
            response = requests.post(
                url=lfasr_host +
                api_get_result +
                "?" +
                urllib.parse.urlencode(param_dict),
                headers={
                    "Content-type": "application/json"})
            # print("get_result_url:",response.request.url)
            result = json.loads(response.text)
            print(result)
            status = result['content']['orderInfo']['status']
            print("status=", status)
            if status == 4 and status == -1:
                break
            time.sleep(1)
        return result


# 定义downloadOrderResul方法：规范音频文件名，若音频文件未下载好，则会连接api后下载音频文件并转为JSON本地文件
def downloadOrderResult(
        appid,
        secret_key,
        lyrics_dir,
        lyrics_file_name,
        upload_file_path,
        download_dir,
        output_file_name):
    file_name = os.path.basename(upload_file_path)
    # 通过正则表达规范所获取歌曲的名字，获取第一个"."之前的内容
    real_file_name = re.search(r"^(.*?)\.", file_name).group(1)
    new_output_file_name = real_file_name + '_' + output_file_name
    # 将下载目录路径和新的输出文件名拼接，生成完整的json结果下载路径
    download_path = download_dir / new_output_file_name
    # 判断音频的json文件是否已经存在，已存在则不执行下载操作
    if not os.path.exists(download_path):
        print(f"Start download '{download_path}' ...")
        # 检查下载目录是否存在，如果不存在则创建该目录
        if not os.path.exists(download_dir):
            os.makedirs(download_dir)
            print(f"Path '{download_dir}' created.")
        else:
            print(f"Path '{download_dir}' already exists.")
        hotword = getHotWords(lyrics_dir=lyrics_dir, file_name=lyrics_file_name)
        # 使用提供的应用程序ID、密钥和上传文件路径初始化
        api = RequestApi(appid=appid,
                         secret_key=secret_key,
                         upload_file_path=upload_file_path,
                         hotword=hotword)
        transfer_result = api.get_result()
        # 获取transfer_result结果中content下orderResult的字符串内容
        orderResult_str = transfer_result['content']['orderResult']
        orderResult_json = json.loads(orderResult_str)
        lattice_json = orderResult_json["lattice"]
        # 将下载后的JSON文件保存到本地
        with open(download_path, "w", encoding="gbk") as json_file:
            json.dump(lattice_json, json_file, indent=2, ensure_ascii=False)
        print(f"File '{download_path}' created!")
    else:
        print(f"File '{download_path}' already exists!Download is close...")
    with open(download_path, 'r', encoding='gbk') as file:
        lattice_json = json.load(file)
    return lattice_json


# gbkXfrFstLetter方法：用于将给定的GBK编码字符串转换为拼音首字母
def gbkXfrFstLetter(gbk_str, style):
    # style参数指定了转换的风格，即只返回拼音的首字母
    if style == 0:
        return gbk_str
    elif style == 1:
        pinyin_list = lazy_pinyin(gbk_str)
        pinyin_result = ' '.join(''.join(inner_list)
                                 for inner_list in pinyin_list)
    elif style == 2:
        pinyin_list = pinyin(gbk_str, style=Style.FIRST_LETTER)
        pinyin_result = ''.join(''.join(inner_list)
                                for inner_list in pinyin_list)
    reg_pinyin_result = re.sub(r'[^a-z\s]', '', pinyin_result)
    return reg_pinyin_result


# extraValues方法：用于从给定的数据中提取特定键（"w"键）的值，并根据需要将中文转换为拼音首字母
def extractValues(data, style=2):
    w_values = []
    # 如果data是一个列表，遍历列表中的每个元素，并递归调用extractValues函数，将返回的值扩展到w_values列表中
    if isinstance(data, list):
        for item in data:
            w_values.extend(
                extractValues(data=item, style=style))
    # 如果data是一个字典，遍历字典中的每个键值对
    elif isinstance(data, dict):
        for key, value in data.items():
            if key == "w":
                # 是否将中文转成拼音首字母，结果用于音频切割
                w_values.append(gbkXfrFstLetter(value, style=style))
            else:
                w_values.extend(
                    extractValues(data=value, style=style))
    return w_values


# getTransferResult方法：从给定的JSON文件中获取转写结果，并根据需要将中文转换为拼音首字母
def getTransferResult(transfer_json, style=2):
    w_list = []
    # 解析元素中的JSON字符串，获取转写结果,从转写结果中提取值，调用extractValues函数，并将返回的值合并为一个字符串
    for element in transfer_json:
        sentence = json.loads(element["json_1best"])
        w_values = extractValues(sentence, style=style)
        concatenated_string = "".join(w_values)
        w_list.append(concatenated_string)
    transfer_result = "".join(w_list)
    print(
        '\n the transfer result is：\n',
        transfer_result)
    return transfer_result


def extractLyrics(lyrics_dir, file_name, style=2):
    lyrics_path = lyrics_dir / file_name
    with open(lyrics_path, 'r', encoding='utf-8') as file:
        raw_lyrics = file.read()
    pattern = re.compile(r'[^\u4e00-\u9fa5]')
    lyrics = re.sub(pattern, '', raw_lyrics)
    lyrics = gbkXfrFstLetter(lyrics, style=style)
    return lyrics


def getHotWords(lyrics_dir, file_name):
    lyrics_path = lyrics_dir / file_name
    with open(lyrics_path, 'r', encoding='utf-8') as file:
        raw_lyrics = file.read()
    pattern = re.compile(r'[^\u4e00-\u9fa5\n]+')
    result = pattern.sub('', raw_lyrics).replace('\n', '|')
    result = re.sub(r'\|+', '|', result)
    return result


def findSubstringIndex(
        full_str,
        lyrics,
        threshold=0.6,
        is_end=False,
        match_str_size=20):
    if is_end:
        match_str = lyrics[-1 * match_str_size:]
        range_list = reversed(range(len(full_str) - match_str_size + 1))
    else:
        match_str = lyrics[:match_str_size]
        range_list = range(len(full_str) - match_str_size + 1)
    for i in range_list:
        substring = full_str[i:i + match_str_size]
        match_percentage = sum(
            1 for x,
            y in zip(
                substring,
                match_str) if x == y) / match_str_size
        if match_percentage >= threshold:
            if is_end:
                return i + match_str_size - 1
            else:
                return i
    raise ValueError(
        f"Failed to match the head index of string {'match_str'}, please try again")


def getCutPoint(
        lyrics_dir,
        w_str_result,
        file_name,
        threshold,
        match_str_size=20):
    # lyrics = extractLyrics(
    #     lyrics_dir=lyrics_dir,
    #     file_name=file_name,
    #     style=2)
    # start_cut_point_index = findSubstringIndex(
    #     w_str_result,
    #     is_end=False,
    #     lyrics=lyrics,
    #     match_str_size=match_str_size,
    #     threshold=threshold)
    # end_cut_point_index = findSubstringIndex(
    #     w_str_result,
    #     is_end=True,
    #     lyrics=lyrics,
    #     match_str_size=match_str_size,
    #     threshold=threshold)
    start_cut_point_index = 0
    end_cut_point_index = len(w_str_result) - 1

    print(
        "start_cut_point_index is",
        start_cut_point_index,
        ",end_cut_point_index is",
        end_cut_point_index)
    return start_cut_point_index, end_cut_point_index


def findWbValue(sentence, current_index, target_index, is_end=False):
    ws_list = sentence["rt"][0]["ws"]
    for word in ws_list:
        if is_end:
            wb_value = word["we"] * 10
        else:
            wb_value = word["wb"] * 10
        cw_list = word["cw"][0]
        if cw_list["wp"] in ['n', 's']:
            w_value = gbkXfrFstLetter(word["cw"][0]["w"], style=2)
        else:
            w_value = ''
        current_index += len(w_value)
        if current_index >= target_index + 1:
            break
    return current_index, wb_value


def getCpTimestamp(transfer_json, target_index, is_end=False):
    current_index = 0
    for element in transfer_json:
        json_best = json.loads(element["json_1best"])
        current_index, wb_values = findWbValue(
            sentence=json_best["st"], current_index=current_index, target_index=target_index, is_end=is_end)
        if current_index >= target_index + 1:
            cut_point_t = int(json_best["st"]["bg"]) + wb_values
            break
    return cut_point_t / 1000


def getPerWordTime(transfer_json):
    wt_list = []
    for element in transfer_json:
        json_best = json.loads(element["json_1best"])
        sentence_bg = int(json_best["st"]["bg"])
        ws_list = json_best["st"]["rt"][0]["ws"]
        for word in ws_list:
            wb_value = word["wb"] * 10
            w_time = (sentence_bg + wb_value)/1000
            cw_list = word["cw"][0]
            if cw_list["wp"] in ['n', 's']:
                w_value = gbkXfrFstLetter(word["cw"][0]["w"], style=0)
                wt_list.append({w_value:w_time})
    return wt_list


def cutAudio(
        start_time=0,
        end_time=None,
        output_dir=None,
        output_audio=None,
        input_audio=None):
    file_name = os.path.basename(input_audio)
    output_name = file_name + '_' + output_audio
    output_path = output_dir / output_name
    print(f"Start download '{output_path}' ...")
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    audio = AudioSegment.from_file(input_audio)
    duration_s = len(audio) / 1000
    if end_time is None:
        end_time = duration_s
    segment = audio[start_time * 1000:end_time * 1000]
    segment.export(output_path, format="mp3")
