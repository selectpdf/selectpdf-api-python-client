#
# SelectPdf Online API Python Client.
#

try:
	from urllib import urlencode
	import urllib2
	from urllib2 import HTTPError, URLError
	IS_PYTHON3 = False
except ImportError:
	from urllib.parse import urlencode
	import urllib.request
	from urllib.error import HTTPError, URLError
	IS_PYTHON3 = True

try:
    import httplib
except:
    import http.client as httplib

try:
    from urlparse import urlparse
except:
    from urllib.parse import urlparse

import sys, os, json, re, time, socket, io, platform

CLIENT_VERSION = '1.4.0'
"""SelectPdf Python client library version."""

class ApiException(Exception):
    """Exception thrown by SelectPdf API Client."""
    
    def __init__(self, message, code=None):
        self.code = code
        self.message = message

    def __str__(self):
        if self.code:
            return "(%d) %s" % (self.code, self.message)
        else:
            return self.message

    def getMessage(self):
        """Get exception error message."""
        if self.code:
            return "(%d) %s" % (self.code, self.message)
        else:
            return self.message

class ApiClient(object):
    """Base class for API clients. Do not use this directly."""
    
    def __init__(self):    
        self.apiEndpoint = "https://selectpdf.com/api2/convert/"
        self.apiAsyncEndpoint = "https://selectpdf.com/api2/asyncjob/"
        self.apiWebElementsEndpoint = "https://selectpdf.com/api2/webelements/"
        self.parameters = dict()
        self.headers = dict()
        self.files = dict()
        self.binaryData = dict()
        self.numberOfPages = 0
        self.jobId = ""
        self.lastHTTPCode = 0
        self.AsyncCallsPingInterval = 3
        self.AsyncCallsMaxPings = 1000
        self.MULTIPART_FORM_DATA_BOUNDARY = '------------SelectPdf_Api_Boundry_$'
        self.NEW_LINE = '\r\n'
        self.NEW_LINE_BINARY = b'\r\n'


    def setApiEndpoint(self, apiEndpoint):
        """Set a custom SelectPdf API endpoint. Do not use this method unless advised by SelectPdf.

        ### Parameters

        - apiEndpoint: API endpoint.
        """

        self.apiEndpoint = apiEndpoint

    def setApiAsyncEndpoint(self, apiAsyncEndpoint):
        """Set a custom SelectPdf API endpoint for async jobs. Do not use this method unless advised by SelectPdf.

        ### Parameters

        - apiAsyncEndpoint: API async jobs endpoint.
        """

        self.apiAsyncEndpoint = apiAsyncEndpoint

    def setApiWebElementsEndpoint(self, apiWebElementsEndpoint):
        """Set a custom SelectPdf API endpoint for web elements. Do not use this method unless advised by SelectPdf.

        ### Parameters

        - apiWebElementsEndpoint: API web elements endpoint.
        """

        self.apiWebElementsEndpoint = apiWebElementsEndpoint

    def getNumberOfPages(self):
        """Get the number of pages of the PDF document resulted from the API call.

        ### Returns

        Number of pages of the PDF document.
        """

        return self.numberOfPages

    def _performPost(self, outStream=None):
        """Create a POST request.

        ### Parameters

        - outStream: Output response to this stream, if specified.

        ### Returns
        
        If output stream is not specified, return response as string.
        """

        self.headers["selectpdf-api-client"] = "python-{0}-{1}".format(platform.python_version(), CLIENT_VERSION)

        # reset results
        self.numberOfPages = 0
        self.jobId = ""
        self.lastHTTPCode = 0

        allheaders = {"Content-type": "application/x-www-form-urlencoded"}
        for k, v in self.headers.items():
            allheaders[k] = v
        
        result = None

        try:
            if IS_PYTHON3:
                req =  urllib.request.Request(self.apiEndpoint, urlencode(self.parameters).encode(), allheaders)
                result = urllib.request.urlopen(req, None, 600) # timeout in seconds 600s=10minutes
            else:
                req = urllib2.Request(self.apiEndpoint, urlencode(self.parameters), allheaders)
                result = urllib2.urlopen(req, None, 600) # timeout in seconds 600s=10minutes

            code = result.getcode()
            self.lastHTTPCode = code
            #print ("Request HTTP Response Code:", code)

            if (code == 200):
                if IS_PYTHON3:
                    self.numberOfPages = result.info()['selectpdf-api-pages']
                    self.jobId = result.info()['selectpdf-api-jobid']
                else:
                    self.numberOfPages = result.info().getheader('selectpdf-api-pages')
                    self.jobId = result.info().getheader('selectpdf-api-jobid')

                if self.jobId is None: self.jobId = ""

                if outStream:
                    while True:
                        bytes = result.read(8192)
                        if bytes:
                            outStream.write(bytes)
                        else:
                            break
                    return outStream
                else:
                    return result.read()
            elif (code == 202):
                if IS_PYTHON3:
                    self.jobId = result.info()['selectpdf-api-jobid']
                else:
                    self.jobId = result.info().getheader('selectpdf-api-jobid')

                if self.jobId is None: self.jobId = ""
            else:
                raise ApiException(result.read(), code)

        except HTTPError as e:
            message = e.read()
            if not message:
                message = e.reason
            else:
                if IS_PYTHON3:
                    message = message.decode()
                else:
                    pass

            self.lastHTTPCode = e.code

            #print("HTTP Error:", e.code, message)
            raise ApiException(message, e.code)
            #print ("HTTP Response Code: {0}\nHTTP Response Message: {1}".format(e.code, e.reason))
        except URLError as e:
            raise ApiException("Wrong url.")
            #print ("Wrong url:", e.reason);
        except:
            raise

    def _performPostAsMultipartFormData(self, outStream=None):
        """Create a multipart/form-data POST request (that can handle file uploads).

        ### Parameters

        - outStream: Output response to this stream, if specified.

        ### Returns
        
        If output stream is not specified, return response as string.
        """

        self.headers["selectpdf-api-client"] = "python-{0}-{1}".format(platform.python_version(), CLIENT_VERSION)

        # reset results
        self.numberOfPages = 0
        self.jobId = ""
        self.lastHTTPCode = 0

        # serialize parameters
        byteData = self.__encodeMultipartFormData()
        
        allheaders = {
            "Content-type": "multipart/form-data; boundary=" + self.MULTIPART_FORM_DATA_BOUNDARY,
            "Content-length": str(len(byteData))
        }
        for k, v in self.headers.items():
            allheaders[k] = v

        url = urlparse(self.apiEndpoint)        

        result = None

        try:
            if self.apiEndpoint.startswith("http://"):
                connection = httplib.HTTPConnection(url.netloc, timeout=600) # timeout in seconds 600s=10minutes
            else:
                connection = httplib.HTTPSConnection(url.netloc, timeout=600) # timeout in seconds 600s=10minutes

            connection.request('POST', url.path, byteData, allheaders)
            result = connection.getresponse()

            code = result.status
            self.lastHTTPCode = code
            #print ("Request HTTP Response Code:", code)

            if (code == 200):
                if IS_PYTHON3:
                    self.numberOfPages = result.info()['selectpdf-api-pages']
                    self.jobId = result.info()['selectpdf-api-jobid']
                else:
                    self.numberOfPages = result.getheader('selectpdf-api-pages')
                    self.jobId = result.getheader('selectpdf-api-jobid')

                if self.jobId is None: self.jobId = ""

                if outStream:
                    while True:
                        bytes = result.read(8192)
                        if bytes:
                            outStream.write(bytes)
                        else:
                            break
                    return outStream
                else:
                    return result.read()
            elif (code == 202):
                if IS_PYTHON3:
                    self.jobId = result.info()['selectpdf-api-jobid']
                else:
                    self.jobId = result.getheader('selectpdf-api-jobid')

                if self.jobId is None: self.jobId = ""
            else:
                raise ApiException(result.read(), code)

        except socket.gaierror as e:
            raise ApiException("Wrong url.")

        except httplib.InvalidURL as e:
            raise ApiException("Wrong url.")
            #print ("Wrong url:", e.reason);

        except httplib.HTTPException as e:
            message = e.read()
            if not message:
                message = e.reason
            else:
                if IS_PYTHON3:
                    message = message.decode()
                else:
                    pass

            self.lastHTTPCode = e.code

            #print("HTTP Error:", e.code, message)
            raise ApiException(message, e.code)
            #print ("HTTP Response Code: {0}\nHTTP Response Message: {1}".format(e.code, e.reason))
        except:
            raise

    def __encodeMultipartFormData(self):
        """Encode data for multipart/form-data POST"""

        allParameters, finalBoundary = [], []
        allData = []

        # encode regular parameters
        for key, value in self.parameters.items():
            allParameters.append('--' + self.MULTIPART_FORM_DATA_BOUNDARY)
            allParameters.append('Content-Disposition: form-data; name="%s"' % key)
            allParameters.append('')
            allParameters.append(str(value))

        #print(*allParameters, sep = "\n")

        if IS_PYTHON3:
            allData.append(self.NEW_LINE.join(allParameters).encode('utf-8'))
        else:
            allData.append(self.NEW_LINE.join(allParameters))

        # encode files
        for key, value in self.files.items():
            allFileEncoding = []

            allFileEncoding.append('--' + self.MULTIPART_FORM_DATA_BOUNDARY)
            allFileEncoding.append('Content-Disposition: form-data; name="{}"; filename="{}"'.format(key, value))
            allFileEncoding.append('Content-Type: application/octet-stream')
            allFileEncoding.append('')

            if IS_PYTHON3:
                allData.append(self.NEW_LINE.join(allFileEncoding).encode('utf-8'))
            else:
                allData.append(self.NEW_LINE.join(allFileEncoding))

            with open(value, 'rb') as f:
                allData.append(f.read())

        # encode additional binary data
        for key, value in self.binaryData.items():
            allFileEncoding = []

            allFileEncoding.append('--' + self.MULTIPART_FORM_DATA_BOUNDARY)
            allFileEncoding.append('Content-Disposition: form-data; name="{}"; filename="{}"'.format(key, key))
            allFileEncoding.append('Content-Type: application/octet-stream')
            allFileEncoding.append('')

            if IS_PYTHON3:
                allData.append(self.NEW_LINE.join(allFileEncoding).encode('utf-8'))
            else:
                allData.append(self.NEW_LINE.join(allFileEncoding))

            allData.append(value)

        # final boundary
        finalBoundary.append('--' + self.MULTIPART_FORM_DATA_BOUNDARY + '--')
        finalBoundary.append('')

        if IS_PYTHON3:
            allData.append(self.NEW_LINE.join(finalBoundary).encode('utf-8'))
        else:
            allData.append(self.NEW_LINE.join(finalBoundary))

        return self.NEW_LINE_BINARY.join(allData)

    def _startAsyncJob(self):
        """Start async job."""

        self.parameters["async"] = True
        self._performPost()
        return self.jobId

    def _startAsyncJobMultipartFormData(self):
        """Start an asynchronous job that requires multipart forma data."""

        self.parameters["async"] = True
        self._performPostAsMultipartFormData()
        return self.jobId

class UsageClient(ApiClient):
    """Get usage details for SelectPdf Online API."""

    def __init__(self, apiKey):    
        """Construct the Usage Client.

        ### Parameters

        - apiKey: API key.
        """

        super(UsageClient, self).__init__()

        self.apiEndpoint = "https://selectpdf.com/api2/usage/"
        self.parameters["key"] = apiKey

    def getUsage(self, getHistory=False):
        """Get API usage information with history if specified.

        ### Parameters

        - getHistory: Get history or not.

        ### Returns

        Json containing usage information.
        """

        self.headers["Accept"] = "text/json"

        if getHistory:
            self.parameters["get_history"] = "True"

        result = self._performPost()
        return json.loads(result)

