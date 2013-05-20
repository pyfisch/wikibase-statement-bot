import sys
import time
import re

#import MySQLdb
import mysql.connector as MySQLdb
import pywikibot

import config

wikidata = pywikibot.site.DataSite('wikidata', 'wikidata')
logpage = pywikibot.Page(wikidata, config.log)
genlogpage = pywikibot.Page(wikidata, config.completed)

def wiki_repr(claim):
    """Returns the wikimarkup for the claims target."""
    if type(claim.target) == pywikibot.ItemPage:
        return "[[%s]]" % claim.target.id
    elif type(claim.target) == unicode:
        return repr(claim.target)

def sqltitle(title):
    """Returns a sql escaped title."""
    return title.replace("'", "''")

def str2cat(catname):
    lang = re.findall('(?<=:).*?(?=:)', catname)[0]
    catname = re.findall('[^:]*?$', catname)[0]
    return pywikibot.Category(pywikibot.Site(lang, 'wikipedia'), catname)


class BaseDB(object):
    def execute(self, query):
        """Execute a query with error handling."""
        for i in range(0, 3):
            try:
                self.cursor.execute(query)
                return
            #except MySQLdb.InterfaceError or MySQLdb.OperationalError:
            except MySQLdb.errors.Error as e:
                time.sleep(0.1)
                self.connect()
                
        print "Can't execute %s." % repr(query)
        sys.exit()
    
    def connect(self):
        try:
            self.connection = MySQLdb.connect(**config.database)
            self.cursor = self.connection.cursor()
            return True
        #except MySQLdb.OperationalError:
        except MySQLdb.errors.Error:
            return False


class DatabaseAccess(object):
    def __init__(self):
        pass
        #BaseDB.__init__(self)
        #if not self.connect():
        #    #raise MySQLdb.OperationalError("Can't connect.")
        #    raise MySQLdb.errors.Error("Can't connect.")

    def execute(self, query, command):
        self.main.request_queries[query] = command
        if command != 'commit':
            while not query in self.main.response_queries:
                pass
            ret = self.main.response_queries[query]
            del self.main.response_queries[query]
            return ret
        

    def checkTransferred(self):
        """Checks if the transfer was logged before.
        @rtype bool
        """
        QUERY = "SELECT EXISTS(SELECT 1 FROM transferred WHERE item='%s')"
        return self.execute(QUERY % self.id, 'bool')
        #return bool(self.cursor.fetchone()[0])
    
    def checkNoItemDB(self):
        """Checks if the lemma was logged with no item.
        @rtype bool
        """
        QUERY = "SELECT EXISTS(SELECT 1 FROM no_item WHERE lemma='w:%s:%s')"
        return self.execute(QUERY % (self.site.lang, sqltitle(self.title())), 'bool')
        #return bool(self.cursor.fetchone()[0])
    
    def logTransferredDB(self):
        """Logs that the item was written to database."""
        QUERY = "INSERT INTO transferred VALUES ('%s', 1)"
        self.execute(QUERY % self.id, 'commit')
        #self.connection.commit()
    
    def logNoItemDB(self):
        """Logs that for this title no item exists."""
        QUERY = "INSERT INTO no_item VALUES ('w:%s:%s')"
        self.execute(QUERY % (self.site.lang, sqltitle(self.title())), 'commit')
        #self.connection.commit()

class WikidataLogger(object):
    
    def logWD(self, **kwargs):
        """Writes messages at the logpage."""
        line = pywikibot.textlib.glue_template_and_params(('/line', kwargs))
        for i in range(0, 3):
            try:
                logpage.put('%s\n%s' % (logpage.get(), line))
                break
            except pywikibot.PageNotSaved:
                logpage.get(force=True)
        
    def logNoItemWD(self):
        """Logs missing items at the logpage."""
        self.logWD(reason='missing', object="[[:w:%s:%s]]" % (self.site.lang, self.title()))
    
    def logInvalidClaim(self, claim):
        if claim.target == u'':
            return
        self.logWD(reason='invalid',
                   object="[[%s]]" % self.id,
                   property=claim.id,
                   value=claim.target,)
    
    def logConflict(self, claim1, claim2):
        self.logWD(reason='conflict',
                   object="[[%s]]" % self.id,
                   property=claim1.id,
                   value=claim1.target.id,
                   remark="existing statement is: %s" % wiki_repr(claim2)
                   )
    
    def logNoItemClaim(self, page, p):
        self.logWD(reason='add',
                   object="[[%s]]" % self.id,
                   property = p,
                   value="[[:w:%s:%s]]" % (page.site.lang, page.title()),
                   remark="Claim value has no item."
                   )
    
    def logMultipleItemsForClaim(self, p, values):
        self.logWD(reason='add',
                   object="[[%s]]" % self.id,
                   property=p,
                   value="/".join(["[[%s]]" % i.id for i in values]),
                   remark="Select the most exact value.")


class MainLogger(BaseDB):
    def __init__(self):
        BaseDB.__init__(self)
        if not self.connect():
            raise MySQLdb.errors.Error("Can't connect.")

    def getNewTask(self):
        """Gets the first undone task from generator."""
        QUERY = "SELECT category FROM generator WHERE state<>2 ORDER BY category ASC LIMIT 1"
        self.execute(QUERY)
        val =  self.cursor.fetchone()[0]
        return val
    
    def setTaskState(self, new_state):
        """Sets the state of a Task."""
        QUERY = "UPDATE generator SET state=%i WHERE category='%s'"
        self.execute(QUERY % (new_state, sqltitle(self.fullcatname)))
        self.connection.commit()
    
    def getTasks(self, state=-1):
        """Gets tasks from the table generator with given state."""
        if state != -1:
            QUERY = "SELECT * FROM generator WHERE state = %i ORDER BY category ASC" % state
        else:
            QUERY = "SELECT * FROM generator ORDER BY category ASC"
        self.execute(QUERY)
        return self.cursor.fetchall()
    
    def checkTaskExists(self, catname):
        """Checks if the lemma was logged with no item.
        @rtype bool
        """
        QUERY = "SELECT EXISTS(SELECT 1 FROM generator WHERE category='%s')"
        self.execute(QUERY % (catname))
        return bool(self.cursor.fetchone()[0])
    
    def addTask(self, catname):
        """Adds a new Category to the generator table."""
        QUERY = "INSERT INTO generator VALUES ('%s', 0)"
        if not self.checkTaskExists(catname):
            if str2cat(catname).exists():
                self.execute(QUERY % sqltitle(catname))
                self.connection.commit()
                return True
        return False

    def logFinished(self):
        """Log that a category was written complete."""
        for i in range(0, 3):
            try:
                genlogpage.put('%s\n* [[%s]]' % (genlogpage.get(), self.fullcatname))
                return
            except pywikibot.PageNotSaved:
                genlogpage.get(force=True)
        print "Can't put new version of %s." % genlogpage.title()


class Logger(DatabaseAccess, WikidataLogger):
    def __init__(self):
        DatabaseAccess.__init__(self)
        WikidataLogger.__init__(self)
    
    def logNoItem(self):
        self.logNoItemDB()
        #self.logNoItemWD()
    
    def checkNoItem(self):
        """Checks if an item exists for the page. Returns True, if item
        exists. Logs it if there is no item.
        @rtype bool
        """
        if self.checkNoItemDB():
            return False
        elif not self.exists():
            self.logNoItem()
            return False
        else:
            return True
    
    
        