import os
import sys
import unittest

import numpy
from PIL import Image
from iptcinfo import IPTCInfo

sys.path.insert(0, os.path.abspath(__file__ + "/../.."))
from label.label import GoogleServiceConnector, LabelServiceExecutor, ImageLabeler, FileWalker
from label.iptcinfo_manipulation import SaveToSameFileIPTCInfo, BackupFileExistsException

TESTDIR = '_testdir'



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
        info = IPTCInfo(self.jpg_file, force=True)
        info.keywords = ('cat', 'mammal')
        info.save()
        os.remove('%s~' % self.jpg_file)
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

    def test_newly_saved_file_with_IPTCInfo_has_same_stats(self):
        self.assertEqual(823, os.lstat(self.jpg_file).st_size)

        SaveToSameFileIPTCInfo(self.jpg_file, force=True).save()
        backup_file = '%s~' % self.jpg_file

        self.assertEqual(861, os.lstat(self.jpg_file).st_size)
        self.assertEqual(823, os.lstat(backup_file).st_size)

    def test_dont_overwrite_backups(self):
        SaveToSameFileIPTCInfo(self.jpg_file, force=True).save()
        self.assertRaisesRegexp(BackupFileExistsException, '_testdir/test_1x1_no_exif.jpg',
                                SaveToSameFileIPTCInfo(self.jpg_file, force=True).save)

    def test_dont_tag_already_tagged_image(self):
        self.fail('not implemented')


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
