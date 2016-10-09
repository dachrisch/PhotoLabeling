import os
import sys
import unittest

import numpy
from PIL import Image
from iptcinfo import IPTCInfo

sys.path.insert(0, os.path.abspath(__file__ + "/../.."))
from label.label import GoogleServiceConnector, LabelServiceExecutor


class ImageLabeler(object):
    def label(self, jpg_file, tags):
        info = IPTCInfo(jpg_file, force=True)
        for tag in tags:
            if tag not in info.keywords:
                info.keywords.append(tag)
        info.save()


class LabelExifTagTest(unittest.TestCase):
    def setUp(self):
        self.image = Image.fromarray(numpy.zeros((100, 100, 3), dtype=numpy.uint8), 'RGB')
        self.jpg_file = 'test_1x1_no_exif.jpg'
        self.image.save(self.jpg_file)

    def tearDown(self):
        os.remove(self.jpg_file)
        pass

    def test_create_empty_keywords(self):
        info = IPTCInfo(self.jpg_file, force=True)
        self.assertEqual(info.keywords, [])

    def test_write_keywords(self):
        info = IPTCInfo(self.jpg_file, force=True)
        info.keywords = ('A', 'B')
        info.save()
        info = IPTCInfo(self.jpg_file)
        self.assertEqual(info.keywords, ['A', 'B'])

    def test_find_labels_for_image(self):
        connector = TestServiceConnector()
        service_executor = LabelServiceExecutor(connector)
        self.assertTupleEqual(
            (u'cat', u'mammal', u'vertebrate', u'whiskers'),
            service_executor.tags_for_image(self.jpg_file))

    def test_label_image(self):
        labeler = ImageLabeler()
        labeler.label(self.jpg_file, (u'cat', u'mammal'))
        info = IPTCInfo(self.jpg_file)
        self.assertEqual(info.keywords, ['cat', 'mammal'])

    def test_preserve_existing_labels(self):
        labeler = ImageLabeler()
        labeler.label(self.jpg_file, (u'cat', u'mammal'))
        labeler.label(self.jpg_file, (u'dog', u'mammal'))
        info = IPTCInfo(self.jpg_file)
        self.assertEqual(info.keywords, ['cat', 'mammal', 'dog'])


class TestServiceConnector(GoogleServiceConnector):
    # noinspection PyMissingConstructor
    def __init__(self):
        pass

    def build_request(self, body):
        response = ({'responses': ({'labelAnnotations': ({'score': 0.96,
                                                          'description': u'cat'},
                                                         {'score': 0.95,
                                                          'description': u'mammal'},
                                                         {'score': 0.94,
                                                          'description': u'vertebrate'},
                                                         {'score': 0.93,
                                                          'description': u'whiskers'}
                                                         )},)})
        from mock import MagicMock
        annotations = MagicMock()
        annotations.execute = MagicMock(return_value=response)
        return annotations
