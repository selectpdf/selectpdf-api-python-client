# -*- coding: utf-8 -*-

import sys, json
import selectpdf

url = "https://selectpdf.com"
localFile = "Test.pdf"

# Web elements lookup requires a paid API key (the demo endpoint
# does not expose the elements service).
apiKey = "Your API key here"

pythonVersion = "Python 3" if selectpdf.IS_PYTHON3 else "Python 2"
print ("This is SelectPdf-{0} using {1}.".format(selectpdf.CLIENT_VERSION, pythonVersion))

try:
    client = selectpdf.HtmlToPdfClient(apiKey)

    # CSS selectors used to identify HTML elements whose location in
    # the resulting PDF should be reported back. See the API docs for
    # selector syntax: https://selectpdf.com/html-to-pdf-api/
    client.setPageSize(selectpdf.PageSize.A4)
    client.setMargins(0)
    client.setPdfWebElementsSelectors("H1, H2, *.menu, *#footer")

    print ("Starting conversion ...")

    client.convertUrlToFile(url, localFile)

    print ("Finished! Number of pages: {0}.".format(client.getNumberOfPages()))

    # Retrieve element rectangles. Returns an empty list if no element
    # matched the configured selectors.
    elements = client.getWebElements()
    print ("Web elements found: {0}.".format(len(elements)))

    for element in elements:
        rectangles = element.get("PdfRectangles") or []
        print (" - <{0}> id='{1}' class='{2}' rectangles={3}".format(
            element.get("HtmlElementTagName"),
            element.get("HtmlElementId"),
            element.get("HtmlElementCssClassName"),
            len(rectangles)))

    # response telemetry
    print ("Mode: {0}, Execution: {1}.".format(client.getMode(), client.getExecutionMode()))
    print ("Credits remaining: {0} / {1}.".format(client.getCreditsRemaining(), client.getCreditsTotal()))

except selectpdf.ApiException as ex:
    print ("An error occurred: {0}.".format(ex.getMessage()))
