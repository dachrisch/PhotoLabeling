import os
import unittest

import numpy
from PIL import Image
from iptcinfo import IPTCInfo

from label.label import GoogleServiceConnector, LabelServiceExecutor


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


class TestServiceConnector(GoogleServiceConnector):
    def __init__(self):
        pass

    def request(self, body):
        return ({'responses': ({'labelAnnotations': ({'score': 0.96,
                                                      'description': u'cat'},
                                                     {'score': 0.95,
                                                      'description': u'mammal'},
                                                     {'score': 0.94,
                                                      'description': u'vertebrate'},
                                                     {'score': 0.93,
                                                      'description': u'whiskers'}
                                                     )},)})


class GoogleLabelServiceTest(unittest.TestCase):
    def setUp(self):
        self.image_jpg = 'cat.jpg'

    def test_find_labels_for_image(self):
        connector = TestServiceConnector()
        service_executor = LabelServiceExecutor(connector)
        self.assertTupleEqual(
            (u'cat', u'mammal', u'vertebrate', u'whiskers'),
            service_executor.tags_for_image(self.image_jpg))
