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

CLIENT_VERSION = '1.6.0'
"""SelectPdf Python client library version."""

DEMO_UPGRADE_URL = "https://selectpdf.com/pricing/"
"""Default upgrade URL displayed in demo mode error messages."""

def _toText(value):
    """Convert a parameter value to text (unicode on Python 3, UTF-8 encoded str on Python 2)."""

    if IS_PYTHON3:
        if isinstance(value, bytes):
            return value.decode('utf-8')
        return str(value)
    else:
        if isinstance(value, unicode):
            return value.encode('utf-8')
        return str(value)

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

class DemoRateLimitException(ApiException):
    """
    Raised when the demo endpoint refuses a request because of a rate limit (HTTP 429 or 503).
    Inspect the reason attribute to distinguish:

    - per_ip: the source IP exceeded its hourly conversion budget
    - concurrency: too many demo conversions are running right now
    - daily_cap: the global demo budget for today has been reached

    ### Attributes

    - statusCode: HTTP status code returned by the server (429 or 503).
    - reason: Machine-readable rate-limit reason: per_ip, concurrency or daily_cap.
    - retryAfter: Seconds the client should wait before retrying (parsed from the Retry-After header). Zero if absent.
    - upgradeUrl: URL the user can visit to upgrade out of demo mode.
    - responseBody: The raw JSON body the server returned, for diagnostics / logging.
    """

    def __init__(self, statusCode, reason, retryAfter, upgradeUrl, responseBody):
        self.statusCode = statusCode
        self.reason = reason if reason else ""
        self.retryAfter = retryAfter
        self.upgradeUrl = upgradeUrl if upgradeUrl else DEMO_UPGRADE_URL
        self.responseBody = responseBody

        retry = " Retry after {0}s.".format(retryAfter) if retryAfter > 0 else ""
        message = "Demo rate limit reached (reason={0}).{1} Upgrade at {2}.".format(reason if reason else "?", retry, self.upgradeUrl)

        super(DemoRateLimitException, self).__init__(message, statusCode)

class DemoSafetyException(ApiException):
    """
    Raised when the demo endpoint safety guard rejects a request because a URL field references a non-public host (HTTP 400).
    Inspect the field attribute for which parameter was rejected and the reason attribute for why.

    ### Attributes

    - statusCode: HTTP status code returned by the server (400).
    - field: Which input field was rejected: url, html, base_url, header_url, footer_url.
    - reason: Why the field was rejected: blocked_host, private_ip, loopback, link_local, cgnat, metadata, multicast, bad_scheme, bad_url, inline_internal_ref:&lt;sub-reason&gt;.
    - responseBody: The raw JSON body the server returned, for diagnostics / logging.
    """

    def __init__(self, statusCode, field, reason, responseBody):
        self.statusCode = statusCode
        self.field = field if field else ""
        self.reason = reason if reason else ""
        self.responseBody = responseBody

        message = "Demo safety guard rejected {0} (reason={1}). Demo conversions cannot fetch internal/private hosts.".format(
            field if field else "?", reason if reason else "?")

        super(DemoSafetyException, self).__init__(message, statusCode)

