# coding: utf-8
import sys, urllib.parse
from bs4 import BeautifulSoup
from urllib.request import urlopen
import SysOutRedirector

def getMaxLengthOfDictValuesForKeys(thisDict, keys):    
    lengths = [len(thisDict[key]) for key in keys]
    if len(lengths) == 0:
        lengths.append(0)
    return max(lengths)

def getMaxLengthOfDictValuesForKeyInListOfDicts(dictList, keys):    
    lengths = [getMaxLengthOfDictValuesForKeys(thisDict, keys) for thisDict in dictList]
    if len(lengths) == 0:
        lengths.append(0)
    return max(lengths)


def displayListings(postingsList):
    print('\nFound {} postings!'.format(len(postingsList)))
    padCompany = getMaxLengthOfDictValuesForKeyInListOfDicts(postingsList, ['company'])
    padTitle = getMaxLengthOfDictValuesForKeyInListOfDicts(postingsList, ['title'])
    padLocation = getMaxLengthOfDictValuesForKeyInListOfDicts(postingsList, ['locale'])
    print('\n\n{0:{4}}  {1:{5}}  {2:{6}}  {3}'.format('Location', 'Organization', 'Job Title', 'Url', padLocation, padCompany, padTitle))
    for i in postingsList:
        # try:
            # print('{0.company!s:{1}}  {0.title!s:{2}}  {0.locale!s:{3}}  {0.url!s}'.format(i, padCompany, padTitle, padLocation))
        # except:
            try:
                # typ, val, tb = sys.exc_info()
                # print('{0!s:{4}}  {1!s:{5}}  {2!s:{6}}  {3!s}         XX {7}  {8}'.format(i.get('company'), i.get('title'), i.get('locale'), i.get('url'), padCompany, padTitle, padLocation, typ, val))
                print('{0!s:{4}}  {1!s:{5}}  {2!s:{6}}  {3!s}'.format(i.get('locale'), i.get('company'), i.get('title'), i.get('url'), padLocation, padCompany, padTitle))
            except:
                typ2, val2, tb2 = sys.exc_info()
                print('cannot print line! - Except type: {}  Val: {}'.format(typ2, val2))

def getHtmlPage(url):
    # print('getting URL "{}"'.format(url))
    pageFile = urlopen(url)
    pageHtml = pageFile.read()
    pageFile.close()
    return pageHtml
    
def parseHtmlPage(pageHtml, urlBase=''):
    soup = BeautifulSoup(pageHtml)
    items = soup.findAll('div', {'class':'row', 'itemtype':'http://schema.org/JobPosting'})
    postingsList = []
    # if len(items) > 0:
        # print('------')
        # print(items[0])       
        # print('------\n')
                
    for it in items:
            
        titleEl = it.find('a', {'itemprop':'title'})
        if titleEl:
            title = titleEl['title']
            if urlBase:
                url = 'http://{}{}'.format(urlBase, titleEl['href'])
            else:
                url = titleEl['href']
        else:
            print('Unable to get title for this item: {}'.format(str(it)))
            title = 'Uknown title!'
            url = 'unknown'
            
        try:
            el = it.find('span', {'itemprop':'hiringOrganization'})
            if el:
                el1 = el.find('span', {'itemprop':'name'})
                if el1:
                    company = el1.string
                else:
                    company = 'unknown - cannot find name'
            else:
                company = 'unknown - cannot find hiringOrg'
        except:
            typ, val, tb = sys.exc_info()
            print('Unable to get company for item: Error type: {}, val: {}'.format(type, val))
            company = 'unknown'
                        
        try:
            el = it.find('span', {'itemprop':'jobLocation'})
            if el:
                el1 = el.find('span', {'itemprop':'address'})
                if el1:
                    el2 = el1.find('span', {'itemprop':'addressLocality'})
                    if el2:
                        locale = el2.string  
                    else:
                        locale = 'unknown - cannot find locality'
                else:
                    locale = 'unknown - cannot find address'
            else:
                locale = 'unknown - cannot find jobLocation'
                
        except:
            locale = 'unknown'
        postingsList.append({'title':title, 'url':url, 'company':company, 'locale':locale})
    return postingsList
    
def buildUrl(urlSchema, netLoc,  urlPath, urlArguments, startIndex):
    urlArguments['start'] = startIndex    
    queryString = urllib.parse.urlencode(urlArguments)
    
    url = urllib.parse.urlunparse((urlSchema, netLoc, urlPath, '', queryString, '')) 
    return url
    
## ------------------------------------------------------------------------------------------------------    
def main(args):
    # netLoc = 'www.indeed.co.uk'
    # location = 'Scotland'
    netLoc = 'ca.indeed.com'
    location = 'Canada'
    sysOutRedirect = SysOutRedirector.SysOutRedirector(path='/workspaces/reports/', filePrefix='ScrapeIndeed-{}'.format(netLoc))
    # url = "http://ca.indeed.com/jobs?as_and=&as_phr=&as_any=java+devops&as_not=&as_ttl=&as_cmp=&jt=contract&st=&salary=&radius=25&l=Canada&fromage=any&limit=100&sort=&psf=advsrch"
    # url = "http://www.indeed.co.uk/jobs?as_and=&as_phr=&as_any=java+devops&as_not=&as_ttl=&as_cmp=&jt=contract&st=&salary=&radius=25&l=Scotland&fromage=any&limit=100&sort=&psf=advsrch"
    # http://www.indeed.co.uk/jobs?q=%28java+or+devops%29&l=Scotland&jt=contract&start=10
    urlSchema = 'http'
    urlPath = 'jobs'
    startIndex = 0
    urlArguments = {'q': '(java or devops)', 
                    'l': location,
                    'jt': 'contract',
                    'start': startIndex }
    url = buildUrl(urlSchema, netLoc, urlPath, urlArguments, startIndex)
    print('\nHere is the initial URL to be "scraped": {}\n\n'.format(url))
    pageHtml = getHtmlPage(url)
    fullPostingsList = []
    postingsList = parseHtmlPage(pageHtml, netLoc)
    fullPostingsList.extend(postingsList)
    while len(postingsList) >= 10:
        startIndex += 10
        url = buildUrl(urlSchema, netLoc, urlPath, urlArguments, startIndex)
        pageHtml = getHtmlPage(url)
        postingsList = parseHtmlPage(pageHtml, netLoc)
        fullPostingsList.extend(postingsList)

    displayListings(fullPostingsList)
    sysOutRedirect.close()

if __name__ == "__main__":
    main(sys.argv)