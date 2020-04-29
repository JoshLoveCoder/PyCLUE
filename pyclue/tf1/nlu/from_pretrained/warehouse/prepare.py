#!/usr/bin/python3

"""
@Author: Liu Shaoweihua
@Site: https://github.com/liushaoweihua
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import codecs
import os
import shutil
import time
import zipfile

import requests
from pyclue.tf1.nlu.from_pretrained.warehouse.convert import Converter
from pyclue.tf1.nlu.from_pretrained.warehouse.information import pretrained_names
from pyclue.tf1.nlu.from_pretrained.warehouse.information import pretrained_type
from pyclue.tf1.nlu.from_pretrained.warehouse.information import pretrained_urls


def get_pretrained_model(pretrained_name, save_path=None, inplace=False):
    if pretrained_name.lower() in pretrained_names:
        if save_path is None:
            save_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'models'))
        else:
            save_path = os.path.abspath(save_path)
        downloader = PretrainedModelBuilder(pretrained_name, save_path, inplace)
        pretrained_dir = downloader.run()
        return pretrained_dir
    else:
        raise ValueError(
            'pretrained_name unknown')


class PretrainedModelBuilder(object):

    def __init__(self, pretrained_name, save_path, inplace=False):
        self.pretrained_name = pretrained_name.lower()
        self.save_path = save_path
        self.inplace = inplace

    def _wget(self, url, save_path=None, rename=None):
        file_name = url[url.rfind('/') + 1:]
        if not rename:
            rename = file_name
        save_path = os.path.abspath(os.path.join(save_path, rename))
        print('[wget]   Downloading model **{}** from: {}'.format(rename[:-4], url))
        start = time.time()
        size = 0
        response = requests.get(url, stream=True)
        if response.headers.get('content-length') is not None:
            chunk_size = 1024
            content_size = int(response.headers['content-length'])
            if response.status_code == 200:
                print('[wget]   File size: %.2f MB' % (content_size / 1024 / 1024))
                with codecs.open(save_path, 'wb') as f:
                    for data in response.iter_content(chunk_size=chunk_size):
                        f.write(data)
                        size += len(data)
                        print('\r' + '[wget]   %s%.2f%%'
                              % ('>' * int(size * 50 / content_size), float(size / content_size * 100)), end='')
            end = time.time()
            print('\n' + '[wget]   Complete! Cost: %.2fs.' % (end - start))
            print('[wget]   save at: {}'.format(save_path))
        else:
            print('[wget]   Failed to download from {}: {}'.format(url, response.text))
        return save_path

    def _mkdir(self, file_dir):
        file_dir = os.path.abspath(os.path.join(self.save_path, file_dir))
        if not os.path.exists(file_dir):
            os.makedirs(file_dir)
            print('[mkdir]  Create directory {}'.format(file_dir))
            run_follow_step = True
        elif self.inplace:
            print('[mkdir]  Directory exists, remove and re-download.')
            self._rmdir(file_dir)
            os.makedirs(file_dir)
            run_follow_step = True
        else:
            print('[mkdir]  Directory exists, ignored.')
            run_follow_step = False
        return file_dir, run_follow_step

    def _rm(self, file):
        file = os.path.abspath(file)
        os.remove(file)
        print('[remove] File {} removed.'.format(file))
        return

    def _rmdir(self, file_dir):
        file_dir = os.path.abspath(file_dir)
        shutil.rmtree(file_dir)
        print('[rmdir]  Directory {} removed.'.format(file_dir))
        return

    def _unzip(self, file, save_path=None):
        if not save_path:
            save_path = os.path.abspath('/'.join(os.path.abspath(file).split('/')[:-1]))
        with zipfile.ZipFile(file) as zf:
            zf.extractall(save_path)
        print('[unzip]  Unzip file {}, save at {}'.format(file, save_path))
        return save_path

    def _mv(self, from_path, to_path):
        from_path = os.path.abspath(from_path)
        to_path = os.path.abspath(to_path)
        os.rename(from_path, to_path)
        print('[move]   Move file from {} to {}'.format(from_path, to_path))
        return

    def _regularize_file_format(self, file_dir):
        for file in os.listdir(file_dir):
            file = os.path.abspath(os.path.join(file_dir, file))
            if os.path.isdir(file):
                for sub_file in os.listdir(file):
                    sub_file = os.path.abspath(os.path.join(file, sub_file))
                    regularized_sub_file = self._regularize_file_name(sub_file)
                    self._mv(
                        from_path=sub_file,
                        to_path=os.path.join(os.path.dirname(file), regularized_sub_file))
                    if len(os.listdir(file)) == 0:
                        self._rmdir(file)
            else:
                regularized_file = self._regularize_file_name(file)
                self._mv(
                    from_path=file,
                    to_path=os.path.join(os.path.dirname(file), regularized_file))

    def _regularize_file_name(self, file_name):
        file_name = os.path.basename(file_name)
        if 'config' in file_name:
            return 'config.json'
        elif 'ckpt' in file_name:
            return ''.join(['model.ckpt', file_name.split('ckpt')[-1]])
        elif 'vocab' in file_name:
            return 'vocab.txt'
        elif 'checkpoint' in file_name:
            return 'checkpoint'
        else:
            return file_name

    def run(self):
        print('**********{}**********'.format(self.pretrained_name))
        pretrained_dir, run_follow_step = self._mkdir(self.pretrained_name)
        if run_follow_step:
            pretrained_zip = self._wget(
                url=pretrained_urls.get(self.pretrained_name),
                save_path=pretrained_dir,
                rename=self.pretrained_name + '.zip')
            self._unzip(file=pretrained_zip)
            print('[saved]  {} saved at {}'.format(self.pretrained_name, pretrained_dir))
            self._rm(pretrained_zip)
            self._regularize_file_format(pretrained_dir)
            # converter = Converter(pretrained_dir, pretrained_type.get(self.pretrained_name))
            # converter.run()
        return pretrained_dir
