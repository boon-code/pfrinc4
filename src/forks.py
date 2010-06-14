import subprocess
import re
import os
import signal
import select
import copy
import time

RUNNING = 'run'
RETURN_CODE = 'rc'
STREAM_OPEN = 'popen'

FORKS_VERSION = "0.0.1"

EXTRA_WAIT_TIME = 1


class ForksException(Exception):
    "General Forks Exception"
    
    pass


class KillForkException(ForksException):
    """ Kill Exception
    
    You should raise this exception if you decide to kill your spoon
    in the callback function. Spoon will automatically kill itself.
    """
    
    pass


class SpoonNotStartedError(ForksException):
    """Not Started Exception
    
    This exception should be raised by Spoon, if you call update_loop()
    before starting the Spoon.
    """
    
    pass


class UninitializedHelper(object):
    """ Helper class used by Spoon
    
    Don't use directly. This class does only raise an exception if
    you call update_loop on your Spoon before calling start
    """
    
    def __init__(self):
        pass
    
    def fileno(self):
        raise SpoonNotStartedError()


class Spoon(object):
    """ Spoon
    
    This class should help you to write applications that read from
    external programs. It's also possible to write data either to 
    stdout or to stderr.
    To uses this class simply derive your custom class from forks.Spoon
    and implement the _update function. You can use read_char to read 
    characters from output stream of the external application. See
    TestSpoon class for implementation details.
    """
    
    def __init__(self):
        """ __init__(self)
        
        Constructor creates the _status variable and fills in basic 
        entries like:
        - RUNNING: is the external application still running?
        - RETURN_CODE: return code of application after exit
        - STREAM_OPEN: is the connected stream still opened?
        """
        
        self._status = {RUNNING : None, RETURN_CODE : None,
                        STREAM_OPEN : True}
        self._callback = None
        self._stream = UninitializedHelper()
    
    def start(self, args, in_data=None, use_stderr=False, cwd=None):
        """ start(self, args, in_data=None, usestderr=False, cwd=None)
        
        This method executes args[0] with parameters args[1:].
        If in_data is a valid string, it will be written to stdin of
        the external application.
        If use_stderr is True, stderr is read in spite of stdout.
        If cwd is a valid string, the external application will be 
        started in cwd directory if possible.
        """
        
        self._status[RUNNING] = True
        params = {}
        
        if not (cwd is None):
            params['cwd'] = cwd
        
        if use_stderr:
            params['stderr'] = subprocess.PIPE
        else:
            params['stdout'] = subprocess.PIPE
        
        if in_data is None:
            self._sproc = subprocess.Popen(args, **params)
        else:
            self._sproc = subprocess.Popen(args, stdin=subprocess.PIPE,
                **params)
            self._sproc.stdin.write(in_data)
            self._sproc.stdin.close()
        
        if use_stderr:
            self._stream = self._sproc.stderr
        else:
            self._stream = self._sproc.stdout
    
    def _call_callback(self):
        "calls callback function (just a shorthand)."
        
        if not (self._callback is None):
            status = copy.copy(self._status)
            self._callback(status)
    
    def read_char(self, wait=0.0):
        """ read_char(self, wait=0)
        
        This method should be used to read a character in the _update
        function.
        Wait defines the wait time before the callback function is 
        called if there is no new data. If wait is set to None, it will
        block forever.
        """
        
        std_nr = self._stream.fileno()
        
        while True:
            if std_nr in select.select([std_nr], [], [], wait)[0]:
                ch = self._stream.read(1)
                if ch == '':
                    self._status[STREAM_OPEN] = False
                return ch
            else:
                self._call_callback()
    
    def update_loop(self, callback=None, wait=EXTRA_WAIT_TIME):
        """ update_loop(self, callback=None, wait=EXTRA_WAIT_TIME)
        
        This starts the update-loop. It will loop until the external
        program terminates.
        If callback is not set, no function will be called, the
        loop will block until finished.
        Wait defines a wait-time to use if the stream is closed but the
        external application still runs. (unimportant)
        """
        
        self._callback = callback
        
        ch = 'a' # value doesn't matter unless it's ''
        while self._status[STREAM_OPEN] or self._status[RUNNING]:
            try:
                if self._status[STREAM_OPEN]:
                    self._update()
                else:
                    time.sleep(wait) # don't waste cpu time...
                self._call_callback()
            except KillForkException:
                self.kill()
            self._status[RETURN_CODE] = self._sproc.poll()
            self._status[RUNNING] = (self._status[RETURN_CODE] is None)
        
        try:
            self._call_callback()
        except KillForkException:
            pass
        
        return copy.deepcopy(self._status)
    
    def kill(self):
        """ kill(self)
        
        Kill tries to really kill the external program, do only use this
        if it's really necessary.
        """
        
        if self._sproc.poll() is None:
            os.kill(self._sproc.pid, signal.SIGTERM)
            return True
        else:
            return False


class TestSpoon(Spoon):
    """ TestSpoon
    
    This is a simple test  class for Spoon. Create an instance and
    call the constructor with a list arg:
    - arg[0] is a command
    - arg[1:] are it's parameters
    
    For example do TestSpoon(["python", "-V"], True)
    """
    
    def __init__(self, cmd, use_stderr=False):
        """ __init__(self, cmd, use_stderr)
        
        Just like using subprocess.Popen(cmd) (since Spoon uses
        subprocess.Popen ...).
        """
        
        Spoon.__init__(self)
        self._status['hui'] = ''
        self.start(cmd, use_stderr=use_stderr)
        self.update_loop(callback=self.callback)
    
    def _update(self):
        """ _update(self)
        
        Simple implementation of _update.
        Uses read_char to read the output and adds all characters to
        status entry 'hui'.
        """
        
        ch = self.read_char(wait=1)
        while ch != '\n' and ch != '':
            self._status['hui'] += ch
            ch = self.read_char(wait=1)
    
    def callback(self, status):
        """ callback(self, status)
        
        This callback function will be called by Spoon.
        Note that this function could be any function, it doesn't have
        to be a member of your class
        """
        
        print status

