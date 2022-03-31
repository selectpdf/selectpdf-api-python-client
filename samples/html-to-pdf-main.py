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

