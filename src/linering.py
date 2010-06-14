import threading

DEFAULT_SIZE = 100

class lring(object):
    "Not thread-safe ring buffer"
    
    def __init__(self, size=DEFAULT_SIZE):
        
        self._lines = ['' for i in range(size)]
        self._position = 0
        self._max = 0
        self._size = size
    
    def clear(self):
        "Clears ring buffer."
        
        self._max = 0
        self._position = 0
        
    def push(self, line):
        "Writes 'line' to next position."
        
        if self._max < self._size:
            self._max += 1
        
        self._lines[self._position] = line
        self._position = (self._position + 1) % self._size
    
    def pop(self):
        "Returns prev. element, none if ring is empty."
        
        if self._max > 0:
            self._max -= 1
            
            self._position = (self._position - 1) % self._size
            return self._lines[self._position]
    
    def get_list(self):
        "Returns list of all elements."
        
        return [self._lines[(self._position - (i + 1)) % self._size] 
                    for i in range(self._max)]
        
        