class DemoUnsupportedException(ApiException):
    """
    Raised when the caller tried to use a feature that demo mode does not support - most commonly PDF passwords (HTTP 400).
    For paid keys, this exception is never raised.

    ### Attributes

    - statusCode: HTTP status code returned by the server (400). Zero if the exception was raised by the local client guard before the request was sent.
    - field: Which feature is unsupported, for example user_password, owner_password, async.
    - upgradeUrl: URL the user can visit to upgrade out of demo mode.
    - responseBody: The raw JSON body the server returned, for diagnostics / logging. None when raised by the local client guard.
    """

    def __init__(self, field, statusCode=0, upgradeUrl=None, responseBody=None):
        self.statusCode = statusCode
        self.field = field if field else ""
        self.upgradeUrl = upgradeUrl if upgradeUrl else DEMO_UPGRADE_URL
        self.responseBody = responseBody

        if statusCode:
            message = "Feature '{0}' is not available in demo mode. Upgrade at {1}.".format(field if field else "?", self.upgradeUrl)
            super(DemoUnsupportedException, self).__init__(message, statusCode)
        else:
            message = "Feature '{0}' is not available in demo mode. Construct HtmlToPdfClient with a paid API key, or upgrade at {1}.".format(
                field if field else "?", DEMO_UPGRADE_URL)
            super(DemoUnsupportedException, self).__init__(message)

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
        self.creditsTotal = None
        self.creditsRemaining = None
        self.mode = ""
        self.executionMode = ""
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

    def getCreditsTotal(self):
        """Get the subscription monthly conversion limit reported by the server (X-SelectPdf-Credits-Total response header).

        ### Returns

        The monthly conversion limit. -1 means unlimited (Dedicated tier).
        None means the most recent response did not include credit information (for example demo endpoint or error response).
        """

        return self.creditsTotal

    def getCreditsRemaining(self):
        """Get the number of conversions remaining in the current month reported by the server (X-SelectPdf-Credits-Remaining response header).

        ### Returns

        The conversions remaining this month. -1 means unlimited (Dedicated tier).
        None means the most recent response did not include credit information.
        """

        return self.creditsRemaining

    def getMode(self):
        """Get the endpoint mode of the most recent response (X-SelectPdf-Mode response header).

        ### Returns

        "production" or "demo". Empty string when the response did not include the header (older server, or non-conversion endpoint).
        """

        return self.mode

    def getExecutionMode(self):
        """Get the server-side execution path of the most recent conversion (X-SelectPdf-Execution response header).

        ### Returns

        "in-process" or "worker". Empty string for endpoints that do not perform a conversion (for example Usage, WebElements).
        """

        return self.executionMode

    def _resetResults(self):
        """Reset the results of the previous API call."""

        self.numberOfPages = 0
        self.jobId = ""
        self.lastHTTPCode = 0
        self.creditsTotal = None
        self.creditsRemaining = None
        self.mode = ""
        self.executionMode = ""

    @staticmethod
    def _getHeader(headers, name):
        """Get a response header value (case insensitive). Returns None if the header is missing."""

        if headers is None:
            return None

        try:
            return headers.get(name)
        except Exception:
            return None

    @staticmethod
    def _parseInt(value):
        """Parse an integer header value. Returns None if the value is missing or invalid."""

        if not value:
            return None

        try:
            return int(value.strip())
        except (ValueError, AttributeError):
            return None

    def _readStandardResponseHeaders(self, headers):
        """Read the standard X-SelectPdf-* response headers."""

        pages = self._parseInt(self._getHeader(headers, "X-SelectPdf-Pages"))
        if pages is not None:
            self.numberOfPages = pages

        jobId = self._getHeader(headers, "X-SelectPdf-Job-Id")
        if jobId:
            self.jobId = jobId

        total = self._parseInt(self._getHeader(headers, "X-SelectPdf-Credits-Total"))
        if total is not None:
            self.creditsTotal = total

        remaining = self._parseInt(self._getHeader(headers, "X-SelectPdf-Credits-Remaining"))
        if remaining is not None:
            self.creditsRemaining = remaining

        mode = self._getHeader(headers, "X-SelectPdf-Mode")
        if mode:
            self.mode = mode

        executionMode = self._getHeader(headers, "X-SelectPdf-Execution")
        if executionMode:
            self.executionMode = executionMode

    def _onResponseHeadersReceived(self, headers):
        """Hook called after a successful response, with the raw response headers.
        Subclasses can override it to capture endpoint-specific headers. Default implementation does nothing.
        """

        pass

    def _handleResponse(self, code, headers, result, reason, outStream):
        """Process an API response: read the response headers and return the content (200),
        record the job id (202) or raise an exception (any other status code)."""

        self.lastHTTPCode = code

        if code == 200:
            self._readStandardResponseHeaders(headers)
            try:
                self._onResponseHeadersReceived(headers)
            except Exception:
                pass

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

        elif code == 202:
            # request accepted (for asynchronous jobs)
            self._readStandardResponseHeaders(headers)
            try:
                self._onResponseHeadersReceived(headers)
            except Exception:
                pass

            result.read()
            return None

        else:
            self._raiseError(code, headers, result.read(), reason)

    def _raiseError(self, code, headers, body, reason):
        """Raise the exception corresponding to an API error response."""

        self.lastHTTPCode = code

        message = body
        if IS_PYTHON3 and isinstance(message, bytes):
            message = message.decode('utf-8', 'replace')
        if not message:
            message = reason if reason else ""

        # The demo endpoint returns JSON error bodies for 400 / 413 / 429 / 503.
        # Parse those into typed exceptions so callers can react programmatically.
        contentType = self._getHeader(headers, "Content-Type") or ""
        if "application/json" in contentType.lower():
            demoException = self._tryBuildDemoException(code, message, headers)
            if demoException is not None:
                raise demoException

        raise ApiException(message, code)

    @staticmethod
    def _tryBuildDemoException(statusCode, body, headers):
        """Build a typed demo exception from a demo endpoint JSON error body. Returns None if the body is not a demo error.

        The demo endpoint returns structured JSON for 400 / 413 / 429 / 503 errors:

        - {"error":"rate_limited","reason":"per_ip","upgrade":"..."}
        - {"error":"unsafe_url","field":"url","reason":"private_ip"}
        - {"error":"unsupported_in_demo","field":"user_password","upgrade":"..."}
        - {"error":"body_too_large","max_bytes":1048576,"upgrade":"..."}
        """

        if not body:
            return None

        try:
            data = json.loads(body)
        except ValueError:
            return None

        if not isinstance(data, dict):
            return None

        def field(name):
            value = data.get(name)
            if value is None:
                return None
            if isinstance(value, bool):
                return "true" if value else "false"
            if isinstance(value, (int, float)):
                return str(value)
            return value

        error = field("error")
        if not error:
            return None

        reason = field("reason")
        fieldName = field("field")
        upgrade = field("upgrade")

        retryAfter = ApiClient._parseInt(ApiClient._getHeader(headers, "Retry-After"))
        if retryAfter is None:
            retryAfter = 0

        if error == "rate_limited":
            return DemoRateLimitException(statusCode, reason, retryAfter, upgrade, body)
        elif error == "unsafe_url":
            return DemoSafetyException(statusCode, fieldName, reason, body)
        elif error == "unsupported_in_demo":
            return DemoUnsupportedException(fieldName, statusCode, upgrade, body)
        elif error == "body_too_large":
            return ApiException("Demo request body exceeds the demo cap. Upgrade at {0}.".format(upgrade if upgrade else DEMO_UPGRADE_URL), statusCode)
        else:
            return None

    def _performPost(self, outStream=None):
        """Create a POST request.

        ### Parameters

        - outStream: Output response to this stream, if specified.

        ### Returns

        If output stream is not specified, return response as string.
        """

        self.headers["selectpdf-api-client"] = "python-{0}-{1}".format(platform.python_version(), CLIENT_VERSION)

        # reset results
        self._resetResults()

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

            try:
                return self._handleResponse(result.getcode(), result.info(), result, None, outStream)
            finally:
                result.close()

        except HTTPError as e:
            try:
                body = e.read()
            except Exception:
                body = None

            self._raiseError(e.code, e.info(), body, e.reason)

        except URLError as e:
            raise ApiException("Wrong url.")

    def _performPostAsMultipartFormData(self, outStream=None):
        """Create a multipart/form-data POST request (that can handle file uploads).

        ### Parameters

        - outStream: Output response to this stream, if specified.

        ### Returns

        If output stream is not specified, return response as string.
        """

        self.headers["selectpdf-api-client"] = "python-{0}-{1}".format(platform.python_version(), CLIENT_VERSION)

        # reset results
        self._resetResults()

        # serialize parameters
        byteData = self.__encodeMultipartFormData()

        allheaders = {
            "Content-type": "multipart/form-data; boundary=" + self.MULTIPART_FORM_DATA_BOUNDARY,
            "Content-length": str(len(byteData))
        }
        for k, v in self.headers.items():
            allheaders[k] = v

        url = urlparse(self.apiEndpoint)

        try:
            if self.apiEndpoint.startswith("http://"):
                connection = httplib.HTTPConnection(url.netloc, timeout=600) # timeout in seconds 600s=10minutes
            else:
                connection = httplib.HTTPSConnection(url.netloc, timeout=600) # timeout in seconds 600s=10minutes

            try:
                connection.request('POST', url.path, byteData, allheaders)
                result = connection.getresponse()

                return self._handleResponse(result.status, result.msg, result, result.reason, outStream)
            finally:
                connection.close()

        except socket.gaierror as e:
            raise ApiException("Wrong url.")

        except httplib.InvalidURL as e:
            raise ApiException("Wrong url.")

        except httplib.HTTPException as e:
            raise ApiException("Could not get a response from the API endpoint: {0}. {1}".format(self.apiEndpoint, e))

    def __encodeMultipartFormData(self):
        """Encode data for multipart/form-data POST"""

        allParameters, finalBoundary = [], []
        allData = []

        # encode regular parameters
        for key, value in self.parameters.items():
            allParameters.append('--' + self.MULTIPART_FORM_DATA_BOUNDARY)
            allParameters.append('Content-Disposition: form-data; name="%s"' % key)
            allParameters.append('')
            allParameters.append(_toText(value))

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

    def _waitForAsyncJob(self, jobId):
        """Poll the asynchronous job until it finishes and return its result.

        ### Parameters

        - jobId: Asynchronous job ID.

        ### Returns

        The result of the asynchronous job.
        """

        if not jobId:
            raise ApiException("An error occurred launching the asynchronous call.")

        noPings = 0

        while (noPings < self.AsyncCallsMaxPings):
            noPings += 1

            # sleep for a few seconds before next ping
            time.sleep(self.AsyncCallsPingInterval)

            asyncJobClient = AsyncJobClient(self.parameters["key"], jobId)
            asyncJobClient.setApiEndpoint(self.apiAsyncEndpoint)

            result = asyncJobClient.getResult()

            if asyncJobClient.finished():
                self.numberOfPages = asyncJobClient.getNumberOfPages()

                if asyncJobClient.getCreditsTotal() is not None:
                    self.creditsTotal = asyncJobClient.getCreditsTotal()
                if asyncJobClient.getCreditsRemaining() is not None:
                    self.creditsRemaining = asyncJobClient.getCreditsRemaining()

                return result

        raise ApiException("Asynchronous call did not finish in expected timeframe.")
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

    Chromium = "Chromium"
    """Chromium rendering engine."""

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

