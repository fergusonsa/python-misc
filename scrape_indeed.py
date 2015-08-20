# coding: utf-8
import sys
import urllib.parse
import os.path
import argparse
import requests
import re
import operator
from time import strftime
from bs4 import BeautifulSoup
from urllib.request import urlopen
import SysOutRedirector
import sqlite3 as sqlite

jobSiteDetails = {
    'ca.indeed.com': {
        'urlSchema': 'http',
        'netLoc': 'ca.indeed.com',
        'location': 'Canada',
        'urlPath': 'jobs',
        'jobTypeKey': 'jt',
        'pageIndexKey': 'start',
        'pageIndexType': 'postingCount',
        'loginUrl': 'http://ca.indeed.com/account/login',
        'nextUrl': '/',
        'username': None,
        'password': None,
        'parseInfo': {
            'numberJobsFound': {
                'element':'div',
                'criteria':{'id':'searchCount'},
                'regex': '^Jobs (?:[0-9,]+) to (?:[0-9,]+) of ([0-9,]+)$',
            },
            'parentElement':'div',
            'parentCriteria': {'class':'row', 'itemtype':'http://schema.org/JobPosting'},
            'fields' : {
                'title': {
                    'element':'a',
                    'criteria':{'itemprop':'title'},
                    'property': 'title',
                },
                'id' : {
                    'element':'parent',
                    'criteria':{},
                    'property': 'data-jk',
                },
                'locale' : {
                    'element':'span',
                    'criteria':{'itemprop':'addressLocality'},
                },
                'company' : {
                    'element':'',
                    'criteria':{},
                },
                'url' : {
                    'element':'a',
                    'criteria': {'itemprop':'title'},
                    'property': 'href',
                },
            },
        }
    },
    'www.simplyhired.ca':   {
        'urlSchema': 'http',
        'netLoc': 'www.simplyhired.ca',
        'location': 'Ontario',
        'urlPath': 'search',
        'jobTypeKey': 'fjt',
        'pageIndexKey': 'pn',
        'pageIndexType': 'pageCount',
        'loginUrl': 'http://www.simplyhired.ca/account/signin',
        'nextUrl': '',
        'username': None,
        'password': None,
        'parseInfo': {
            'parentElement':'li',
            'parentCriteria': {'class':'result'},
            'fields' : {
                'title': {
                    'element':'a',
                    'criteria':{'itemprop':'title'},
                },
                'id' : {
                    'element':'parent',
                    'criteria':{},
                    'property': 'id',
                    'regex': '(?mx)^r.(.*):[0-9]$',
                },
                'locale' : {
                    'element':'span',
                    'criteria':{'itemprop':'address'},
                },
                'company' : {
                    'element':'h4',
                    'criteria':{'class':'company', 'itemprop':'name'},
                },
                'url' : {
                    'element':'a',
                    'criteria': {'itemprop':'title'},
                    'property': 'href',
                },
            },
        }
    },
}

def executeUpdateSQL(sqlQuery, databaseName=None):
    '''
    Parameters:

    '''
    resList = []
    con = sqlite.connect(databaseName)

    try:
        with con:
            cursor = con.cursor()
            cursor.executescript(sqlQuery)

            con.commit()
    except Exception as e:
        print( "Something went wrong:")
        print( e)

def getResultDictForSQL(sqlQuery, paramsDict={}, databaseName=None):
    '''
    Parameters:

    '''
    resList = []
    con = sqlite.connect(databaseName)

    if paramsDict == None:
        paramsDict = {}

    with con:
        # con.create_function("instr", 2, instr)
        con.row_factory = sqlite.Row
        cursor = con.cursor()
        if len(paramsDict.keys()) > 0:
            cursor.execute(sqlQuery, paramsDict)
        else:
            cursor.execute(sqlQuery)

        row = cursor.fetchone()
        while row:
            rowList = {}
            for col in row.keys():
                rowList[col] = row[col]
            resList.append(rowList)
            row = cursor.fetchone()
    return resList

def runSQLScriptFile(scriptfilename, dbfilename):
    try:
        print("\nOpening DB")
        connection = sqlite.connect(dbfilename)
        cursor = connection.cursor()

        print("Reading Script...")
        scriptFile = open(scriptfilename, 'r')
        script = scriptFile.read()
        scriptFile.close()

        print("Running Script...")
        cursor.executescript(script)

        connection.commit()
        print("Changes successfully committed\n")

    except Exception as e:
        print( "Something went wrong:")
        print( e)
    finally:
        print("\nClosing DB")
        connection.close()

