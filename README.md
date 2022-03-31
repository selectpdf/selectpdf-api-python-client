# SelectPdf Online REST API - Python Client

SelectPdf Online REST API is a professional solution for managing PDF documents online. It now has a dedicated, easy to use, Python client library that can be setup in minutes.

## Installation

Download [selectpdf-api-python-client-1.4.0.zip](https://github.com/selectpdf/selectpdf-api-python-client/releases/download/1.4.0/selectpdf-api-python-client-1.4.0.zip), unzip it and run:

```
cd selectpdf-api-python-client-1.4.0
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