class AsyncJobClient(ApiClient):
    """Get the result of an asynchronous call."""

    def __init__(self, apiKey, jobId):    
        """Construct the async job client.

        ### Parameters

        - apiKey: API key.
        - jobId: Job ID.
        """

        super(AsyncJobClient, self).__init__()

        self.apiEndpoint = "https://selectpdf.com/api2/asyncjob/"
        self.parameters["key"] = apiKey
        self.parameters["job_id"] = jobId

    def getResult(self):
        """Get result of the asynchronous job.

        ### Returns

        Byte array containing the resulted file if the job is finished. Returns Null if the job is still running. Throws an exception if an error occurred.
        """

        result = self._performPost()
        
        if self.jobId:
            return False
        else:
            return result

    def finished(self):
        """Check if asynchronous job is finished.

        ### Returns

        True if job finished.
        """

        if self.lastHTTPCode != 202:
            return True
        else:
            return False

class WebElementsClient(ApiClient):
    """
    Get the locations of certain web elements. 
    This is retrieved if pdf_web_elements_selectors parameter was set during the initial conversion call and elements were found to match the selectors.
    """

    def __init__(self, apiKey, jobId):    
        """Construct the Web Elements Client.

        ### Parameters

        - apiKey: API key.
        - jobId: Job ID.
        """

        super(WebElementsClient, self).__init__()

        self.apiEndpoint = "https://selectpdf.com/api2/webelements/"
        self.parameters["key"] = apiKey
        self.parameters["job_id"] = jobId

    def getWebElements(self):
        """Get the locations of certain web elements. This is retrieved if pdf_web_elements_selectors parameter is set and elements were found to match the selectors.

        ### Returns

        Json containing web elements locations.
        """

        self.headers["Accept"] = "text/json"

        result = self._performPost()

        if result:
            return json.loads(result)
        else:
            return []

class PageSize:
    """PDF page size."""

    Custom = "Custom"
    """Custom page size."""

    A0 = "A0"
    """A0 page size."""

    A1 = "A1"
    """A1 page size."""

    A2 = "A2"
    """A2 page size."""

    A3 = "A3"
    """A3 page size."""

    A4 = "A4"
    """A4 page size."""

    A5 = "A5"
    """A5 page size."""

    A6 = "A6"
    """A6 page size."""

    A7 = "A7"
    """A7 page size."""

    A8 = "A8"
    """A8 page size."""

    Letter = "Letter"
    """Letter page size."""

    HalfLetter = "HalfLetter"
    """HalfLetter page size."""

    Ledger = "Ledger"
    """Ledger page size."""

    Legal = "Legal"
    """Legal page size."""

class PageOrientation:
    """PDF page orientation."""

    Portrait = "Portrait"
    """Portrait page orientation."""

    Landscape = "Landscape"
    """Landscape page orientation."""

class RenderingEngine:
    """Rendering engine used for HTML to PDF conversion."""

    WebKit = "WebKit"
    """WebKit rendering engine."""

    Restricted = "Restricted"
    """WebKit Restricted rendering engine."""

    Blink = "Blink"
    """Blink rendering engine."""

class SecureProtocol:
    """Protocol used for secure (HTTPS) connections."""

    Tls11OrNewer = 0
    """TLS 1.1 or newer. Recommended value."""

    Tls10 = 1
    """TLS 1.0 only."""

    Ssl3 = 2
    """SSL v3 only."""

class PageLayout:
    """The page layout to be used when the pdf document is opened in a viewer."""

    SinglePage = 0
    """Displays one page at a time."""

    OneColumn = 1
    """Displays the pages in one column."""

    TwoColumnLeft = 2
    """Displays the pages in two columns, with odd-numbered pages on the left."""

    TwoColumnRight = 3
    """Displays the pages in two columns, with odd-numbered pages on the right."""

class PageMode:
    """The PDF document's page mode."""

    UseNone = 0
    """Neither document outline (bookmarks) nor thumbnail images are visible."""

    UseOutlines = 1
    """Document outline (bookmarks) are visible."""

    UseThumbs = 2
    """Thumbnail images are visible."""

    FullScreen = 3
    """Full-screen mode, with no menu bar, window controls or any other window visible."""

    UseOC = 4
    """Optional content group panel is visible."""

    UseAttachments = 5
    """Document attachments are visible."""

class PageNumbersAlignment:
    """Alignment for page numbers."""

    Left = 1
    """Align left."""

    Center = 2
    """Align center."""

    Right = 3
    """Align right."""

class StartupMode:
    """Specifies the converter startup mode."""

    Automatic = "Automatic"
    """The conversion starts right after the page loads."""

    Manual = "Manual"
    """The conversion starts only when called from JavaScript."""

class TextLayout:
    """The output text layout (for pdf to text calls)."""

    Original = 0
    """The original layout of the text from the PDF document is preserved."""

    Reading = 1
    """The text is produced in reading order."""

class OutputFormat:
    """The output format (for pdf to text calls)."""

    Text = 0
    """Text"""

    Html = 1
    """Html"""