class PdfStandard:
    """
    PDF conformance target for the generated document.

    Tagged standards (PdfA3A) require the Blink or Chromium rendering engine.
    When no engine is specified the API promotes the request to Chromium and reports the engine used in the X-SelectPdf-Engine response header.
    """

    Full = "Full"
    """The complete PDF feature set. Default."""

    PdfA = "PdfA"
    """PDF/A - long term archiving."""

    PdfA2B = "PdfA2B"
    """PDF/A-2B - long term archiving, transparencies allowed."""

    PdfA3A = "PdfA3A"
    """PDF/A-3A - the accessible level of PDF/A-3. Implies a tagged document and can carry a ZUGFeRD / Factur-X electronic invoice."""

    PdfA3B = "PdfA3B"
    """PDF/A-3B - long term archiving with arbitrary embedded files. Can carry a ZUGFeRD / Factur-X electronic invoice."""

    PdfA3U = "PdfA3U"
    """PDF/A-3U - PDF/A-3B with Unicode mapping for all text. Can carry a ZUGFeRD / Factur-X electronic invoice."""

    PdfX = "PdfX"
    """PDF/X - graphics exchange."""

    PdfSiqQ_A = "PdfSiqQ_A"
    """PDF/SiqQ Level A - suitable for digital signatures, external links disabled."""

    PdfSiqQ_B = "PdfSiqQ_B"
    """PDF/SiqQ Level B - suitable for digital signatures."""

