# -*- coding: utf-8 -*-

import re

import pywikibot

from ruleclasses import BotClaim

ItemPage = pywikibot.ItemPage
wikidata = pywikibot.site.DataSite('wikidata', 'wikidata')

SOURCES = {
    'de': 'q48183',
    'en': 'q328',
    'fr': 'q8447',
    'it': 'q11920',
}

TYP_de = {
    u'p': 'q215627',
    u'k': 'q43229',
    u'v': 'q1656682',
    u'w': 'q386724',
    u's': 'q1969448',
    u'g': 'q618123',
}

TYPE_fr = {
    u'personne': 'q215627',
    u'organisation': 'q43229',
}

BVK_VARIANTS = {
    u'VM': 'q10905425',
    u'VKB': 'q10905380',
    u'VK1': 'q10905334',
    u'GrVK': 'q10905276',
    u'GrVKSt': 'q10905235',
    u'GrVKStSb': 'q10905171',
    u'GK': 'q10905105',
    u'GKbA': 'q10905054',
    u'SoGK': 'q10904959'
}

BUNDESANZEIGER_SOURCE = {
    "hash": "0e0a3292a55b54488417307e0f3b22c540290cf9",
    "snaks": {
        "p248": [
            {
                "snaktype": "value",
                "property": "p248",
                "datavalue": {
                    "value": {
                        "entity-type": "item",
                        "numeric-id": 1005565
                    },
                    "type": "wikibase-entityid"
                }
            }
        ],
        "p433": [
            {
                "snaktype": "value",
                "property": "p433",
                "datavalue": {
                    "value": None,
                    "type": "string"
                }
            }
        ]
    }
}

def page2source(page):
    source = pywikibot.Claim(wikidata, 'p143', isReference=True)
    source.setTarget(ItemPage(wikidata, SOURCES[page.site.lang]))
    return source