class HtmlToPdfClient(ApiClient):
    """Html To Pdf Conversion with SelectPdf Online API."""

    def __init__(self, apiKey):    
        """Construct the Html To Pdf Client.

        ### Parameters

        - apiKey: API key.
        """

        super(HtmlToPdfClient, self).__init__()

        self.apiEndpoint = "https://selectpdf.com/api2/convert/"
        self.parameters["key"] = apiKey

    def convertUrl(self, url):
        """Convert the specified url to PDF. SelectPdf online API can convert http:// and https:// publicly available urls.

        ### Parameters

        - url: Address of the web page being converted.
        
        ### Returns

        Resulted PDF.
        """

        if not url.startswith("http://") and not url.startswith("https://"):
            raise ApiException("The supported protocols for the converted webpage are http:// and https://.")
        
        if url.startswith("http://localhost"):
            raise ApiException("Cannot convert local urls. SelectPdf online API can only convert publicly available urls.")

        self.parameters["url"] = url
        self.parameters["html"] = ""
        self.parameters["base_url"] = ""
        self.parameters["async"] = False

        return self._performPost()

    def convertUrlToStream(self, url, stream):
        """Convert the specified url to PDF and writes the resulted PDF to an output stream. SelectPdf online API can convert http:// and https:// publicly available urls.

        ### Parameters

        - url: Address of the web page being converted.
        - stream: The output stream where the resulted PDF will be written.
        """

        if not url.startswith("http://") and not url.startswith("https://"):
            raise ApiException("The supported protocols for the converted webpage are http:// and https://.")
        
        if url.startswith("http://localhost"):
            raise ApiException("Cannot convert local urls. SelectPdf online API can only convert publicly available urls.")

        self.parameters["url"] = url
        self.parameters["html"] = ""
        self.parameters["base_url"] = ""
        self.parameters["async"] = False

        return self._performPost(stream)

    def convertUrlToFile(self, url, filePath):
        """Convert the specified url to PDF and writes the resulted PDF to a local file. SelectPdf online API can convert http:// and https:// publicly available urls.

        ### Parameters

        - url: Address of the web page being converted.
        - filePath: Local file including path if necessary.
        """

        if not url.startswith("http://") and not url.startswith("https://"):
            raise ApiException("The supported protocols for the converted webpage are http:// and https://.")
        
        if url.startswith("http://localhost"):
            raise ApiException("Cannot convert local urls. SelectPdf online API can only convert publicly available urls.")

        outputFile = open(filePath, 'wb')
        try:
            self.convertUrlToStream(url, outputFile)
            outputFile.close()
        except ApiException:
            outputFile.close()
            os.remove(filePath)
            raise

    def convertUrlAsync(self, url):
        """Convert the specified url to PDF using an asynchronous call. SelectPdf online API can convert http:// and https:// publicly available urls.

        ### Parameters

        - url: Address of the web page being converted.
        
        ### Returns

        Resulted PDF.
        """

        if not url.startswith("http://") and not url.startswith("https://"):
            raise ApiException("The supported protocols for the converted webpage are http:// and https://.")
        
        if url.startswith("http://localhost"):
            raise ApiException("Cannot convert local urls. SelectPdf online API can only convert publicly available urls.")

        self.parameters["url"] = url
        self.parameters["html"] = ""
        self.parameters["base_url"] = ""
        
        JobID = self._startAsyncJob()

        if not JobID:
            raise ApiException("An error occurred launching the asynchronous call.")

        noPings = 0

        while (noPings < self.AsyncCallsMaxPings):
            noPings += 1

            # sleep for a few seconds before next ping
            time.sleep(self.AsyncCallsPingInterval)

            asyncJobClient = AsyncJobClient(self.parameters["key"], JobID)
            asyncJobClient.setApiEndpoint(self.apiAsyncEndpoint)

            result = asyncJobClient.getResult()

            if asyncJobClient.finished():
                self.numberOfPages = asyncJobClient.getNumberOfPages()

                return result

        raise ApiException("Asynchronous call did not finish in expected timeframe.")

    def convertUrlToFileAsync(self, url, filePath):
        """Convert the specified url to PDF using an asynchronous call and writes the resulted PDF to a local file. 
        SelectPdf online API can convert http:// and https:// publicly available urls.

        ### Parameters

        - url: Address of the web page being converted.
        - filePath: Local file including path if necessary.
        """

        outputFile = open(filePath, 'wb')
        try:
            result = self.convertUrlAsync(url)
            outputFile.write(result)
            outputFile.close()
        except ApiException:
            outputFile.close()
            os.remove(filePath)
            raise

    def convertUrlToStreamAsync(self, url, stream):
        """Convert the specified url to PDF using an asynchronous and writes the resulted PDF to an output stream. 
        SelectPdf online API can convert http:// and https:// publicly available urls.

        ### Parameters

        - url: Address of the web page being converted.
        - stream: The output stream where the resulted PDF will be written.
        """

        result = self.convertUrlAsync(url)
        stream.write(result)

    def convertHtmlStringWithBaseUrl(self, htmlString, baseUrl):
        """Convert the specified HTML string to PDF. Use a base url to resolve relative paths to resources.

        ### Parameters

        - htmlString: HTML string with the content being converted.
        - baseUrl: Base url used to resolve relative paths to resources (css, images, javascript, etc). Must be a http:// or https:// publicly available url.

        ### Returns

        The resulted PDF.
        """

        self.parameters["url"] = ""
        self.parameters["async"] = False
        self.parameters["html"] = htmlString

        if baseUrl and baseUrl.strip():
            self.parameters["base_url"] = baseUrl

        return self._performPost()

    def convertHtmlStringWithBaseUrlToStream(self, htmlString, baseUrl, stream):
        """Convert the specified HTML string to PDF and writes the resulted PDF to an output stream. Use a base url to resolve relative paths to resources.

        ### Parameters

        - htmlString: HTML string with the content being converted.
        - baseUrl: Base url used to resolve relative paths to resources (css, images, javascript, etc). Must be a http:// or https:// publicly available url.
        - stream: The output stream where the resulted PDF will be written.
        """

        self.parameters["url"] = ""
        self.parameters["async"] = False
        self.parameters["html"] = htmlString

        if baseUrl and baseUrl.strip():
            self.parameters["base_url"] = baseUrl

        return self._performPost(stream)

    def convertHtmlStringWithBaseUrlToFile(self, htmlString, baseUrl, filePath):
        """Convert the specified HTML string to PDF and writes the resulted PDF to a local file. Use a base url to resolve relative paths to resources.

        ### Parameters

        - htmlString: HTML string with the content being converted.
        - baseUrl: Base url used to resolve relative paths to resources (css, images, javascript, etc). Must be a http:// or https:// publicly available url.
        - filePath: Local file including path if necessary.
        """

        outputFile = open(filePath, 'wb')
        try:
            self.convertHtmlStringWithBaseUrlToStream(htmlString, baseUrl, outputFile)
            outputFile.close()
        except ApiException:
            outputFile.close()
            os.remove(filePath)
            raise

    def convertHtmlStringWithBaseUrlAsync(self, htmlString, baseUrl):
        """Convert the specified HTML string to PDF with an asynchronous call. Use a base url to resolve relative paths to resources.

        ### Parameters

        - htmlString: HTML string with the content being converted.
        - baseUrl: Base url used to resolve relative paths to resources (css, images, javascript, etc). Must be a http:// or https:// publicly available url.

        ### Returns

        The resulted PDF.
        """

        self.parameters["url"] = ""
        self.parameters["html"] = htmlString

        if baseUrl and baseUrl.strip():
            self.parameters["base_url"] = baseUrl

        JobID = self._startAsyncJob()

        if not JobID:
            raise ApiException("An error occurred launching the asynchronous call.")

        noPings = 0

        while (noPings < self.AsyncCallsMaxPings):
            noPings += 1

            # sleep for a few seconds before next ping
            time.sleep(self.AsyncCallsPingInterval)

            asyncJobClient = AsyncJobClient(self.parameters["key"], JobID)
            asyncJobClient.setApiEndpoint(self.apiAsyncEndpoint)

            result = asyncJobClient.getResult()

            if asyncJobClient.finished():
                self.numberOfPages = asyncJobClient.getNumberOfPages()

                return result

        raise ApiException("Asynchronous call did not finish in expected timeframe.")

    def convertHtmlStringWithBaseUrlToStreamAsync(self, htmlString, baseUrl, stream):
        """Convert the specified HTML string to PDF with an asynchronous call and writes the resulted PDF to an output stream. 
        Use a base url to resolve relative paths to resources.

        ### Parameters

        - htmlString: HTML string with the content being converted.
        - baseUrl: Base url used to resolve relative paths to resources (css, images, javascript, etc). Must be a http:// or https:// publicly available url.
        - stream: The output stream where the resulted PDF will be written.
        """

        result = self.convertHtmlStringWithBaseUrlAsync(htmlString, baseUrl)
        stream.write(result)

    def convertHtmlStringWithBaseUrlToFileAsync(self, htmlString, baseUrl, filePath):
        """Convert the specified HTML string to PDF with an asynchronous call and writes the resulted PDF to a local file. 
        Use a base url to resolve relative paths to resources.

        ### Parameters

        - htmlString: HTML string with the content being converted.
        - baseUrl: Base url used to resolve relative paths to resources (css, images, javascript, etc). Must be a http:// or https:// publicly available url.
        - filePath: Local file including path if necessary.
        """

        outputFile = open(filePath, 'wb')
        try:
            self.convertHtmlStringWithBaseUrlToStreamAsync(htmlString, baseUrl, outputFile)
            outputFile.close()
        except ApiException:
            outputFile.close()
            os.remove(filePath)
            raise

    def convertHtmlString(self, htmlString):
        """Convert the specified HTML string to PDF.

        ### Parameters

        - htmlString: HTML string with the content being converted.

        ### Returns

        The resulted PDF.
        """

        return self.convertHtmlStringWithBaseUrl(htmlString, None)

    def convertHtmlStringToStream(self, htmlString, stream):
        """Convert the specified HTML string to PDF and writes the resulted PDF to an output stream.

        ### Parameters

        - htmlString: HTML string with the content being converted.
        - stream: The output stream where the resulted PDF will be written.
        """

        return self.convertHtmlStringWithBaseUrlToStream(htmlString, None, stream)

    def convertHtmlStringToFile(self, htmlString, filePath):
        """Convert the specified HTML string to PDF and writes the resulted PDF to a local file.

        ### Parameters

        - htmlString: HTML string with the content being converted.
        - filePath: Local file including path if necessary.
        """

        return self.convertHtmlStringWithBaseUrlToFile(htmlString, None, filePath)

    def convertHtmlStringAsync(self, htmlString):
        """Convert the specified HTML string to PDF with an asynchronous call.

        ### Parameters

        - htmlString: HTML string with the content being converted.

        ### Returns

        The resulted PDF.
        """

        return self.convertHtmlStringWithBaseUrlAsync(htmlString, None)

    def convertHtmlStringToStreamAsync(self, htmlString, stream):
        """Convert the specified HTML string to PDF with an asynchronous call and writes the resulted PDF to an output stream.

        ### Parameters

        - htmlString: HTML string with the content being converted.
        - stream: The output stream where the resulted PDF will be written.
        """

        return self.convertHtmlStringWithBaseUrlToStreamAsync(htmlString, None, stream)

    def convertHtmlStringToFileAsync(self, htmlString, filePath):
        """Convert the specified HTML string to PDF with an asynchronous call and writes the resulted PDF to a local file.

        ### Parameters

        - htmlString: HTML string with the content being converted.
        - filePath: Local file including path if necessary.
        """

        return self.convertHtmlStringWithBaseUrlToFileAsync(htmlString, None, filePath)

    def setPageSize(self, pageSize):
        """Set PDF page size. Default value is A4. If page size is set to Custom, use setPageWidth and setPageHeight methods to set the custom width/height of the PDF pages.

        ### Parameters

        - pageSize: PDF page size. Possible values: Custom, A1, A2, A3, A4, A5, Letter, HalfLetter, Ledger, Legal. Use constants from selectpdf.PageSize class.

        ### Returns

        Reference to the current object.
        """

        if not re.match('(?i)^(Custom|A1|A2|A3|A4|A5|Letter|HalfLetter|Ledger|Legal)$', pageSize):
            raise ApiException("Allowed values for Page Size: Custom, A1, A2, A3, A4, A5, Letter, HalfLetter, Ledger, Legal.")

        self.parameters["page_size"] = pageSize
        return self

    def setPageWidth(self, pageWidth):
        """Set PDF page width in points. Default value is 595pt (A4 page width in points). 1pt = 1/72 inch. This is taken into account only if page size is set to Custom using setPageSize method.

        ### Parameters

        - pageWidth: Page width in points.

        ### Returns

        Reference to the current object.
        """

        self.parameters["page_width"] = pageWidth
        return self

    def setPageHeight(self, pageHeight):
        """Set PDF page height in points. Default value is 842pt (A4 page height in points). 1pt = 1/72 inch. This is taken into account only if page size is set to Custom using setPageSize method.

        ### Parameters

        - pageHeight: Page height in points.

        ### Returns

        Reference to the current object.
        """

        self.parameters["page_height"] = pageHeight
        return self

    def setPageOrientation(self, pageOrientation):
        """Set PDF page orientation. Default value is Portrait.

        ### Parameters

        - pageOrientation: PDF page orientation. Possible values: Portrait, Landscape. Use constants from selectpdf.PageOrientation class.

        ### Returns

        Reference to the current object.
        """

        if not re.match('(?i)^(Portrait|Landscape)$', pageOrientation):
            raise ApiException("Allowed values for Page Orientation: Portrait, Landscape.")

        self.parameters["page_orientation"] = pageOrientation
        return self

    def setMarginTop(self, marginTop):
        """Set top margin of the PDF pages. Default value is 5pt.

        ### Parameters

        - marginTop: Margin value in points. 1pt = 1/72 inch.

        ### Returns

        Reference to the current object.
        """

        self.parameters["margin_top"] = marginTop
        return self

    def setMarginRight(self, marginRight):
        """Set right margin of the PDF pages. Default value is 5pt.

        ### Parameters

        - marginRight: Margin value in points. 1pt = 1/72 inch.

        ### Returns

        Reference to the current object.
        """

        self.parameters["margin_right"] = marginRight
        return self

    def setMarginBottom(self, marginBottom):
        """Set bottom margin of the PDF pages. Default value is 5pt.

        ### Parameters

        - marginBottom: Margin value in points. 1pt = 1/72 inch.

        ### Returns

        Reference to the current object.
        """

        self.parameters["margin_bottom"] = marginBottom
        return self

    def setMarginLeft(self, marginLeft):
        """Set left margin of the PDF pages. Default value is 5pt.

        ### Parameters

        - marginLeft: Margin value in points. 1pt = 1/72 inch.

        ### Returns

        Reference to the current object.
        """

        self.parameters["margin_left"] = marginLeft
        return self

    def setMargins(self, margin):
        """Set all margins of the PDF pages to the same value. Default value is 5pt.

        ### Parameters

        - margin: Margin value in points. 1pt = 1/72 inch.

        ### Returns

        Reference to the current object.
        """

        return self.setMarginTop(margin).setMarginRight(margin).setMarginBottom(margin).setMarginLeft(margin)

    def setPdfName(self, pdfName):
        """Specify the name of the pdf document that will be created. The default value is Document.pdf.

        ### Parameters

        - pdfName: Name of the generated PDF document.

        ### Returns

        Reference to the current object.
        """

        self.parameters["pdf_name"] = pdfName
        return self

    def setRenderingEngine(self, renderingEngine):
        """Set the rendering engine used for the HTML to PDF conversion. Default value is WebKit.

        ### Parameters

        - renderingEngine: HTML rendering engine. Use constants from selectpdf.RenderingEngine class.

        ### Returns

        Reference to the current object.
        """

        if not re.match('(?i)^(WebKit|Restricted|Blink)$', renderingEngine):
            raise ApiException("Allowed values for Rendering Engine: WebKit, Restricted, Blink.")

        self.parameters["engine"] = renderingEngine
        return self        

    def setUserPassword(self, userPassword):
        """Set PDF user password.

        ### Parameters

        - userPassword: PDF user password.

        ### Returns

        Reference to the current object.
        """

        self.parameters["user_password"] = userPassword
        return self

    def setOwnerPassword(self, ownerPassword):
        """Set PDF owner password.

        ### Parameters

        - ownerPassword: PDF owner password.

        ### Returns

        Reference to the current object.
        """

        self.parameters["owner_password"] = ownerPassword
        return self
        
    def setWebPageWidth(self, webPageWidth):
        """Set the width used by the converter's internal browser window in pixels. The default value is 1024px.

        ### Parameters

        - webPageWidth: Browser window width in pixels.

        ### Returns

        Reference to the current object.
        """

        self.parameters["web_page_width"] = webPageWidth
        return self
    
    def setWebPageHeight(self, webPageHeight):
        """Set the height used by the converter's internal browser window in pixels. The default value is 0px and it means that the page height is automatically calculated by the converter.

        ### Parameters

        - webPageHeight: Browser window height in pixels. Set it to 0px to automatically calculate page height.

        ### Returns

        Reference to the current object.
        """

        self.parameters["web_page_height"] = webPageHeight
        return self

    def setMinLoadTime(self, minLoadTime):
        """
        Introduce a delay (in seconds) before the actual conversion to allow the web page to fully load. This method is an alias for setConversionDelay. 
        The default value is 1 second. Use a larger value if the web page has content that takes time to render when it is displayed in the browser.

        ### Parameters

        - minLoadTime: Delay in seconds.

        ### Returns

        Reference to the current object.
        """

        self.parameters["min_load_time"] = minLoadTime
        return self

    def setConversionDelay(self, delay):
        """
        Introduce a delay (in seconds) before the actual conversion to allow the web page to fully load. This method is an alias for setMinLoadTime. 
        The default value is 1 second. Use a larger value if the web page has content that takes time to render when it is displayed in the browser.

        ### Parameters

        - delay: Delay in seconds.

        ### Returns

        Reference to the current object.
        """

        return self.setMinLoadTime(delay)

    def setMaxLoadTime(self, maxLoadTime):
        """
        Set the maximum amount of time (in seconds) that the convert will wait for the page to load. This method is an alias for setNavigationTimeout. 
        A timeout error is displayed when this time elapses. The default value is 30 seconds. 
        Use a larger value (up to 120 seconds allowed) for pages that take a long time to load.

        ### Parameters

        - maxLoadTime: Timeout in seconds.

        ### Returns

        Reference to the current object.
        """

        self.parameters["max_load_time"] = maxLoadTime
        return self

    def setNavigationTimeout(self, timeout):
        """
        Set the maximum amount of time (in seconds) that the convert will wait for the page to load. This method is an alias for setMaxLoadTime. 
        A timeout error is displayed when this time elapses. The default value is 30 seconds. Use a larger value (up to 120 seconds allowed) for pages that take a long time to load.

        ### Parameters

        - timeout: Timeout in seconds.

        ### Returns

        Reference to the current object.
        """

        return self.setMaxLoadTime(timeout)

    def setSecureProtocol(self, secureProtocol):
        """Set the protocol used for secure (HTTPS) connections. Set this only if you have an older server that only works with older SSL connections.

        ### Parameters

        - secureProtocol: Secure protocol. Possible values: 0 (TLS 1.1 or newer), 1 (TLS 1.0), 2 (SSL v3 only). Use constants from selectpdf.SecureProtocol class.

        ### Returns

        Reference to the current object.
        """

        if secureProtocol != 0 and secureProtocol != 1 and secureProtocol != 2:
            raise ApiException("Allowed values for Secure Protocol: 0 (TLS 1.1 or newer), 1 (TLS 1.0), 2 (SSL v3 only).");

        self.parameters["protocol"] = secureProtocol
        return self

    def setUseCssPrint(self, useCssPrint):
        """Specify if the CSS Print media type is used instead of the Screen media type. The default value is False.

        ### Parameters

        - useCssPrint: Use CSS Print media or not.

        ### Returns

        Reference to the current object.
        """

        self.parameters["use_css_print"] = useCssPrint
        return self

    def setBackgroundColor(self, backgroundColor):
        """Specify the background color of the PDF page in RGB html format. The default is #FFFFFF.

        ### Parameters

        - backgroundColor: Background color in #RRGGBB format.

        ### Returns

        Reference to the current object.
        """

        if not re.match('^#?[0-9a-fA-F]{6}$', backgroundColor):
            raise ApiException("Color value must be in #RRGGBB format.")

        self.parameters["background_color"] = backgroundColor
        return self

    def setDrawHtmlBackground(self, drawHtmlBackground):
        """Set a flag indicating if the web page background is rendered in PDF. The default value is True.

        ### Parameters

        - drawHtmlBackground: Draw the HTML background or not.

        ### Returns

        Reference to the current object.
        """

        self.parameters["draw_html_background"] = drawHtmlBackground
        return self

    def setDisableJavascript(self, disableJavascript):
        """Do not run JavaScript in web pages. The default value is False and javascript is executed.

        ### Parameters

        - disableJavascript: Disable javascript or not.

        ### Returns

        Reference to the current object.
        """

        self.parameters["disable_javascript"] = disableJavascript
        return self

    def setDisableInternalLinks(self, disableInternalLinks):
        """Do not create internal links in the PDF. The default value is False and internal links are created.

        ### Parameters

        - disableInternalLinks: Disable internal links or not.

        ### Returns

        Reference to the current object.
        """

        self.parameters["disable_internal_links"] = disableInternalLinks
        return self

    def setDisableExternalLinks(self, disableExternalLinks):
        """Do not create external links in the PDF. The default value is False and external links are created.

        ### Parameters

        - disableExternalLinks: Disable external links or not.

        ### Returns

        Reference to the current object.
        """

        self.parameters["disable_external_links"] = disableExternalLinks
        return self

    def setRenderOnTimeout(self, renderOnTimeout):
        """Try to render the PDF even in case of the web page loading timeout. The default value is False and an exception is raised in case of web page navigation timeout.

        ### Parameters

        - renderOnTimeout: Render in case of timeout or not.

        ### Returns

        Reference to the current object.
        """

        self.parameters["render_on_timeout"] = renderOnTimeout
        return self

    def setKeepImagesTogether(self, keepImagesTogether):
        """Avoid breaking images between PDF pages. The default value is False and images are split between pages if larger.

        ### Parameters

        - keepImagesTogether: Try to keep images on same page or not.

        ### Returns

        Reference to the current object.
        """

        self.parameters["keep_images_together"] = keepImagesTogether
        return self


    def setDocTitle(self, docTitle):
        """Set the PDF document title.

        ### Parameters

        - docTitle: Document title.

        ### Returns

        Reference to the current object.
        """

        self.parameters["doc_title"] = docTitle
        return self

    def setDocSubject(self, docSubject):
        """Set the subject of the PDF document.

        ### Parameters

        - docSubject: Document subject.

        ### Returns

        Reference to the current object.
        """

        self.parameters["doc_subject"] = docSubject
        return self

    def setDocKeywords(self, docKeywords):
        """Set the PDF document keywords.

        ### Parameters

        - docKeywords: Document keywords.

        ### Returns

        Reference to the current object.
        """

        self.parameters["doc_keywords"] = docKeywords
        return self

    def setDocAuthor(self, docAuthor):
        """Set the name of the PDF document author.

        ### Parameters

        - docAuthor: Document author.

        ### Returns

        Reference to the current object.
        """

        self.parameters["doc_author"] = docAuthor
        return self

    def setDocAddCreationDate(self, docAddCreationDate):
        """Add the date and time when the PDF document was created to the PDF document information. The default value is False.

        ### Parameters

        - docAddCreationDate: Add creation date to the document metadata or not.

        ### Returns

        Reference to the current object.
        """

        self.parameters["doc_add_creation_date"] = docAddCreationDate
        return self

    def setViewerPageLayout(self, pageLayout):
        """Set the page layout to be used when the document is opened in a PDF viewer. The default value is 1 - OneColumn.

        ### Parameters

        - pageLayout: Page layout. Possible values: 0 (Single Page), 1 (One Column), 2 (Two Column Left), 3 (Two Column Right). Use constants from selectpdf.PageLayout class.

        ### Returns

        Reference to the current object.
        """

        if pageLayout != 0 and pageLayout != 1 and pageLayout != 2 and pageLayout != 3:
            raise ApiException("Allowed values for Page Layout: 0 (Single Page), 1 (One Column), 2 (Two Column Left), 3 (Two Column Right).")

        self.parameters["viewer_page_layout"] = pageLayout
        return self

    def setViewerPageMode(self, pageMode):
        """Set the document page mode when the pdf document is opened in a PDF viewer. The default value is 0 - UseNone.

        ### Parameters

        - pageMode: Page mode. Possible values: 0 (Use None), 1 (Use Outlines), 2 (Use Thumbs), 3 (Full Screen), 4 (Use OC), 5 (Use Attachments). Use constants from selectpdf.PageMode class.

        ### Returns

        Reference to the current object.
        """

        if pageMode != 0 and pageMode != 1 and pageMode != 2 and pageMode != 3 and pageMode != 4 and pageMode != 5:
            raise ApiException("Allowed values for Page Mode: 0 (Use None), 1 (Use Outlines), 2 (Use Thumbs), 3 (Full Screen), 4 (Use OC), 5 (Use Attachments).")

        self.parameters["viewer_page_mode"] = pageMode
        return self

    def setViewerCenterWindow(self, viewerCenterWindow):
        """Set a flag specifying whether to position the document's window in the center of the screen. The default value is False.

        ### Parameters

        - viewerCenterWindow: Center window or not.

        ### Returns

        Reference to the current object.
        """

        self.parameters["viewer_center_window"] = viewerCenterWindow
        return self

    def setViewerDisplayDocTitle(self, viewerDisplayDocTitle):
        """Set a flag specifying whether the window's title bar should display the document title taken from document information. The default value is False.

        ### Parameters

        - viewerDisplayDocTitle: Display title or not.

        ### Returns

        Reference to the current object.
        """

        self.parameters["viewer_display_doc_title"] = viewerDisplayDocTitle
        return self

    def setViewerFitWindow(self, viewerFitWindow):
        """Set a flag specifying whether to resize the document's window to fit the size of the first displayed page. The default value is False.

        ### Parameters

        - viewerFitWindow: Fit window or not.

        ### Returns

        Reference to the current object.
        """

        self.parameters["viewer_fit_window"] = viewerFitWindow
        return self

    def setViewerHideMenuBar(self, viewerHideMenuBar):
        """Set a flag specifying whether to hide the pdf viewer application's menu bar when the document is active. The default value is False.

        ### Parameters

        - viewerHideMenuBar: Hide menu bar or not.

        ### Returns

        Reference to the current object.
        """

        self.parameters["viewer_hide_menu_bar"] = viewerHideMenuBar
        return self

    def setViewerHideToolbar(self, viewerHideToolbar):
        """Set a flag specifying whether to hide the pdf viewer application's tool bars when the document is active. The default value is False.

        ### Parameters

        - viewerHideToolbar: Hide tool bars or not.

        ### Returns

        Reference to the current object.
        """

        self.parameters["viewer_hide_toolbar"] = viewerHideToolbar
        return self

    def setViewerHideWindowUI(self, viewerHideWindowUI):
        """Set a flag specifying whether to hide user interface elements in the document's window (such as scroll bars and navigation controls), leaving only the document's contents displayed.

        ### Parameters

        - viewerHideWindowUI: Hide window UI or not.

        ### Returns

        Reference to the current object.
        """

        self.parameters["viewer_hide_window_ui"] = viewerHideWindowUI
        return self

    def setShowHeader(self, showHeader):
        """Control if a custom header is displayed in the generated PDF document. The default value is False.

        ### Parameters

        - showHeader: Show header or not.

        ### Returns

        Reference to the current object.
        """

        self.parameters["show_header"] = showHeader
        return self

    def setHeaderHeight(self, height):
        """The height of the pdf document header. This height is specified in points. 1 point is 1/72 inch. The default value is 50.

        ### Parameters

        - height: Header height.

        ### Returns

        Reference to the current object.
        """

        self.parameters["header_height"] = height
        return self

    def setHeaderUrl(self, url):
        """Set the url of the web page that is converted and rendered in the PDF document header.

        ### Parameters

        - url: The url of the web page that is converted and rendered in the pdf document header.

        ### Returns

        Reference to the current object.
        """

        if not url.startswith("http://") and not url.startswith("https://"):
            raise ApiException("The supported protocols for the converted webpage are http:// and https://.")
        
        if url.startswith("http://localhost"):
            raise ApiException("Cannot convert local urls. SelectPdf online API can only convert publicly available urls.")

        self.parameters["header_url"] = url
        return self

    def setHeaderHtml(self, html):
        """Set the raw html that is converted and rendered in the pdf document header.

        ### Parameters

        - html: The raw html that is converted and rendered in the pdf document header.

        ### Returns

        Reference to the current object.
        """

        self.parameters["header_html"] = html
        return self

    def setHeaderBaseUrl(self, baseUrl):
        """Set an optional base url parameter can be used together with the header HTML to resolve relative paths from the html string.

        ### Parameters

        - baseUrl: Header base url.

        ### Returns

        Reference to the current object.
        """

        if not baseUrl.startswith("http://") and not baseUrl.startswith("https://"):
            raise ApiException("The supported protocols for the converted webpage are http:// and https://.")
        
        if baseUrl.startswith("http://localhost"):
            raise ApiException("Cannot convert local urls. SelectPdf online API can only convert publicly available urls.")

        self.parameters["header_base_url"] = baseUrl
        return self

    def setHeaderDisplayOnFirstPage(self, displayOnFirstPage):
        """Control the visibility of the header on the first page of the generated pdf document. The default value is True.

        ### Parameters

        - displayOnFirstPage: Display header on the first page or not.        

        ### Returns

        Reference to the current object.
        """

        self.parameters["header_display_on_first_page"] = displayOnFirstPage
        return self

    def setHeaderDisplayOnOddPages(self, displayOnOddPages):
        """Control the visibility of the header on the odd numbered pages of the generated pdf document. The default value is True.

        ### Parameters

        - displayOnOddPages: Display header on odd pages or not.

        ### Returns

        Reference to the current object.
        """

        self.parameters["header_display_on_odd_pages"] = displayOnOddPages
        return self

    def setHeaderDisplayOnEvenPages(self, displayOnEvenPages):
        """Control the visibility of the header on the even numbered pages of the generated pdf document. The default value is True.

        ### Parameters

        - displayOnEvenPages: Display header on even pages or not.

        ### Returns

        Reference to the current object.
        """

        self.parameters["header_display_on_even_pages"] = displayOnEvenPages
        return self

    def setHeaderWebPageWidth(self, headerWebPageWidth):
        """Set the width in pixels used by the converter's internal browser window during the conversion of the header content. The default value is 1024px.

        ### Parameters

        - headerWebPageWidth: Browser window width in pixels.

        ### Returns

        Reference to the current object.
        """

        self.parameters["header_web_page_width"] = headerWebPageWidth
        return self
    
    def setHeaderWebPageHeight(self, headerWebPageHeight):
        """Set the height in pixels used by the converter's internal browser window during the conversion of the header content. The default value is 0px and it means that the page height is automatically calculated by the converter.

        ### Parameters

        - headerWebPageHeight: Browser window height in pixels. Set it to 0px to automatically calculate page height.

        ### Returns

        Reference to the current object.
        """

        self.parameters["header_web_page_height"] = headerWebPageHeight
        return self

    def setShowFooter(self, showFooter):
        """Control if a custom footer is displayed in the generated PDF document. The default value is False.

        ### Parameters

        - showFooter: Show footer or not.

        ### Returns

        Reference to the current object.
        """

        self.parameters["show_footer"] = showFooter
        return self

    def setFooterHeight(self, height):
        """The height of the pdf document footer. This height is specified in points. 1 point is 1/72 inch. The default value is 50.

        ### Parameters

        - height: Footer height.

        ### Returns

        Reference to the current object.
        """

        self.parameters["footer_height"] = height
        return self

    def setFooterUrl(self, url):
        """Set the url of the web page that is converted and rendered in the PDF document footer.

        ### Parameters

        - url: The url of the web page that is converted and rendered in the pdf document footer.

        ### Returns

        Reference to the current object.
        """

        if not url.startswith("http://") and not url.startswith("https://"):
            raise ApiException("The supported protocols for the converted webpage are http:// and https://.")
        
        if url.startswith("http://localhost"):
            raise ApiException("Cannot convert local urls. SelectPdf online API can only convert publicly available urls.")

        self.parameters["footer_url"] = url
        return self

    def setFooterHtml(self, html):
        """Set the raw html that is converted and rendered in the pdf document footer.

        ### Parameters

        - html: The raw html that is converted and rendered in the pdf document footer.

        ### Returns

        Reference to the current object.
        """

        self.parameters["footer_html"] = html
        return self

    def setFooterBaseUrl(self, baseUrl):
        """Set an optional base url parameter can be used together with the footer HTML to resolve relative paths from the html string.

        ### Parameters

        - baseUrl Footer base url.

        ### Returns

        Reference to the current object.
        """

        if not baseUrl.startswith("http://") and not baseUrl.startswith("https://"):
            raise ApiException("The supported protocols for the converted webpage are http:// and https://.")
        
        if baseUrl.startswith("http://localhost"):
            raise ApiException("Cannot convert local urls. SelectPdf online API can only convert publicly available urls.")

        self.parameters["footer_base_url"] = baseUrl
        return self

    def setFooterDisplayOnFirstPage(self, displayOnFirstPage):
        """Control the visibility of the footer on the first page of the generated pdf document. The default value is True.

        ### Parameters

        - displayOnFirstPage: Display footer on the first page or not.

        ### Returns

        Reference to the current object.
        """

        self.parameters["footer_display_on_first_page"] = displayOnFirstPage
        return self

    def setFooterDisplayOnOddPages(self, displayOnOddPages):
        """Control the visibility of the footer on the odd numbered pages of the generated pdf document. The default value is True.

        ### Parameters

        - displayOnOddPages: Display footer on odd pages or not.

        ### Returns

        Reference to the current object.
        """

        self.parameters["footer_display_on_odd_pages"] = displayOnOddPages
        return self

    def setFooterDisplayOnEvenPages(self, displayOnEvenPages):
        """Control the visibility of the footer on the even numbered pages of the generated pdf document. The default value is True.

        ### Parameters

        - displayOnEvenPages: Display footer on even pages or not.

        ### Returns

        Reference to the current object.
        """

        self.parameters["footer_display_on_even_pages"] = displayOnEvenPages
        return self

    def setFooterDisplayOnLastPage(self, displayOnLastPage):
        """
        Add a special footer on the last page of the generated pdf document only. The default value is False. 
        Use setFooterUrl or setFooterHtml and setFooterBaseUrl to specify the content of the last page footer. 
        Use setFooterHeight to specify the height of the special last page footer.

        ### Parameters

        - displayOnLastPage: Display special footer on the last page or not.

        ### Returns

        Reference to the current object.
        """

        self.parameters["footer_display_on_last_page"] = displayOnLastPage
        return self

    def setFooterWebPageWidth(self, footerWebPageWidth):
        """Set the width in pixels used by the converter's internal browser window during the conversion of the footer content. The default value is 1024px.

        ### Parameters

        - footerWebPageWidth: Browser window width in pixels.

        ### Returns

        Reference to the current object.
        """

        self.parameters["footer_web_page_width"] = footerWebPageWidth
        return self
    
    def setFooterWebPageHeight(self, footerWebPageHeight):
        """Set the height in pixels used by the converter's internal browser window during the conversion of the footer content. The default value is 0px and it means that the page height is automatically calculated by the converter.

        ### Parameters

        - footerWebPageHeight: Browser window height in pixels. Set it to 0px to automatically calculate page height.

        ### Returns

        Reference to the current object.
        """

        self.parameters["footer_web_page_height"] = footerWebPageHeight
        return self

    def setShowPageNumbers(self, showPageNumbers):
        """Show page numbers. Default value is True. Page numbers will be displayed in the footer of the PDF document.

        ### Parameters

        - showPageNumbers: Show page numbers or not.

        ### Returns

        Reference to the current object.
        """

        self.parameters["page_numbers"] = showPageNumbers
        return self

    def setPageNumbersFirst(self, firstPageNumber):
        """Control the page number for the first page being rendered. The default value is 1.

        ### Parameters

        - firstPageNumber: First page number.

        ### Returns

        Reference to the current object.
        """

        self.parameters["page_numbers_first"] = firstPageNumber
        return self

    def setPageNumbersOffset(self, totalPagesOffset):
        """Control the total number of pages offset in the generated pdf document. The default value is 0.

        ### Parameters

        - totalPagesOffset: Offset for the total number of pages in the generated pdf document.

        ### Returns

        Reference to the current object.
        """

        self.parameters["page_numbers_offset"] = totalPagesOffset
        return self

    def setPageNumbersTemplate(self, template):
        """Set the text that is used to display the page numbers. It can contain the placeholder {page_number} for the current page number and {total_pages} 
        for the total number of pages. The default value is "Page: {page_number} of {total_pages}".

        ### Parameters

        - template: Page numbers template.

        ### Returns

        Reference to the current object.
        """

        self.parameters["page_numbers_template"] = template
        return self

    def setPageNumbersFontName(self, fontName):
        """Set the font used to display the page numbers text. The default value is "Helvetica".

        ### Parameters

        - fontName: The font used to display the page numbers text.

        ### Returns

        Reference to the current object.
        """

        self.parameters["page_numbers_font_name"] = fontName
        return self

    def setPageNumbersFontSize(self, fontSize):
        """Set the size of the font used to display the page numbers. The default value is 10 points.

        ### Parameters

        - fontSize: The size in points of the font used to display the page numbers.

        ### Returns

        Reference to the current object.
        """

        self.parameters["page_numbers_font_size"] = fontSize
        return self

    def setPageNumbersAlignment(self, alignment):
        """Set the alignment of the page numbers text. The default value is "2" - PageNumbersAlignment.Right.

        ### Parameters

        - alignment" The alignment of the page numbers text. Possible values: 1 (Left), 2 (Center), 3 (Right). Use constants from selectpdf.PageNumbersAlignment class.

        ### Returns

        Reference to the current object.
        """

        if alignment != 1 and alignment != 2 and alignment != 3:
            raise ApiException("Allowed values for Page Numbers Alignment: 1 (Left), 2 (Center), 3 (Right).")

        self.parameters["page_numbers_alignment"] = alignment
        return self

    def setPageNumbersColor(self, color):
        """Specify the color of the page numbers text in #RRGGBB html format. The default value is #333333.

        ### Parameters

        - color: Page numbers color.

        ### Returns

        Reference to the current object.
        """

        if not re.match('^#?[0-9a-fA-F]{6}$', color):
            raise ApiException("Color value must be in #RRGGBB format.")

        self.parameters["page_numbers_color"] = color
        return self

    def setPageNumbersVerticalPosition(self, position):
        """Specify the position in points on the vertical where the page numbers text is displayed in the footer. The default value is 10 points.

        ### Parameters

        - position: Page numbers Y position in points.

        ### Returns

        Reference to the current object.
        """

        self.parameters["page_numbers_pos_y"] = position
        return self

    def setPdfBookmarksSelectors(self, selectors):
        """Generate automatic bookmarks in pdf. The elements that will be bookmarked are defined using CSS selectors. 
        For example, the selector for all the H1 elements is "H1", the selector for all the elements with the CSS class name 'myclass' is "*.myclass" and 
        the selector for the elements with the id 'myid' is "*#myid". 
        Read more about CSS selectors <a href="http://www.w3schools.com/cssref/css_selectors.asp" target="_blank">here</a>.

        ### Parameters

        - selectors: CSS selectors used to identify HTML elements, comma separated.

        ### Returns

        Reference to the current object.
        """

        self.parameters["pdf_bookmarks_selectors"] = selectors
        return self

    def setPdfHideElements(self, selectors):
        """Exclude page elements from the conversion. The elements that will be excluded are defined using CSS selectors. 
        For example, the selector for all the H1 elements is "H1", the selector for all the elements with the CSS class name 'myclass' is "*.myclass" and 
        the selector for the elements with the id 'myid' is "*#myid". 
        Read more about CSS selectors <a href="http://www.w3schools.com/cssref/css_selectors.asp" target="_blank">here</a>.

        ### Parameters

        - selectors: CSS selectors used to identify HTML elements, comma separated.

        ### Returns

        Reference to the current object.
        """

        self.parameters["pdf_hide_elements"] = selectors
        return self

    def setPdfShowOnlyElementID(self, elementID):
        """Convert only a specific section of the web page to pdf. The section that will be converted to pdf is specified by the html element ID. 
        The element can be anything (image, table, table row, div, text, etc).

        ### Parameters

        - elementID: HTML element ID.

        ### Returns

        Reference to the current object.
        """

        self.parameters["pdf_show_only_element_id"] = elementID
        return self

    def setPdfWebElementsSelectors(self, selectors):
        """Get the locations of page elements from the conversion. The elements that will have their locations retrieved are defined using CSS selectors.  
        For example, the selector for all the H1 elements is "H1", the selector for all the elements with the CSS class name 'myclass' is "*.myclass" and 
        the selector for the elements with the id 'myid' is "*#myid". 
        Read more about CSS selectors <a href="http://www.w3schools.com/cssref/css_selectors.asp" target="_blank">here</a>.

        ### Parameters

        - selectors: CSS selectors used to identify HTML elements, comma separated.

        ### Returns

        Reference to the current object.
        """

        self.parameters["pdf_web_elements_selectors"] = selectors
        return self

    def setStartupMode(self, startupMode):
        """Set converter startup mode. The default value is StartupMode.Automatic and the conversion is started immediately. 
        By default this is set to StartupMode.Automatic and the conversion is started as soon as the page loads (and conversion delay set with setConversionDelay elapses). 
        If set to StartupMode.Manual, the conversion is started only by a javascript call to SelectPdf.startConversion() from within the web page.

        ### Parameters

        - startupMode: Converter startup mode. Possible values: Automatic, Manual. Use constants from selectpdf.StartupMode class.

        ### Returns

        Reference to the current object.
        """

        if not re.match('(?i)^(Automatic|Manual)$', startupMode):
            raise ApiException("Allowed values for Startup Mode: Automatic, Manual.")

        self.parameters["startup_mode"] = startupMode
        return self

    def setSkipDecoding(self, skipDecoding):
        """Internal use only.

        ### Parameters

        - skipDecoding: The default value is True.

        ### Returns

        Reference to the current object.
        """

        self.parameters["skip_decoding"] = skipDecoding
        return self

    def setScaleImages(self, scaleImages):
        """Set a flag indicating if the images from the page are scaled during the conversion process. The default value is False and images are not scaled.

        ### Parameters

        - scaleImages: Scale images or not.

        ### Returns

        Reference to the current object.
        """

        self.parameters["scale_images"] = scaleImages
        return self

    def setSinglePagePdf(self, generateSinglePagePdf):
        """Generate a single page PDF. The converter will automatically resize the PDF page to fit all the content in a single page. 
        The default value of this property is False and the PDF will contain several pages if the content is large.

        ### Parameters

        - generateSinglePagePdf: Generate a single page PDF or not.

        ### Returns

        Reference to the current object.
        """

        self.parameters["single_page_pdf"] = generateSinglePagePdf
        return self

    def setPageBreaksEnhancedAlgorithm(self, enableEnhancedPageBreaksAlgorithm):
        """Get or set a flag indicating if an enhanced custom page breaks algorithm is used. 
        The enhanced algorithm is a little bit slower but it will prevent the appearance of hidden text in the PDF when custom page breaks are used. 
        The default value for this property is False.

        ### Parameters

        - enableEnhancedPageBreaksAlgorithm: Enable enhanced page breaks algorithm or not.

        ### Returns

        Reference to the current object.
        """
        
        self.parameters["page_breaks_enhanced_algorithm"] = enableEnhancedPageBreaksAlgorithm
        return self

    def setCookies(self, cookies):
        """Set HTTP cookies for the web page being converted.

        ### Parameters

        - cookies: Dictionary with HTTP cookies that will be sent to the page being converted.

        ### Returns

        Reference to the current object.
        """
        
        self.parameters["cookies_string"] = urlencode(cookies)
        return self

    def setCustomParameter(self, parameterName, parameterValue):
        """Set a custom parameter. Do not use this method unless advised by SelectPdf.

        ### Parameters

        - parameterName: Parameter name.
        - parameterValue: Parameter value.

        ### Returns

        Reference to the current object.
        """
        
        self.parameters[parameterName] = parameterValue
        return self

    def getWebElements(self):
        """Get the locations of certain web elements. This is retrieved if pdf_web_elements_selectors parameter is set and elements were found to match the selectors.

        ### Returns

        Json with web elements locations.
        """

        webElementsClient = WebElementsClient(self.parameters["key"], self.jobId)
        webElementsClient.setApiEndpoint(self.apiWebElementsEndpoint)

        return webElementsClient.getWebElements()

