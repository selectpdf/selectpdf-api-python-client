from setuptools import setup

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name="selectpdf", 
    version="1.0.0",
    author="SelectPdf",
    author_email="support@selectpdf.com",
    description="Python client for SelectPdf Online REST API",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/selectpdf/selectpdf-api-python-client",
    py_modules=['selectpdf'],
    license="License :: OSI Approved :: MIT License",
    classifiers=[
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries",
    ],
)