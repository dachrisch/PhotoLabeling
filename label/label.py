#!/usr/bin/env python

import base64
import logging
import os

from googleapiclient import discovery
from googleapiclient.errors import HttpError
from oauth2client.client import GoogleCredentials

from iptcinfo_manipulation import SaveToSameFileIPTCInfo

TAGGED_PHOTO_KEY = 'custom1'
TAGGED_PHOTO_LABEL = 'already_tagged_PhotoLabel_v1.0'
EXCLUDED_DIRS = ('@eaDir',)
EXCLUDED_FILES = ('SYNOPHOTO_THUMB',)


class GoogleServiceConnector(object):
    def __init__(self):
        self._log = logging.getLogger(self.__class__.__name__)
        credentials = GoogleCredentials.get_application_default()
        self._log.info('logging into Google Vision using [%s]' % credentials.service_account_email)
        self._service = discovery.build('vision', 'v1', credentials=credentials)

    def build_request(self, body):
        request = self._service.images().annotate(body=body)
        return request


class LabelServiceExecutor(object):
    def __init__(self, connector):
        self.__connector = connector
        self._log = logging.getLogger(self.__class__.__name__)

    def _perform_request(self, image_file):
        self._log.debug('performing vision request for [%s]' % image_file)
        return self._execute_request(body={
            'requests': [{
                'image': {
                    'content': self.image_to_base64_utf8(image_file)
                },
                'features': [{
                    'type': 'LABEL_DETECTION',
                    'maxResults': 10
                }]
            }]
        })

    def tags_for_image(self, image_file):
        try:
            response = self._perform_request(image_file)
        except HttpError, e:
            if 'Request Admission Denied.' in str(e):
                raise ImageTooBigException(image_file, e)
            raise

        if 'labelAnnotations' not in response['responses'][0]:
            raise NoLabelFoundException(response['responses'])

        labels = tuple(
            annotation['description'] for annotation in
            sorted(filter(lambda field: field['score'] > 0.8, response['responses'][0]['labelAnnotations']) or
                   response['responses'][0]['labelAnnotations'],
                   key=lambda field: field['score'], reverse=True))

        if len(labels) == 0:
            raise NoLabelFoundException("no labels left after filter", response['responses'])
        self._log.info('found (%d) tags for file [%s]: %s' % (len(labels), image_file, labels))
        return labels

    @staticmethod
    def image_to_base64_utf8(image_file):
        with open(image_file, 'rb') as image:
            image_content = base64.b64encode(image.read())
            return image_content.decode('UTF-8')

    def _execute_request(self, body):
        return self.__connector.build_request(body).execute()


class NoLabelFoundException(Exception):
    pass


class AlreadyLabeledException(Exception):
    pass


class ImageTooBigException(Exception):
    pass


class FileLabeler(object):
    def __init__(self):
        self._log = logging.getLogger(self.__class__.__name__)

    def label(self, jpg_file, tags):
        if self.already_labeled(jpg_file):
            raise AlreadyLabeledException(jpg_file)
        info = SaveToSameFileIPTCInfo(jpg_file, force=True)
        remaining_tags = filter(lambda _tag: _tag not in info.keywords, tags)
        if remaining_tags:
            self._log.debug('appending non existent tags (%s) to [%s]' % (remaining_tags, info.keywords))
            info.keywords.extend(remaining_tags)
            info.data[TAGGED_PHOTO_KEY] = TAGGED_PHOTO_LABEL
            info.save()
        else:
            self._log.debug('all tags already present: %s' % str(tags))

    @staticmethod
    def already_labeled(jpg_file):
        try:
            info = SaveToSameFileIPTCInfo(jpg_file)
            return info.data[TAGGED_PHOTO_KEY] == TAGGED_PHOTO_LABEL
        except Exception, e:
            if e.message == 'No IPTC data found.':
                return False
            raise


class FileWalker(object):
    def __init__(self, file_labeler, label_service):
        self._file_labeler = file_labeler
        self._label_service = label_service
        self._log = logging.getLogger(self.__class__.__name__)

    def walk_and_tag(self, parent_directory):
        files = self.collect_files(parent_directory)
        self._log.info('Found (%d) files in [%s]. Start labeling...' % (len(files), parent_directory))
        for jpg_file in files:
            if self._file_labeler.already_labeled(jpg_file):
                self._log.info('Skipping already labeled file [%s]' % jpg_file)
                continue
            self._log.info('Labeling file [%s]' % jpg_file)
            try:
                tags = self._label_service.tags_for_image(jpg_file)
                self._file_labeler.label(jpg_file, tags)
            except NoLabelFoundException, e:
                self._log.warn('no labels found for [%s]: %s' % (jpg_file, e.message))
            except ImageTooBigException:
                self._log.error('image [%s] is too big, skipping' % jpg_file)
        self._log.info('done.')

    @staticmethod
    def collect_files(parent_directory):
        from fnmatch import filter as file_filter
        from os import path, walk

        collected_files = []
        for root, dirs, filenames in walk(parent_directory):
            dirs[:] = filter(lambda d: d not in EXCLUDED_DIRS, dirs)
            filtered_filenames = filter(lambda f: not (any(exclude in f for exclude in EXCLUDED_FILES)), filenames)
            collected_files.extend(tuple(
                map(lambda filename: path.join(root, filename), file_filter(filtered_filenames, "*.jpg"))))
        return collected_files


class ImageReSizer(object):
    def __init__(self, base_height=640):
        self.base_height = base_height

    def resize(self, image_file):
        from tempfile import NamedTemporaryFile
        from PIL import Image
        (path, extension) = os.path.splitext(image_file)
        re_sized_image_file = NamedTemporaryFile(suffix=extension)

        img = Image.open(image_file)
        hpercent = (self.base_height / float(img.size[1]))
        wsize = int((float(img.size[0]) * float(hpercent)))
        img = img.resize((wsize, self.base_height), Image.ANTIALIAS)
        img.save(re_sized_image_file)
        return re_sized_image_file