class PdfMergeClient(ApiClient):
    """Pdf Merge with SelectPdf Online API."""

    def __init__(self, apiKey):    
        """Construct the Pdf Merge Client.

        ### Parameters

        - apiKey: API key.
        """

        super(PdfMergeClient, self).__init__()

        self.apiEndpoint = "https://selectpdf.com/api2/pdfmerge/"
        self.parameters["key"] = apiKey
        self.fileIdx = 0

    def addFile(self, inputPdf):
        """Add local PDF document to the list of input files.

        ### Parameters

        - inputPdf: Path to a local PDF file.

        ### Returns

        Reference to the current object.
        """
        
        self.fileIdx += 1

        self.files["file_" + str(self.fileIdx)] = inputPdf
        self.parameters.pop("url_" + str(self.fileIdx), None)
        self.parameters.pop("password_" + str(self.fileIdx), None)

        return self

    def addFileWithPassword(self, inputPdf, userPassword):
        """Add local PDF document to the list of input files.

        ### Parameters

        - inputPdf: Path to a local PDF file.
        - userPassword: User password for the PDF document.

        ### Returns

        Reference to the current object.
        """
        
        self.fileIdx += 1

        self.files["file_" + str(self.fileIdx)] = inputPdf
        self.parameters.pop("url_" + str(self.fileIdx), None)
        self.parameters["password_" + str(self.fileIdx)] = userPassword

        return self

    def addUrlFile(self, inputUrl):
        """Add remote PDF document to the list of input files.

        ### Parameters

        - inputUrl: Url of a remote PDF file.

        ### Returns

        Reference to the current object.
        """
        
        self.fileIdx += 1 

        self.parameters["url_" + str(self.fileIdx)] = inputUrl
        self.parameters.pop("password_" + str(self.fileIdx), None)

        return self

    def addUrlFileWithPassword(self, inputUrl, userPassword):
        """Add remote PDF document to the list of input files.

        ### Parameters

        - inputUrl: Url of a remote PDF file.
        - userPassword: User password for the PDF document.

        ### Returns

        Reference to the current object.
        """
        
        self.fileIdx += 1

        self.parameters["url_" + str(self.fileIdx)] = inputUrl
        self.parameters["password_" + str(self.fileIdx)] = userPassword

        return self
    
    def save(self):
        """Merge all specified input pdfs and return the resulted PDF.

        ### Returns

        Byte array containing the resulted PDF.
        """
        
        self.parameters["async"] = "False"
        self.parameters["files_no"] = self.fileIdx

        result = self._performPostAsMultipartFormData()

        self.fileIdx = 0
        self.files = dict()

        return result

    def saveToFile(self, filePath):
        """Merge all specified input pdfs and writes the resulted PDF to a local file.

        ### Parameters

        - filePath: Local output file including path if necessary.
        """
        
        self.parameters["async"] = "False"
        self.parameters["files_no"] = self.fileIdx

        outputFile = open(filePath, 'wb')
        try:
            result = self._performPostAsMultipartFormData()

            outputFile.write(result)
            outputFile.close()

            self.fileIdx = 0
            self.files = dict()
        except ApiException:
            outputFile.close()
            os.remove(filePath)

            self.fileIdx = 0
            self.files = dict()

            raise

    def saveToStream(self, stream):
        """Merge all specified input pdfs and writes the resulted PDF to a specified stream.

        ### Parameters

        - stream: The output stream where the resulted PDF will be written.
        """
        
        self.parameters["async"] = "False"
        self.parameters["files_no"] = self.fileIdx

        result = self._performPostAsMultipartFormData()
        stream.write(result)

        self.fileIdx = 0
        self.files = dict()

    def saveAsync(self):
        """Merge all specified input pdfs and return the resulted PDF. An asynchronous call is used.

        ### Returns

        Resulted PDF.
        """

        self.parameters["files_no"] = self.fileIdx
        
        JobID = self._startAsyncJobMultipartFormData()

        if not JobID:
            raise ApiException("An error occurred launching the asynchronous call.")

        noPings = 0

        while (noPings < self.AsyncCallsMaxPings):
            noPings += 1

            # sleep for a few seconds before next ping
            time.sleep(self.AsyncCallsPingInterval)

            asyncJobClient = AsyncJobClient(self.parameters["key"], JobID)
            asyncJobClient.setApiEndpoint(self.apiAsyncEndpoint)

            result = asyncJobClient.getResult()

            if asyncJobClient.finished():
                self.numberOfPages = asyncJobClient.getNumberOfPages()

                self.fileIdx = 0
                self.files = dict()

                return result

        self.fileIdx = 0
        self.files = dict()

        raise ApiException("Asynchronous call did not finish in expected timeframe.")

    def saveToFileAsync(self, filePath):
        """Merge all specified input pdfs and writes the resulted PDF to a local file. An asynchronous call is used.

        ### Parameters

        - filePath: Local file including path if necessary.
        """

        outputFile = open(filePath, 'wb')
        try:
            result = self.saveAsync()
            outputFile.write(result)
            outputFile.close()
        except ApiException:
            outputFile.close()
            os.remove(filePath)
            raise

    def saveToStreamAsync(self, stream):
        """Merge all specified input pdfs and writes the resulted PDF to a specified stream. An asynchronous call is used.

        ### Parameters

        - stream: The output stream where the resulted PDF will be written.
        """

        result = self.saveAsync()
        stream.write(result)

    def setDocTitle(self, docTitle):
        """Set the PDF document title.

        ### Parameters

        - docTitle: Document title.

        ### Returns

        Reference to the current object.
        """

        self.parameters["doc_title"] = docTitle
        return self

    def setDocSubject(self, docSubject):
        """Set the subject of the PDF document.

        ### Parameters

        - docSubject: Document subject.

        ### Returns

        Reference to the current object.
        """

        self.parameters["doc_subject"] = docSubject
        return self

    def setDocKeywords(self, docKeywords):
        """Set the PDF document keywords.

        ### Parameters

        - docKeywords: Document keywords.

        ### Returns

        Reference to the current object.
        """

        self.parameters["doc_keywords"] = docKeywords
        return self

    def setDocAuthor(self, docAuthor):
        """Set the name of the PDF document author.

        ### Parameters

        - docAuthor: Document author.

        ### Returns

        Reference to the current object.
        """

        self.parameters["doc_author"] = docAuthor
        return self

    def setDocAddCreationDate(self, docAddCreationDate):
        """Add the date and time when the PDF document was created to the PDF document information. The default value is False.

        ### Parameters

        - docAddCreationDate: Add creation date to the document metadata or not.

        ### Returns

        Reference to the current object.
        """

        self.parameters["doc_add_creation_date"] = docAddCreationDate
        return self

    def setViewerPageLayout(self, pageLayout):
        """Set the page layout to be used when the document is opened in a PDF viewer. The default value is 1 - OneColumn.

        ### Parameters

        - pageLayout: Page layout. Possible values: 0 (Single Page), 1 (One Column), 2 (Two Column Left), 3 (Two Column Right). Use constants from selectpdf.PageLayout class.

        ### Returns

        Reference to the current object.
        """

        if pageLayout != 0 and pageLayout != 1 and pageLayout != 2 and pageLayout != 3:
            raise ApiException("Allowed values for Page Layout: 0 (Single Page), 1 (One Column), 2 (Two Column Left), 3 (Two Column Right).")

        self.parameters["viewer_page_layout"] = pageLayout
        return self

    def setViewerPageMode(self, pageMode):
        """Set the document page mode when the pdf document is opened in a PDF viewer. The default value is 0 - UseNone.

        ### Parameters

        - pageMode: Page mode. Possible values: 0 (Use None), 1 (Use Outlines), 2 (Use Thumbs), 3 (Full Screen), 4 (Use OC), 5 (Use Attachments). Use constants from selectpdf.PageMode class.

        ### Returns

        Reference to the current object.
        """

        if pageMode != 0 and pageMode != 1 and pageMode != 2 and pageMode != 3 and pageMode != 4 and pageMode != 5:
            raise ApiException("Allowed values for Page Mode: 0 (Use None), 1 (Use Outlines), 2 (Use Thumbs), 3 (Full Screen), 4 (Use OC), 5 (Use Attachments).")

        self.parameters["viewer_page_mode"] = pageMode
        return self

    def setViewerCenterWindow(self, viewerCenterWindow):
        """Set a flag specifying whether to position the document's window in the center of the screen. The default value is False.

        ### Parameters

        - viewerCenterWindow: Center window or not.

        ### Returns

        Reference to the current object.
        """

        self.parameters["viewer_center_window"] = viewerCenterWindow
        return self

    def setViewerDisplayDocTitle(self, viewerDisplayDocTitle):
        """Set a flag specifying whether the window's title bar should display the document title taken from document information. The default value is False.

        ### Parameters

        - viewerDisplayDocTitle: Display title or not.

        ### Returns

        Reference to the current object.
        """

        self.parameters["viewer_display_doc_title"] = viewerDisplayDocTitle
        return self

    def setViewerFitWindow(self, viewerFitWindow):
        """Set a flag specifying whether to resize the document's window to fit the size of the first displayed page. The default value is False.

        ### Parameters

        - viewerFitWindow: Fit window or not.

        ### Returns

        Reference to the current object.
        """

        self.parameters["viewer_fit_window"] = viewerFitWindow
        return self

    def setViewerHideMenuBar(self, viewerHideMenuBar):
        """Set a flag specifying whether to hide the pdf viewer application's menu bar when the document is active. The default value is False.

        ### Parameters

        - viewerHideMenuBar: Hide menu bar or not.

        ### Returns

        Reference to the current object.
        """

        self.parameters["viewer_hide_menu_bar"] = viewerHideMenuBar
        return self

    def setViewerHideToolbar(self, viewerHideToolbar):
        """Set a flag specifying whether to hide the pdf viewer application's tool bars when the document is active. The default value is False.

        ### Parameters

        - viewerHideToolbar: Hide tool bars or not.

        ### Returns

        Reference to the current object.
        """

        self.parameters["viewer_hide_toolbar"] = viewerHideToolbar
        return self

    def setViewerHideWindowUI(self, viewerHideWindowUI):
        """Set a flag specifying whether to hide user interface elements in the document's window (such as scroll bars and navigation controls), leaving only the document's contents displayed.

        ### Parameters

        - viewerHideWindowUI: Hide window UI or not.

        ### Returns

        Reference to the current object.
        """

        self.parameters["viewer_hide_window_ui"] = viewerHideWindowUI
        return self

    def setUserPassword(self, userPassword):
        """Set PDF user password.

        ### Parameters

        - userPassword: PDF user password.

        ### Returns

        Reference to the current object.
        """

        self.parameters["user_password"] = userPassword
        return self

    def setOwnerPassword(self, ownerPassword):
        """Set PDF owner password.

        ### Parameters

        - ownerPassword: PDF owner password.

        ### Returns

        Reference to the current object.
        """

        self.parameters["owner_password"] = ownerPassword
        return self
        
    def setCustomParameter(self, parameterName, parameterValue):
        """Set a custom parameter. Do not use this method unless advised by SelectPdf.

        ### Parameters

        - parameterName: Parameter name.
        - parameterValues: Parameter value.

        ### Returns

        Reference to the current object.
        """
        
        self.parameters[parameterName] = parameterValue
        return self

    def setTimeout(self, timeout):
        """
        Set the maximum amount of time (in seconds) for this job.
        The default value is 30 seconds. 
        Use a larger value (up to 120 seconds allowed) for pages that take a long time to load.

        ### Parameters

        - timeout: Timeout in seconds.

        ### Returns

        Reference to the current object.
        """

        self.parameters["timeout"] = timeout
        return self

