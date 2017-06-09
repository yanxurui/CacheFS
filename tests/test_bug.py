
from common import *

class TestBug(BaseTest):
    def test_erase_wrong_position(self):
    	"""erase outside volume limit size

    	in lua we can not ftruncate a file, so volume can not be shorten
    	there may be some residual content in the end of volume when delete a file
    	"""
        key = 'foo'
        r=self.put(key, 1024*1024+20) # volume 0
        r=self.put(key, 1024*1024) # volume 1
        r=self.put(key, 1024*1024) # volume 0
        r=self.put(key, 1024*1024) # volume 1
        r=self.put(key, 1024*1024-20) # volume 0
        r=self.put(key, 1024*1024) # volume 1
        # this may result in a 500 becase erase function read the key lenght at a dirty position
        r=self.put(key, 10) # volume 1
