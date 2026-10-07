# SelectPdf Online REST API - Python Client

SelectPdf Online REST API is a professional solution for managing PDF documents online. It now has a dedicated, easy to use, Python client library that can be setup in minutes.

## Try without an API key (demo mode)

```python
import selectpdf

# No API key -> keyless demo mode (5-page cap, watermarked output, Chromium engine).
client = selectpdf.HtmlToPdfClient() # also: selectpdf.HtmlToPdfClient("demo")
client.convertUrlToFile("https://example.com", "demo.pdf")
print("Pages: {0}".format(client.getNumberOfPages()))
if client.wasClamped():
    print("Server clamped: {0}".format(", ".join(client.getClampedFields())))
# Upgrade for unwatermarked, unlimited-page PDFs: https://selectpdf.com/pricing/
```

### Demo mode limitations

Demo mode is intended for evaluating the API. To keep the public endpoint stable and prevent abuse, several limits and restrictions apply that don't exist on a paid endpoint.

**Output:**

- **5 pages maximum.** Pages beyond the fifth are dropped, then a final branding/notice page is appended (so a typical demo PDF is 1-6 pages depending on the source).
- **Watermarked.** A diagonal SelectPdf demo stamp is rendered on every page plus a footer attribution line.
- **Chromium rendering engine only.** If you call `setRenderingEngine(...)` with `WebKit`, `Restricted` or `Blink`, the server silently force-clamps to `Chromium`. `client.wasClamped()` returns `True` and `client.getClampedFields()` includes `engine`.

**Parameters not allowed:**

| Parameter / method | Behavior in demo mode |
| --- | --- |
| `setUserPassword(...)` | Raises `DemoUnsupportedException` client-side (before the request is sent). |
| `setOwnerPassword(...)` | Same - raises `DemoUnsupportedException`. |
| `convert...Async(...)` | Raises `DemoUnsupportedException` client-side. The demo endpoint is synchronous only; there is no `/api2/asyncjob/` polling for demo conversions. |
| `getWebElements()` | Raises `DemoUnsupportedException` client-side. The web elements service requires an API key. |

The two time parameters are accepted but capped:

| Parameter | Production cap | Demo cap |
| --- | --- | --- |
| `setNavigationTimeout(...)` (`max_load_time`) | up to 120 s | clamped to **15 s** |
| `setConversionDelay(...)` (`min_load_time`) | up to 120 s | clamped to **5 s** |

When clamping happens, `client.wasClamped()` returns `True` and `client.getClampedFields()` lists the affected field names.

**Silently dropped fields:**

A few request fields are accepted but never honored by the demo endpoint. Any caller-supplied value is reported back via `client.wasAnyFieldDropped()` / `client.getDroppedFields()` so you can see what was ignored.

| Field | Reason |
| --- | --- |
| `auth_username` / `auth_password` | Would let demo callers send credentials to internal HTTP-Basic endpoints. |
| `cookies` (`setCookies(...)`) / `cookies_string` | Session-hijack vector if combined with a target inside our own infrastructure. |
| `raw_parameters` | Escape hatch that bypasses the parameter clamp. |
| `pdf_name` | Demo always returns inline `demo.pdf`. |
| `async` | Demo is sync-only. |

Distinct from the clamped fields: clamped means the value was modified (capped, force-set), dropped means it was thrown away.

**URLs:**

The demo endpoint accepts only publicly reachable `http://` / `https://` URLs. Requests targeting non-public destinations are rejected with `DemoSafetyException` (HTTP 400). Use a paid key if you need to convert content from a private network.

**Rate limits:**

| Layer | Default | Failure |
| --- | --- | --- |
| Per-IP | 30 requests / rolling hour | `DemoRateLimitException` with `reason="per_ip"`, `retryAfter` about 3600 |
| Daily global ceiling | 50,000 successful conversions / 24 h across all clients | `DemoRateLimitException` with `reason="daily_cap"` |
| Concurrency | 4 in-flight conversions globally | `DemoRateLimitException` with `reason="concurrency"`, `retryAfter` about 5 |

`retryAfter` is taken from the `Retry-After` response header. Both the per-IP and daily counters include rejected attempts, so retrying after a block doesn't reset anything.

**Request size:**

