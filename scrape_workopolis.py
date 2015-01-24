# coding: utf-8
import sys, urllib.parse
from bs4 import BeautifulSoup
from urllib.request import urlopen
import SysOutRedirector

def getMaxLengthOfDictValuesForKeys(thisDict, keys):    
    lengths = [len(thisDict.get(key, '')) for key in keys]
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
    items = soup.findAll('article', {'itemtype':'http://schema.org/JobPosting'})
    postingsList = []
    # if len(items) > 0:
        # print('------')
        # print(items[0])       
        # print('------\n')
                
    for it in items:
            
        topEl = it.find('a', {'data-automation':'automation-job-url'})
        el = topEl.find('div', {'class':'sr-position'})
        if el:
            el2 = el.find('h5', {'itemprop':'title'})
            if el2:
                # print(el2)
                el3 = el2.find('span')
                if el3:
                    title = el3.string  
                else:
                    title = 'unknown - cannot find title span'
            else:
                title = 'unknown - cannot find title h5'
            el2 = el.find('h6', {'itemprop':'hiringOrganization'})
            if el2:
                company = el2.string
            else:
                company = 'unknown - cannot find hiringOrganization'
            el2 = el.find('p', {'itemprop':'jobLocation'})
            if el2:
                locale = el2.string
            else:
                locale = 'unknown - cannot find jobLocation'
            
            if urlBase:
                url = 'http://{}{}'.format(urlBase, topEl['href'])
            else:
                url = topEl['href']
        else:
            print('Unable to get sr-position element for this item: {}'.format(str(it)))
            title = 'Uknown title!'
            url = 'unknown'
            company = 'unknown'
            locale = 'unknown'
                        
        # print(locale)
        # print(company)
        # print(title)
        # print(url)
        print('===')
        postingsList.append({'title':title, 'url':url, 'company':company, 'locale':locale})
    return postingsList
    
def buildUrl(urlSchema, netLoc,  urlPath, urlArguments, startIndex):
    urlArguments['pn'] = startIndex    
    queryString = urllib.parse.urlencode(urlArguments)
    
    url = urllib.parse.urlunparse((urlSchema, netLoc, urlPath, '', queryString, '')) 
    return url
    
## ------------------------------------------------------------------------------------------------------    
def main(args):
    # http://www.workopolis.com/jobsearch/find-jobs?lk=java+devops&l=canada&cl=3&pt=9&lg=en&pn=1
    netLoc = 'www.workopolis.com'
    location = 'Canada'
    sysOutRedirect = SysOutRedirector.SysOutRedirector(path='/workspaces/reports/', filePrefix='ScrapeWorkopolis-{}'.format(netLoc))
    urlSchema = 'http'
    urlPath = 'jobsearch/find-jobs'
    startIndex = 1
    urlArguments = {'lk': 'java devops', 
                    'l': location,
                    'cl': '3',
                    'pt': '9',
                    'lg': 'en',
                    'lr': '50',
                    'pn': startIndex }
    url = buildUrl(urlSchema, netLoc, urlPath, urlArguments, startIndex)
    print('\nHere is the initial URL to be "scraped": {}\n'.format(url))
    pageHtml = getHtmlPage(url)
    fullPostingsList = []
    postingsList = parseHtmlPage(pageHtml, netLoc)
    fullPostingsList.extend(postingsList)
    while len(postingsList) >= 20:
        
        startIndex += 1
        url = buildUrl(urlSchema, netLoc, urlPath, urlArguments, startIndex)
        print('Just got {} posts. Here is the next URL to be "scraped": {}\n'.format(len(postingsList), url))
        pageHtml = getHtmlPage(url)
        postingsList = parseHtmlPage(pageHtml, netLoc)
        fullPostingsList.extend(postingsList)

    displayListings(fullPostingsList)
    sysOutRedirect.close()

if __name__ == "__main__":
    main(sys.argv)