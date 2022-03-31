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

