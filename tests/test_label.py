import os
import sys
import unittest

import numpy
from PIL import Image
from iptcinfo import IPTCInfo

TESTDIR = '_testdir'

sys.path.insert(0, os.path.abspath(__file__ + "/../.."))
from label.label import GoogleServiceConnector, LabelServiceExecutor, ImageLabeler


class FileWalker(object):
    def __init__(self, file_labeler, label_service):
        self._file_labeler = file_labeler
        self._label_service = label_service

    def walk_and_tag(self, parent_directory):
        files = self.__collect_files(parent_directory)

        for jpg_file in files:
            tags = self._label_service.tags_for_image(jpg_file)
            self._file_labeler.label(jpg_file, tags)

    def __collect_files(self, parent_directory):
        from fnmatch import filter
        from os import path, walk

        collected_files = []
        for root, _, filenames in walk(parent_directory):
            collected_files.extend(tuple(
                map(lambda filename: path.join(root, filename), filter(filenames, "*.jpg"))))
        return collected_files


class LabelExifTagTest(unittest.TestCase):
    def setUp(self):
        os.makedirs(TESTDIR)
        self.jpg_file = os.path.join(TESTDIR, 'test_1x1_no_exif.jpg')
        self._create_testfile(self.jpg_file)

    def _create_testfile(self, jpg_filename):
        image = Image.fromarray(numpy.zeros((100, 100, 3), dtype=numpy.uint8), 'RGB')
        image.save(jpg_filename)

    def tearDown(self):
        import shutil
        shutil.rmtree(TESTDIR)
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

    def test_walk_files_and_tag(self):
        file_walker = FileWalker(ImageLabeler(), LabelServiceExecutor(TestServiceConnector()))
        os.makedirs('_testdir/2016/10')
        self._create_testfile('_testdir/2016/10/test1.jpg')
        os.makedirs('_testdir/2016/11')
        self._create_testfile('_testdir/2016/11/test2.jpg')
        os.makedirs('_testdir/2015/10')
        self._create_testfile('_testdir/2015/10/test3.jpg')
        file_walker.walk_and_tag('_testdir/2016')
        self.assertEqual(IPTCInfo('_testdir/2016/10/test1.jpg').keywords, ['cat', 'mammal', 'vertebrate', 'whiskers'])
        self.assertEqual(IPTCInfo('_testdir/2016/11/test2.jpg').keywords, ['cat', 'mammal', 'vertebrate', 'whiskers'])
        self.assertRaisesRegexp(Exception, 'No IPTC data found', IPTCInfo, '_testdir/2015/10/test3.jpg')


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
