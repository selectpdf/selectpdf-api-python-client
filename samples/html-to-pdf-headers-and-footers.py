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

    # get API usage
    usageClient = selectpdf.UsageClient(apiKey)
    usage = usageClient.getUsage()
    print("Conversions remained this month: {0}.".format(usage["available"]))

except selectpdf.ApiException as ex:
    print ("An error occurred: {0}.".format(ex.getMessage()))