- **1 MB request body cap.** Larger payloads are rejected with HTTP 413 - typically only an issue if you're inlining a very large HTML string.

**Response:**

- No credit information (the demo endpoint is keyless, so there's no billing account to attribute usage to): `client.getCreditsTotal()` and `client.getCreditsRemaining()` return `None`.
- `client.getMode() == "demo"` (helper: `client.isDemoResponse()` returns `True`).
- `client.getExecutionMode()` is either `"in-process"` or `"worker"` depending on how the server was deployed.

### Catching demo mode errors

The client raises three typed exceptions for demo-specific failures. All of them derive from `selectpdf.ApiException`, so existing error handling keeps working:

```python
import selectpdf

try:
    client = selectpdf.HtmlToPdfClient() # demo mode
    pdf = client.convertUrl("https://example.com")

except selectpdf.DemoRateLimitException as ex:
    # reason: "per_ip" | "daily_cap" | "concurrency"
    print("Rate limited: {0}, retry after {1}s".format(ex.reason, ex.retryAfter))
    print("Upgrade: {0}".format(ex.upgradeUrl))

except selectpdf.DemoSafetyException as ex:
    # The supplied URL was rejected. Use a paid key for non-public targets.
    print("URL rejected: {0} (field={1}, reason={2})".format(ex.getMessage(), ex.field, ex.reason))

except selectpdf.DemoUnsupportedException as ex:
    # field: which parameter is unavailable in demo mode
    print("'{0}' not available in demo mode. Upgrade: {1}".format(ex.field, ex.upgradeUrl))

except selectpdf.ApiException as ex:
    print("An error occurred: {0}".format(ex.getMessage()))
```

| Exception | Attributes |
| --- | --- |
| `DemoRateLimitException` | `statusCode` (429 or 503), `reason`, `retryAfter` (seconds, 0 if absent), `upgradeUrl`, `responseBody` |
| `DemoSafetyException` | `statusCode` (400), `field` (`url`, `html`, `base_url`, `header_url`, `footer_url`), `reason`, `responseBody` |
| `DemoUnsupportedException` | `statusCode` (400, or 0 when raised by the client before the request is sent), `field`, `upgradeUrl`, `responseBody` |

For unwatermarked production output without these limits, pass a real API key - same client class, same methods:

```python
client = selectpdf.HtmlToPdfClient("Your API key here")
```

`client.isDemoMode()` is set at construction time and stable for the client's lifetime, so a client created with a real key never silently falls back to demo behavior.

## Installation

Download [selectpdf-api-python-client-1.6.0.zip](https://github.com/selectpdf/selectpdf-api-python-client/releases/download/1.6.0/selectpdf-api-python-client-1.6.0.zip), unzip it and run:

```
cd selectpdf-api-python-client-1.6.0
python setup.py install
```

OR

Install SelectPdf Python Client for Online API via PyPI: [SelectPdf on PyPI](https://pypi.python.org/pypi/selectpdf).

```
pip install selectpdf
```

OR

Clone [selectpdf-api-python-client](https://github.com/selectpdf/selectpdf-api-python-client) from Github and install the library.

```
git clone https://github.com/selectpdf/selectpdf-api-python-client
cd selectpdf-api-python-client
python setup.py install
```

## HTML To PDF API - Python Client

SelectPdf HTML To PDF Online REST API is a professional solution that lets you create PDF from web pages and raw HTML code in your applications. The API is easy to use and the integration takes only a few lines of code.

### Features

* Create PDF from any web page or html string.
* Full html5/css3/javascript support.
* Set PDF options such as page size and orientation, margins, security, web page settings.
* Set PDF viewer options and PDF document information.
* Create custom headers and footers for the pdf document.
* Hide web page elements during the conversion.
* Automatically generate bookmarks during the html to pdf conversion.
* Support for partial page conversion.
* Produce tagged, accessible PDF and target a PDF/A, PDF/X or PDF/SiqQ conformance level.
* Easy integration, no third party libraries needed.
* Works in all programming languages.
* No installation required.

Sign up for for free to get instant API access to SelectPdf [HTML to PDF API](https://selectpdf.com/html-to-pdf-api/).

### Sample Code

```python
# -*- coding: utf-8 -*-

import sys, json
import selectpdf

url = "https://selectpdf.com"
localFile = "Test.pdf"
apiKey = "Your API key here"

pythonVersion = "Python 3" if selectpdf.IS_PYTHON3 else "Python 2"
print ("This is SelectPdf-{0} using {1}.".format(selectpdf.CLIENT_VERSION, pythonVersion))

try:
    client = selectpdf.HtmlToPdfClient(apiKey)

    # set parameters - see full list at https://selectpdf.com/html-to-pdf-api/

    # main properties

    client.setPageSize(selectpdf.PageSize.A4) # PDF page size
    client.setPageOrientation(selectpdf.PageOrientation.Portrait) # PDF page orientation
    client.setMargins(0) # PDF page margins
    client.setRenderingEngine(selectpdf.RenderingEngine.WebKit) # rendering engine
    client.setConversionDelay(1) # conversion delay
    client.setNavigationTimeout(30) # navigation timeout
    client.setShowPageNumbers(False) # page numbers
    client.setPageBreaksEnhancedAlgorithm(True) # enhanced page break algorithm

    # additional properties
    
    # client.setUseCssPrint(True) # enable CSS media print
    # client.setDisableJavascript(True) # disable javascript
    # client.setDisableInternalLinks(True) # disable internal links
    # client.setDisableExternalLinks(True) # disable external links
    # client.setKeepImagesTogether(True) # keep images together
    # client.setScaleImages(True) # scale images to create smaller pdfs
    # client.setSinglePagePdf(True) # generate a single page PDF
    # client.setUserPassword("password") # secure the PDF with a password

    # generate automatic bookmarks

    # client.setPdfBookmarksSelectors("H1, H2") # create outlines (bookmarks) for the specified elements
    # client.setViewerPageMode(selectpdf.PageMode.UseOutlines) # display outlines (bookmarks) in viewer

    print ("Starting conversion ...")
    
    # convert url to file
    client.convertUrlToFile(url, localFile)

    # convert url to memory
    # pdf = client.convertUrl(url)

    # convert html string to file
    # client.convertHtmlStringToFile("This is some <b>html</b>.", localFile)

    # convert html string to memory
    # pdf = client.convertHtmlString("This is some <b>html</b>.")

    print ("Finished! Number of pages: {0}.".format(client.getNumberOfPages()))

    # get API usage
    usageClient = selectpdf.UsageClient(apiKey)
    usage = usageClient.getUsage()
    print("Conversions remained this month: {0}.".format(usage["available"]))

except selectpdf.ApiException as ex:
    print ("An error occurred: {0}.".format(ex.getMessage()))

```

### More HtmlToPdfClient settings

* `setWebPageFixedSize(True)` - leave out the content below the web page height (set with `setWebPageHeight`) instead of letting the page flow onto further pages. `False` converts the whole page. When not set, WebKit and WebKit Restricted cut the page whenever a web page height is set, while Blink and Chromium convert the whole page.
* `setAuthUsername(...)` / `setAuthPassword(...)` - HTTP Basic authentication credentials for the web page being converted.
* `setCookies({...})` - HTTP cookies sent to the web page being converted.
* `setRenderingEngine(selectpdf.RenderingEngine.Chromium)` - the Chromium rendering engine (also `WebKit`, `Restricted`, `Blink`).

### Response telemetry

Every client (`HtmlToPdfClient`, `InvoiceClient`, `PdfMergeClient`, `PdfToTextClient`, `UsageClient`) exposes information about the most recent API call, read from the response headers:

| Method | Description |
| --- | --- |
| `getNumberOfPages()` | Number of pages of the resulted PDF (`X-SelectPdf-Pages`). |
| `getCreditsTotal()` | Subscription monthly conversion limit (`X-SelectPdf-Credits-Total`). -1 means unlimited. `None` when the response has no credit information (demo endpoint, error response). |
| `getCreditsRemaining()` | Conversions remaining this month (`X-SelectPdf-Credits-Remaining`). -1 means unlimited. `None` when absent. |
| `getMode()` | `"production"` or `"demo"` (`X-SelectPdf-Mode`). Empty string when absent. |
| `getExecutionMode()` | `"in-process"` or `"worker"` (`X-SelectPdf-Execution`). Empty string for endpoints that don't convert. |

`HtmlToPdfClient` (and `InvoiceClient`) also offers `isDemoMode()`, `isDemoResponse()`, `getClampedFields()`, `wasClamped()`, `getDroppedFields()` and `wasAnyFieldDropped()` - see the demo mode section above.

```python
client = selectpdf.HtmlToPdfClient("Your API key here")
pdf = client.convertUrl("https://selectpdf.com")

print("Pages: {0}".format(client.getNumberOfPages()))
print("Mode: {0}, Execution: {1}".format(client.getMode(), client.getExecutionMode()))
print("Credits remaining: {0} / {1}".format(client.getCreditsRemaining(), client.getCreditsTotal()))
```

## Accessible PDF and PDF Standards

Produce a tagged, accessible PDF and target a PDF conformance level, using the same `HtmlToPdfClient` you already use for conversions.

### Features

* Tagged PDF with a logical structure tree: headings, paragraphs, lists, tables, figures with alternate text, links and reading order.
* Document language written as the PDF `/Lang` entry and onto the tagged structure elements.
* PDF/A for long term archiving, PDF/X for graphics exchange, PDF/SiqQ for documents that will be digitally signed.
* PDF/A-3A is the accessible archival level and implies a tagged document on its own.

Tagged output requires the Blink or Chromium rendering engine - the WebKit engines cannot build a structure tree. If you do not set an engine, the API promotes the conversion to Chromium and reports the engine it used in the `X-SelectPdf-Engine` response header. Asking for tagged output together with an explicit WebKit engine is rejected rather than silently producing an untagged PDF.

Note this produces tagged PDF/A output; it is not a conformance certification.

| Method | Description |
| --- | --- |
| `setTagged(True)` | Produce a tagged, accessible PDF. Default is `False`. |
| `setPdfStandard(...)` | Conformance target: `Full` (default), `PdfA`, `PdfA2B`, `PdfA3A`, `PdfA3B`, `PdfA3U`, `PdfX`, `PdfSiqQ_A`, `PdfSiqQ_B`. Use constants from `selectpdf.PdfStandard`. |
| `setDocumentLanguage(...)` | Natural language of the document, for example `"en-US"` (default) or `"de-DE"`. |

### Sample Code - Accessible PDF

```python
import selectpdf

client = selectpdf.HtmlToPdfClient("Your API key here")

client.setTagged(True)
client.setDocTitle("SelectPdf - accessible sample")
client.setViewerDisplayDocTitle(True)
client.setDocumentLanguage("en-US")
client.setPdfStandard(selectpdf.PdfStandard.PdfA3A)

client.convertUrlToFile("https://selectpdf.com", "Accessible.pdf")
print("Pages: {0}.".format(client.getNumberOfPages()))
```

## Electronic Invoicing API - ZUGFeRD / Factur-X

Turn an HTML invoice into a hybrid electronic invoice: one PDF/A-3 file carrying both the invoice a human reads and the XML a recipient's accounting system reads, embedded as an associated file with the metadata invoice software looks for.

### Features

* Profiles MINIMUM, BASIC WL, BASIC, EN 16931, EXTENDED and XRECHNUNG.
* The attachment relationship is derived from the profile when you do not set one.
* The embedded file is named as the standard requires - `factur-x.xml`, or `xrechnung.xml` for the XRECHNUNG profile - because recipients look it up by name.
* Factur-X 1.0 metadata by default; the deprecated ZUGFeRD 2.0 schema is available for recipients that still require it.
* Carrier defaults to PDF/A-3A, the accessible level, so the visible invoice is readable by assistive technology as well as archivable.
* Every HTML to PDF conversion setting applies, because `InvoiceClient` derives from `HtmlToPdfClient`.

The invoice XML can only be embedded into a document created as PDF/A-3, so there is no variant that attaches it to an existing PDF you already have. An API key is required - the keyless demo endpoint does not produce electronic invoices, and `InvoiceClient` raises `ApiException` when constructed without a key.

| Method | Description |
| --- | --- |
| `setInvoiceXmlFile(path)` | The invoice XML, from a local file. |
| `setInvoiceXml(xml)` | The invoice XML, from memory (`bytes` or a string, encoded as UTF-8). |
| `setZugferdProfile(...)` | Required. `Minimum`, `Basic_WL`, `Basic`, `En16931`, `Extended`, `XRechnung`. Use constants from `selectpdf.ZugferdProfile`. |
| `setZugferdRelationship(...)` | Optional. `Data`, `Alternative`, `Source`, `Supplement`. When not set, the API uses `Alternative` for `Minimum` and `Basic_WL`, and `Data` for the rest. Use constants from `selectpdf.ZugferdRelationship`. |
| `setZugferdSchema(...)` | Optional. `FacturX10` (default) or `Zugferd20`. Use constants from `selectpdf.ZugferdSchema`. |
| `createFromUrl(url)`, `createFromHtmlString(html)`, `createFromHtmlStringWithBaseUrl(html, baseUrl)` | Create the invoice. Each has `...ToStream`, `...ToFile`, `...Async`, `...ToStreamAsync` and `...ToFileAsync` variants. |

### Sample Code - Electronic Invoice

```python
import selectpdf

client = selectpdf.InvoiceClient("Your API key here")

client.setInvoiceXmlFile("factur-x.xml") # or setInvoiceXml(bytes / string)
client.setZugferdProfile(selectpdf.ZugferdProfile.En16931)

client.createFromHtmlStringToFile(invoiceHtml, "Invoice.pdf")
# ... or from the invoice page your application already renders:
# client.createFromUrlToFile("https://your-app.example/invoices/INV-2026-001", "Invoice.pdf")

print("Pages: {0}.".format(client.getNumberOfPages()))
```

## Pdf Merge API

SelectPdf Pdf Merge REST API is an online solution that lets you merge local or remote PDFs into a final PDF document.

### Features

* Merge local PDF document.
* Merge remote PDF from public url.
* Set PDF viewer options and PDF document information.
* Secure generated PDF with a password.
* Works in all programming languages.

See [PDF Merge API](https://selectpdf.com/pdf-merge-api/) page for full list of parameters.

### Sample Code

```python
# -*- coding: utf-8 -*-

import sys, json
import selectpdf

testUrl = "https://selectpdf.com/demo/files/selectpdf.pdf"
testPdf = "Input.pdf"
localFile = "Result.pdf"
apiKey = "Your API key here"

pythonVersion = "Python 3" if selectpdf.IS_PYTHON3 else "Python 2"
print ("This is SelectPdf-{0} using {1}.".format(selectpdf.CLIENT_VERSION, pythonVersion))

try:
    client = selectpdf.PdfMergeClient(apiKey)

    # set parameters - see full list at https://selectpdf.com/pdf-merge-api/

    # specify the pdf files that will be merged (order will be preserved in the final pdf)

    client.addFile(testPdf) # add PDF from local file
    client.addUrlFile(testUrl) # add PDF From public url
    # client.addFileWithPassword(testPdf, "pdf_password") # add PDF (that requires a password) from local file
    # client.addUrlFileWithPassword(testUrl, "pdf_password") # add PDF (that requires a password) from public url

    print ("Starting pdf merge ...")
    
    # merge pdfs to local file
    client.saveToFile(localFile)

    # merge pdfs to memory
    # pdf = client.save()

    print ("Finished! Number of pages: {0}.".format(client.getNumberOfPages()))

    # get API usage
    usageClient = selectpdf.UsageClient(apiKey)
    usage = usageClient.getUsage()
    print("Conversions remained this month: {0}.".format(usage["available"]))

except selectpdf.ApiException as ex:
    print ("An error occurred: {0}.".format(ex.getMessage()))

```

## Pdf To Text API

SelectPdf Pdf To Text REST API is an online solution that lets you extract text from your PDF documents or search your PDF document for certain words.

### Features

* Extract text from PDF.
* Search PDF.
* Specify start and end page for partial file processing.
* Specify output format (plain text or html).
* Use a PDF from an online location (url) or upload a local PDF document.

See [Pdf To Text API](https://selectpdf.com/pdf-to-text-api/) page for full list of parameters.

### Sample Code - Pdf To Text

```python
# -*- coding: utf-8 -*-

import sys, json
import selectpdf

testUrl = "https://selectpdf.com/demo/files/selectpdf.pdf"
testPdf = "Input.pdf"
localFile = "Result.txt"
apiKey = "Your API key here"

pythonVersion = "Python 3" if selectpdf.IS_PYTHON3 else "Python 2"
print ("This is SelectPdf-{0} using {1}.".format(selectpdf.CLIENT_VERSION, pythonVersion))

try:
    client = selectpdf.PdfToTextClient(apiKey)

    # set parameters - see full list at https://selectpdf.com/pdf-to-text-api/

    client.setStartPage(1) # start page (processing starts from here)
    client.setEndPage(0) # end page (set 0 to process file til the end)
    client.setOutputFormat(selectpdf.OutputFormat.Text) # set output format (0-Text or 1-HTML)

    print ("Starting pdf to text ...")
    
    # convert local pdf to local text file
    client.getTextFromFileToFile(testPdf, localFile)

    # extract text from local pdf to memory
    # text = client.getTextFromFile(testPdf)
    # print text
    # print (text)

    # convert pdf from public url to local text file
    # client.getTextFromUrlToFile(testUrl, localFile)

    # extract text from pdf from public url to memory
    # text = client.getTextFromUrl(testUrl)
    # print text
    # print (text)

    print ("Finished! Number of pages processed: {0}.".format(client.getNumberOfPages()))

    # get API usage
    usageClient = selectpdf.UsageClient(apiKey)
    usage = usageClient.getUsage()
    print("Conversions remained this month: {0}.".format(usage["available"]))

except selectpdf.ApiException as ex:
    print ("An error occurred: {0}.".format(ex.getMessage()))

```

### Sample Code - Search Pdf

```python
# -*- coding: utf-8 -*-

import sys, json
import selectpdf

testUrl = "https://selectpdf.com/demo/files/selectpdf.pdf"
testPdf = "Input.pdf"
apiKey = "Your API key here"

pythonVersion = "Python 3" if selectpdf.IS_PYTHON3 else "Python 2"
print ("This is SelectPdf-{0} using {1}.".format(selectpdf.CLIENT_VERSION, pythonVersion))

try:
    client = selectpdf.PdfToTextClient(apiKey)

    # set parameters - see full list at https://selectpdf.com/pdf-to-text-api/

    client.setStartPage(1) # start page (processing starts from here)
    client.setEndPage(0) # end page (set 0 to process file til the end)
    client.setOutputFormat(selectpdf.OutputFormat.Text) # set output format (0-Text or 1-HTML)

    print ("Starting search pdf ...")
    
    # search local pdf
    results = client.searchFile(testPdf, "pdf")

    # search pdf from public url
    # results = client.searchUrl(testUrl, "pdf")

    print ("Search results:\n{0}\nSearch results count: {1}.".format(json.dumps(results, indent=4), len(results)))

    print ("Finished! Number of pages processed: {0}.".format(client.getNumberOfPages()))

    # get API usage
    usageClient = selectpdf.UsageClient(apiKey)
    usage = usageClient.getUsage()
    print("Conversions remained this month: {0}.".format(usage["available"]))

except selectpdf.ApiException as ex:
    print ("An error occurred: {0}.".format(ex.getMessage()))

```

## What's new in 1.6.0

Version 1.6.0 brings the Python client to feature parity with the .NET client 1.6.0, including the features of the .NET 1.5.0 release:

* `InvoiceClient` for ZUGFeRD / Factur-X hybrid electronic invoices, with the `ZugferdProfile`, `ZugferdRelationship` and `ZugferdSchema` constants.
* Tagged, accessible PDF and PDF conformance levels: `setTagged`, `setPdfStandard` (`PdfStandard` constants) and `setDocumentLanguage`.
* `setWebPageFixedSize`, `setAuthUsername` and `setAuthPassword` on `HtmlToPdfClient`.
* Keyless demo mode for `HtmlToPdfClient`, with the typed `DemoRateLimitException`, `DemoSafetyException` and `DemoUnsupportedException`.
* Response telemetry on every client: `getCreditsTotal`, `getCreditsRemaining`, `getMode`, `getExecutionMode`, plus the demo clamped / dropped fields.
* The `Chromium` rendering engine, and the `A0`, `A6`, `A7` and `A8` page sizes.

See [CHANGELOG.md](https://github.com/selectpdf/selectpdf-api-python-client/blob/master/CHANGELOG.md) for the full list.