def ensureDatabaseTablesAlreadyCreated(databaseName):
    # Get the list of required tables from the available C:\workspaces\scripts\AppInfoDatabase\*.sql files
    path = os.path.dirname(databaseName)
    reqTableNames = [os.path.splitext(f)[0] for f in os.listdir(path) if f.endswith('.sql')]
    # print(reqTableNames)

    con = sqlite.connect(databaseName)
    cursor = con.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = map(lambda t: t[0], cursor.fetchall())
    availableTables = []
    for table in tables:
        availableTables.append(table)

    # print('Number of tables in database: {}'.format(len(availableTables)))
    # print(availableTables)

    # Find out if any of the required tables are missing
    missingTables = set(reqTableNames).difference(set(availableTables))
    for missingTable in missingTables:
        sqlFilePath = os.path.join(path, '{}.sql'.format(missingTable))
        print('Creating the missing database table {} in the database {} using the SQL file {}.'.format(missingTable, databaseName, sqlFilePath))
        runSQLScriptFile(sqlFilePath, databaseName)

def savePostingsToDB(fullPostingsList, dbName):
    con = sqlite.connect(dbName)
    insertedCount = 0
    alreadyThereCount = 0
    with con:
        con.row_factory = sqlite.Row
        sqlQuery = 'INSERT INTO JobPostings (Id, URL, Title, Company, Locale) VALUES (?, ?, ?, ?, ?) ' #,
        for posting in fullPostingsList:
            cursor = con.cursor()
            try:
                cursor.execute(sqlQuery, (posting['id'], posting['url'], posting['title'], posting['company'], posting['locale'], ))
                con.commit()
                insertedCount += 1
            except sqlite.IntegrityError as e:
                # print('Unable to insert posting id: "{}", url: "{}", title: "{}", company: "{}", locale: "{}" as the Id, URL, Title, Company, Locale values are not unique.'.format(posting['id'], posting['url'], posting['title'], posting['company'], posting['locale']))
                alreadyThereCount += 1
                fullPostingsList.remove(posting)

    print('\nInserted {} of the {} found postings into the database.  {} postings were already there. \n'.format(insertedCount, len(fullPostingsList), alreadyThereCount))

    if insertedCount > 0:
        executeUpdateSQL("update JobPostings set province = trim(substr(Locale, instr(Locale, ',')+1)) where Province is null;", dbName)
        executeUpdateSQL("update JobPostings set City = trim(substr(Locale, 1, instr(Locale, ',')-1)) where City is null;", dbName)
        executeUpdateSQL("insert into RecruitingCompanies(Name, DateInserted) select Company as Name, min(insertedDate) as DateInserted from JobPostings left join RecruitingCompanies on Company = Name where Name is null group by Company order by Company", dbName)

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
    print('\nFound {} postings!\n\n'.format(len(postingsList)))
    if len(postingsList) > 0:
        padCompany = getMaxLengthOfDictValuesForKeyInListOfDicts(postingsList, ['company'])
        padTitle = getMaxLengthOfDictValuesForKeyInListOfDicts(postingsList, ['title'])
        padLocation = getMaxLengthOfDictValuesForKeyInListOfDicts(postingsList, ['locale'])
        print('{0:{4}}  {1:{5}}  {2:{6}}  {3}'.format('Location', 'Organization', 'Job Title', 'Url', padLocation, padCompany, padTitle))
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

