# -*- coding: utf-8 -*-

import sys, json
import selectpdf

url = "https://selectpdf.com"
localFile = "Test.pdf"

# Pass None, "" or "demo" to use the keyless demo endpoint
# (output is watermarked, capped at 5 pages, Chromium engine only).
# Replace with a real key for full production output.
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
    client.setRenderingEngine(selectpdf.RenderingEngine.WebKit) # rendering engine (demo mode forces Chromium)
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
    # client.setUserPassword("password") # secure the PDF with a password (paid keys only)

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

    # response telemetry
    print ("Mode: {0}, Execution: {1}.".format(client.getMode(), client.getExecutionMode()))

    if client.isDemoMode():
        if client.wasClamped():
            print ("Demo clamped: {0}.".format(", ".join(client.getClampedFields())))
        if client.wasAnyFieldDropped():
            print ("Demo dropped: {0}.".format(", ".join(client.getDroppedFields())))
    else:
        print ("Credits remaining: {0} / {1}.".format(client.getCreditsRemaining(), client.getCreditsTotal()))

        # get API usage (paid keys only - the demo endpoint has no usage account)
        usageClient = selectpdf.UsageClient(apiKey)
        usage = usageClient.getUsage()
        print("Conversions remained this month: {0}.".format(usage["available"]))

except selectpdf.DemoRateLimitException as ex:
    # reason is one of: per_ip, daily_cap, concurrency
    print ("Demo rate limit ({0}). Retry after {1}s. Upgrade: {2}".format(ex.reason, ex.retryAfter, ex.upgradeUrl))

except selectpdf.DemoSafetyException as ex:
    # demo only converts public URLs - internal/private hosts are rejected
    print ("Demo safety guard rejected '{0}' (reason={1}).".format(ex.field, ex.reason))

except selectpdf.DemoUnsupportedException as ex:
    # feature not available on the demo endpoint (e.g. setUserPassword)
    print ("Feature '{0}' not available in demo mode. Upgrade: {1}".format(ex.field, ex.upgradeUrl))

except selectpdf.ApiException as ex:
    print ("An error occurred: {0}.".format(ex.getMessage()))