class ZugferdProfile:
    """
    The data profile of a ZUGFeRD / Factur-X hybrid electronic invoice.
    The profile determines how much of the EN 16931 semantic model the embedded XML carries.
    """

    Minimum = "Minimum"
    """MINIMUM - accounting information only. Not a complete invoice."""

    Basic_WL = "Basic_WL"
    """BASIC WL - header and footer data without invoice lines. Not a complete invoice."""

    Basic = "Basic"
    """BASIC - a subset of EN 16931 covering simple invoices, with lines."""

    En16931 = "En16931"
    """EN 16931 (formerly COMFORT) - the full European semantic standard."""

    Extended = "Extended"
    """EXTENDED - EN 16931 plus additional business terms."""

    XRechnung = "XRechnung"
    """XRECHNUNG - the German public-sector reference profile. The embedded file is named xrechnung.xml instead of factur-x.xml."""

class ZugferdRelationship:
    """
    How the embedded invoice XML relates to the visible invoice page.

    When not set, the API derives this from the profile: Alternative for Minimum and Basic_WL, Data for the rest.
    Minimum and Basic_WL combined with Data are rejected, because those profiles do not carry a complete invoice.
    """

    Data = "Data"
    """The XML and the visible page carry exactly the same invoice content. Mandatory in Germany for the Basic, En16931, Extended and XRechnung profiles."""

    Alternative = "Alternative"
    """The visible page carries more than the XML does - always the case for the Minimum and Basic_WL profiles - or the page was generated from the XML."""

    Source = "Source"
    """The XML is the source the visible page was produced from."""

    Supplement = "Supplement"
    """The XML supplements the visible page."""

class ZugferdSchema:
    """The metadata schema used to identify a hybrid invoice inside the PDF."""

    FacturX10 = "FacturX10"
    """Factur-X 1.0 / ZUGFeRD 2.x - the current schema. Default."""

    Zugferd20 = "Zugferd20"
    """ZUGFeRD 2.0 - the legacy schema, deprecated but still accepted. Use only for recipients that explicitly require it."""


