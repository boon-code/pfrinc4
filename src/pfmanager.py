import sys
import Queue
import threading
import time
import sys
import os
import pfutil
import linering
import logging
import pfpacket
import copy

LOGGER_NAME = 'pf-manager'

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
            logging.Formatter("%(name)s : %(threadName)s : %(levelname)s : %(message)s"))
        log.addHandler(st_log)
        del st_log
    del log
else:
    log = logging.getLogger(LOGGER_NAME)
    log.setLevel(logging.CRITICAL)

class manager(object):
    
    def __init__(self, config, detainer, info=None, load_pending=True, 
        use_info_thread=False):
        
        self._running = True
        self._packets = []
        self._config = copy.copy(config)
        self._lock = threading.RLock()
        self._log = logging.getLogger(LOGGER_NAME)
        self._detainer = detainer
        self._info = info
        self._cmds = Queue.Queue()
        self._worker = []
        self._info_thread = None
        
        if load_pending:
            for link in self._detainer.get_pending():
                self._add_link(link)
        
        if (not (info is None)) and use_info_thread:
            self._info_thread = threading.Thread(
                target=self._info_loop, name="Info-Thread")
            self._info_thread.start()
        
        for i in xrange(2):
            self._worker.append(threading.Thread(target=self._workloop,
                name=("Worker-%d" % i)))
        
        for i in self._worker:
            i.start()
    
    def get_packets(self):
        
        self._lock.acquire()
        try:
            packets = copy.copy(self._packets)
        finally:
            self._lock.release()
        
        return packets
    
    def update_info(self, force=False):
        
        if not self._info is None:
            self._info.update_status(self.get_packets(), force=force)
    
    def _add_link(self, link):
        "Only used by 'add' to add just one link to the list."
        
        result = pfutil.PACKET_NAME_RE.search(link)
        
        if result is None:
            result = pfutil.PACKET_NAME_SIMPLE_RE.search(link)
        
        if result is None:
            self._log.warning("couldn't add link (%s)" % link)
            return False
            
        name = result.group(1)
        was_downloaded = self._detainer.was_downloaded(name)
        
        self._lock.acquire()
        try:
            pack = None
            
            for i in self._packets:
                if i.has_name(name):
                    pack = i
                    break
            
            if pack is None:
                pack = pfpacket.pf_packet(name, repeated=was_downloaded)
                self._packets.append(pack)
        finally:
            self._lock.release()
        
        if not was_downloaded:
            self._detainer.added(link)
        
        pack.add(link) # now its outside the locked block...
        return True
    
    def padd(self, links):
        "Adds all elements of 'links' to download."
        
        count = 0
        
        for link in links:
            if self._add_link(link):
                count += 1
        
        self.update_info()
        
        # save often to ensure that unfinished links are saved
        # in case of shutdown
        self._detainer.sync()
        return count
    
        
    def tmp_add_pwd(self, pwd):
        "Temporary adds password to pwd-list."

        try:        
            self._lock.acquire()
            try:
                self._config['pwd'].append(pwd)
            finally:
                self._lock.release()
            self._log.debug("adding new password %s" % pwd)
        except:
            self._log.error("no 'pwd' section in config (this is a problem)")
    
    def _find_packet(self, packet_name):
        
        self._lock.acquire()
        try:
            for packet in self._packets:
                if packet.has_name(packet_name):
                    return packet
        finally:
            self._lock.release()
        
        return None
        
    
    def pstart(self, packet_name):
        
        result = False
        packet = self._find_packet(packet_name)
        
        if not (packet is None):
            if packet.set_waiting():
                # ensures that packet is only downloaded once
                self._cmds.put(('start', packet))
                result = True
            else:
                self._log.debug("packet %s refused to set waiting state"
                    % packet_name)
        
        if result:
            self._log.debug("started packet %s successfully" % packet_name)
        else:
            self._log.warning("couldn't start packet %s" % packet_name)
        
        self._detainer.sync()
        return result
    
    
    def pkill(self, packet_name):
        
        result = False
        packet = self._find_packet(packet_name)
        
        if not (packet is None):
            packet.kill()
            result = True
        
        if result:
            self._log.debug("killed packet %s successfully" % packet_name)
        else:
            self._log.warning("couldn't kill packet %s" % packet_name)
        
        # well... no real need for that...
        self._detainer.sync()
        
        return result
    
    
    def preset(self, packet_name, force=False):
        
        result = False
        packet = self._find_packet(packet_name)
        
        if not (packet is None):
            result = packet.reset(force=force)
        
        if result:
            self._log.debug("reset packet %s successfully" % packet_name)
        else:
            self._log.warning("couldn't reset packet %s" % packet_name)
        
        return result

    
    # worker-threads-main-loop
    
    def _workloop(self):
        
        run = True
        while run:
            try:
                self._lock.acquire()
                try:
                    run = self._running
                finally:
                    self._lock.release()
                
                cmd = self._cmds.get(timeout=1)
                if cmd[0] == 'start':
                    pack = cmd[1]
                    self._work(pack)
                
                self._cmds.task_done()
            except Queue.Empty:
                pass
            
        self._log.info("working loop terminates")
    
    def _work(self, pack):
        "Downloads and extracts packet."
        
        extr = None
        rs_cookie = None
        
        self._lock.acquire()
        try:
            rs_cookie = self._config['rapid-share']
            src = self._config['from']
            dest = self._config['to']
            pwds = copy.copy(self._config['pwd'])
        finally:
            self._lock.release()
        
        pack.download(src, rs_cookie)
        pack.extract(src, dest, pwds)
        
        pack_name = pack.get_name()
        
        if pack.is_finished():
            self._log.debug("finished packet %s" % pack_name)
            self._detainer.finished(pack_name)
        else:
            self._log.info("packet %s failed" % pack_name)
    
    
    def _info_loop(self):
        
        run = True
        
        while run:
            self.update_info()
            time.sleep(pfutil.UPDATE_INTERVAL)
            
            self._lock.acquire()
            try:
                run = self._running
            finally:
                self._lock.release()
        
        self._log.info("info loop exits")
    
    def kill(self):
        
        self._lock.acquire()
        try:
            self._running = False
            packets = copy.copy(self._packets)
        finally:
            self._lock.release()
        
        self._log.info("killing all packets...")
        for i in packets:
            i.kill()
        
        self._detainer.sync()
        
        self._log.info("waiting for workerloop(s) to quit")
        
        for i in self._worker:
            i.join()
        
        if not (self._info is None):
            
            if not (self._info_thread is None):
                self._log.info("waiting for info-thread to terminate...")
                self._info_thread.join()
            
            self._log.info("killing info-server...")
            self._info.kill()
        
        self._log.info("pfmanager terminated...")

