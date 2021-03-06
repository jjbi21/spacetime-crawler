import logging
from datamodel.search.JjbiFlavioq_datamodel import JjbiFlavioqLink, OneJjbiFlavioqUnProcessedLink
from spacetime.client.IApplication import IApplication
from spacetime.client.declarations import Producer, GetterSetter, Getter
from lxml import html,etree
import re, os
from time import time
from uuid import uuid4
from urlparse import urljoin

from urlparse import urlparse, parse_qs
from uuid import uuid4

logger = logging.getLogger(__name__)
LOG_HEADER = "[CRAWLER]"
global d
d = {'n_urls': 0, 'sub_domains': {}, 'most_out_links': {'': 0}}

@Producer(JjbiFlavioqLink)
@GetterSetter(OneJjbiFlavioqUnProcessedLink)
class CrawlerFrame(IApplication):
    app_id = "JjbiFlavioq"

    def __init__(self, frame):
        self.app_id = "JjbiFlavioq"
        self.frame = frame


    def initialize(self):
        self.count = 0
        links = self.frame.get_new(OneJjbiFlavioqUnProcessedLink)
        if len(links) > 0:
            print "Resuming from the previous state."
            self.download_links(links)
        else:
            l = JjbiFlavioqLink("http://www.ics.uci.edu/")
            print l.full_url
            self.frame.add(l)

    def update(self):
        unprocessed_links = self.frame.get_new(OneJjbiFlavioqUnProcessedLink)
        if unprocessed_links:
            self.download_links(unprocessed_links)

    def download_links(self, unprocessed_links):
        for link in unprocessed_links:
            print "Got a link to download:", link.full_url
            downloaded = link.download()
            links = extract_next_links(downloaded)
            for l in links:
                if is_valid(l):
                    self.frame.add(JjbiFlavioqLink(l))

    def shutdown(self):
        print (
            "Time time spent this session: ",
            time() - self.starttime, " seconds.")
    
def extract_next_links(rawDataObj):
    outputLinks = []
    '''
    rawDataObj is an object of type UrlResponse declared at L20-30
    datamodel/search/server_datamodel.py
    the return of this function should be a list of urls in their absolute form
    Validation of link via is_valid function is done later (see line 42).
    It is not required to remove duplicates that have already been downloaded. 
    The frontier takes care of that.
    
    Suggested library: lxml
    '''
    if rawDataObj.http_code >= 400:
        return outputLinks

    tree = etree.HTML(rawDataObj.content)
    if tree!=None:
        links = tree.xpath('//a')
    else:
        links = []
    for link in links:
        if 'href' in link.attrib:
            #print("found link: ", type(link.attrib['href']))
            try:
                if not re.match("^(http|https)", link.attrib['href']):
                    outputLinks.append(urljoin(rawDataObj.url, link.attrib['href']).encode("utf-8"))
                #    print(outputLinks[-1])
                #    print("created absolute")
                else:
                    outputLinks.append(link.attrib['href'].encode("utf-8"))
                #    print(outputLinks[-1])
                #    print("came absolute)")
            except(UnicodeDecodeError):
                pass
    d['n_urls'] += 1
    url = urlparse(rawDataObj.url)
    sub = url.hostname.rpartition('.')[0].rpartition('.')[0].rpartition('.')[0]
    if sub in d['sub_domains'].keys():
        d['sub_domains'][sub] += 1
    else:
        d['sub_domains'][sub] = 1
    l = len(links)
    if l > d['most_out_links'].values()[0]:
        d['most_out_links'].popitem()
        d['most_out_links'][rawDataObj.url] = l

    if d['n_urls'] == 3000:
        fout = "analytics.txt"
        fo = open(fout, "w")
        for k, v in d.items():
            fo.write(str(k) + ' >>> ' + str(v) + '\n\n')
        fo.close()
    
    print d
    return outputLinks


def is_valid(url):
    '''
    Function returns True or False based on whether the url has to be
    downloaded or not.
    Robot rules and duplication rules are checked separately.
    This is a great place to filter out crawler traps.
    '''
    parsed = urlparse(url)
    if parsed.scheme not in set(["http", "https"]):
        return False
    try:
        if ".ics.uci.edu" in parsed.hostname \
            and not re.match(".*\.(css|js|bmp|gif|jpe?g|ico" + "|png|tiff?|mid|mp2|mp3|mp4"\
            + "|wav|avi|mov|mpeg|ram|m4v|mkv|ogg|ogv|pdf" \
            + "|ps|eps|tex|ppt|pptx|doc|docx|xls|xlsx|names|data|dat|exe|bz2|tar|msi|bin|7z|psd|dmg|iso|epub|dll|cnf|tgz|sha1" \
            + "|thmx|mso|arff|rtf|jar|csv"\
            + "|rm|smil|wmv|swf|wma|zip|rar|gz|pdf)$", parsed.path.lower()):
            if re.match("^.*calendar.*$", parsed.path) or re.match("^.*/[^/]{300,}$", parsed.path) or \
                    re.match("^.*?(/.+?/).*?\1.*$|^.*?/(.+?/)\2.*$", parsed.path):
                return False
            else:
                return True

    except TypeError:
        print ("TypeError for ", parsed)
        return False