class HtmlToPdfClient(ApiClient):
    """Html To Pdf Conversion with SelectPdf Online API."""

    PRODUCTION_ENDPOINT = "https://selectpdf.com/api2/convert/"
    """The production HTML to PDF endpoint."""

    DEMO_ENDPOINT = "https://selectpdf.com/api2/convert/demo/"
    """The keyless demo HTML to PDF endpoint."""

    def __init__(self, apiKey=None):
        """Construct the Html To Pdf Client.

        Pass a paid API key for production use. Pass None, an empty string or "demo" (case insensitive) to use the keyless demo endpoint -
        output is watermarked and capped at 5 pages, but no signup is required.

        ### Parameters

        - apiKey: API key. Defaults to None, which selects demo mode. Pass a real key for full unwatermarked output.
        """

        super(HtmlToPdfClient, self).__init__()

        self.clampedFields = []
        self.droppedFields = []

        demo = (not apiKey) or apiKey.strip().lower() == "demo"

        if demo:
            # Demo is keyless. The key parameter is not sent.
            self.apiEndpoint = self.DEMO_ENDPOINT
            self.demoMode = True
        else:
            self.apiEndpoint = self.PRODUCTION_ENDPOINT
            self.demoMode = False
            self.parameters["key"] = apiKey

    def isDemoMode(self):
        """Check if the client was constructed for the keyless demo endpoint (the API key was None, empty or "demo").
        Set at construction time and stable for the lifetime of the client. Calling setApiEndpoint does NOT change it.

        ### Returns

        True if the client is in demo mode.
        """

        return self.demoMode

    def isDemoResponse(self):
        """Check if the most recent response was tagged X-SelectPdf-Mode: demo (the request actually landed on a demo endpoint).

        ### Returns

        True if the most recent response came from the demo endpoint.
        """

        return bool(self.mode) and self.mode.lower() == "demo"

    def getClampedFields(self):
        """Get the names of the parameters the demo endpoint clamped on the most recent conversion (for example ["max_load_time", "engine"]).
        "Clamped" means the value was modified (capped, force-set), not discarded.

        ### Returns

        List of parameter names. Empty list if nothing was clamped or for non-demo responses.
        """

        return self.clampedFields

    def wasClamped(self):
        """Check if the most recent response had any clamped fields.

        ### Returns

        True if the demo endpoint clamped at least one parameter.
        """

        return len(self.clampedFields) > 0

    def getDroppedFields(self):
        """Get the names of the parameters the demo endpoint silently dropped on the most recent conversion (for example ["auth_username", "cookies"]).
        The demo endpoint refuses to honor a small set of fields for safety reasons - auth credentials, cookies, raw_parameters, pdf_name, async -
        and reports any caller-supplied value via the X-SelectPdf-Demo-Dropped response header.
        Distinct from getClampedFields: clamped = value modified, dropped = value thrown away.

        ### Returns

        List of parameter names. Empty list if nothing was dropped or for non-demo responses.
        """

        return self.droppedFields

    def wasAnyFieldDropped(self):
        """Check if the most recent response reported any dropped fields.

        ### Returns

        True if the demo endpoint dropped at least one parameter.
        """

        return len(self.droppedFields) > 0

    def _onResponseHeadersReceived(self, headers):
        """Capture the demo specific response headers (the demo clamped fields list and the demo dropped fields list)."""

        self.clampedFields = self._splitFields(self._getHeader(headers, "X-SelectPdf-Demo-Clamped"))
        self.droppedFields = self._splitFields(self._getHeader(headers, "X-SelectPdf-Demo-Dropped"))

    @staticmethod
    def _splitFields(raw):
        """Split a comma separated list of field names."""

        if not raw:
            return []

        return [part.strip() for part in raw.split(',')]

    def _ensureAsyncSupported(self):
        """Asynchronous conversions are not available on the keyless demo endpoint."""

        if self.demoMode:
            raise DemoUnsupportedException("async")

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

        self._ensureAsyncSupported()

        if not url.startswith("http://") and not url.startswith("https://"):
            raise ApiException("The supported protocols for the converted webpage are http:// and https://.")

        if url.startswith("http://localhost"):
            raise ApiException("Cannot convert local urls. SelectPdf online API can only convert publicly available urls.")

        self.parameters["url"] = url
        self.parameters["html"] = ""
        self.parameters["base_url"] = ""

        JobID = self._startAsyncJob()

        return self._waitForAsyncJob(JobID)

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

        self._ensureAsyncSupported()

        self.parameters["url"] = ""
        self.parameters["html"] = htmlString

        if baseUrl and baseUrl.strip():
            self.parameters["base_url"] = baseUrl

        JobID = self._startAsyncJob()

        return self._waitForAsyncJob(JobID)

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

        - pageSize: PDF page size. Possible values: Custom, A0, A1, A2, A3, A4, A5, A6, A7, A8, Letter, HalfLetter, Ledger, Legal. Use constants from selectpdf.PageSize class.

        ### Returns

        Reference to the current object.
        """

        if not re.match('(?i)^(Custom|A0|A1|A2|A3|A4|A5|A6|A7|A8|Letter|HalfLetter|Ledger|Legal)$', pageSize):
            raise ApiException("Allowed values for Page Size: Custom, A0, A1, A2, A3, A4, A5, A6, A7, A8, Letter, HalfLetter, Ledger, Legal.")

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

        if not re.match('(?i)^(WebKit|Restricted|Blink|Chromium)$', renderingEngine):
            raise ApiException("Allowed values for Rendering Engine: WebKit, Restricted, Blink, Chromium.")

        self.parameters["engine"] = renderingEngine
        return self

    def setTagged(self, tagged):
        """Produce a tagged, accessible PDF: a logical structure tree covering headings, paragraphs, lists, tables,
        figures with alternate text, links and reading order. Default is False.

        Requires the Blink or Chromium rendering engine - the WebKit engines cannot produce a structure tree.
        If no engine is set, the API promotes the request to Chromium and reports it in the X-SelectPdf-Engine response header.
        Setting an explicit WebKit engine together with tagged output is rejected by the API.

        A tagged document also needs a title, so set setDocTitle - the converter falls back to the HTML document title when it is not set.

        ### Parameters

        - tagged: Produce a tagged, accessible PDF.

        ### Returns

        Reference to the current object.
        """

        self.parameters["tagged"] = tagged
        return self

    def setPdfStandard(self, pdfStandard):
        """Set the PDF conformance target - PDF/A for archiving, PDF/X for graphics exchange, PDF/SiqQ for digital signatures. Default is Full.

        PdfA3A is the accessible level of PDF/A-3: it implies a tagged document, so it carries the same rendering engine requirement as setTagged.

        ### Parameters

        - pdfStandard: PDF conformance target. Possible values: Full, PdfA, PdfA2B, PdfA3A, PdfA3B, PdfA3U, PdfX, PdfSiqQ_A, PdfSiqQ_B. Use constants from selectpdf.PdfStandard class.

        ### Returns

        Reference to the current object.
        """

        if not re.match('(?i)^(Full|PdfA|PdfA2B|PdfA3A|PdfA3B|PdfA3U|PdfX|PdfSiqQ_A|PdfSiqQ_B)$', pdfStandard):
            raise ApiException("Allowed values for Pdf Standard: Full, PdfA, PdfA2B, PdfA3A, PdfA3B, PdfA3U, PdfX, PdfSiqQ_A, PdfSiqQ_B.")

        self.parameters["pdf_standard"] = pdfStandard
        return self

    def setDocumentLanguage(self, documentLanguage):
        """Set the natural language of the document, for example "en-US" or "de-DE".
        Written as the PDF /Lang entry and onto tagged structure elements. Default is "en-US".

        ### Parameters

        - documentLanguage: Language tag, for example "en-US".

        ### Returns

        Reference to the current object.
        """

        self.parameters["doc_language"] = documentLanguage
        return self

    def setUserPassword(self, userPassword):
        """Set PDF user password.

        ### Parameters

        - userPassword: PDF user password.

        ### Returns

        Reference to the current object.

        ### Raises

        DemoUnsupportedException if the client was constructed in demo mode.
        """

        if self.demoMode and userPassword:
            raise DemoUnsupportedException("user_password")

        self.parameters["user_password"] = userPassword
        return self

    def setOwnerPassword(self, ownerPassword):
        """Set PDF owner password.

        ### Parameters

        - ownerPassword: PDF owner password.

        ### Returns

        Reference to the current object.

        ### Raises

        DemoUnsupportedException if the client was constructed in demo mode.
        """

        if self.demoMode and ownerPassword:
            raise DemoUnsupportedException("owner_password")

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

    def setWebPageFixedSize(self, webPageFixedSize):
        """Leave out the content below the web page height (set with setWebPageHeight) instead of letting the page flow onto further pages.

        When not set, each rendering engine keeps its own behavior: WebKit and WebKit Restricted leave the content out whenever a web page height is set,
        Blink and Chromium convert the whole page. Set it to True or False to choose explicitly. It needs a non-zero web page height; with 0 there is no
        height to fix the page at and the setting is ignored. With WebKit, a fixed size also cuts off content wider than the web page width.

        ### Parameters

        - webPageFixedSize: True to cut the page at the web page height, False to convert the whole page.

        ### Returns

        Reference to the current object.
        """

        self.parameters["web_page_fixed_size"] = webPageFixedSize
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

    def setAuthUsername(self, authUsername):
        """Set the user name for HTTP Basic authentication on the web page being converted.

        Use it together with setAuthPassword. The demo endpoint does not send credentials; it reports the value in getDroppedFields.

        ### Parameters

        - authUsername: User name for HTTP Basic authentication.

        ### Returns

        Reference to the current object.
        """

        self.parameters["auth_username"] = authUsername
        return self

    def setAuthPassword(self, authPassword):
        """Set the password for HTTP Basic authentication on the web page being converted.

        Use it together with setAuthUsername. The demo endpoint does not send credentials; it reports the value in getDroppedFields.

        ### Parameters

        - authPassword: Password for HTTP Basic authentication.

        ### Returns

        Reference to the current object.
        """

        self.parameters["auth_password"] = authPassword
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

        ### Raises

        DemoUnsupportedException if the client was constructed in demo mode (the web elements service requires an API key).
        """

        if self.demoMode:
            raise DemoUnsupportedException("pdf_web_elements_selectors")

        webElementsClient = WebElementsClient(self.parameters["key"], self.jobId)
        webElementsClient.setApiEndpoint(self.apiWebElementsEndpoint)

        return webElementsClient.getWebElements()