class PdfToTextClient(ApiClient):
    """Pdf To Text Conversion with SelectPdf Online API."""

    def __init__(self, apiKey):    
        """Construct the Pdf To Text Client.

        ### Parameters

        - apiKey: API key.
        """

        super(PdfToTextClient, self).__init__()

        self.apiEndpoint = "https://selectpdf.com/api2/pdftotext/"
        self.parameters["key"] = apiKey
        self.fileIdx = 0

    def __format_text__(self, text):
        """Format text to UTF-8

        ### Parameters

        - text: Text to be formatted.

        ### Returns

        Formatted text.
        """

        if IS_PYTHON3:
            # Python 3
            try:
                return text.decode("utf-8").replace('\r', '')
            except AttributeError:
                pass
        else:
            # Python 2
            if isinstance(text, unicode):
                return text.encode('utf-8').replace('\r', '')
        return text.replace('\r', '')


    def getTextFromFile(self, inputPdf):
        """Get the text from the specified pdf.

        ### Parameters

        - inputPdf: Path to a local PDF file.

        ### Returns

        Extracted text.
        """

        self.parameters["async"] = False
        self.parameters["action"] = "Convert"
        self.parameters["url"] = ""

        self.files = dict()
        self.files["inputPdf"] = inputPdf

        result = self._performPostAsMultipartFormData()
        return self.__format_text__(result)

    def getTextFromFileToFile(self, inputPdf, outputFilePath):
        """Get the text from the specified pdf and write it to the specified text file.

        ### Parameters

        - inputPdf: Path to a local PDF file.
        - outputFilePath: The output file where the resulted text will be written.
        """

        outputFile = io.open(outputFilePath, 'w', encoding='utf-8')
        try:
            result = self.getTextFromFile(inputPdf)

            if IS_PYTHON3:
                outputFile.write(result)
            else:
                if isinstance(result, str):
                    outputFile.write(unicode(result, 'UTF-8'))
                else:
                    outputFile.write(result)

            outputFile.close()
        except ApiException:
            outputFile.close()
            os.remove(outputFilePath)
            raise

    def getTextFromFileToStream(self, inputPdf, stream):
        """Get the text from the specified pdf and write it to the specified stream.

        ### Parameters

        - inputPdf: Path to a local PDF file.
        - stream: The output stream where the resulted PDF will be written.
        """

        result = self.getTextFromFile(inputPdf)

        if IS_PYTHON3:
            stream.write(result)
        else:
            if isinstance(result, str):
                stream.write(unicode(result, 'UTF-8'))
            else:
                stream.write(result)

    def getTextFromFileAsync(self, inputPdf):
        """Get the text from the specified pdf with an asynchronous call.

        ### Parameters

        - inputPdf: Path to a local PDF file.

        ### Returns

        Extracted text.
        """

        self.parameters["action"] = "Convert"
        self.parameters["url"] = ""

        self.files = dict()
        self.files["inputPdf"] = inputPdf
        
        JobID = self._startAsyncJobMultipartFormData()

        if not JobID:
            raise ApiException("An error occurred launching the asynchronous call.")

        noPings = 0

        while (noPings < self.AsyncCallsMaxPings):
            noPings += 1

            # sleep for a few seconds before next ping
            time.sleep(self.AsyncCallsPingInterval)

            asyncJobClient = AsyncJobClient(self.parameters["key"], JobID)
            asyncJobClient.setApiEndpoint(self.apiAsyncEndpoint)

            result = asyncJobClient.getResult()

            if asyncJobClient.finished():
                self.numberOfPages = asyncJobClient.getNumberOfPages()

                return self.__format_text__(result)

        raise ApiException("Asynchronous call did not finish in expected timeframe.")

    def getTextFromFileToFileAsync(self, inputPdf, outputFilePath):
        """Get the text from the specified pdf with an asynchronous call and write it to the specified text file.

        ### Parameters

        - inputPdf: Path to a local PDF file.
        - outputFilePath: The output file where the resulted text will be written.
        """

        outputFile = io.open(outputFilePath, 'w', encoding='utf-8')
        try:
            result = self.getTextFromFileAsync(inputPdf)

            if IS_PYTHON3:
                outputFile.write(result)
            else:
                if isinstance(result, str):
                    outputFile.write(unicode(result, 'UTF-8'))
                else:
                    outputFile.write(result)

            outputFile.close()
        except ApiException:
            outputFile.close()
            os.remove(outputFilePath)
            raise

    def getTextFromFileToStreamAsync(self, inputPdf, stream):
        """Get the text from the specified pdf with an asynchronous call and write it to the specified stream.

        ### Parameters

        - inputPdf: Path to a local PDF file.
        - stream: The output stream where the resulted PDF will be written.
        """

        result = self.getTextFromFileAsync(inputPdf)

        if IS_PYTHON3:
            stream.write(result)
        else:
            if isinstance(result, str):
                stream.write(unicode(result, 'UTF-8'))
            else:
                stream.write(result)

    def getTextFromUrl(self, url):
        """Get the text from the specified pdf.

        ### Parameters

        - url: Address of the PDF file.

        ### Returns

        Extracted text.
        """

        if not url.startswith("http://") and not url.startswith("https://"):
            raise ApiException("The supported protocols for the PDFs available online are http:// and https://.")
        
        if url.startswith("http://localhost"):
            raise ApiException("Cannot convert local urls via this method. Use getTextFromFile instead.")

        self.parameters["async"] = False
        self.parameters["action"] = "Convert"
        self.parameters["url"] = url

        self.files = dict()

        result = self._performPostAsMultipartFormData()
        return self.__format_text__(result)

    def getTextFromUrlToFile(self, url, outputFilePath):
        """Get the text from the specified pdf and write it to the specified text file.

        ### Parameters

        - url: Address of the PDF file.
        - outputFilePath: The output file where the resulted text will be written.
        """

        outputFile = io.open(outputFilePath, 'w', encoding='utf-8')
        try:
            result = self.getTextFromUrl(url)

            if IS_PYTHON3:
                outputFile.write(result)
            else:
                if isinstance(result, str):
                    outputFile.write(unicode(result, 'UTF-8'))
                else:
                    outputFile.write(result)

            outputFile.close()
        except ApiException:
            outputFile.close()
            os.remove(outputFilePath)
            raise

    def getTextFromUrlToStream(self, url, stream):
        """Get the text from the specified pdf and write it to the specified stream.

        ### Parameters

        - url: Address of the PDF file.
        - stream: The output stream where the resulted PDF will be written.
        """

        result = self.getTextFromUrl(url)

        if IS_PYTHON3:
            stream.write(result)
        else:
            if isinstance(result, str):
                stream.write(unicode(result, 'UTF-8'))
            else:
                stream.write(result)

    def getTextFromUrlAsync(self, url):
        """Get the text from the specified pdf with an asynchronous call.

        ### Parameters

        - url: Address of the PDF file.

        ### Returns

        Extracted text.
        """

        if not url.startswith("http://") and not url.startswith("https://"):
            raise ApiException("The supported protocols for the PDFs available online are http:// and https://.")
        
        if url.startswith("http://localhost"):
            raise ApiException("Cannot convert local urls via this method. Use getTextFromFileAsync instead.")

        self.parameters["action"] = "Convert"
        self.parameters["url"] = url

        self.files = dict()
        
        JobID = self._startAsyncJobMultipartFormData()

        if not JobID:
            raise ApiException("An error occurred launching the asynchronous call.")

        noPings = 0

        while (noPings < self.AsyncCallsMaxPings):
            noPings += 1

            # sleep for a few seconds before next ping
            time.sleep(self.AsyncCallsPingInterval)

            asyncJobClient = AsyncJobClient(self.parameters["key"], JobID)
            asyncJobClient.setApiEndpoint(self.apiAsyncEndpoint)

            result = asyncJobClient.getResult()

            if asyncJobClient.finished():
                self.numberOfPages = asyncJobClient.getNumberOfPages()

                return self.__format_text__(result)

        raise ApiException("Asynchronous call did not finish in expected timeframe.")

    def getTextFromUrlToFileAsync(self, url, outputFilePath):
        """Get the text from the specified pdf with an asynchronous call and write it to the specified text file.

        ### Parameters

        - url: Address of the PDF file.
        - outputFilePath: The output file where the resulted text will be written.
        """

        outputFile = io.open(outputFilePath, 'w', encoding='utf-8')
        try:
            result = self.getTextFromUrlAsync(url)

            if IS_PYTHON3:
                outputFile.write(result)
            else:
                if isinstance(result, str):
                    outputFile.write(unicode(result, 'UTF-8'))
                else:
                    outputFile.write(result)

            outputFile.close()
        except ApiException:
            outputFile.close()
            os.remove(outputFilePath)
            raise

    def getTextFromUrlToStreamAsync(self, url, stream):
        """Get the text from the specified pdf with an asynchronous call and write it to the specified stream.

        ### Parameters

        - url: Address of the PDF file.
        - stream: The output stream where the resulted PDF will be written.
        """

        result = self.getTextFromUrlAsync(url)

        if IS_PYTHON3:
            stream.write(result)
        else:
            if isinstance(result, str):
                stream.write(unicode(result, 'UTF-8'))
            else:
                stream.write(result)

    def searchFile(self, inputPdf, textToSearch, caseSensitive=False, wholeWordsOnly=False):
        """Search for a specific text in a PDF document.
        Pages that participate to this operation are specified by setStartPage() and setEndPage() methods.

        ### Parameters

        - inputPdf: Path to a local PDF file.
        - textToSearch: Text to search.
        - caseSensitive: If the search is case sensitive or not.
        - wholeWordsOnly: If the search works on whole words or not.

        ### Returns

        List with text positions in the current PDF document.
        """

        if not textToSearch:
            raise ApiException("Search text cannot be empty.")

        self.parameters["async"] = "False"
        self.parameters["action"] = "Search"
        self.parameters["url"] = ""
        self.parameters["search_text"] = textToSearch
        self.parameters["case_sensitive"] = caseSensitive
        self.parameters["whole_words_only"] = wholeWordsOnly

        self.files = dict()
        self.files["inputPdf"] = inputPdf

        self.headers["Accept"] = "text/json"

        result = self._performPostAsMultipartFormData()
        if result:
            return json.loads(result)
        else:
            return []

    def searchFileAsync(self, inputPdf, textToSearch, caseSensitive=False, wholeWordsOnly=False):
        """Search for a specific text in a PDF document with an asynchronous call.
        Pages that participate to this operation are specified by setStartPage() and setEndPage() methods.

        ### Parameters

        - inputPdf: Path to a local PDF file.
        - textToSearch: Text to search.
        - caseSensitive: If the search is case sensitive or not.
        - wholeWordsOnly: If the search works on whole words or not.

        ### Returns

        List with text positions in the current PDF document.
        """

        if not textToSearch:
            raise ApiException("Search text cannot be empty.")

        self.parameters["action"] = "Search"
        self.parameters["url"] = ""
        self.parameters["search_text"] = textToSearch
        self.parameters["case_sensitive"] = caseSensitive
        self.parameters["whole_words_only"] = wholeWordsOnly

        self.files = dict()
        self.files["inputPdf"] = inputPdf

        self.headers["Accept"] = "text/json"

        JobID = self._startAsyncJobMultipartFormData()

        if not JobID:
            raise ApiException("An error occurred launching the asynchronous call.")

        noPings = 0

        while (noPings < self.AsyncCallsMaxPings):
            noPings += 1

            # sleep for a few seconds before next ping
            time.sleep(self.AsyncCallsPingInterval)

            asyncJobClient = AsyncJobClient(self.parameters["key"], JobID)
            asyncJobClient.setApiEndpoint(self.apiAsyncEndpoint)

            result = asyncJobClient.getResult()

            if asyncJobClient.finished():
                self.numberOfPages = asyncJobClient.getNumberOfPages()
                if result:
                    return json.loads(result)
                else:
                    return []

        raise ApiException("Asynchronous call did not finish in expected timeframe.")

    def searchUrl(self, url, textToSearch, caseSensitive=False, wholeWordsOnly=False):
        """Search for a specific text in a PDF document.
        Pages that participate to this operation are specified by setStartPage() and setEndPage() methods.

        ### Parameters

        - url: Address of the PDF file.
        - textToSearch: Text to search.
        - caseSensitive: If the search is case sensitive or not.
        - wholeWordsOnly: If the search works on whole words or not.

        ### Returns

        List with text positions in the current PDF document.
        """

        if not url.startswith("http://") and not url.startswith("https://"):
            raise ApiException("The supported protocols for the PDFs available online are http:// and https://.")
        
        if url.startswith("http://localhost"):
            raise ApiException("Cannot search local urls via this method. Use searchFile instead.")

        if not textToSearch:
            raise ApiException("Search text cannot be empty.")

        self.parameters["async"] = "False"
        self.parameters["action"] = "Search"
        self.parameters["search_text"] = textToSearch
        self.parameters["case_sensitive"] = caseSensitive
        self.parameters["whole_words_only"] = wholeWordsOnly

        self.files = dict()
        self.parameters["url"] = url

        self.headers["Accept"] = "text/json"

        result = self._performPostAsMultipartFormData()
        if result:
            return json.loads(result)
        else:
            return []

    def searchUrlAsync(self, url, textToSearch, caseSensitive=False, wholeWordsOnly=False):
        """Search for a specific text in a PDF document with an asynchronous call.
        Pages that participate to this operation are specified by setStartPage() and setEndPage() methods.

        ### Parameters

        - url: Address of the PDF file.
        - textToSearch: Text to search.
        - caseSensitive: If the search is case sensitive or not.
        - wholeWordsOnly: If the search works on whole words or not.

        ### Returns

        List with text positions in the current PDF document.
        """

        if not url.startswith("http://") and not url.startswith("https://"):
            raise ApiException("The supported protocols for the PDFs available online are http:// and https://.")
        
        if url.startswith("http://localhost"):
            raise ApiException("Cannot search local urls via this method. Use searchFileAsync instead.")

        if not textToSearch:
            raise ApiException("Search text cannot be empty.")

        self.parameters["action"] = "Search"
        self.parameters["search_text"] = textToSearch
        self.parameters["case_sensitive"] = caseSensitive
        self.parameters["whole_words_only"] = wholeWordsOnly

        self.files = dict()
        self.parameters["url"] = url

        self.headers["Accept"] = "text/json"

        JobID = self._startAsyncJobMultipartFormData()

        if not JobID:
            raise ApiException("An error occurred launching the asynchronous call.")

        noPings = 0

        while (noPings < self.AsyncCallsMaxPings):
            noPings += 1

            # sleep for a few seconds before next ping
            time.sleep(self.AsyncCallsPingInterval)

            asyncJobClient = AsyncJobClient(self.parameters["key"], JobID)
            asyncJobClient.setApiEndpoint(self.apiAsyncEndpoint)

            result = asyncJobClient.getResult()

            if asyncJobClient.finished():
                self.numberOfPages = asyncJobClient.getNumberOfPages()
                if result:
                    return json.loads(result)
                else:
                    return []

        raise ApiException("Asynchronous call did not finish in expected timeframe.")

    def setCustomParameter(self, parameterName, parameterValue):
        """Set a custom parameter. Do not use this method unless advised by SelectPdf.

        ### Parameters

        - parameterName: Parameter name.
        - parameterValues: Parameter value.

        ### Returns

        Reference to the current object.
        """
        
        self.parameters[parameterName] = parameterValue
        return self

    def setTimeout(self, timeout):
        """
        Set the maximum amount of time (in seconds) for this job.
        The default value is 30 seconds. 
        Use a larger value (up to 120 seconds allowed) for large documents.

        ### Parameters

        - timeout: Timeout in seconds.

        ### Returns

        Reference to the current object.
        """

        self.parameters["timeout"] = timeout
        return self

    def setStartPage(self, startPage):
        """
        Set Start Page number. Default value is 1 (first page of the document).

        ### Parameters

        - startPage: Start page number (1-based).

        ### Returns

        Reference to the current object.
        """

        self.parameters["start_page"] = startPage
        return self

    def setEndPage(self, endPage):
        """
        Set End Page number. Default value is 0 (process till the last page of the document).

        ### Parameters

        - endPage: End page number (1-based).

        ### Returns

        Reference to the current object.
        """

        self.parameters["end_page"] = endPage
        return self

    def setUserPassword(self, userPassword):
        """Set PDF user password.

        ### Parameters

        - userPassword: PDF user password.

        ### Returns

        Reference to the current object.
        """

        self.parameters["user_password"] = userPassword
        return self

    def setTextLayout(self, textLayout):
        """Set the text layout. The default value is 0 - TextLayout.Original.

        ### Parameters

        - textLayout: The text layout. Possible values: 0 (Original), 1 (Reading). Use constants from selectpdf.TextLayout class.

        ### Returns

        Reference to the current object.
        """

        if textLayout != 0 and textLayout != 1:
            raise ApiException("Allowed values for Text Layout: 0 (Original), 1 (Reading).")

        self.parameters["text_layout"] = textLayout
        return self

    def setOutputFormat(self, outputFormat):
        """Set the output format. The default value is 0 - OutputFormat.Text.

        ### Parameters

        - outputFormat: The output format. Possible values: 0 (Text), 1 (Html). Use constants from selectpdf.OutputFormat class.

        ### Returns

        Reference to the current object.
        """

        if outputFormat != 0 and outputFormat != 1:
            raise ApiException("Allowed values for Output Format: 0 (Text), 1 (Html).")

        self.parameters["output_format"] = outputFormat
        return self
