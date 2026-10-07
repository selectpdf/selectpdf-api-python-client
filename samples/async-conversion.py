# -*- coding: utf-8 -*-

import sys, json
import selectpdf

url = "https://selectpdf.com"
localFile = "Test.pdf"

# Async conversions are not supported on the demo endpoint -
# this sample requires a paid API key.
apiKey = "Your API key here"

pythonVersion = "Python 3" if selectpdf.IS_PYTHON3 else "Python 2"
print ("This is SelectPdf-{0} using {1}.".format(selectpdf.CLIENT_VERSION, pythonVersion))

try:
    client = selectpdf.HtmlToPdfClient(apiKey)

    # Tune polling for the async job (optional).
    # The client polls /api2/asyncjob/ every AsyncCallsPingInterval
    # seconds, up to AsyncCallsMaxPings times, then gives up.
    client.AsyncCallsPingInterval = 3 # seconds between polls
    client.AsyncCallsMaxPings = 1000 # max polls before timeout

    client.setPageSize(selectpdf.PageSize.A4)
    client.setPageOrientation(selectpdf.PageOrientation.Portrait)
    client.setMargins(0)
    client.setPageBreaksEnhancedAlgorithm(True)

    print ("Starting async conversion ...")

    # url to file (async)
    client.convertUrlToFileAsync(url, localFile)

    # url to memory (async)
    # pdf = client.convertUrlAsync(url)

    # html string to file (async)
    # client.convertHtmlStringToFileAsync("This is some <b>html</b>.", localFile)

    # html string to memory (async)
    # pdf = client.convertHtmlStringAsync("This is some <b>html</b>.")

    print ("Finished! Number of pages: {0}.".format(client.getNumberOfPages()))

    # response telemetry
    print ("Mode: {0}, Execution: {1}.".format(client.getMode(), client.getExecutionMode()))
    print ("Credits remaining: {0} / {1}.".format(client.getCreditsRemaining(), client.getCreditsTotal()))

except selectpdf.ApiException as ex:
    print ("An error occurred: {0}.".format(ex.getMessage()))