def generateHtmlPage(dirPath, netloc, searchTermsList, postingsList):
    fileName = 'FoundJobPostings-{}-{}.html'.format(netloc, strftime("%Y%m%d.%H%M%S"))
    filenamePath = os.path.abspath(os.path.join(dirPath, fileName))
    # Sort the list of postings by the locale
    sortedPostings = sorted(postingsList, key=lambda k: k['locale'])
    with open(filenamePath, 'w') as myFile:
        myFile.write('<html>\n<body>\n<p><h2>Search Site:</h2> {}</p>\n<p><h2>Search Terms:</h2>\n<hr\><ul>\n'.format(netloc))
        for st in searchTermsList:
            myFile.write('<li>{}</li>\n'.format(st))
        myFile.write('</ul></p>\n\n')

        for posting in sortedPostings:
            try:
                linkElems = posting['elem'].findAll('a')
                for linkElem in linkElems:
                    if not linkElem['href'].startswith('http'):
                        if linkElem['href'].startswith('/'):
                            linkElem['href'] = 'http://' + netloc + linkElem['href']
                        else:
                            linkElem['href'] = 'http://' + netloc + '/' + linkElem['href']
                myFile.write(str(posting['elem']))
            except:
                typ2, val2, tb2 = sys.exc_info()
                print('cannot print elem to html file! - Except type: {}  Val: {} - Id: {} url: {}'.format(typ2, val2, posting['id'], posting['url']))
            myFile.write('\n\n<hr/>\n\n')
        myFile.write('\n</body>\n</html>')
    print('\nWrote {} postings to the html file {}\n'.format(len(postingsList), filenamePath))

def getHtmlPage(url):
    # print('getting URL "{}"'.format(url))
    pageFile = urlopen(url)
    pageHtml = pageFile.read()
    pageFile.close()
    return pageHtml

def parseHtmlPage2(pageHtml, jobsiteDetails, knownPostingIdsList=[]):
    '''
            'numberJobsFound': {
                'element':'div',
                'criteria':{'id':'searchCount'},
                'regex': '^Jobs (?:[0-9,]+) to (?:[0-9,]+) of ([0-9,]+)$',
            },
    '''
    # print('size of known postings list: {}'.format(len(knownPostingIdsList)))
    soup = BeautifulSoup(pageHtml)
    totalNumberJobsFound = 'Unknown'
    numJobsDetails = jobsiteDetails['parseInfo'].get('numberJobsFound')
    if numJobsDetails:
        numberPostingsElem = soup.find(numJobsDetails['element'], numJobsDetails['criteria'])
        if numberPostingsElem:
            value = None
            prop = numJobsDetails.get('property')
            if prop:
                value = numberPostingsElem[prop]
            elif numberPostingsElem.text:
                value = numberPostingsElem.text
            else:
                value = numberPostingsElem.string

            if numJobsDetails.get('regex'):
                value = re.sub(numJobsDetails['regex'], r"\1", value)
            totalNumberJobsFound = int(value.replace(',', ''))

    items = soup.findAll(jobsiteDetails['parseInfo']['parentElement'], jobsiteDetails['parseInfo']['parentCriteria'])
    postingsList = {}
    # print('Found {} items on page.'.format(len(items)))


    for it in items:
        postingInfo = {}
        postingInfo['elem'] = it
        for field in jobsiteDetails['parseInfo']['fields'].keys():
            fieldInfo = jobsiteDetails['parseInfo']['fields'][field]
            # print('looking for field {}'.format(field))
            try:
                value = None
                elem = None
                prop = None
                elemType = fieldInfo['element']
                if elemType == 'parent':
                    elem = it
                else:
                    elem = it.find(elemType, fieldInfo.get('criteria'))
                prop = fieldInfo.get('property')
                if prop:
                    value = elem[prop]
                elif elem.text:
                    value = elem.text
                else:
                    value = elem.string

                if fieldInfo.get('regex'):
                    value = re.sub(fieldInfo['regex'], r"\1", value)

                if value:
                    postingInfo[field] = value.strip()
            except Exception as e:
                typ, val, tb = sys.exc_info()
                print('Unable to parse posting {} information for item: \n\n{} \n\nError type: {}, val: {}'.format(field, it, type, val))

        if postingInfo.get('id') and postingInfo.get('id') not in knownPostingIdsList:
            postingsList[postingInfo['id']] = postingInfo
            knownPostingIdsList.append(postingInfo['id'])
            print('Adding item details for id "{}" to list'.format(postingInfo['id']))
        elif postingInfo.get('id') in knownPostingIdsList:
            print('Item ID "{}" is already in the list of {} known posting ids'.format(postingInfo['id'], len(knownPostingIdsList)))
        else:
            print('Unknown item not being added to list')
    return postingsList, len(items), totalNumberJobsFound

