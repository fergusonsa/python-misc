# coding: utf-8
import sys, urllib.parse
from bs4 import BeautifulSoup
from urllib.request import urlopen
import SysOutRedirector

def getMaxLengthOfDictValuesForKeys(thisDict, keys):    
    lengths = [len(thisDict.get(key)) for key in keys if thisDict.get(key) != None]
    if len(lengths) == 0:
        lengths.append(0)
    return max(lengths) + 1

def getMaxLengthOfDictValuesForKeyInListOfDicts(dictList, keys):    
    lengths = [getMaxLengthOfDictValuesForKeys(thisDict, keys) for thisDict in dictList]
    if len(lengths) == 0:
        lengths.append([])
    return max(lengths)


def displayListings(postingsList):
    print('\nFound {} postings!'.format(len(postingsList)))
    if len(postingsList) > 0:
        padCompany = getMaxLengthOfDictValuesForKeyInListOfDicts(postingsList, ['company'])
        padTitle = getMaxLengthOfDictValuesForKeyInListOfDicts(postingsList, ['title'])
        padLocation = getMaxLengthOfDictValuesForKeyInListOfDicts(postingsList, ['locale'])
        print('padCompany: {}    padTitle: {}   padLocation: {}'.format(padCompany, padTitle, padLocation))
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
    items = soup.findAll('div', {'class':'serp-result-content'})
    postingsList = []
    # if len(items) > 0:
        # print('------')
        # print(items[0])       
        # print('------\n')
                
    for it in items:
            
        # topEl = it.find('a', {'data-automation':'automation-job-url'})
        el = it.find('h3')
        if el:
            el2 = el.find('a')
            if el2:
                title = el2.string  
                url = el2['href']
            else:
                title = 'unknown - cannot find title h3 a'
                url = 'unknown url'
        else:
            title = 'unknown - cannot find title h3'
            url = 'unknown url'

        el = it.find('ul', {'class':'list-inline details'})
        if el:
            el2 = el.find('li', {'class':'employer'})
            if el2:
                el3 = el.find('a')
                if el3:
                    company = el3.string
                else:
                    company = 'unknown - cannot find employer a'
            else:
                company = 'unknown - cannot find hiringOrganization'
            el2 = el.find('li', {'class':'location'})
            if el2:
                locale = el2.get_text()
            else:
                locale = 'unknown - cannot find jobLocation'            
        else:
            print('Unable to get ul element for this item: {}'.format(str(it)))
            company = 'Uknown company!'
            location = 'unknown location'
                        
        # print(locale)
        # print(company)
        # print(title)
        # print(url)
        # print('===')
        postingsList.append({'title':title, 'url':url, 'company':company, 'locale':locale})
    return postingsList
    
def buildUrl(urlSchema, netLoc,  urlPath, urlArguments, startIndex):
    # urlArguments['pn'] = startIndex    
    # queryString = urllib.parse.urlencode(urlArguments)
    location = urlArguments['for_loc']
    restPath = 'jobs/q-%28java+OR+devops+OR+python%29-jtype-Contracts-sort-date-l-{}-startPage-{}-limit-10-jobs'.format(location, startIndex)
    url = urllib.parse.urlunparse((urlSchema, netLoc, restPath, '', '', '')) 
    return url
    
## ------------------------------------------------------------------------------------------------------    
def main(args):
    # https://www.dice.com/jobs/advancedResult.html?for_one=java+devops+python&for_loc=BC&limit=10&radius=100&sort=date&jtype=Contracts
    # https://www.dice.com/jobs/q-%28java+OR+devops+OR+python%29-jtype-Contracts-sort-date-l-BC-startPage-2-limit-10-jobs.html
    # https://www.dice.com/jobs/advancedResult.html?for_one=java+devops+python&for_loc=ON&limit=10&radius=100&sort=date&jtype=Contracts
    # https://www.dice.com/jobs/q-%28java+OR+devops+OR+python%29-jtype-Contract%20Corp-To-Corp-sort-date-l-ON-startPage-1-limit-10-jobs.html
    # https://www.dice.com/jobs/q-%28java+OR+devops+OR+python%29-jtype-Contract%20Corp-To-Corp-sort-date-l-ON-startPage-3-limit-10-jobs.[html
    # https://www.dice.com/jobs/advancedResult.html?for_one=java+devops+python&for_loc=Vancouver%2C+BC&radius=100&sort=relevance&jtype=Contracts
    # https://www.dice.com/jobs/advancedResult.html?for_one=java+devops+python&for_loc=Canada&limit=50&radius=100&sort=date&jtype=Contracts
    netLoc = 'www.dice.com'
    locationList = ['BC', 'AB', 'SK', 'MB', 'ON', 'QC', 'NB', 'PE', 'NS', 'NL']
    sysOutRedirect = SysOutRedirector.SysOutRedirector(path='/workspaces/reports/', filePrefix='ScrapeWorkopolis-{}'.format(netLoc))
    urlSchema = 'http'
    urlPath = 'jobs/advancedResult.html'
    fullPostingsList = []
    for location in locationList: 
        startIndex = 1
        urlArguments = {
                        'for_one':'java devops python',
                        'for_loc':location,
                        'limit':10,
                        'radius':100,
                        'sort':'date',
                        'jtype':'Contracts' }
        url = buildUrl(urlSchema, netLoc, urlPath, urlArguments, startIndex)
        print('\nHere is the initial URL to be "scraped": {}\n'.format(url))
        pageHtml = getHtmlPage(url)
        postingsList = parseHtmlPage(pageHtml, netLoc)
        fullPostingsList.extend(postingsList)
        while len(postingsList) >= 10:
            
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