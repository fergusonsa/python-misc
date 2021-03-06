# coding: utf-8
import datetime
import sys
import urllib.parse
import os.path
import argparse
import pprint
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
                'element': 'div',
                'criteria': {'id': 'searchCount'},
                'regex': '^Jobs (?:[0-9,]+) to (?:[0-9,]+) of ([0-9,]+)$',
            },
            'parentElement': 'div',
            'parentCriteria': {'class': 'row',
                               'itemtype': 'http://schema.org/JobPosting'},
            'fields': {
                'title': {
                    'element': 'a',
                    'criteria': {'itemprop': 'title'},
                    'property': 'title',
                },
                'id': {
                    'element': 'parent',
                    'criteria': {},
                    'property': 'data-jk',
                },
                'locale': {
                    'element': 'span',
                    'criteria': {'itemprop': 'addressLocality'},
                },
                'company': {
                    'element': 'span',
                    'criteria': {'itemprop': 'hiringOrganization'},
                },
                'url': {
                    'element': 'a',
                    'criteria': {'itemprop': 'title'},
                    'property': 'href',
                },
                'postedDate': {
                    'element': 'span',
                    'criteria': {'class': 'date'},
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
            'numberJobsFound': {
                'element': 'h1',
                'criteria': {},
                'regex':
                'Showing (?:[0-9,]+)-(?:[0-9,]+) of ([0-9,]+) (?:[a-zA-Z ])*',
            },
            'parentElement': 'div',
            'parentCriteria': {'class': 'js-job'},
            'fields': {
                'title': {
                    'element': 'h2',
                    'criteria': {'itemprop': 'title'},
                },
                'id': {
                    'element': 'parent',
                    'criteria': {},
                    'property': 'id',
                    'regex': '(?mx)^r:(.*):[0-9]+$',
                },
                'locale': {
                    'element': 'span',
                    'criteria': {'itemprop': 'address'},
                },
                'company': {
                    'element': 'span',
                    'criteria': {'class': 'serp-company', 'itemprop': 'name'},
                },
                'url': {
                    'element': 'a',
                    'criteria': {'class': 'js-job-link'},
                    'property': 'href',
                },
                'postedDate': {
                    'element': 'span',
                    'criteria': {'class': 'serp-timestamp'},
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
        print("Something went wrong:")
        print(e)


def getResultDictForSQL(sqlQuery, paramsDict={}, databaseName=None):
    '''
    Parameters:

    '''
    resList = []
    con = sqlite.connect(databaseName)

    if not paramsDict:
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
        print("Something went wrong:")
        print(e)
    finally:
        print("\nClosing DB")
        connection.close()


def ensureDatabaseTablesAlreadyCreated(databaseName):
    ''' Get the list of required tables from the available
    # C:\workspaces\scripts\AppInfoDatabase\*.sql files
    '''
    path = os.path.dirname(databaseName)
    reqTableNames = [os.path.splitext(f)[0] for f in os.listdir(path)
                     if f.endswith('.sql')]
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
        print('Creating the missing database table ' +
              '{} in the database {} using the SQL file {}.'.format(
                    missingTable, databaseName, sqlFilePath))
        runSQLScriptFile(sqlFilePath, databaseName)


def savePostingsToDB(fullPostingsList, dbName):
    con = sqlite.connect(dbName)
    insertedCount = 0
    alreadyThereCount = 0
    with con:
        con.row_factory = sqlite.Row
        sqlQuery = ('INSERT INTO JobPostings (Id, URL, Title, Company, '
                    'Locale, SearchTerms, ElementHtml, postedDate) '
                    'VALUES (?, ?, ?, ?, ?, ?, ?, ?) ')
        for posting in fullPostingsList:
            cursor = con.cursor()
            try:
                cursor.execute(sqlQuery, (posting['id'], posting['url'],
                                          posting['title'],
                                          posting.get('company'),
                                          posting.get('locale'),
                                          posting['searchTerms'],
                                          posting['elem'].prettify(
                                                formatter="html"),
                                          posting.get('postedDate')))
                con.commit()
                insertedCount += 1
            except sqlite.InterfaceError as e:
                pp = pprint.PrettyPrinter()
                print(('Error with the parameters being supplied to the SQL. '
                       'Here is the posting to be entered:'))
                pp.pprint(posting)
                break
            except sqlite.IntegrityError as e:
                alreadyThereCount += 1
                fullPostingsList.remove(posting)

    print(('\nInserted {} of the {} found postings into the database.  {} '
           'postings were already there. \n').format(insertedCount,
                                                     len(fullPostingsList),
                                                     alreadyThereCount))

    if insertedCount > 0:
        executeUpdateSQL(("update JobPostings set province = "
                          "trim(substr(Locale, instr(Locale, ',')+1)) "
                          "where Province is null;"), dbName)
        executeUpdateSQL(("update JobPostings set City = "
                          "trim(substr(Locale, 1, instr(Locale, ',')-1)) "
                          "where City is null;"), dbName)
        executeUpdateSQL(("insert into RecruitingCompanies "
                          "(Name, DateInserted) select Company as Name, "
                          "min(insertedDate) as DateInserted "
                          "from JobPostings left join RecruitingCompanies "
                          "on Company = Name where Name is null "
                          "group by Company order by Company"), dbName)


def getRecentPostings(dbName):
    pastDate = (datetime.datetime.now() - datetime.timedelta(
                    days=4)).strftime('%Y-%m-%d')
    res = getResultDictForSQL(("select Id as id, URL as url, Title, Company "
                               "as company, Locale as locale, SearchTerms as"
                               " searchTerms, ElementHtml as elem, postedDate"
                               ", insertedDate from JobPostings where "
                               "postedDate > '{0}' and insertedDate > '{0}'"
                               ).format(pastDate), databaseName=dbName)
    print('Numbr of res returned: {}'.format(len(res)))
    # print(res[0])
    for item in res:
        item['elem'] = BeautifulSoup(item['elem'])
    postings = {item['id']: item for item in res}
    print('Numbr of postings returned: {}'.format(len(postings)))
    return postings

def getMaxLengthOfDictValuesForKeys(thisDict, keys):
    lengths = [len(thisDict.get(key)) if thisDict.get(key) else 0
               for key in keys]
    if len(lengths) == 0:
        lengths.append(0)
    return max(lengths)


def getMaxLengthOfDictValuesForKeyInListOfDicts(dictList, keys):
    lengths = [getMaxLengthOfDictValuesForKeys(thisDict, keys)
               for thisDict in dictList]
    if len(lengths) == 0:
        lengths.append(0)
    return max(lengths)


def displayListings(postingsList):
    print('\nFound {} postings!\n\n'.format(len(postingsList)))
    if len(postingsList) > 0:
        padCompany = getMaxLengthOfDictValuesForKeyInListOfDicts(
            postingsList, ['company'])
        padTitle = getMaxLengthOfDictValuesForKeyInListOfDicts(
            postingsList, ['title'])
        padLocation = getMaxLengthOfDictValuesForKeyInListOfDicts(
            postingsList, ['locale'])
        print('{0:{4}}  {1:{5}}  {2:{6}}  {3}'.format(
            'Location', 'Organization', 'Job Title', 'Url',
            padLocation, padCompany, padTitle))
        for i in postingsList:
            try:
                print('{0!s:{4}}  {1!s:{5}}  {2!s:{6}}  {3!s}'.format(
                    i.get('locale'), i.get('company'), i.get('title'),
                    i.get('url'), padLocation, padCompany, padTitle))
            except:
                typ2, val2, tb2 = sys.exc_info()
                print('cannot print line! - Except type: {}  Val: {}'.format(
                    typ2, val2))


def generateHtmlPage(dirPath, netloc, searchTermsList, postingsList):
    fileName = 'FoundJobPostings-{}-{}.html'.format(netloc,
                                                    strftime("%Y%m%d.%H%M%S"))
    filenamePath = os.path.abspath(os.path.join(dirPath, fileName))
    # Sort the list of postings by the locale
    sortedPostings = sorted(postingsList, key=lambda k: k['locale'])
    with open(filenamePath, 'w', encoding='utf-8') as myFile:
        myFile.write('<html>\n<head>\n<style>.job-tools-description { ')
        myFile.write('padding: 5px; }\n.job-tools-apply { ')
        myFile.write('padding: 5px; }\n.recent-date { font-weight: bold;')
        myFile.write('\ncolor: green; }\n.desired-location { ')
        myFile.write('font-weight: bold;\ncolor: green; }\n</style>\n')
        myFile.write('</head>\n<body>\n<p><h2>')
        myFile.write('Search Site:</h2> {}</p>\n'.format(netloc))
        myFile.write('<p><h2>Search Terms:</h2>\n<hr/><ul>\n')
        for st in searchTermsList:
            myFile.write('<li>{}</li>\n'.format(st))
        myFile.write('</ul></p>\n\n<hr/>\n\n')

        for posting in sortedPostings:
            try:
                for anch in posting['elem'].findAll('a'):
                    del(anch['onclick'])
                    del(anch['onmousedown'])
                myFile.write(('<ul><li>ID: {0}</li><li>Title: {1}</li><li>URL'
                              ': <a href="{2}">{2}</a></li><li>Company: {3}'
                              '</li><li>Location: <span class={6}>{4}</span>'
                              '</li><li>Posted Date: <span class={7}>{5}'
                              '</span></li></ul>\n').format(
                                    posting.get('id'),
                                    posting.get('title'),
                                    posting.get('url'),
                                    posting.get('company'),
                                    posting.get('locale'),
                                    posting.get('postedDate'),
                                    'desired-location' if False else '',
                                    'recent-date' if False else '',))
                myFile.write(str(posting['elem']))
            except:
                typ2, val2, tb2 = sys.exc_info()
                print(('cannot print elem to html file! - Except type: {}  '
                       'Val: {} - Id: {} url: {}').format(typ2, val2,
                                                          posting['id'],
                                                          posting['url']))
            myFile.write('\n\n<hr/>\n\n')
        myFile.write('\n</body>\n</html>')
    print('\nWrote {} postings to the html file {}\n'.format(len(postingsList),
                                                             filenamePath))


def convertAgoToDate(agoStr):
    value = re.sub('([0-9]+[+]?) (?:minute[s]?|hour[s]?|day[s]?) ago', r"\1",
                   agoStr)

    if 'minute' in agoStr:
        dt = (datetime.datetime.now() - datetime.timedelta(
                            minutes=int(value))).strftime('%Y-%m-%d %H:%M:%S')
    elif 'hour' in agoStr:
        dt = (datetime.datetime.now() - datetime.timedelta(
                            hours=int(value))).strftime('%Y-%m-%d %H:%M:%S')
    elif 'day' in agoStr:
        if value == '30+':
            dt = 'over 30 days old'
        else:
            dt = (datetime.datetime.now() - datetime.timedelta(
                            days=int(value))).strftime('%Y-%m-%d %H:%M:%S')
    else:
        dt = 'unknown'
    return dt


def parseHtmlPage2(pageHtml, jobsiteDetails, searchTerms='',
                   knownPostIds=[]):
    '''
            'numberJobsFound': {
                'element':'div',
                'criteria':{'id':'searchCount'},
                'regex': '^Jobs (?:[0-9,]+) to (?:[0-9,]+) of ([0-9,]+)$',
            },
    '''
    soup = BeautifulSoup(pageHtml)
    totalNumberJobsFound = -1
    numJobsDetails = jobsiteDetails['parseInfo'].get('numberJobsFound')
    if numJobsDetails:
        numberPostingsElem = soup.find(numJobsDetails['element'],
                                       numJobsDetails['criteria'])
        if numberPostingsElem:
            value = None
            prop = numJobsDetails.get('property')
            if prop:
                value = numberPostingsElem[prop]
            elif hasattr(numberPostingsElem, 'text'):
                value = numberPostingsElem.text
            else:
                value = numberPostingsElem.string

            if numJobsDetails.get('regex'):
                value = re.sub(numJobsDetails['regex'], r"\1", value)
            totalNumberJobsFound = int(value.replace(',', ''))

    items = soup.findAll(jobsiteDetails['parseInfo']['parentElement'],
                         jobsiteDetails['parseInfo']['parentCriteria'])
    postingsList = {}

    for it in items:
        postingInfo = {'elem': it, 'searchTerms': searchTerms}
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
                elif hasattr(elem, 'text'):
                    value = elem.text
                elif elem:
                    value = elem.string

                if fieldInfo.get('regex'):
                    value = re.sub(fieldInfo['regex'], r"\1", value)

                if value:
                    postingInfo[field] = re.sub(r"^\s+|\s+$|\s+(?=\s)", "",
                                                value)
            except Exception as e:
                typ, val, tb = sys.exc_info()
                print(('Unable to parse posting {} information for item: '
                       '\n\n{} \n\nError type: {}, val: {}').format(field, it,
                                                                    typ, val))

        if postingInfo.get('id') and postingInfo.get('id') not in knownPostIds:
            if postingInfo.get('postedDate'):
                postingInfo['postedDate'] = convertAgoToDate(
                                                postingInfo['postedDate'])

            if postingInfo.get('url'):
                postingInfo['url'] = 'http://{}{}'.format(
                        jobsiteDetails['netLoc'], postingInfo['url'])
            if postingInfo.get('elem'):
                linkElems = postingInfo['elem'].findAll('a')
                for linkElem in linkElems:
                    if not linkElem['href'].startswith('http'):
                        if linkElem['href'].startswith('/'):
                            linkElem['href'] = 'http://{}{}'.format(
                                    jobsiteDetails['netLoc'], linkElem['href'])
                        else:
                            linkElem['href'] = 'http://{}/{}'.format(
                                    jobsiteDetails['netLoc'], linkElem['href'])

            postingsList[postingInfo['id']] = postingInfo
            knownPostIds.append(postingInfo['id'])
            print(('Adding item details for id "{}" to list with posted Date '
                   '{}').format(postingInfo['id'],
                                postingInfo.get('postedDate')))
        elif postingInfo.get('id') in knownPostIds:
            print(('Item ID "{}" is already in the list of {} known posting '
                   'ids').format(postingInfo['id'], len(knownPostIds)))
        else:
            print('Unknown item not being added to list')
    return postingsList, len(items), totalNumberJobsFound


def sort_by_subdict(dictionary, subdict_key):
    return sorted(dictionary.items(), key=lambda k_v: k_v[1][subdict_key])


def loginToWebSite(session, jobSiteDetailInfo):
    if jobSiteDetailInfo['username'] and jobSiteDetailInfo['password']:
        login_data = dict(username=jobSiteDetailInfo['username'],
                          password=jobSiteDetailInfo['password'])
        if jobSiteDetailsInfo['nextUrl']:
            login_data['next'] = jobSiteDetailsInfo['nextUrl']

        session.get(jobSiteDetailsInfo['loginUrl'], verify=False)
        session.post(jobSiteDetailsInfo['loginUrl'], data=login_data,
                     headers={"Referer": "HOMEPAGE"})


def getJobPostingsFromSiteForMultipleSearchTerms(jobSiteDetailsInfo,
                                                 searchTermsList,
                                                 knownPostIds=[],
                                                 expectedPostingsPerPage=10,
                                                 maxPages=100, minPages=4):
    fullPostingsList = {}
    session = requests.Session()
    if jobSiteDetailsInfo['urlSchema'] == 'https':
        loginToWebsite(session, jobSiteDetailsInfo)

    for searchTerm in searchTermsList:
        fullPostingsList.update(getJobPostingsFromSite(
                jobSiteDetailsInfo, searchTerm, knownPostIds,
                expectedPostingsPerPage=expectedPostingsPerPage,
                maxPages=maxPages, minPages=minPages, session=session))
    session = None
    return fullPostingsList


def checkForMorePostings(numPostingsOnPage, expectedPostingsPerPage,
                         numAllUniquePostingsFoundOnPage, numPostingsSiteFound,
                         startIndex, maxPages, minPages):
    '''
    Checks criteria for whether to check for more postings on the next page.

    Args:
        numPostingsOnPage (int): the total number of postings found on the page
        expectedPostingsPerPage (int): the number of postings expected to be on the page
        numAllUniquePostingsFoundOnPage (int): the number of new/unique postings found on the page
        numPostingsSiteFound (int): the total number of postings found on the site
        startIndex (int): the starting index for the page, should be a multiple of expectedPostingsPerPage
        maxPages (int): the maximum number of pages to scrape
        minPages (int): the minimum number of pages to scrape
    '''
    if startIndex + expectedPostingsPerPage <= numPostingsSiteFound:
        if numPostingsOnPage == expectedPostingsPerPage:
            if (numAllUniquePostingsFoundOnPage > 0 and
                    startIndex < expectedPostingsPerPage * (maxPages-1)):
                return True
            elif startIndex < expectedPostingsPerPage * (minPages-1):
                return True
        print('numPostingsOnPage ({0}) != expectedPostingsPerPage ({1}) OR numAllUniquePostingsFoundOnPage ({2}) == 0 OR startIndex ({3}) < expectedPostingsPerPage ({4}) * (maxPages ({5}) -1) OR startIndex ({3}) < expectedPostingsPerPage ({4}) * (minPages ({6}) -1) '.format(numPostingsOnPage, expectedPostingsPerPage, numAllUniquePostingsFoundOnPage, startIndex, expectedPostingsPerPage, maxPages, minPages))
        return False
    else:
        print('startIndex ({}) + expectedPostingsPerPage ({}) <= numPostingsSiteFound ({}) is False'.format(startIndex, expectedPostingsPerPage, numPostingsSiteFound))
        return False


def getJobPostingsFromSite(jobSiteDetailsInfo, searchTerm, knownPostIds=[],
                           expectedPostingsPerPage=10, maxPages=100,
                           minPages=4, session=None):
    fullPostingsList = {}
    if not session:
        session = requests.Session()

        if jobSiteDetailsInfo['urlSchema'] == 'https':
            loginToWebsite(session, jobSiteDetailsInfo)

    startIndex = 0
    urlArguments = {'q': searchTerm,
                    'l': jobSiteDetailsInfo['location'],
                    jobSiteDetailsInfo['jobTypeKey']: 'contract',
                    'sort': 'date',
                    jobSiteDetailsInfo['pageIndexKey']: 0,
                    }

    url = '{}://{}/{}'.format(jobSiteDetailsInfo['urlSchema'],
                              jobSiteDetailsInfo['netLoc'],
                              jobSiteDetailsInfo['urlPath'])
    page = session.get(url, params=urlArguments, verify=False)
    # print('\n\npage header content-type info: {}\n'.format(
    #     page.headers['content-type']))
    print('\n\nHere is initial URL to be "scraped": {}\n'.format(page.url))

    postingsList, numPostingsOnPage, initTotalNumPostings = parseHtmlPage2(
            page.text, jobSiteDetailsInfo, searchTerm, knownPostIds)
    print('Found {} new of {} postings of {} from url {}'.format(
            len(postingsList), numPostingsOnPage,
            initTotalNumPostings, page.url))
    fullPostingsList.update(postingsList)
    knownPostIds.extend(list(postingsList.keys()))
    while checkForMorePostings(numPostingsOnPage, expectedPostingsPerPage,
                               len(postingsList), initTotalNumPostings,
                               startIndex, maxPages, minPages):
        startIndex += expectedPostingsPerPage
        if jobSiteDetailsInfo['pageIndexType'] == 'pageCount':
            urlArguments[jobSiteDetailsInfo['pageIndexKey']] += 1
        else:
            urlArguments[jobSiteDetailsInfo['pageIndexKey']] = startIndex
        page = session.get(url, params=urlArguments, verify=False)
        postingsList, numPostingsOnPage, totalNumberJobsFound = parseHtmlPage2(
                page.text, jobSiteDetailsInfo, searchTerm, knownPostIds)
        fullPostingsList.update(postingsList)
        knownPostIds.extend(list(postingsList.keys()))
        print(('Found {} new of {} postings of {} from url {}  Now {} '
               'postings found').format(len(postingsList), numPostingsOnPage,
                                        totalNumberJobsFound, page.url,
                                        len(fullPostingsList)))
    return fullPostingsList


def testKeywordSearches(args):

    # jobSiteDetailsInfo = jobSiteDetails['ca.indeed.com']
    jobSiteDetailsInfo = jobSiteDetails['www.simplyhired.ca']

    sysOutRedirect = SysOutRedirector.SysOutRedirector(
            path='/workspaces/reports/',
            filePrefix='ScrapeIndeed-KeywordTests-{}'.format(
                jobSiteDetailsInfo['netLoc']))
    print(('\nTesting Keyword Searchs for the {} website job posting '
           'searches.\n').format(jobSiteDetailsInfo['netLoc']))
    searchTermsList = ['java', 'devops', 'python', 'java devops python',
                       'java or devops or python', ]
    # searchTermsList = ['python', ]
    # urlSchemas = ['http', 'https']
    urlSchemas = ['http']
    # fullPostingsList = {}
    allPosts = {}
    knownPostIds = []
    for urlSchema in urlSchemas:
        jobSiteDetailsInfo['urlSchema'] = urlSchema
        allPosts[urlSchema] = getJobPostingsFromSiteForMultipleSearchTerms(
                jobSiteDetailsInfo, searchTermsList, knownPostIds)

    print('\n\nResults found:\n')

    # diffs = {}
    sames = {}
    for urlSchema in urlSchemas:
        sames[urlSchema] = {}

        for searchTerm in searchTermsList:
            if searchTerm not in sames[urlSchema].keys():
                sames[urlSchema][searchTerm] = {}

            for othSrchTerm in searchTermsList:
                if othSrchTerm == searchTerm:
                    sames[urlSchema][searchTerm][othSrchTerm] = '-'
                else:
                    stKeys = set(allPosts[urlSchema][searchTerm].keys())
                    ostKeys = set(allPosts[urlSchema][othSrchTerm].keys())
                    sames[urlSchema][searchTerm][othSrchTerm] = len(
                            stKeys.intersection(ostKeys))

    if len(urlSchemas) > 1:
        urlSchema = 'diff'
        diffSchemasSames = {}
        for searchTerm in searchTermsList:
            if searchTerm not in diffSchemasSames.keys():
                diffSchemasSames[searchTerm] = {}

            stKeys = set(allPosts[urlSchemas[0]][searchTerm].keys())
            ostKeys = set(allPosts[urlSchemas[1]][searchTerm].keys())
            keysInBoth = stKeys.intersection(ostKeys)
            diffSchemasSames[searchTerm] = len(keysInBoth)

    print('\n\nHere is listing of the number of same entries in each list:\n')
    print('Schema  Search Terms            Postings', end='')
    for searchTerm in searchTermsList:
        print('  {0:^24}'.format(searchTerm), end='')
    print()
    for urlSchema in urlSchemas:
        for searchTerm in searchTermsList:
            print('{2:10}  {0:^24}  {1:^8}  '.format(
                    searchTerm, len(allPosts[urlSchema][searchTerm]),
                    urlSchema), end='')
            for st in searchTermsList:
                print('{0:^24}  '.format(sames[urlSchema][searchTerm][st]),
                      end='')
            print()

    if len(urlSchemas) > 1:
        print(('\n\nHere is a listing of the number of same entries in for '
               'the different schemas (logged in vs not):\n'))
        print('Search Terms            Postings  Number Same Postinge'.format(
                searchTermsList))
        for searchTerm in diffSchemasSames.keys():
            print('{0:^24}  {1:^8}  {2:^24}'.format(
                    searchTerm, len(allPosts[urlSchema][searchTerm]),
                    diffSchemasSames[searchTerm]))

    print('\n\n')


def main(args):
    dbName = 'c:\workspaces\jobPosting\jobPosting.db'
    searchTermsList = ['java', 'devops', 'python', ]
    reportPath = '/workspaces/reports/'

    parser = argparse.ArgumentParser(
        description=('Searches a job posting website for jobs with the '
                     'desired search term(s), saves them to a db and creates '
                     'an html file with links to each new posting.'))
    parser.add_argument('--allSites', '-a', action='store_const', const=True,
                        default=True,
                        help=('Search all known job post websites. Known '
                              'websites are: {}. This overrides the "website"'
                              ' argument. This is the default option.').format(
                                ', '.join(jobSiteDetails.keys())))
    parser.add_argument('--getAllPostings', '-g', action='store_const',
                        const=True, default=None,
                        help=('Get all of the job postings found for the '
                              'specified search term(s). The default is to '
                              'only get job postings that have not already '
                              'been scraped and stored in the database.'))
    parser.add_argument('--doNotSave', '-n', action='store_const',
                        const=True, default=None,
                        help=('Do not save any new postings to the database. '
                              'This is used to help test. The default is to '
                              'save all new postings to the database. '))
    parser.add_argument('--website', '-w', choices=jobSiteDetails.keys(),
                        default=None,
                        help=('Only search one website. Must be one of {}.')
                        .format(', '.join(jobSiteDetails.keys())))
    parser.add_argument('--search', '-s', nargs='*', default=searchTermsList,
                        help=('The search term(s) to search for. Can be a '
                              'list of terms separated by one or more spaces.'
                              ' Default is to search for each of these terms:'
                              ' "{}"').format('", "'.join(searchTermsList)))
    parser.add_argument('--databaseName', '-d', default=dbName,
                        help=('The name and path of the database to save the '
                              'job postings into. Defaults to "{}".').format(
                                    dbName))
    parser.add_argument('--reportPath', '-r', default=reportPath,
                        help=('The path for where the resulting report files '
                              'will be placed. Defaults to "{}".').format(
                                    reportPath))
    parser.add_argument('--generateReport', '-gr', action='store_const',
                        const=True, default=None,
                        help=('Generate the HTML report containing the '
                              'postings already scraped that were posted in '
                              'the past 4 days. Do not check websites for '
                              'new posts.'))
    args = parser.parse_args()

    reportPath = args.reportPath
    dbName = args.databaseName
    searchTermsList = args.search
    if args.website:
        siteList = {args.website: jobSiteDetails[args.website]}
    else:
        siteList = jobSiteDetails

    sysOutRedirect = SysOutRedirector.SysOutRedirector(
            path=reportPath,
            filePrefix='JobsSiteScrape-{}'.format('_'.join(siteList.keys())))

    fullPostingsList = {}
    if args.generateReport:
        fullPostingsList = getRecentPostings(dbName)
    else:
        knownPostIds = []
        if not args.getAllPostings:
            alreadyStoredPostingsRows = getResultDictForSQL(
                    'select distinct Id from JobPostings', None, dbName)
            knownPostIds = [it['Id'] for it in alreadyStoredPostingsRows]
            print('\nGot list of {} ids already in the database.\n'.format(
                len(knownPostIds)))

        if not os.path.isfile(dbName):
            ensureDatabaseTablesAlreadyCreated(dbName)

        for jobSiteDetailsInfo in siteList.values():
            fullPostingsList.update(
                getJobPostingsFromSiteForMultipleSearchTerms(jobSiteDetailsInfo,
                                                             searchTermsList,
                                                             knownPostIds))

        if len(fullPostingsList.keys()) > 0:
            displayListings(fullPostingsList.values())
            if not args.doNotSave:
                savePostingsToDB(fullPostingsList.values(), dbName)
        print('\nScraped {} postings.\n'.format(len(fullPostingsList)))

    if len(fullPostingsList.keys()) > 0:
        generateHtmlPage(sysOutRedirect.getReportDirectory(),
                         '_'.join(siteList.keys()),
                         searchTermsList, fullPostingsList.values())

    sysOutRedirect.close()


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
                        jobSiteDetailsInfo['jobTypeKey']: 'contract',
                        'sort': 'date',
                        jobSiteDetailsInfo['pageIndexKey']: 0,
                        }

        url = '{}://{}/{}'.format(jobSiteDetailsInfo['urlSchema'],
                                  jobSiteDetailsInfo['netLoc'],
                                  jobSiteDetailsInfo['urlPath'])

        page = c.get(url, params=urlArguments)
        print('\nHere is the initial URL to be "scraped": {}\n\n'.format(
            page.url))
        postingsList, numPostingsOnPage = parseHtmlPage2(page.text,
                                                         jobSiteDetailsInfo)
        pp = pprint.PrettyPrinter(indent=4)
        pp.pprint(postingsList)
        newlist = sort_by_subdict(postingsList, 'locale')
        pp.pprint(newlist)
        generateHtmlPage('/workspaces/reports/', jobSiteDetailsInfo['netLoc'],
                         [searchTerm], postingsList.values())


if __name__ == "__main__":
    if '--test' in sys.argv:
        login(sys.argv)
    elif '--test2' in sys.argv:
        testKeywordSearches(sys.argv)
    else:
        main(sys.argv)
