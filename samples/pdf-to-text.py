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

