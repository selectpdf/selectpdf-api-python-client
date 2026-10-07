# -*- coding: utf-8 -*-

# Tagged (accessible) PDF and PDF conformance standards.

import sys, json
import selectpdf

url = "https://selectpdf.com"
localFile = "Accessible.pdf"

# Works with the keyless demo endpoint too - pass None or "demo". Note the demo
# stamps its output after conversion, so a demo PDF demonstrates the feature rather
# than being a conformant artifact; use a real key for output you intend to ship.
apiKey = "Your API key here"

pythonVersion = "Python 3" if selectpdf.IS_PYTHON3 else "Python 2"
print ("This is SelectPdf-{0} using {1}.".format(selectpdf.CLIENT_VERSION, pythonVersion))

try:
    client = selectpdf.HtmlToPdfClient(apiKey)

    # set parameters - see full list at https://selectpdf.com/html-to-pdf-api-parameters/

    # Produce a tagged PDF: a logical structure tree covering headings,
    # paragraphs, lists, tables, figures with alternate text, links and
    # reading order - what a screen reader needs to read the document.
    client.setTagged(True)

    # A tagged document needs a title. Without this the converter falls
    # back to the HTML <title>.
    client.setDocTitle("SelectPdf - accessible sample")

    # Shown by viewers that honour it; accessible PDF expects it on, and
    # the API turns it on for you whenever tagged output is requested.
    client.setViewerDisplayDocTitle(True)

    # The document language, written as the PDF /Lang entry and onto the
    # tagged structure elements.
    client.setDocumentLanguage("en-US")

    # Conformance target. PdfA3A is the ACCESSIBLE level of PDF/A-3: it
    # implies a tagged document on its own, and it is the level required
    # to carry a ZUGFeRD / Factur-X invoice (see electronic-invoice.py).
    #   Full   - the complete PDF feature set (default)
    #   PdfA / PdfA2B / PdfA3B / PdfA3U - long term archiving
    #   PdfA3A - archiving + accessibility
    #   PdfX   - graphics exchange
    #   PdfSiqQ_A / PdfSiqQ_B - digital signatures
    client.setPdfStandard(selectpdf.PdfStandard.PdfA3A)

    # Tagged output requires the Blink or Chromium engine - the WebKit
    # engines cannot build a structure tree. You can name one explicitly:
    #
    #     client.setRenderingEngine(selectpdf.RenderingEngine.Chromium)
    #
    # If you don't, the API promotes the conversion to Chromium for you and
    # reports the engine it used in the X-SelectPdf-Engine response header.
    # Asking for tagged output together with an explicit WebKit engine is
    # rejected with HTTP 400 rather than silently producing an untagged PDF.

    print ("Starting conversion ...")

    # convert url to local file
    client.convertUrlToFile(url, localFile)

    # convert url to memory
    # pdf = client.convertUrl(url)

    print ("Finished! Number of pages: {0}.".format(client.getNumberOfPages()))

    # response telemetry
    print ("Mode: {0}, Execution: {1}.".format(client.getMode(), client.getExecutionMode()))
    print ("Credits remaining: {0} / {1}.".format(client.getCreditsRemaining(), client.getCreditsTotal()))

except selectpdf.ApiException as ex:
    print ("An error occurred: {0}.".format(ex.getMessage()))
