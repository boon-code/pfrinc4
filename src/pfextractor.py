import os
import unrar

class extractor(object):
    
    def __init__(self, source, dest, pwds):
        "Creates and configures an extractor-object"
        
        self._to = dest
        self._from = source
        self._pwd = pwds
    
    def extract(self, filename, proc=None):
        "Starts extractor-utility and extracts packets."
        
        file_path = os.path.join(self._from, filename)
        
        for pwd in self._pwd:
            unr = unrar.UnrarSpoon(file_path, self._to, pwd)
            status = unr.update_loop(callback=proc)
            
            if status[unrar.STATUS_OK]:
                return True
        
        return False
