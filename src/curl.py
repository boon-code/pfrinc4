import re
import subprocess

import forks

FULL_EXTR =("\\s*(\\d{1,3})" + 
            "\\s*([0-9.]+[k,M,m,G,g]{0,1})" + 
            "\\s*(\\d{1,3})" +
            "\\s*([0-9.]+[k,M,m,G,g]{0,1})" +
            "\\s*(\\d{1,3})" +
            "\\s*([0-9.]+[k,M,m,G,g]{0,1})" +
            "\\s*([0-9.]+[k,M,m,G,g]{0,1})" +
            "\\s*([0-9.]+[k,M,m,G,g]{0,1})" +
            "\\s*(\\d+[:]{1}\\d+[:]{1}\\d+)" +
            "\\s*(\\d+[:]{1}\\d+[:]{1}\\d+)" +
            "\\s*(\\d+[:]{1}\\d+[:]{1}\\d+)" +
            "\\s*([0-9.]+[k,M,m,G,g]{0,1})\\s*")

FULL_EXTR_EXPR = re.compile(FULL_EXTR)

PERCENT = 'percent'
SPEED = 'speed'
DL_SIZE = 'dlsize'
TOTAL_SIZE = 'totalsize'
TIME_LEFT = 'eta'

DEFAULT_WAITTIME = 1

def _mklist(*elements):
    return elements


def simple_download(link, *args):
    """ simple_download(link, *args)
    Just starts curl: 'curl link args[0] args[1] ...'
    Returns output of curl on stdout (normally the downloaded file)
    Don't use for big files (use class curl instead...)
    """
    
    args = _mklist('curl', link, *args)
    print args
    subp = subprocess.Popen(args, stdout=subprocess.PIPE)
    return subp.communicate()[0]


class CurlSpoon(forks.Spoon):
    """ CurlSpoon
    This is a download class which uses the tool curl to download stuff.
    It's quite easy to use, just create curl object and the process starts...
    To get some information about the progress just call update, or use
    update_loop which will repeadetly call a callback funtion.
    
    Note that this class is (due to it's compactness) not threadsafe...
    It could be made threadsafe quite easily, just protect self._status
    with some threading.RLock() ...
    """
    
    def __init__(self, link, dest, args=[], cookie=None):
        """ __init__(self, link, dest, *args)
        This constructor starts downloading link and safes it to 
        dest (file). Args will be passed to curl tool.
        """
        
        forks.Spoon.__init__(self)
        self._status[PERCENT] = 0
        self._status[SPEED] = '???'
        self._status[DL_SIZE] = '???'
        self._status[TOTAL_SIZE] = '???'
        self._status[TIME_LEFT] = '???'
        self._line = ""
        
        if cookie is None:
            args = _mklist('curl', link, '-o', dest, *args)
        else:
            args = _mklist('curl', link, '-o', dest, '--cookie', '-',
                            *args)
        
        self.start(args, in_data=cookie, use_stderr=True)
    
    def _read_line(self):
        
        while self._status[forks.STREAM_OPEN]:
            
            ch = self.read_char(wait=DEFAULT_WAITTIME)
            
            if ch == '\r' or ch == '\n':
                re_full = FULL_EXTR_EXPR.search(self._line)
                if not (re_full is None):
                    self._status[PERCENT] = int(re_full.group(3))
                    self._status[SPEED] = re_full.group(12)
                    self._status[TOTAL_SIZE] = re_full.group(2)
                    self._status[DL_SIZE] = re_full.group(4)
                    self._status[TIME_LEFT] = re_full.group(11)
                    self._line = ''
                    return True
            elif ch != '':
                self._line += ch
        
        return False
    
    def _update(self):
        
        self._read_line()
