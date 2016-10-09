import logging

from iptcinfo import IPTCInfo


class BackupFileExistsException(Exception):
    pass


class SaveToSameFileIPTCInfo(IPTCInfo):
    def __init__(self, fobj, *args, **kwds):
        super(SaveToSameFileIPTCInfo, self).__init__(fobj, *args, **kwds)
        self._log = logging.getLogger(self.__class__.__name__)

    def save(self, options=None):
        """Saves Jpeg with IPTC data to a given file name."""

        self._backup_original()
        # Open file and snarf data from it.
        fh = self._getfh()
        assert fh
        fh.seek(0, 0)
        if not self.fileIsJpeg(fh):
            self._log.error("Source file is not a Jpeg; I can only save Jpegs."
                            " Sorry.")
            return None
        ret = self.jpegCollectFileParts(fh, options)
        self._closefh(fh)
        if ret is None:
            self._log.error("collectfileparts failed")
            raise Exception('collectfileparts failed')

        (start, end, adobe) = ret
        self._log.debug('start: %d, end: %d, adobe:%d', *map(len, ret))
        self.hexDump(start), len(end)
        self._log.debug('adobe1: %r', adobe)
        if options is not None and 'discardAdobeParts' in options:
            adobe = None
        self._log.debug('adobe2: %r', adobe)

        self._log.debug('writing...')
        tmpfh = self._getfh('wb')
        # fh = StringIO()
        if not tmpfh:
            self._log.error("Can't open output file %r", self._filename)
            return None
        self._log.debug('start=%d end=%d', len(start), len(end))
        tmpfh.write(start)
        # character set
        ch = self.c_charset_r.get(self.out_charset, None)

        self._log.debug('pos: %d', self._filepos(tmpfh))
        data = self.photoshopIIMBlock(adobe, self.packedIIMData())
        self._log.debug('data len=%d dmp=%r', len(data), self.hexDump(data))
        tmpfh.write(data)
        self._log.debug('pos: %d', self._filepos(tmpfh))
        tmpfh.write(end)
        self._log.debug('pos: %d', self._filepos(tmpfh))
        tmpfh.flush()
        tmpfh.close()
        return True

    def _backup_original(self):
        import shutil
        backup_filename = '%s~' % self._filename
        import os
        if os.path.exists(backup_filename):
            raise BackupFileExistsException(self._filename)
        shutil.copy2(self._filename, backup_filename)
