import time

import pywikibot

import output
from rules import Rules, catrules, unique_propertys, page2source, templaterules
from ruleclasses import BotClaim

wikidata = pywikibot.site.DataSite('wikidata', 'wikidata')

def isClaimInList(claim, others):
    for i in others:
        if i.type == 'item' and i.snaktype == 'value':
            if i.target.id == claim.target.id:
                return True
        else:
            if i.target == claim.target:
                return True
    return False

class ClaimContainer(pywikibot.ItemPage, output.Logger, Rules):
    def __init__(self, page, main):
        """Inits the Container and the claim buffers. Gets the item of a page
         and check if it exists, and if it is already transffered to Wikidata.
        @param page Wikipedia Page object.
        @var self.claims Raw claims as extracted.
        @var self.merged_claims self.claims merged between the languages.
        @var self.validated_claims Merged claims after checks for some
            selected propertys.
        @var self.new_claims Claims, which where not on Wikidata before and
            have no conficts.
        @var self.proceed If the item should be extracted.
        """
        #create variables
        self.lang_claims = []
        self.merged_claims = []
        self.validated_claims = []
        self.new_claims = []
        self.proceed = True
        self.main = main
        #init parents
        pywikibot.ItemPage.__init__(self, page.site, page.title())
        output.Logger.__init__(self)
        Rules.__init__(self)
        self.main = main
        #get the page
        if not self.checkNoItem():
            self.proceed = False
        else:
            self.get()
            #check if the item is untransferred
            if self.checkTransferred():
                self.proceed = False

    def extractFromTemplates(self, page):
        templates = pywikibot.textlib.extract_templates_and_params(page.get())
        langparsers = self.parsers[page.site.lang]
        for (template, params) in templates:
            if template in langparsers:
                parser = langparsers[template]
                for arg in params:
                    if arg in parser and params[arg]:
                        parser[arg](arg=params[arg], page=page)
                if not params and parser.has_key('#NOARGS#'):
                    parser['#NOARGS#'](arg=None, page=page)

    def extractFromCategories(self, page):
        for i in page.categories():
            if i.title(withNamespace=False) in catrules[page.site.lang]:
                new_claims = catrules[page.site.lang][i.title(withNamespace=False)]
                for property, item in new_claims:
                    self.lang_claims.append(BotClaim(property, 
                                                     pywikibot.ItemPage(wikidata, item),
                                                     [page2source(page)]))
        
    def mergeLanguageClaims(self):
        """Merges the extracted claims."""
        self.lang_claims.sort()
        for claim in self.lang_claims:
            if self.merged_claims and self.merged_claims[-1] == claim:
                self.merged_claims[-1].new_sources |= claim.new_sources
            else:
                self.merged_claims.append(claim)

    def validateClaims(self):
        """Validates all merged claims where a validator is defined."""
        for claim in self.merged_claims:
            if claim.id in validators and not validators[claim.id](claim.target):
                self.logInvalidClaim(claim)
            else:
                self.validated_claims.append(claim)
    
    def mergeWithWikidata(self):
        for claim in self.merged_claims:
            if claim.id in self.claims:
                if not isClaimInList(claim, self.claims[claim.id]) and not claim.id in unique_propertys:
                    self.new_claims.append(claim)
            else:
                self.new_claims.append(claim)
                    
    
    def writeToWikidata(self):
        for claim in self.new_claims:
            for j in range(3):
                try:
                    self.addClaim(claim)
                    break
                except (pywikibot.Error, pywikibot.data.api.APIError):
                    time.sleep(1)
                    self.get(force=True)
                except KeyError: break
            for i in claim.new_sources:
                for j in range(3):
                    try:
                        claim.addSource(i, bot=True)
                        break
                    except (pywikibot.Error, pywikibot.data.api.APIError):
                        time.sleep(1)
                        self.get(force=True)
                    except KeyError: break
    
    def writeDescs(self):
        if self.new_descriptions:
            for i in range(3):
                try:
                    self.editDescriptions(self.new_descriptions)
                except (pywikibot.Error, pywikibot.data.api.APIError):
                    self.get(force=True)
                except KeyError: break

    def extract(self):
        for sitelink in self.sitelinks.items():
            lang = sitelink[0][:-4]
            if lang in templaterules or lang in catrules:
                site = pywikibot.Site(lang, 'wikipedia')
                page = pywikibot.Page(site, sitelink[1])
                if page.exists() and not page.isRedirectPage():
                    if lang in templaterules:
                        self.extractFromTemplates(page)
                    if lang in catrules:
                        self.extractFromCategories(page)

    def processItem(self):
        """Function for single threaded usage, which extracts, merges and
         writes claims.
         """
        self.extract()
        self.mergeLanguageClaims()
        self.validateClaims()
        self.mergeWithWikidata()
        self.writeToWikidata()
        self.log()