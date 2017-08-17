'''
inspired by <http://code.activestate.com/recipes/498266-a-self-cleaning-dict-like-container-which-limits-t/>
This container stores its items both in a dict (for direct access) and in a
bi-directionally linked list(for prune), which enables it to update itself in essentially
O(1) time.
'''

from UserDict import DictMixin
import sys
from time import time

class _Item(object):
    '''
    wrapper for items stored in ExpiringCount, providing them with references to one another
    '''
    __slots__ = "key value nextItem previousItem mtime".split()
    def __init__(self, key, value):
        self.key = key
        self.value = value
        self.nextItem = None
        self.previousItem = None
        self.mtime = time()


class ExpiringCounter():
    '''
    a counter with ttl
    '''
    def __init__(self, timeout):
        self._timeout = timeout
        self._data = {}
        # pointers to newest and oldest items
        self._newest = None
        self._oldest = None


    def _setNewest(self, item):
        '''
        put a new or retrieved item at the top of the pile
        '''
        item.mtime = time()

        if item is self._newest:                        # item is already on top
            return

        if item.nextItem or item.previousItem:          # this item is currently in the pile...
            self._pullout(item)                         # pull it out

        if self._newest:
            self._newest.nextItem = item                # point the previously newest item to this one...
            item.previousItem = self._newest            # and vice versa

        self._newest = item                             # reset the 'newest' pointer

        if not self._oldest:                            # this only applies if the pile was empty
            self._oldest = item


    def _pullout(self, item):
        '''
        pull an item out of the pile and hook up the neighbours to each other
        '''
        if item is self._oldest:
            if item is self._newest:                    # removing the only item
                self._newest = self._oldest = None
            else:                                       # removing the oldest item of 2 or more
                self._oldest = item.nextItem
                self._oldest.previousItem = None

        elif item is self._newest:                      # removing the newest item of 2 or more
            self._newest = item.previousItem
            self._newest.nextItem = None

        else:   # we are somewhere in between at least 2 others - hitch up the neighbours to each other
            prev = item.previousItem
            next = item.nextItem

            prev.nextItem = next
            next.previousItem = prev

        item.nextItem = item.previousItem = None


    def count(self, key, value=1):
        '''
        add an item and count it
        '''
        self.prune()

        item = self._data.get(key)
        if item:
            value += item.value
            item.value = value
        else:
            item = self._data[key] = _Item(key, value)
        self._setNewest(item)
        return value


    def remove(self, key):
        '''
        delete an item
        '''
        item = self._data.pop(key)
        self._pullout(item)


    def prune(self):
        '''
        drop the expired members 
        '''
        outtime = time() - self._timeout
        while self._oldest and self._oldest.mtime < outtime:
            drop = self._data.pop(self._oldest.key)
            self._oldest = drop.nextItem
            if self._oldest:
                self._oldest.previousItem = None


    def _contents(self, method, *args):
        '''
        common backend for methods:
        keys, values, items, __len__, __contains__
        '''
        self.prune()

        data = getattr(self._data, method)(*args)
        return data

    def __contains__(self, key):
        return self._contents('__contains__', key)

    has_key = __contains__


    def __len__(self):
        return self._contents('__len__')


    def keys(self):
        return self._contents('keys')


    def values(self):
        data = self._contents('values')
        return [v.value for v in data]


    def items(self):
        data = self._contents('items')
        return [(k, v.value) for k, v in data]


    def __repr__(self):
        d = dict(self.items())
        return '%s(timeout=%s, data=%s)' % (self.__class__.__name__, self._timeout, repr(d))

