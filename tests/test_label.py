import unittest

import numpy
import pexif
from PIL import Image
import os
from iptcinfo import IPTCInfo


class LabelTest(unittest.TestCase):
    def setUp(self):
        self.image = Image.fromarray(numpy.zeros((100, 100, 3), dtype=numpy.uint8), 'RGB')
        self.jpg_file = 'test_1x1_no_exif.jpg'
        self.image.save(self.jpg_file)

    def tearDown(self):
        # os.remove(self.jpg_file)
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

