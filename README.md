# HTML To PDF API - Python Client

SelectPdf HTML To PDF Online REST API is a professional solution that lets you create PDF from web pages and raw HTML code in your applications. The API is easy to use and the integration takes only a few lines of code.

## Features

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

## Installation

Download [selectpdf-api-python-client-1.0.0.zip](https://github.com/selectpdf/selectpdf-api-python-client/releases/download/1.0.0/selectpdf-api-python-client-1.0.0.zip), unzip it and run:

```
cd selectpdf-api-python-client-1.0.0
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

## Sample Code

```
import sys
import selectpdf

url = "https://selectpdf.com"
outFile = "test.pdf"

try:
    api = selectpdf.HtmlToPdfClient("Your key here")

    api.setPageSize(selectpdf.PageSize.A4)
    api.setPageOrientation(selectpdf.PageOrientation.Portrait)
    api.setMargins(0)
    api.setNavigationTimeout(30)
    api.setShowPageNumbers(False)
    api.setPageBreaksEnhancedAlgorithm(True)

    print ("Starting conversion...")

    api.convertUrlToFile(url, outFile)
    
    print ("Conversion finished successfully!")

    usage = selectpdf.UsageClient("Your key here")
    info = usage.getUsage(True)
    print("Conversions left this month:", info["available"])

except selectpdf.ApiException as ex:
    print ("An error occurred:", ex.getMessage())

```