class InvoiceClient(HtmlToPdfClient):
    """
    Create ZUGFeRD / Factur-X hybrid electronic invoices with SelectPdf Online API.

    A hybrid electronic invoice is one PDF/A-3 file carrying both halves of the invoice: the page a human reads,
    and the XML a recipient's accounting system reads. This client converts a url or an HTML string into the visible invoice
    and embeds the XML into it as an associated file, with the metadata invoice software looks for.

    It derives from HtmlToPdfClient, so every conversion setting - page size, margins, headers, footers, rendering engine - applies here too.
    Use the createFrom* methods rather than the inherited convert* methods: the invoice endpoint takes a multipart request,
    because the XML is uploaded as a file part.

    The carrier document must be PDF/A-3. The default is PdfStandard.PdfA3A, the accessible level, which the standards recommend
    because it makes the visible invoice readable by assistive technology as well as archivable. Because PdfA3A is a tagged standard,
    a request that does not set a rendering engine is promoted to Chromium by the API, which reports the engine used in the
    X-SelectPdf-Engine response header.

    There is no way to attach an invoice XML to an existing PDF you already have: the XML can only be embedded into a document created as PDF/A-3.
    """

    INVOICE_ENDPOINT = "https://selectpdf.com/api2/invoice/"
    """The production endpoint for hybrid electronic invoices."""

    def __init__(self, apiKey):
        """Construct the Invoice Client.

        Unlike HtmlToPdfClient, this client has no demo mode - the keyless demo endpoint does not produce electronic invoices - so an API key is required.

        ### Parameters

        - apiKey: API key.

        ### Raises

        ApiException if no API key is supplied.
        """

        if not apiKey or apiKey.strip().lower() == "demo":
            raise ApiException("An API key is required to create electronic invoices. The keyless demo endpoint does not support them.")

        super(InvoiceClient, self).__init__(apiKey)

        self.apiEndpoint = self.INVOICE_ENDPOINT

        # The carrier has to be PDF/A-3; default to the accessible level, which
        # the standards recommend. Overridable with setPdfStandard.
        self.parameters["pdf_standard"] = PdfStandard.PdfA3A

    def setInvoiceXmlFile(self, invoiceXmlFile):
        """Set the invoice XML from a local file.

        Only the content of the file is used - the name recorded inside the PDF is the one the standard prescribes
        ("factur-x.xml", or "xrechnung.xml" for the XRECHNUNG profile), because recipients look it up by name.

        ### Parameters

        - invoiceXmlFile: Path to the local invoice XML file.

        ### Returns

        Reference to the current object.
        """

        self.binaryData.pop("zugferd_xml", None)
        self.files["zugferd_xml"] = invoiceXmlFile
        return self

    def setInvoiceXml(self, invoiceXml):
        """Set the invoice XML from memory.

        ### Parameters

        - invoiceXml: The invoice XML, as bytes or as a string (a string is encoded as UTF-8).

        ### Returns

        Reference to the current object.
        """

        if IS_PYTHON3:
            if isinstance(invoiceXml, str):
                data = invoiceXml.encode('utf-8')
            else:
                data = bytes(invoiceXml)
        else:
            if isinstance(invoiceXml, unicode):
                data = invoiceXml.encode('utf-8')
            else:
                data = str(invoiceXml)

        self.files.pop("zugferd_xml", None)
        self.binaryData["zugferd_xml"] = data
        return self

    def setZugferdProfile(self, profile):
        """Set the data profile of the invoice XML. Required.

        ### Parameters

        - profile: The invoice data profile. Possible values: Minimum, Basic_WL, Basic, En16931, Extended, XRechnung. Use constants from selectpdf.ZugferdProfile class.

        ### Returns

        Reference to the current object.
        """

        if not re.match('(?i)^(Minimum|Basic_WL|Basic|En16931|Extended|XRechnung)$', profile):
            raise ApiException("Allowed values for Zugferd Profile: Minimum, Basic_WL, Basic, En16931, Extended, XRechnung.")

        self.parameters["zugferd_profile"] = profile
        return self

    def setZugferdRelationship(self, relationship):
        """Set how the embedded XML relates to the visible invoice page.

        Optional. When not set, the API derives it from the profile: Alternative for Minimum and Basic_WL,
        which do not carry a complete invoice, and Data for the rest. Those two profiles combined with Data are rejected by the API.

        ### Parameters

        - relationship: The relationship between XML and page. Possible values: Data, Alternative, Source, Supplement. Use constants from selectpdf.ZugferdRelationship class.

        ### Returns

        Reference to the current object.
        """

        if not re.match('(?i)^(Data|Alternative|Source|Supplement)$', relationship):
            raise ApiException("Allowed values for Zugferd Relationship: Data, Alternative, Source, Supplement.")

        self.parameters["zugferd_relationship"] = relationship
        return self

    def setZugferdSchema(self, schema):
        """Set the metadata schema identifying the invoice. Defaults to ZugferdSchema.FacturX10.

        ### Parameters

        - schema: The invoice metadata schema. Possible values: FacturX10, Zugferd20. Use constants from selectpdf.ZugferdSchema class.

        ### Returns

        Reference to the current object.
        """

        if not re.match('(?i)^(FacturX10|Zugferd20)$', schema):
            raise ApiException("Allowed values for Zugferd Schema: FacturX10, Zugferd20.")

        self.parameters["zugferd_schema"] = schema
        return self

    # --- synchronous -----------------------------------------------------

    def createFromUrl(self, url):
        """Create a hybrid electronic invoice from the invoice page at the specified url.

        ### Parameters

        - url: Url of the invoice page.

        ### Returns

        The resulted hybrid invoice PDF.
        """

        self._prepareUrl(url)
        self.parameters["async"] = False

        return self._performPostAsMultipartFormData()

    def createFromUrlToStream(self, url, stream):
        """Create a hybrid electronic invoice from the invoice page at the specified url and write it to an output stream.

        ### Parameters

        - url: Url of the invoice page.
        - stream: The output stream where the resulted PDF will be written.
        """

        self._prepareUrl(url)
        self.parameters["async"] = False

        return self._performPostAsMultipartFormData(stream)

    def createFromUrlToFile(self, url, filePath):
        """Create a hybrid electronic invoice from the invoice page at the specified url and write it to a local file.

        ### Parameters

        - url: Url of the invoice page.
        - filePath: Local file including path if necessary.
        """

        self._prepareUrl(url)

        outputFile = open(filePath, 'wb')
        try:
            self.createFromUrlToStream(url, outputFile)
            outputFile.close()
        except ApiException:
            outputFile.close()
            os.remove(filePath)
            raise

    def createFromHtmlString(self, htmlString):
        """Create a hybrid electronic invoice from a raw HTML string.

        ### Parameters

        - htmlString: The invoice HTML.

        ### Returns

        The resulted hybrid invoice PDF.
        """

        return self.createFromHtmlStringWithBaseUrl(htmlString, None)

    def createFromHtmlStringToStream(self, htmlString, stream):
        """Create a hybrid electronic invoice from a raw HTML string and write it to an output stream.

        ### Parameters

        - htmlString: The invoice HTML.
        - stream: The output stream where the resulted PDF will be written.
        """

        return self.createFromHtmlStringWithBaseUrlToStream(htmlString, None, stream)

    def createFromHtmlStringToFile(self, htmlString, filePath):
        """Create a hybrid electronic invoice from a raw HTML string and write it to a local file.

        ### Parameters

        - htmlString: The invoice HTML.
        - filePath: Local file including path if necessary.
        """

        return self.createFromHtmlStringWithBaseUrlToFile(htmlString, None, filePath)

    def createFromHtmlStringWithBaseUrl(self, htmlString, baseUrl):
        """Create a hybrid electronic invoice from a raw HTML string. Use a base url to resolve relative paths to resources.

        ### Parameters

        - htmlString: The invoice HTML.
        - baseUrl: Base url used to resolve relative paths in the HTML (css, images, etc). Must be a http:// or https:// publicly available url.

        ### Returns

        The resulted hybrid invoice PDF.
        """

        self._prepareHtml(htmlString, baseUrl)
        self.parameters["async"] = False

        return self._performPostAsMultipartFormData()

    def createFromHtmlStringWithBaseUrlToStream(self, htmlString, baseUrl, stream):
        """Create a hybrid electronic invoice from a raw HTML string and write it to an output stream. Use a base url to resolve relative paths to resources.

        ### Parameters

        - htmlString: The invoice HTML.
        - baseUrl: Base url used to resolve relative paths in the HTML (css, images, etc). Must be a http:// or https:// publicly available url.
        - stream: The output stream where the resulted PDF will be written.
        """

        self._prepareHtml(htmlString, baseUrl)
        self.parameters["async"] = False

        return self._performPostAsMultipartFormData(stream)

    def createFromHtmlStringWithBaseUrlToFile(self, htmlString, baseUrl, filePath):
        """Create a hybrid electronic invoice from a raw HTML string and write it to a local file. Use a base url to resolve relative paths to resources.

        ### Parameters

        - htmlString: The invoice HTML.
        - baseUrl: Base url used to resolve relative paths in the HTML (css, images, etc). Must be a http:// or https:// publicly available url.
        - filePath: Local file including path if necessary.
        """

        self._prepareHtml(htmlString, baseUrl)

        outputFile = open(filePath, 'wb')
        try:
            self.createFromHtmlStringWithBaseUrlToStream(htmlString, baseUrl, outputFile)
            outputFile.close()
        except ApiException:
            outputFile.close()
            os.remove(filePath)
            raise

    # --- asynchronous ----------------------------------------------------

    def createFromUrlAsync(self, url):
        """Create a hybrid electronic invoice from the invoice page at the specified url, using an asynchronous call.
        Recommended for long invoice pages or callers that cannot hold an HTTP connection open for the whole conversion.

        ### Parameters

        - url: Url of the invoice page.

        ### Returns

        The resulted hybrid invoice PDF.
        """

        self._prepareUrl(url)

        JobID = self._startAsyncJobMultipartFormData()

        return self._waitForAsyncJob(JobID)

    def createFromUrlToStreamAsync(self, url, stream):
        """Create a hybrid electronic invoice from the invoice page at the specified url, using an asynchronous call, and write it to an output stream.

        ### Parameters

        - url: Url of the invoice page.
        - stream: The output stream where the resulted PDF will be written.
        """

        result = self.createFromUrlAsync(url)
        stream.write(result)

    def createFromUrlToFileAsync(self, url, filePath):
        """Create a hybrid electronic invoice from the invoice page at the specified url, using an asynchronous call, and write it to a local file.

        ### Parameters

        - url: Url of the invoice page.
        - filePath: Local file including path if necessary.
        """

        result = self.createFromUrlAsync(url)

        with open(filePath, 'wb') as outputFile:
            outputFile.write(result)

    def createFromHtmlStringAsync(self, htmlString):
        """Create a hybrid electronic invoice from a raw HTML string, using an asynchronous call.

        ### Parameters

        - htmlString: The invoice HTML.

        ### Returns

        The resulted hybrid invoice PDF.
        """

        return self.createFromHtmlStringWithBaseUrlAsync(htmlString, None)

    def createFromHtmlStringToStreamAsync(self, htmlString, stream):
        """Create a hybrid electronic invoice from a raw HTML string, using an asynchronous call, and write it to an output stream.

        ### Parameters

        - htmlString: The invoice HTML.
        - stream: The output stream where the resulted PDF will be written.
        """

        return self.createFromHtmlStringWithBaseUrlToStreamAsync(htmlString, None, stream)

    def createFromHtmlStringToFileAsync(self, htmlString, filePath):
        """Create a hybrid electronic invoice from a raw HTML string, using an asynchronous call, and write it to a local file.

        ### Parameters

        - htmlString: The invoice HTML.
        - filePath: Local file including path if necessary.
        """

        return self.createFromHtmlStringWithBaseUrlToFileAsync(htmlString, None, filePath)

    def createFromHtmlStringWithBaseUrlAsync(self, htmlString, baseUrl):
        """Create a hybrid electronic invoice from a raw HTML string, using an asynchronous call. Use a base url to resolve relative paths to resources.

        ### Parameters

        - htmlString: The invoice HTML.
        - baseUrl: Base url used to resolve relative paths in the HTML (css, images, etc). Must be a http:// or https:// publicly available url.

        ### Returns

        The resulted hybrid invoice PDF.
        """

        self._prepareHtml(htmlString, baseUrl)

        JobID = self._startAsyncJobMultipartFormData()

        return self._waitForAsyncJob(JobID)

    def createFromHtmlStringWithBaseUrlToStreamAsync(self, htmlString, baseUrl, stream):
        """Create a hybrid electronic invoice from a raw HTML string, using an asynchronous call, and write it to an output stream.
        Use a base url to resolve relative paths to resources.

        ### Parameters

        - htmlString: The invoice HTML.
        - baseUrl: Base url used to resolve relative paths in the HTML (css, images, etc). Must be a http:// or https:// publicly available url.
        - stream: The output stream where the resulted PDF will be written.
        """

        result = self.createFromHtmlStringWithBaseUrlAsync(htmlString, baseUrl)
        stream.write(result)

    def createFromHtmlStringWithBaseUrlToFileAsync(self, htmlString, baseUrl, filePath):
        """Create a hybrid electronic invoice from a raw HTML string, using an asynchronous call, and write it to a local file.
        Use a base url to resolve relative paths to resources.

        ### Parameters

        - htmlString: The invoice HTML.
        - baseUrl: Base url used to resolve relative paths in the HTML (css, images, etc). Must be a http:// or https:// publicly available url.
        - filePath: Local file including path if necessary.
        """

        result = self.createFromHtmlStringWithBaseUrlAsync(htmlString, baseUrl)

        with open(filePath, 'wb') as outputFile:
            outputFile.write(result)

    # --- internals -------------------------------------------------------

    def _prepareUrl(self, url):
        """Validate the invoice page url and set the url parameters."""

        if not url.startswith("http://") and not url.startswith("https://"):
            raise ApiException("The supported protocols for the converted webpage are http:// and https://.")

        if url.startswith("http://localhost"):
            raise ApiException("Cannot convert local urls. SelectPdf online API can only convert publicly available urls.")

        self._requireInvoiceXml()

        self.parameters["url"] = url
        self.parameters["html"] = ""
        self.parameters["base_url"] = ""

    def _prepareHtml(self, htmlString, baseUrl):
        """Set the html parameters."""

        self._requireInvoiceXml()

        self.parameters["url"] = ""
        self.parameters["html"] = htmlString
        self.parameters["base_url"] = baseUrl if baseUrl else ""

    def _requireInvoiceXml(self):
        """Fail here rather than spending a round trip on a request the API will reject with the same message."""

        if "zugferd_xml" not in self.files and "zugferd_xml" not in self.binaryData:
            raise ApiException("The invoice XML was not specified. Call setInvoiceXmlFile or setInvoiceXml before creating the invoice.")

        if not self.parameters.get("zugferd_profile"):
            raise ApiException("The invoice profile was not specified. Call setZugferdProfile before creating the invoice.")

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