class Rules(object):
    def __init__(self):
        self.new_descriptions = {}
        self.parsers = {
            'de': {
                u'Normdaten': {
                    u'VIAF': self.getVIAF,
                    u'GND': self.getGND,
                    u'TYP': self.getTYP_de,
                    u'LCCN': self.getLCCN,
                    u'PND': self.getGND,
                    },
                u'Personendaten': {
                    u'GEBURTSORT': self.getBirthPlace,
                    u'STERBEORT': self.getDeathPlace,
                    u'KURZBESCHREIBUNG': self.getDescription,
                    },
                u'Commonscat': {
                    u'1': self.getCommonscat,
                    u'#NOARGS#': self.getCommonscat,
                    },
                u'BVK': {
                    '1': self.getBVKItem,
                    '2':self.addBVKSource,
                    },
                },
            'en': {
                u'Authority control': {
                    u'VIAF': self.getVIAF,
                    u'GND': self.getGND,
                    u'LCCN': self.getLCCN,
                    u'BNF': self.getBNF,
                    u'ULAN': self.getULAN,
                    u'PND': self.getGND,
                    },
                u'Commons category': {
                    u'1': self.getCommonscat,
                    u'#NOARGS#': self.getCommonscat, 
                    },
                },
            'fr': {
                u'Autorité': {
                    u'type': self.getTYPE_fr,
                    u'BNF': self.getBNF,
                    u'GND': self.getGND,
                    u'PND': self.getGND,
                    u'LCCN': self.getLCCN,
                    u'SUDOC': self.getSUDOC,
                    u'VIAF': self.getVIAF,
                    },
                u'Commonscat': {
                    u'1': self.getCommonscat,
                    u'#NOARGS#': self.getCommonscat, 
                    },
                u'Autres projets': {
                    u'commons': self.getCommonscat_fr,
                    },
                },
            'it': {
                u'Controllo di autorità': {
                    u'VIAF': self.getVIAF,
                    u'LCCN': self.getLCCN,
                    }
                }
            }
    
    @staticmethod
    def validateString(pattern, string):
        return bool(re.match('^%s$' % pattern, string))
    
    def getString(self, arg, page, pattern, property_, **kwargs):
        if self.validateString(pattern, arg):
            self.lang_claims.append(BotClaim(property_,
                                             arg,
                                             [page2source(page)]))
        else:
            pass
    
    def getLCCN(self, arg, page, **kwargs):
        if self.validateString('[a-z]*/(\d\d|\d\d\d\d)/\d+', arg):
            parts = arg.split('/')
            lccn = parts[0] + parts[1] + '0' * (6 - len(parts[2])) + parts[2]
            self.lang_claims.append(BotClaim('p244', lccn, [page2source(page)]))

    def getVIAF(self, **kwargs):
        self.getString(property_='p214', pattern="\d+", **kwargs)
        #self.lang_claims.append(BotClaim('p214', arg, [page2source(page)]))
    
    def getGND(self, **kwargs):
        self.getString(property_='p227', 
                       pattern="(1|10)\d{7}[0-9X]|[47]\d{6}-\d|[1-9]\d{0,7}-[0-9X]|3\d{7}[0-9X]",
                       **kwargs)
        #self.lang_claims.append(BotClaim('p227', arg, [page2source(page)]))
    
    def getBNF(self, arg, page, **kwargs):
        self.lang_claims.append(BotClaim('p268', arg, [page2source(page)]))
    
    def getULAN(self, arg, page, **kwargs):
        self.lang_claims.append(BotClaim('p245', arg, [page2source(page)]))
    
    def getSUDOC(self, **kwargs):
        self.getString(property_='p269',
                       pattern="\d\d\d\d\d\d\d\d[\dX]?",
                       **kwargs)
        #self.lang_claims.append(BotClaim('p269', arg, [page2source(page)]))
             
    def getDescription(self, arg, page, **kwargs):
        text = re.sub("\[\[([^\|]*?)\]\]", "\g<1>", arg)
        text = re.sub("\[\[.*?\|(.*?)\]\]", "\g<1>", text)
        text = re.sub("'''(.*?)'''", "\g<1>", text)
        text = re.sub("''(.*?)''", "\g<1>", text)
        if not page.site.lang in self.descriptions:
            self.new_descriptions[page.site.lang] = text
    
    def getBirthPlace(self, **kwargs):
        self.getPlace(property_='p19', **kwargs)

    def getDeathPlace(self, **kwargs):
        self.getPlace(property_='p20', **kwargs)
    
    def getPlace(self, arg, page, property_, **kwargs):
        links = re.findall("(?<=\[\[).*?(?=\||\])", arg)
        locations = []
        for link in links:
            page = pywikibot.Page(page.site, link)
            item = pywikibot.ItemPage.fromPage(page)
            if item.exists():
                locations.append(item)
        if len(locations):
            self.lang_claims.append(BotClaim(property_,
                                             locations[0],
                                             [page2source(page)]))
    
    def getTYP_de(self, arg, page, **kwargs):
        if arg in TYP_de:
            self.lang_claims.append(BotClaim('p107', 
                                             ItemPage(wikidata,
                                                      TYP_de[arg]),
                                             [page2source(page)]))
    
    def getTYPE_fr(self, arg, page, **kwargs):
        if arg in TYPE_fr:
            self.lang_claims.append(BotClaim('p107',
                                             ItemPage(wikidata,
                                                      TYPE_fr[arg]),
                                             [page2source(page)]))
    
    def getCommonscat(self, arg, page, **kwargs):
        if not arg:
            arg = page.title()
        self.lang_claims.append(BotClaim('p373',
                                         arg.replace('_', ' '),
                                         [page2source(page)]))
    
    def getCommonscat_fr(self, arg, page, **kwargs):
        if arg.startswith('Category:'):
            self.getCommonscat(arg[9:], page, **kwargs)
    
    def getBVKItem(self, arg, page, **kwargs):
        if arg in BVK_VARIANTS:
            self.lang_claims.append(BotClaim('p166', BVK_VARIANTS[arg], [page2source(page)]))
        else:
            print "*** Unknown BVK arg '%s' at '%s'" % (arg, page.title())
    
    def addBVKSource(self, arg, page, **kwargs):
        BUNDESANZEIGER_SOURCE["snaks"]["p433"]["datavalue"]["value"] = arg
        self.lang_claims[-1].new_sources.append(pywikibot.Claim.referenceFromJSON(BUNDESANZEIGER_SOURCE))