def parseHtmlPage(pageHtml, urlBase='', knownPostingIdsList=[]):
    '''
    For ca.indeed.com website pages, the criteria for each item is as follows:
        parent div:     'div', {'class':'row', 'itemtype':'http://schema.org/JobPosting'}
        title:          'a', {'itemprop':'title'} 'title' property
        url:            'a', {'itemprop':'title'} 'href' property
        company:        'span', {'itemprop':'hiringOrganization'}, 'span', {'itemprop':'name'}, string value
        locale:         'span', {'itemprop':'jobLocation'}, 'span', {'itemprop':'address'}, 'span', {'itemprop':'addressLocality'}, string value
        id:             'a', {'itemprop':'title'} part 2 of 'href' property when split('=')

    For www.simplyhired.ca website pages, the criteria for each item is as follows:
        parent element: 'li', {'class':'result'op'}, 'p', {'class':'serp-title', 'itemprop':'title'}, 'span', {'class':'serp-title-text'} string valu
        company:        'h4', {'class':'company', 'itemprop':'name'}, string value
        locale:         'span', {'itemprop':'jobLocation'}, 'span', {'itemprop':'address'}, string value
        id:             parent li id property

    '''

    soup = BeautifulSoup(pageHtml)
    items = []
    if urlBase == 'ca.indeed.com' or urlBase == '':
        # items = soup.findAll('div', {'class':'row', 'itemtype':'http://schema.org/JobPosting'})
        items = soup.findAll('div', {'itemtype':'http://schema.org/JobPosting'})
    elif urlBase == 'www.simplyhired.ca':
        items = soup.findAll('li', {'class':'result'})

    postingsList = {}
    # if len(items) > 0:
        # print('------')
        # print(items[0])
        # print('------\n')

    for it in items:

        id = None
        title = None
        url = None
        company = None
        locale = None

        if urlBase == 'ca.indeed.com' or urlBase == '':
            titleEl = it.find('a', {'itemprop':'title'})
            if titleEl:
                title = titleEl['title']
                if urlBase:
                    url = 'http://{}{}'.format(urlBase, titleEl['href'])
                else:
                    url = titleEl['href']
                id = titleEl['href'].split('=')[1]
                if id in knownPostingIdsList:
                    continue
            else:
                print('Unable to get title for this item: {}'.format(str(it)))
                title = 'Uknown title!'
                url = 'unknown'

            try:
                el = it.find('span', {'itemprop':'hiringOrganization'})
                if el:
                    el1 = el.find('span', {'itemprop':'name'})
                    if el1:
                        company = el1.string.strip()
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
        elif urlBase == 'www.simplyhired.ca':
            id = it['id'][2:-2]
            titleEl = it.find('a', {'itemprop':'title'})
            if titleEl:
                title = titleEl.text
                if urlBase:
                    url = 'http://{}{}'.format(urlBase, titleEl['href'])
                else:
                    url = titleEl['href']
            companyEl = it.find('h4', {'class':'company', 'itemprop':'name'})
            if companyEl:
                company = companyEl.text
            localeEl = it.find('span', {'itemprop':'address'})
            locale = localeEl.text.replace('\n', '').strip()

        if id:
            postingsList[id] = {'title':title, 'url':url, 'company':company, 'locale':locale, 'id':id, 'elem': it}
    return postingsList, len(items)

def buildUrl(urlSchema, netLoc,  urlPath, urlArguments, startIndex):
    urlArguments['start'] = startIndex
    queryString = urllib.parse.urlencode(urlArguments)

    url = urllib.parse.urlunparse((urlSchema, netLoc, urlPath, '', queryString, ''))
    return url

def sort_by_subdict(dictionary, subdict_key):
    return sorted(dictionary.items(), key=lambda k_v: k_v[1][subdict_key])

def isSmallListInBigList(bigList, smallList):

    for item in smallList:
        if item not in bigList:
            return False
    return True

def loginToWebSite(session, jobSiteDetailInfo):
    if jobSiteDetailInfo['username'] and jobSiteDetailInfo['password']:
        login_data = dict(username=jobSiteDetailInfo['username'], password=jobSiteDetailInfo['password'])
        if jobSiteDetailsInfo['nextUrl']:
            login_data['next'] = jobSiteDetailsInfo['nextUrl']

        session.get(jobSiteDetailsInfo['loginUrl'], verify=False)
        session.post(jobSiteDetailsInfo['loginUrl'], data=login_data, headers={"Referer":"HOMEPAGE"})

