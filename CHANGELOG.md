### 1.6.0
Brings the Python client to feature parity with the .NET client 1.6.0. The Python client skipped 1.5.0, so this release also contains the 1.5.0 features.

From 1.5.0:
* Keyless demo mode: HtmlToPdfClient() / HtmlToPdfClient("") / HtmlToPdfClient("demo") targets https://selectpdf.com/api2/convert/demo/ (watermarked, 5-page cap, Chromium engine). isDemoMode(), isDemoResponse().
* setUserPassword, setOwnerPassword, the async conversions and getWebElements raise DemoUnsupportedException in demo mode, before any request is sent.
* Typed demo exceptions built from the demo endpoint JSON error bodies: DemoRateLimitException (statusCode, reason, retryAfter, upgradeUrl, responseBody), DemoSafetyException (statusCode, field, reason, responseBody), DemoUnsupportedException (statusCode, field, upgradeUrl, responseBody). All derive from ApiException.
* Response telemetry on every client: getCreditsTotal(), getCreditsRemaining(), getMode(), getExecutionMode(); getClampedFields() / wasClamped() and getDroppedFields() / wasAnyFieldDropped() on HtmlToPdfClient.
* RenderingEngine.Chromium.

New in 1.6.0:
* InvoiceClient for ZUGFeRD / Factur-X hybrid electronic invoices (POST /api2/invoice/): setInvoiceXmlFile, setInvoiceXml (bytes or string), setZugferdProfile, setZugferdRelationship, setZugferdSchema, and createFromUrl / createFromHtmlString / createFromHtmlStringWithBaseUrl with ToStream, ToFile and Async variants. The carrier defaults to PDF/A-3A; an API key is required.
* Accessible PDF and PDF standards on HtmlToPdfClient: setTagged, setPdfStandard, setDocumentLanguage.
* setWebPageFixedSize, setAuthUsername, setAuthPassword on HtmlToPdfClient.
* New constants: PdfStandard, ZugferdProfile, ZugferdRelationship, ZugferdSchema.
* setPageSize accepts A0, A6, A7 and A8 (the PageSize constants already existed).
* The page count and job id are read from the X-SelectPdf-Pages / X-SelectPdf-Job-Id response headers; getNumberOfPages() now returns an int.
* Error responses are always reported as text (the multipart/form-data path used to return the raw bytes of the error body).
* New samples: accessible-pdf.py, electronic-invoice.py, async-conversion.py, web-elements.py; the existing samples print the response telemetry.

### 1.4.0
* Pdf Merge Client, Pdf To Text Client
