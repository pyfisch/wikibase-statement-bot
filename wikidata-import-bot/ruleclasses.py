import pywikibot

class BotClaim(pywikibot.Claim):
    def __init__(self, pid, target, sources):
        pywikibot.Claim.__init__(self,
                                 pywikibot.site.DataSite('wikidata', 'wikidata'),
                                 pid)
        self.setTarget(target)
        self.new_sources = set(sources)
    
    def __str__(self):
        return "".join([self.title(asLink=True, allowInterwiki=False), ' -> ', repr(self.target), ' (lang: ', self.langstr(), ')'])
    
    def __cmp__(self, other):
        id_diff = int(self.id[1:]) - int(other.id[1:])
        if not id_diff:
            if self.target < other.target:
                return -1
            elif self.target == other.target:
                return 0
            else:
                return 1
        return id_diff
    
    def langstr(self):
        return ', '.join(self.lang)
            
        

class ItemLite(pywikibot.ItemPage):
    def __init__(self, title):
        pywikibot.ItemPage.__init__(self,
                           pywikibot.site.DataSite('wikidata', 'wikidata'),
                           title)
    
    def __repr__(self):
        return self.title(asLink=True, allowInterwiki=False)

Q = ItemLite