def getJobPostingsFromSiteForMultipleSearchTerms(jobSiteDetailsInfo, searchTermsList, expectedPostingsPerPage=10,maxPages=100, minPages=10):
    fullPostingsList = {}
    session = requests.Session()
    if jobSiteDetailsInfo['urlSchema'] == 'https':
        loginToWebsite(session, jobSiteDetailsInfo)

    for searchTerm in searchTermsList:
        fullPostingsList[searchTerm] = getJobPostingsFromSite(jobSiteDetailsInfo, searchTerm, expectedPostingsPerPage=expectedPostingsPerPage,maxPages=maxPages, minPages=minPages, session=session)
    session = None
    return fullPostingsList

def checkForMorePostings(numPostingsOnPage, expectedPostingsPerPage, numAllUniquePostingsFoundOnPage, numPostingsSiteFound, startIndex, maxPages, minPages):
    '''
    Checks the conditions for whether to check for more postings on the next page.


    '''
    if startIndex + expectedPostingsPerPage <= numPostingsSiteFound:
        return True
    elif numPostingsOnPage == expectedPostingsPerPage:
         if numAllUniquePostingsFoundOnPage > 0 and startIndex < expectedPostingsPerPage * (maxPages-1):
             return True
         elif startIndex < expectedPostingsPerPage * (minPages-1):
             return True
         else:
             return False
    else:
         return False

def getJobPostingsFromSite(jobSiteDetailsInfo, searchTerm, expectedPostingsPerPage=10,maxPages=100, minPages=4, session=None):
    fullPostingsList = {}
    if not session:
        session = requests.Session()

        if jobSiteDetailsInfo['urlSchema'] == 'https':
            loginToWebsite(session, jobSiteDetailsInfo)

    startIndex = 0
    urlArguments = {'q': searchTerm,
                    'l': jobSiteDetailsInfo['location'],
                    jobSiteDetailsInfo['jobTypeKey'] : 'contract',
                    'sort': 'date',
                    jobSiteDetailsInfo['pageIndexKey'] : 0,
                }

    url = '{}://{}/{}'.format(jobSiteDetailsInfo['urlSchema'], jobSiteDetailsInfo['netLoc'], jobSiteDetailsInfo['urlPath'])
    page = session.get(url, params=urlArguments, verify=False)
    print('\n\nHere is the initial URL to be "scraped": {}\n'.format(page.url))

    postingsList, numPostingsOnPage, initialTotalNumberJobsFound = parseHtmlPage2(page.text, jobSiteDetailsInfo, list(fullPostingsList.keys()))
    print('Found {} new of {} postings of {} from url {}'.format(len(postingsList), numPostingsOnPage, initialTotalNumberJobsFound, page.url))
    fullPostingsList.update(postingsList)
    # while numPostingsOnPage == expectedPostingsPerPage and ((len(postingsList) > 0 and startIndex < expectedPostingsPerPage * (maxPages-1)) or startIndex < expectedPostingsPerPage * (minPages-1)):
    while checkForMorePostings(len(postingsList), expectedPostingsPerPage, len(fullPostingsList.keys()), initialTotalNumberJobsFound, startIndex, maxPages, minPages):
        startIndex += expectedPostingsPerPage
        if jobSiteDetailsInfo['pageIndexType'] == 'pageCount':
            urlArguments[jobSiteDetailsInfo['pageIndexKey']] += 1
        else:
            urlArguments[jobSiteDetailsInfo['pageIndexKey']] = startIndex
        page = session.get(url, params=urlArguments, verify=False)
        postingsList, numPostingsOnPage, totalNumberJobsFound = parseHtmlPage2(page.text, jobSiteDetailsInfo, list(fullPostingsList.keys()))
        fullPostingsList.update(postingsList)
        print('Found {} new of {} postings of {} from url {}  Now {} postings found'.format(len(postingsList), numPostingsOnPage, totalNumberJobsFound, page.url, len(fullPostingsList)))
    return fullPostingsList

