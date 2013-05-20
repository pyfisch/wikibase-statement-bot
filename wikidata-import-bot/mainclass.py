# -*- coding: utf-8 -*-
import threading
import re
import time

import pywikibot

import output
import config
from containerclass import ClaimContainer

pywikibot.config.put_throttle = 1

STOP_THREAD = 0
ACTIVE_THREAD = 1
WAIT_OVERFLOW_THREAD = 2
WAIT_EMPTY_THREAD = 3
INACTIVE_THREAD = -1
ERROR_ENDED_THREAD = -2

class Main(output.MainLogger):
    def __init__(self):
        """
        @var self.buffer Buffer of extracted items, waiting for writing.
        @var self.gen Generator containing items to be extracted.
        @var self.fullcatname Name of current category.
        """
        output.MainLogger.__init__(self)
        self.buffer = []
        self.gen = []
        self.fullcatname = ''
        self.request_queries = {}
        self.response_queries = {}
        self.extract_threads = self.createThreads(self.extractThread,
                                                  "extractThread%i",
                                                  config.extract_threads)
        self.write_threads = self.createThreads(self.writeThread,
                                                "writeThread%i",
                                                config.write_threads)
        self.gen_threads = self.createThreads(self.genThread, "genThread%i", 1)

    def createThreads(self, function, name, quantity):
        """Creates a given number of thread instances."""
        threads = []
        for i in range(quantity):
            extractThread = threading.Thread(target=function,
                                             args=(i,),
                                             name=name % i)
            threads.append({'thread': extractThread,
                            'name': name % i,
                            'state': INACTIVE_THREAD,
                            'stop': False})
        return threads
    
    def extractThread(self, index):
        try:
            while not self.extract_threads[index]['stop']:
                if len(self.buffer) > 20:
                    self.extract_threads[index]['state'] = WAIT_OVERFLOW_THREAD
                elif self.gen:
                    self.extract_threads[index]['state'] = ACTIVE_THREAD
                    try: page = self.gen.pop()
                    except IndexError: continue
                    itemcont = ClaimContainer(page, self)
                    if itemcont.proceed:
                        itemcont.extract()
                        self.buffer.append(itemcont)
                        itemcont.mergeLanguageClaims()
                        #itemcont.validateClaims()
                        itemcont.mergeWithWikidata()
                else:
                    self.extract_threads[index]['state'] = WAIT_EMPTY_THREAD
            self.extract_threads[index]['state'] = INACTIVE_THREAD
        finally:
            if not self.extract_threads[index]['state'] == INACTIVE_THREAD:
                self.extract_threads[index]['state'] = ERROR_ENDED_THREAD
    
    def writeThread(self, index):
        try:
            while not self.write_threads[index]['stop']:
                if self.buffer:
                    self.write_threads[index]['state'] = ACTIVE_THREAD
                    try:
                        itemcont = self.buffer.pop()
                    except IndexError:
                        continue
                    itemcont.writeDescs()
                    itemcont.writeToWikidata()
                    itemcont.logTransferredDB()
                    #itemcont.connection.close()
                else:
                    self.write_threads[index]['state'] = WAIT_EMPTY_THREAD
            self.write_threads[index][['state']] = INACTIVE_THREAD
        finally:
            if not self.write_threads[index]['state'] == INACTIVE_THREAD:
                self.write_threads[index]['state'] = ERROR_ENDED_THREAD
    
    def fillGenerator(self):
        if len(self.gen) < 3:
            if self.fullcatname:
                self.setTaskState(2)
                self.logFinished()
            self.fullcatname = self.getNewTask()
            lang = re.findall('(?<=:).*?(?=:)', self.fullcatname)[0]
            catname = re.findall('[^:]*?$', self.fullcatname)[0]
            cat = pywikibot.Category(pywikibot.Site(lang, 'wikipedia'), catname)
            self.gen = list(cat.articles())
            self.setTaskState(1)
        
    def isError(self):
        for i in self.extract_threads + self.write_threads + self.gen_threads:
            if i['state'] == ERROR_ENDED_THREAD:
                self.stopAllThreads()
    
    def stopAllThreads(self):
        for i in self.extract_threads + self.write_threads + self.gen_threads:
            i['stop'] = True
    
    def processQueries(self):
        for i in self.request_queries.keys():
            self.execute(i)
            if self.request_queries[i] == 'bool':
                self.response_queries[i] = bool(self.cursor.fetchone()[0])
            del self.request_queries[i]
        self.connection.commit()

    
    def genThread(self, index):
        try:
            while not self.gen_threads[0]['stop']:
                self.fillGenerator()
                self.processQueries()
            self.write_threads[index][['state']] = INACTIVE_THREAD
        finally:
            if not self.gen_threads[index]['state'] == INACTIVE_THREAD:
                self.gen_threads[index]['state'] = ERROR_ENDED_THREAD 

    def end(self):
        for i in self.extract_threads:
            if i['state'] > 0:
                i['stop'] = 0
    
    def startThreads(self):
        for i in self.extract_threads + self.write_threads + self.gen_threads:
            i['thread'].start()