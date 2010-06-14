import socket
import Queue
import threading
import time
import copy
import logging
import sys
import traceback

LOGGER_NAME = 'pf-info'

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


DEFAULT_SOCKET_TIMEOUT = 0.5
DEFAULT_TIMEOUT = 1.0
BIND_WAITTIME = 60.0

class info_server(object):
    
    def __init__(self, port):
        "Initializes info server object, listens on port 'port'."
        
        self._msgqueue = Queue.Queue()
        self._lock = threading.RLock()
        self._msg_running = True
        self._acc_running = True
        
        self._log = logging.getLogger(LOGGER_NAME)
        
        self._clients = []
        self._old_status = ""
        self._accept_thread = threading.Thread(target=self._accept,
            args=(port,))
        self._msg_thread = threading.Thread(target=self._msg)
        
        self._log.info("starting accept-thread...")
        self._accept_thread.start()
        
        self._log.info("starting msg-thread...")
        self._msg_thread.start()
    
    def _correct_msg(self, msg):
        "checks if message has right format, returns valid message."
        
        l = 'l'
        data = []
        for i in msg:
            if l == '\n' and i == '\n':
                pass
            else:
                data.append(i)
                l = i
        
        return ("".join(data)).strip('\n')
        
    def put_msg(self, msg):
        "Pushes new message on queue and tells every client."
        
        msg = self._correct_msg(msg)
        self._msgqueue.put("msg " + msg + '\n\n')
        
    def _msg(self):
        "Message Loop, processes every message which was put into queue."
        
        while self._msg_is_running():
            try:
                msg = self._msgqueue.get(True, DEFAULT_TIMEOUT)
                dead_clients = []
                
                self._lock.acquire()
                try:
                    for client in self._clients:
                        try:
                            client.sendall(msg)
                        except socket.error:
                            dead_clients.append(client.getsockname())
                            self._clients.remove(client)
                finally:
                    self._lock.release()
                
                for client_addr in dead_clients:
                    self._log.debug("client (%s:%d) was removed" % 
                        client_addr) 
            except Queue.Empty:
                pass
        
        self._log.info("shutting down info-server")
        self._lock.acquire()
        try:
            for client in self._clients:
                client.close()
        finally:
            self._lock.release()
        
    
    def update_status(self, packets, force=False):
        "updates current buffer."
        
        
        buffer = ""
        for i in packets:
            buffer += "".join((i.get_name(), ' ', i.status(), '\n'))
        
        buffer = self._correct_msg(buffer)
    
        self._lock.acquire()
        try:    
            if (buffer != '' and buffer != self._old_status):
                self._msgqueue.put("status " + buffer + '\n\n')
                self._old_status = buffer
            elif force:
                self._msgqueue.put("status " + buffer + '\n\n')
                self._old_status = buffer
             
        finally:
            self._lock.release()
            
    def _accept(self, port):
        "This loop accepts new connections."
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        try:
            sock.bind(('', port))
        except:
            self._log.warning("socket.bind failed (retrying once) %s" % 
                traceback.format_exc())
            time.sleep(BIND_WAITTIME)
            sock.bind(('', port))
            self._log.info("now bind worked...")
        
        sock.listen(100)
        sock.settimeout(DEFAULT_SOCKET_TIMEOUT)
        
        while self._acc_is_running():
            try:
                client, address = sock.accept()
                self._lock.acquire()
                try:
                    self._clients.append(client)
                finally:
                    self._lock.release()
                peer = client.getpeername()
                self._log.debug("accepted new client (%s:%d)" % peer)
            except socket.timeout:
                pass
            except socket.error:
                self._log.debug("socket error happend...")
        
        self._log.info("shutting down accept-loop")
        sock.close()
            
    def _msg_is_running(self):
        
        self._lock.acquire()
        try:
            run = copy.copy(self._msg_running)
            return run
        finally:
            self._lock.release()
    
    def _acc_is_running(self):
        
        self._lock.acquire()
        try:
            run = copy.copy(self._acc_running)
            return run
        finally:
            self._lock.release()
    
    def kill(self):
        "Stop Threads and quit job (blocking)."
        
        self._lock.acquire()
        try:
            self._acc_running = False
        finally:
            self._lock.release()
        
        self._accept_thread.join()
        
        self._lock.acquire()
        try:
            self._msg_running = False
        finally:
            self._lock.release()
        
        self._msg_thread.join()