def testKeywordSearches(args):

    jobSiteDetailsInfo = jobSiteDetails['ca.indeed.com']

    sysOutRedirect = SysOutRedirector.SysOutRedirector(path='/workspaces/reports/', filePrefix='ScrapeIndeed-KeywordTests-{}'.format(jobSiteDetailsInfo['netLoc']))
    print('\nTesting Keyword Searchs for the {} website job posting searches.\n'.format(jobSiteDetailsInfo['netLoc']))
    searchTermsList = ['java', 'devops', 'python', 'java devops python', 'java or devops or python',]
    # searchTermsList = ['python', ]
    # urlSchemas = ['http', 'https']
    urlSchemas = ['http']
    # fullPostingsList = {}
    fullPostingsList = {}
    for urlSchema in urlSchemas:
        jobSiteDetailsInfo['urlSchema'] = urlSchema
        fullPostingsList[urlSchema] = getJobPostingsFromSiteForMultipleSearchTerms(jobSiteDetailsInfo, searchTermsList)

    print('\n\nResults found:\n')

    # diffs = {}
    sames = {}
    for urlSchema in urlSchemas:
        sames[urlSchema] = {}

        for searchTerm in searchTermsList:
            if searchTerm not in sames[urlSchema].keys():
                sames[urlSchema][searchTerm] = {}

            for otherSearchTerm in searchTermsList:
                if otherSearchTerm == searchTerm:
                    sames[urlSchema][searchTerm][otherSearchTerm] = '-'
                else:
                    stKeys = set(fullPostingsList[urlSchema][searchTerm].keys())
                    ostKeys = set(fullPostingsList[urlSchema][otherSearchTerm].keys())
                    sames[urlSchema][searchTerm][otherSearchTerm] = len(stKeys.intersection(ostKeys))

    if len(urlSchemas) > 1:
        urlSchema = 'diff'
        diffSchemasSames = {}
        for searchTerm in searchTermsList:
            if searchTerm not in diffSchemasSames.keys():
                diffSchemasSames[searchTerm] = {}

            stKeys = set(fullPostingsList[urlSchemas[0]][searchTerm].keys())
            ostKeys = set(fullPostingsList[urlSchemas[1]][searchTerm].keys())
            keysInBoth = stKeys.intersection(ostKeys)
            diffSchemasSames[searchTerm] = len(keysInBoth)

    print('\n\nHere is a listing of the number of same entries in each list:\n')

    print('Schema  Search Terms            Postings', end='')
    for searchTerm in searchTermsList:
        print('  {0:^24}'.format(searchTerm), end='')
    print()
    for urlSchema in urlSchemas:
        for searchTerm in searchTermsList:
            print('{2:10}  {0:^24}  {1:^8}  '.format(searchTerm, len(fullPostingsList[urlSchema][searchTerm]), urlSchema), end='')
            for st in searchTermsList:
                print('{0:^24}  '.format(sames[urlSchema][searchTerm][st]), end='')
            print()

    if len(urlSchemas) > 1:
        print('\n\nHere is a listing of the number of same entries in for the different schemas (logged in vs not):\n')
        print('Search Terms            Postings  Number Same Postinge'.format(searchTermsList))
        for searchTerm in diffSchemasSames.keys():
            print('{0:^24}  {1:^8}  {2:^24}'.format(searchTerm, len(fullPostingsList[urlSchema][searchTerm]), diffSchemasSames[searchTerm]))

    print('\n\n')

def login(args):
    loginUrl = 'http://ca.indeed.com/account/login'
    searchTerm = 'python'
    jobSiteDetailsInfo = jobSiteDetails['ca.indeed.com']
    with requests.Session() as c:

        if jobSiteDetailsInfo['urlSchema'] == 'https':
            loginToWebsite(session, jobSiteDetailsInfo)
        startIndex = 0
        urlArguments = {'q': searchTerm,
                        'l': jobSiteDetailsInfo['location'],
                        jobSiteDetailsInfo['jobTypeKey'] : 'contract',
                        'sort': 'date',
                        jobSiteDetailsInfo['pageIndexKey'] : 0,
                    }

        url = '{}://{}/{}'.format(jobSiteDetailsInfo['urlSchema'], jobSiteDetailsInfo['netLoc'], jobSiteDetailsInfo['urlPath'])

        page = c.get(url, params=urlArguments)
        print('\nHere is the initial URL to be "scraped": {}\n\n'.format(page.url))
        postingsList, numPostingsOnPage = parseHtmlPage2(page.text, jobSiteDetailsInfo)
        import pprint
        pp = pprint.PrettyPrinter(indent=4)
        pp.pprint(postingsList)
        newlist = sort_by_subdict(postingsList, 'locale')
        pp.pprint(newlist)
        generateHtmlPage('/workspaces/reports/', jobSiteDetailsInfo['netLoc'], [searchTerm], postingsList.values())

