#!/usr/bin/env python
import argparse
import base64

from googleapiclient import discovery
from oauth2client.client import GoogleCredentials


def main(args):
    pass


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('image_file', help='The image you\'d like to label.')
    args = parser.parse_args()
    main(args)


class GoogleServiceConnector(object):
    def __init__(self):
        credentials = GoogleCredentials.get_application_default()
        self._service = discovery.build('vision', 'v1', credentials=credentials)

    def build_request(self, body):
        request = self._service.images().annotate(body=body)
        return request


class LabelServiceExecutor(object):
    def __init__(self, connector):
        self.__connector = connector

    def _perform_request(self, image_file):
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
        label = tuple(
            annotation['description'] for annotation in
            sorted(filter(lambda field: field['score'] > 0.8, response['responses'][0]['labelAnnotations']),
                   key=lambda field: field['score'], reverse=True))
        return label

    @staticmethod
    def image_to_base64_utf8(image_file):
        with open(image_file, 'rb') as image:
            image_content = base64.b64encode(image.read())
            return image_content.decode('UTF-8')

    def _execute_request(self, body):
        return self.__connector.build_request(body).execute()
