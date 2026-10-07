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

    client.setMargins(0) # PDF page margins
    client.setPageBreaksEnhancedAlgorithm(True) # enhanced page break algorithm

    # header properties

    client.setShowHeader(True) # display header
    # client.setHeaderHeight(50) # header height
    # client.setHeaderUrl(url) # header url
    client.setHeaderHtml("This is the <b>HEADER</b>!!!!") # header html

    # footer properties

    client.setShowFooter(True) # display footer
    # client.setFooterHeight(60) # footer height
    # client.setFooterUrl(url) # footer url
    client.setFooterHtml("This is the <b>FOOTER</b>!!!!") # footer html

    # footer page numbers

    client.setShowPageNumbers(True) # show page numbers in footer
    client.setPageNumbersTemplate("{page_number} / {total_pages}") # page numbers template
    client.setPageNumbersFontName("Verdana") # page numbers font name
    client.setPageNumbersFontSize(12) # page numbers font size
    client.setPageNumbersAlignment(selectpdf.PageNumbersAlignment.Center) # page numbers alignment (2-Center)

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

        # get API usage (paid keys only)
        usageClient = selectpdf.UsageClient(apiKey)
        usage = usageClient.getUsage()
        print("Conversions remained this month: {0}.".format(usage["available"]))

except selectpdf.DemoRateLimitException as ex:
    print ("Demo rate limit ({0}). Retry after {1}s. Upgrade: {2}".format(ex.reason, ex.retryAfter, ex.upgradeUrl))

except selectpdf.DemoSafetyException as ex:
    print ("Demo safety guard rejected '{0}' (reason={1}).".format(ex.field, ex.reason))

except selectpdf.DemoUnsupportedException as ex:
    print ("Feature '{0}' not available in demo mode. Upgrade: {1}".format(ex.field, ex.upgradeUrl))

except selectpdf.ApiException as ex:
    print ("An error occurred: {0}.".format(ex.getMessage()))
