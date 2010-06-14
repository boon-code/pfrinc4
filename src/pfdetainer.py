import os
import logging
import threading
import re
import sys
import copy
import linering

PACKET_NAME_RE = re.compile(".*/([^/]*)[.]{1}part\\d+[.]{1}rar")
PACKET_NAME_SIMPLE_RE = re.compile(".*/([^/]*)[.]{1}rar")
AUTO_SYNC_COUNT = 10
LOGGER_NAME = 'detainer'

import __main__
if 'DEBUG_' in dir(__main__):
    __main__.LOG_LEVEL_ = logging.DEBUG
else:
    DEBUG_ = False

if 'LOG_LEVEL_' in dir(__main__):
    log = logging.getLogger(LOGGER_NAME)
    log.setLevel(__main__.LOG_LEVEL_)
    if len(log.handlers) <= 0:
        st_log = logging.StreamHandler(sys.stderr)
        st_log.setFormatter(
            logging.Formatter("%(name)s : %(levelname)s : %(message)s"))
        log.addHandler(st_log)
        del st_log
    del log
else:
    log = logging.getLogger(LOGGER_NAME)
    log.setLevel(logging.CRITICAL)


class mem_detainer(object):
    
    def __init__(self):
        
        self._log = logging.getLogger(LOGGER_NAME)
        self._lock = threading.RLock()
        
        self._pending = []
        self._finished = []
        
    def added(self, *links):
        
        self._lock.acquire()
        try:
            for link in links:
                if not link in self._pending:
                    self._pending.append(link)
        finally:
            self._lock.release()
        
    def finished(self, name):
        
        self._lock.acquire()
        try:
            remove_list = []
            for link in self._pending:
                re_full = PACKET_NAME_RE.search(link)
                re_simple = PACKET_NAME_SIMPLE_RE.search(link)
                
                if not (re_full is None):
                    if name == re_full.group(1):
                        remove_list.append(link)
                elif not (re_simple is None):
                    if name == re_simple.group(1):
                        remove_list.append(link)
            
            for link in remove_list:
                self._pending.remove(link)
            
            if len(remove_list) > 0:
                self._finished.append(name)
            
            packet_count = len(self._finished)
        finally:
            self._lock.release()
        
        if len(remove_list) <= 0:
            self._log.debug("didn't find name (%s) in pending list..."
                % name)
    
    def sync(self):
        "Nothing to do..."
        pass
    
    def was_downloaded(self, name):
        
        self._lock.acquire()
        try:
            if name in self._finished:
                return True
        finally:
            self._lock.release()
        
        return False
    
    def get_finished(self, count=None):
        
        self._lock.acquire()
        try:
            fin_count = len(self._finished)
            if count is None:
                count = fin_count
            else:
                count = min(count, fin_count)
            
            ret = []
            
            for i in xrange(fin_count, fin_count - count, -1):
                ret.append(copy.copy(self._finished[i]))
            
            return ret
        finally:
            self._lock.release()
    
    def get_pending(self):
        
        self._lock.acquire()
        try:
            pending = copy.copy(self._pending)
            return pending
        finally:
            self._lock.release()

class file_detainer(object):
    
    def __init__(self, path, fin_name='finished-packet',
        bak_name='backup', auto_sync_count=AUTO_SYNC_COUNT):
        
        self._fin = os.path.join(path, fin_name)
        self._bak = os.path.join(path, bak_name)
        self._log = logging.getLogger(LOGGER_NAME)
        self._lock = threading.RLock()
        self._async_count = auto_sync_count
        
        self._pending = []
        self._finished = []
        
        self._load_pending_links()
        
    def added(self, *links):
        
        self._lock.acquire()
        try:
            for link in links:
                if not link in self._pending:
                    self._pending.append(link)
            
            link_count = len(links)
        finally:
            self._lock.release()
        
        if link_count >= self._async_count:
            self.sync()
        
    def finished(self, name):
        
        self._lock.acquire()
        try:
            remove_list = []
            for link in self._pending:
                re_full = PACKET_NAME_RE.search(link)
                re_simple = PACKET_NAME_SIMPLE_RE.search(link)
                
                if not (re_full is None):
                    if name == re_full.group(1):
                        remove_list.append(link)
                elif not (re_simple is None):
                    if name == re_simple.group(1):
                        remove_list.append(link)
            
            for link in remove_list:
                self._pending.remove(link)
            
            if len(remove_list) > 0:
                self._finished.append(name)
            
            packet_count = len(self._finished)
        finally:
            self._lock.release()
        
        if len(remove_list) <= 0:
            self._log.debug("didn't find name (%s) in pending list..."
                % name)
        
        if packet_count >= self._async_count:
            self.sync()
    
    def sync(self):
        
        if not os.path.exists(self._fin):
            self._log.warning("the 'finished' file (%s) doesn't exist, well i will create it..."
                % self._fin)
        
        self._lock.acquire()
        try:
            f = open(self._fin, 'a')
            
            for name in self._finished:
                f.write(name.rstrip('\n') + '\n')
            
            self._finished = []
            f.close()
            
            f = open(self._bak, "w")
            
            for link in self._pending:
                f.write(link.strip('\n') + '\n')
            
            f.close()
        finally:
            self._lock.release()
    
    def _load_pending_links(self):
        
        if os.path.exists(self._bak):
            self._lock.acquire()
            try:
                f = open(self._bak, 'r')
                
                for line in f:
                    l = line.rstrip('\r').rstrip('\n').rstrip('\r')
                    self._pending.append(l)
                
                f.close()
            finally:
                self._lock.release()
        else:
            self._log.warning("backup file (%s) for started packets doesn't exist"
                % self._bak)
    
    def was_downloaded(self, name):
        
        self._lock.acquire()
        try:
            if name in self._finished:
                return True
            elif os.path.exists(self._fin):
                done = False
                f = open(self._fin, 'r')
                for line in f:
                    if name == line.strip('\r').strip('\n').strip('\r'):
                        done = True
                f.close()
                return done
        finally:
            self._lock.release()
        
        self._log.warning("couln'd check if '%s' was downloaded, file (%s) not found"
            % (name, self._fin))
        return False
    
    def get_finished(self, count=None):
        
        self.sync()
        
        self._lock.acquire()
        try:
            flf = open(self._fin, 'r')
            ret = []
            
            if count is None:
                for i in flf:
                    ret.insert(0, i.rstrip('\n'))
            else:
                ring = linering.lring(size = count)
                for i in flf:
                    ring.push(i.rstrip('\n'))
                ret = ring.get_list()
            
            flf.close()
            
            return ret
        finally:
            self._lock.release()
    
    def get_pending(self):
        
        self._lock.acquire()
        try:
            pending = copy.copy(self._pending)
            return pending
        finally:
            self._lock.release()
