import re

import forks

UNRAR_CRC_ERROR = re.compile("CRC failed in ([A-Za-z0-9,\\/, ,\\.,_,\\-,\\,,#]+)")
UNRAR_PERCENT = re.compile("(\\d+)%")
UNRAR_MISSING_VOLUME = re.compile("Cannot find volume ([A-Za-z0-9,\\/, ,\\.,_,\\-,\\,,#]+)")
UNRAR_ALL_OK = re.compile("All OK")
UNRAR_NOOPEN = re.compile("Cannot open ([A-Za-z0-9,\\/, ,\\.,_,\\-,\\,,#]+)")

STATUS_PERCENT = 'percent'
STATUS_OK = 'success'
STATUS_MSG = 'status'

DEFAULT_WAITTIME = 0.01

def _mklist(*elements):
    return elements

class UnrarSpoon(forks.Spoon):
    """ UnrarSpoon
    
    This class uses the unrar program to extract the given file (filepath)
    to the dst_dir directory. Filepath must be an absolut path because
    the program will be started with the working directory set to dst_path
    (well you could relativ paths to the working directory...)
    
    It should be quite easy to use this class, just create an instance
    and call update to see unrar processing your files. 
    You could also call update_loop and give it a callback function. This
    function will be called each time unrar produces some wired output... ;P
    
    Take care that you only uses this class in one thread because it's not
    designed for beeing used in multithreaded environments. Note that it could
    very easily be made thread safe, just protect self._status with some
    threading.RLock() for example...
    """
    
    def __init__(self, filepath, dst_dir, pwd):
        """"__init__(self, filepath, dst_dir, pwd)
        
        starts extraction of filepath (absolut path) to dst_dir with 
        pwd (password)
        Note that this class will always use a password... (ugly)
        """
        
        forks.Spoon.__init__(self)
        self._status[STATUS_MSG] = 'extracting'
        self._status[STATUS_PERCENT] = 0
        self._status[STATUS_OK] = False
        
        self._err_crc = None
        self._err_miss = None
        self._no_open = None
        self._line = ''
        
        args = ['unrar', '-ierr', 'e', '-o+', '-p' + pwd, filepath]
        self.start(args, use_stderr=True, cwd=dst_dir)
    
    def _read_line(self):
        
        while self._status[forks.STREAM_OPEN]:
            ch = self.read_char(wait=DEFAULT_WAITTIME)
            
            if ch == '\r' or ch == '\n':
                self._update_line()
                self._line = ''
                return True
            elif ch == '\x08':
                re_percent = UNRAR_PERCENT.search(self._line)
        
                if not (re_percent is None):
                    self._status[STATUS_PERCENT] = int(re_percent.group(1))
                    self._line = self._line[re_percent.end():]
                    return True
            elif ch != '':
                self._line += ch
        
        return False
    
    def _update(self):
        self._read_line()
    
    def _update_line(self):
        
        re_error = UNRAR_CRC_ERROR.search(self._line)
        re_missing = UNRAR_MISSING_VOLUME.search(self._line)
        re_ok = UNRAR_ALL_OK.search(self._line)
        re_percent = UNRAR_PERCENT.search(self._line)
        re_noopen = UNRAR_NOOPEN.search(self._line)
        
        if not (re_percent is None):
            self._status[STATUS_PERCENT] = int(re_percent.group(1))
        
        if not (re_error is None):
            self._err_crc = re_error.group(1)
            
        if not (re_missing is None):
            self._err_miss = re_missing.group(1)
        
        if not (re_noopen is None):
            self._no_open = re_noopen.group(1)
            
        if not (re_ok is None):
            self._status[STATUS_OK] = True
        
        if not (self._no_open is None):
            self._status[STATUS_MSG] = ("couldn't open file(s) %s" % 
                self._no_open)
        elif not (self._err_miss is None):
            self._status[STATUS_MSG] = ("missing file(s) %s" % 
                self._err_miss)
        elif not (self._err_crc is None):
            self._status[STATUS_MSG] = ("crc error or wrong pwd in %s " %
                self._err_crc)
