#!/usr/bin/env python

import base64
import logging

from googleapiclient import discovery
from oauth2client.client import GoogleCredentials

from iptcinfo_manipulation import SaveToSameFileIPTCInfo

TAGGED_PHOTO_KEY = 'custom1'
TAGGED_PHOTO_LABEL = 'already_tagged_PhotoLabel_v1.0'


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
        response = self._perform_request(image_file)

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
            else:
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
        self._log.info('done.')

    @staticmethod
    def collect_files(parent_directory):
        from fnmatch import filter
        from os import path, walk

        collected_files = []
        for root, _, filenames in walk(parent_directory):
            collected_files.extend(tuple(
                map(lambda filename: path.join(root, filename), filter(filenames, "*.jpg"))))
        return collected_files
