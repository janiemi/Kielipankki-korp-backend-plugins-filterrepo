#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
korp_download.cgi

A CGI script to convert Korp query results to downloadable formats

The script requires the following CGI parameters:
- query_result: the Korp query result to format

The following CGI parameters are optional
- format: the format to which to convert the result (json (default),
  csv, tsv, ...)
- filename: the (suggested) name of the file to generate (default:
  korp_kwic_TIME.FMT, where time is the current time (YYYYMMDDhhmmss)
  and FMT the format)
- query_params: korp.cgi parameters for generating query_result
"""


from __future__ import absolute_import

import sys
import os
import time
import cgi
import logging
import korpexport.exporter as ke


# Default Korp server URL
KORP_SERVER = "http://localhost/cgi-bin/korp/korp.cgi"

# Path to log file; use /dev/null to disable logging
LOG_FILE = "/v/korp/log/korp-cgi.log"
# Log level: set to logging.DEBUG for also logging actual CQP
# commands, logging.WARNING for only warnings and errors,
# logging.CRITICAL to disable logging
LOG_LEVEL = logging.INFO


def main():
    """The main CGI handler, modified from that of korp.cgi.

    Converts CGI parameters to a dictionary and initializes logging.
    The actual work is done in make_download_file its helper functions
    below.
    """
    starttime = time.time()
    # Open unbuffered stdout
    sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0)
    # Convert form fields to regular dictionary with unicode values;
    # assume that the input is encoded in UTF-8
    form_raw = cgi.FieldStorage()
    form = dict((field, form_raw.getvalue(field).decode("utf-8"))
                for field in form_raw.keys())
    # Configure logging
    loglevel = logging.DEBUG if "debug" in form else LOG_LEVEL
    logfile = form.get("logfile", LOG_FILE)
    logging.basicConfig(filename=logfile,
                        format=('[%(filename)s %(process)d' +
                                ' %(levelname)s @ %(asctime)s]' +
                                ' %(message)s'),
                        level=loglevel)
    # Log remote IP address and CGI parameters
    logging.info('IP: %s', cgi.os.environ.get('REMOTE_ADDR'))
    # Limit the length of query_result written to the log
    logging.info("Params: {'format': '%s', 'filename': '%s', "
                 "'query_params': '%s', 'query_result': '%.800s', "
                 "'headings': '%s', 'structs': '%s', 'attrs': '%s'}",
                 form.get("format"), form.get("filename"),
                 form.get("query_params"), form.get("query_result"),
                 form.get("headings"), form.get("structs"), form.get("attrs"))
    try:
        result = ke.make_download_file(form, 
                                       form.get("korp_server", KORP_SERVER))
    except Exception as e:
        import traceback
        exc = sys.exc_info()
        result = {"ERROR": {"type": exc[0].__name__,
                            "value": str(exc[1])}
                  }
        result["ERROR"]["traceback"] = traceback.format_exc().splitlines()
        logging.error("%s", result["ERROR"])
        # Show traceback only if the parameter debug is specified
        if "debug" not in form:
            del result["ERROR"]["traceback"]
    # Print HTTP header and content
    print_header(result)
    print_object(result)
    # Log elapsed time
    logging.info("Elapsed: %s", str(time.time() - starttime))


def print_header(obj):
    """Print header for the downloadable file (or error message) in obj.

    obj may contain the following keys affecting the output headers:
    - download_content_type => Content-Type (default: text/plain)
    - download_charset => Charset (default: utf-8)
    - download_filename => Content-Disposition filename
    - download_content => Length to Content-Length
    """
    charset = obj.get("download_charset", "utf-8")
    print ("Content-Type: "
           + (obj.get("download_content_type", "text/plain")
              if "ERROR" not in obj
              else "text/plain")
           + "; charset=" + charset)
    if "ERROR" not in obj:
        # Default filename 
        print ("Content-Disposition: attachment; filename="
               + obj.get("download_filename", "korp_kwic"))
        print "Content-Length: " + str(len(obj["download_content"]))
    print


def print_object(obj):
    """Print the downloadable content (or error message) in obj."""
    if "ERROR" in obj:
        error = obj["ERROR"]
        print "Error when trying to download results:"
        print error["type"] + ": " + error["value"]
        if "traceback" in error:
            print error["traceback"]
    else:
        print obj["download_content"],


if __name__ == "__main__":
    main()