## ------------------------------------------------------------------------------------------------------
def main(args):
    searchTermsList = ['java', 'devops', 'python']
    netLoc = 'ca.indeed.com'
    location = 'Canada'
    urlPath = 'jobs'
    parser = argparse.ArgumentParser(description='Searches a job posting website for jobs with the desired search term(s), saves them to a db and creates an html file with links to each new posting.')
    parser.add_argument('--website', '-w', help='The website to search for job postings. Should be one of "*.indeed.com", "www.simplyhired.c*". Default is "{}"'.format(netLoc), default=netLoc)
    parser.add_argument('--path', '-p', help='The website path for searching for job postings. Default is "{}", which is for the "{}" website.'.format(urlPath, netLoc), default=urlPath)

    parser.add_argument('--search', '-s', help='The search term(s) to search for. Can be a list of terms separated by one or more spaces. Default is to search for each of these terms: "{}"'.format('", "'.join(searchTermsList)), nargs='*', default=searchTermsList)
    parser.add_argument('--location', '-l', help='The location or region to search for. Default is "{}"'.format(location), default=location)

    args = parser.parse_args()
    netLoc = args.website
    location = args.location
    searchTermsList = args.search
    urlPath = args.path

    dbName = 'c:\workspaces\jobPosting\jobPosting.db'
    sysOutRedirect = SysOutRedirector.SysOutRedirector(path='/workspaces/reports/', filePrefix='JobsSiteScrape-{}'.format(netLoc))

    fullPostingsList = getJobPostingsFromSite(jobSiteDetailsInfo, searchTermsList, maxPages=100, minPages=2)

    fullPostingsList = []
    urlSchema = 'http'
    for searchTerm in searchTermsList:
        startIndex = 0
        urlArguments = {'q': searchTerm,
                        'l': location,
                        'jt': 'contract',
                        'sort': 'date',
                        'start': startIndex }
        url = buildUrl(urlSchema, netLoc, urlPath, urlArguments, startIndex)
        print('\nHere is the initial URL to be "scraped": {}\n\n'.format(url))
        pageHtml = getHtmlPage(url)
        if not os.path.isfile(dbName):
            ensureDatabaseTablesAlreadyCreated(dbName)

        alreadyStoredPostingsRows = getResultDictForSQL('select distinct Id from JobPostings', None, dbName)
        alreadyStoredPostings = [it['Id'] for it in alreadyStoredPostingsRows]

        postingsList, numPostingsOnPage = parseHtmlPage(pageHtml, netLoc, alreadyStoredPostings)
        print('Found {} new postings to save from url {}!'.format(len(postingsList), url))
        fullPostingsList.extend(postingsList.values())
        while numPostingsOnPage == 10 and ((len(postingsList) > 0 and startIndex < 1000) or startIndex < 40):
            startIndex += 10
            url = buildUrl(urlSchema, netLoc, urlPath, urlArguments, startIndex)
            pageHtml = getHtmlPage(url)
            postingsList, numPostingsOnPage = parseHtmlPage(pageHtml, netLoc, alreadyStoredPostings)
            print('Found {} new postings to save from url {}!'.format(len(postingsList), url))
            fullPostingsList.extend(postingsList.values())

    if len(fullPostingsList) > 0:
        displayListings(fullPostingsList)
        savePostingsToDB(fullPostingsList, dbName)
        generateHtmlPage(sysOutRedirect.getReportDirectory(), netLoc, searchTermsList, fullPostingsList)

    print('\nScraped {} postings from {} with the location {}.\n'.format(len(fullPostingsList), netLoc, location))
    sysOutRedirect.close()

if __name__ == "__main__":
    if '--test' in sys.argv:
        login(sys.argv)
    elif '--test2' in sys.argv:
        testKeywordSearches(sys.argv)
    else:
        main(sys.argv)
