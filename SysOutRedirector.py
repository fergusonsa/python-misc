import sys, os.path, codecs
from time import strftime

class SysOutRedirector:

    streams = []
    originalSysOut = None
    fileName = None
    path = None

    def getReportDirectory(self):
        return self.path
        
    def getFileDirectory(self, filePath=None, path=None, filePrefix=None, createParentDirectory=None):
        reportPath = ''
        if not filePath:
            if not path and not filePrefix:
                raise 'Neither a file name or a path and file prefix have been provided for the output file.'
            else:
                reportPath = path
        elif not path:
            reportPath, fileName = os.path.split(filePath)
        else:
            raise 'Missing parameter. Must provide either "path" or "filePath"'
        if not reportPath:
            reportPath = '.'
        if createParentDirectory:
            filePrefix = self.getOutputFileNamePrefix(filePrefix)
            reportPath = os.path.join(path, '{}-{}'.format(filePrefix, strftime("%Y%m%d.%H%M%S")))

        # Check to make sure that the directory has been created
        if not os.path.exists(reportPath):
            if ' ' in reportPath:
                reportPath = reportPath.replace(' ', '_')
            if not os.path.exists(reportPath):
                os.makedirs(reportPath)
        return reportPath
        
    def addOutputFile(self, filePath=None, path=None, filePrefix=None, includeSysOut='true', createParentDirectory=None):
        filePrefix = self.getOutputFileNamePrefix(filePrefix)
        if not filePath:
            timestamp = strftime("%Y%m%d.%H%M%S")
            fileName = '%s-%s.txt' % (filePrefix, timestamp) 
        elif not path:
             fileName = os.path.basename(filePath)
        else:
            raise 'Cannot get filename because path and filePath parameters are None.'
        self.fileName = fileName

        path = self.getFileDirectory(filePath, path, filePrefix, createParentDirectory)
        self.toStdOut('Setting fileName to %r\nSetting path to %r\n' % (fileName, path))
        self.path = path
        
        reportFileName = self.getOutputFileName()    
        if os.path.exists(reportFileName):
            mode = 'a'
        else:
            mode = 'w'
            
        # Create the log file
        reportFile = open(reportFileName, mode)
        self.streams.append(reportFile)

    def __init__(self, filePath=None, path=None, filePrefix=None, includeSysOut='true', createParentDirectory=None):
                   
        # save the existing sys.stdout 
        self.originalSysOut = sys.__stdout__
        if includeSysOut:
            if sys.__stdout__.encoding != 'UTF-8':
                # See http://www.macfreek.nl/memory/Encoding_of_Python_stdout for explanation of what is going on.
                self.streams.append(codecs.getwriter('utf-8')(self.originalSysOut.buffer, 'strict'))
            else:    
                self.streams.append(self.originalSysOut)

        self.addOutputFile(filePath, path, filePrefix, includeSysOut, createParentDirectory)
        
        sys.stdout = self
        
    def write(self, txt):
        if txt:
            for strm in self.streams:
                if isinstance(txt, str):
                    st = txt
                else:
                    st = str(txt, 'utf8', 'replace')                    
                try:
                    strm.write(st)
                except:
                    self.originalSysOut.write('EXCEPTION SysOutRedirector: Cannot write "{}" to stream {}.'.format(st, self.streams.index(strm)))
                    
                strm.flush()

    def writeln(self, txt):
        if txt:
            self.write(txt)
            for strm in self.streams:
                strm.write('\n')

    #pass all other methods to __stdout__ so that we don't have to override them
    def __getattr__(self, name):
        try:
            return getattr(sys.__stdout__, name)
        except:
            sys.__stdout__.write('EXCEPTION SysOutRedirector.__getattr__: Cannot get sys.__stdout__ attribute "{}"'.format(name))
        
    def flush(self):
        for strm in self.streams:
            strm.flush()
        
    def close(self):
        if self.originalSysOut:
            sys.stdout = sys.__stdout__
        for strm in self.streams:
            if strm != self.originalSysOut:
                strm.close()
        self.streams = []
        self.originalSysOut = None
                
    def getOutputFileName(self):
        return os.path.abspath(os.path.join(self.path, self.fileName))
        
    def toStdOut(self, txt):
        if txt:
            sys.__stdout__.write(txt)
            sys.__stdout__.write('\n')
            
    def status(self):
        sys.__stdout__.write('Number of streams: %d\n' % len(self.streams))
        sys.__stdout__.write('fileName: %r\n' % self.fileName)
        sys.__stdout__.write('path: %r\n' % self.path)
        if self.originalSysOut:
            if self.originalSysOut == sys.__stdout__:
                sys.__stdout__.write('originalSysOut == sys.__stdout__\n')
            else:
                sys.__stdout__.write('originalSysOut != sys.__stdout__\n')
        else:
            sys.__stdout__.write('originalSysOut != sys.__stdout__\n')
                
        if self == sys.stdout:
            sys.__stdout__.write('self == sys.stdout\n')
        else:
            sys.__stdout__.write('self != sys.stdout\n')

            
    def getOutputFileNamePrefix(self, filePrefix=None):
        if not filePrefix: 
            filePrefix = 'SysOutRedirectorOutput'
        if ' ' in filePrefix:
            filePrefix = filePrefix.replace(' ', '_')
        return filePrefix
        
    def switchOutputFiles(self, filePathToRemove=None, pathToRemove=None, filePrefixToRemove=None, filePath=None, path=None, filePrefix=None, includeSysOut='true'):
        self.removeOutputFile(filePathToRemove, pathToRemove, filePrefixToRemove)
        self.addOutputFile(filePath, path, filePrefix, includeSysOut)
        
    def removeOutputFile(self, filePath=None, path=None, filePrefix=None):
        filePrefix = self.getOutputFileNamePrefix(filePrefix)
        for strm in self.streams:
            if strm != self.originalSysOut:
                fileName = strm.name
                base = os.path.basename(fileName)
                if base.startswith(filePrefix):
                    strm.close()
                    self.streams.remove(strm)
                    if self.fileName == fileName:
                        self.fileName = None
                    break
                