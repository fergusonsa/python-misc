# coding: utf-8
import sys, urllib.parse, os.path
from bs4 import BeautifulSoup
from urllib.request import urlopen
import SysOutRedirector
import sqlite3 as sqlite
   
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
                
    print('\nInserted {} of the {} found postings into the database. {} postings were already there. \n'.format(insertedCount, len(fullPostingsList), alreadyThereCount))

    if insertedCount > 0:
        executeUpdateSQL("update JobPostings set province = trim(substr(Locale, instr(Locale, ',')+1)) where Province is null;", dbName)
        executeUpdateSQL("update JobPostings set City = trim(substr(Locale, 1, instr(Locale, ',')-1)) where City is null;", dbName)
        executeUpdateSQL("insert into RecruitingCompanies select Company as Name, min(insertedDate) as DateContacted, '' as Comment, 0 as ResumeSubmitted, 0 as NotInterested, '' as URL, 0 as CannotSubmitResume from JobPostings left join RecruitingCompanies on Company = Name where Name is null group by Company order by Company", dbName)

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

def getHtmlPage(url):
    # print('getting URL "{}"'.format(url))
    pageFile = urlopen(url)
    pageHtml = pageFile.read()
    pageFile.close()
    return pageHtml
    
def parseHtmlPage(pageHtml, urlBase='', knownPostingIdsList=[]):
    soup = BeautifulSoup(pageHtml)
    items = soup.findAll('div', {'class':'row', 'itemtype':'http://schema.org/JobPosting'})
    postingsList = []
    # if len(items) > 0:
        # print('------')
        # print(items[0])       
        # print('------\n')
                
    for it in items:
            
        id = None
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
        postingsList.append({'title':title, 'url':url, 'company':company, 'locale':locale, 'id':id})
    return postingsList
    
def buildUrl(urlSchema, netLoc,  urlPath, urlArguments, startIndex):
    urlArguments['start'] = startIndex    
    queryString = urllib.parse.urlencode(urlArguments)
    
    url = urllib.parse.urlunparse((urlSchema, netLoc, urlPath, '', queryString, '')) 
    return url
    
def isSmallListInBigList(bigList, smallList):
    
    for item in smallList:
        if item not in bigList:
            return False
    return True

## ------------------------------------------------------------------------------------------------------    
def main(args):
    dbName = 'c:\workspaces\jobPosting\jobPosting.db'
    # netLoc = 'www.indeed.co.uk'
    # location = 'Scotland'
    netLoc = 'ca.indeed.com'
    location = 'Canada'
    sysOutRedirect = SysOutRedirector.SysOutRedirector(path='/workspaces/reports/', filePrefix='ScrapeIndeed-{}'.format(netLoc))
    # url = "http://ca.indeed.com/jobs?as_and=&as_phr=&as_any=java+devops&as_not=&as_ttl=&as_cmp=&jt=contract&st=&salary=&radius=25&l=Canada&fromage=any&limit=100&sort=&psf=advsrch"
    # url = "http://www.indeed.co.uk/jobs?as_and=&as_phr=&as_any=java+devops&as_not=&as_ttl=&as_cmp=&jt=contract&st=&salary=&radius=25&l=Scotland&fromage=any&limit=100&sort=&psf=advsrch"
    fullPostingsList = []
    searchTermsList = ['java', 'devops']
    urlSchema = 'http'
    urlPath = 'jobs'
    startIndex = 0
    for searchTerm in searchTermsList:
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
        
        postingsList = parseHtmlPage(pageHtml, netLoc, alreadyStoredPostings)
        print('Found {} new postings to save from url {}!'.format(len(postingsList), url))
        fullPostingsList.extend(postingsList)
        while len(postingsList) > 0 and startIndex < 1000:
            startIndex += 10
            url = buildUrl(urlSchema, netLoc, urlPath, urlArguments, startIndex)
            pageHtml = getHtmlPage(url)
            postingsList = parseHtmlPage(pageHtml, netLoc, alreadyStoredPostings)
            print('Found {} new postings to save from url {}!'.format(len(postingsList), url))
            fullPostingsList.extend(postingsList)

    displayListings(fullPostingsList)
    savePostingsToDB(fullPostingsList, dbName)
    
    print('\nScraped {} postings from {} with the location {}.\n'.format(len(fullPostingsList), netLoc, location))
    sysOutRedirect.close()

if __name__ == "__main__":
    main(sys.argv)