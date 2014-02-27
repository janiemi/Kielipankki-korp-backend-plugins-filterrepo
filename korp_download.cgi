#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
"""


from collections import defaultdict

import sys
import os
import time
import cgi
import re
import json
import urllib, urllib2, base64, md5
import logging


# Path to log file; use /dev/null to disable logging
LOG_FILE = "/v/korp/log/korp-cgi.log"
# Log level: set to logging.DEBUG for also logging actual CQP
# commands, logging.WARNING for only warnings and errors,
# logging.CRITICAL to disable logging
LOG_LEVEL = logging.INFO


def main():
    """
    """
    starttime = time.time()

    sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0) # Open unbuffered stdout
    
    # Convert form fields to regular dictionary
    form_raw = cgi.FieldStorage()
    form = dict((field, form_raw.getvalue(field)) for field in form_raw.keys())

    # Configure logging
    loglevel = logging.DEBUG if "debug" in form else LOG_LEVEL
    logging.basicConfig(filename=LOG_FILE,
                        format=('[%(filename)s %(process)d' +
                                ' %(levelname)s @ %(asctime)s]' +
                                ' %(message)s'),
                        level=loglevel)
    # Log remote IP address and CGI parameters
    logging.info('IP: %s', cgi.os.environ.get('REMOTE_ADDR'))
    logging.info('Params: %s', form)

    try:
        make_download_file(form)
    except Exception, e:
        raise
    

def make_download_file(form):
    """Perform a query and return the result in a downloadable format.

    The required parameters are the same as for query.

    The optional parameters:
    - format: download format ("json", "csv", "tsv", ...)

    For format FMT, the function calls the global function
    make_download_content_FMT with the result returned by query() as
    the argument. The function should return a triple (file content,
    file MIME type, filename extension).
    """

    result = {}
    format_type = form.get("format", "json").lower()
    query_params = json.loads(form.get("query_params", ""))
    query_result = json.loads(form.get("query_result", ""))
    content, content_type, filename_ext = \
        globals()["make_download_content_" + format_type](query_result)
    result["download_charset"] = form.get("encoding", "utf-8")
    result["download_content"] = content.encode(result["download_charset"])
    result["download_content_type"] = content_type
    result["download_filename"] = form.get(
        "filename", "korp_kwic_" + time.strftime("%Y%m%d%H%M%S") + filename_ext)
    print_download_object(result)


def make_download_content_json(query_result):
    """Convert query_result to JSON."""
    return (json.dumps(query_result["kwic"], sort_keys=True, indent=4),
            "application/json", ".json")


def make_download_content_csv(query_result):
    """Convert query_result to comma-separated-values format."""
    return (format_download_content_delimited(query_result, delimiter=u",",
                                              quote=u"\"", escape_quote=u"\"",
                                              newline=u"\r\n"),
            "text/csv", ".csv")


def make_download_content_tsv(query_result):
    """Convert query_result to tab-separated-values format."""
    return (format_download_content_delimited(query_result, delimiter=u"\t",
                                              quote=u"", escape_quote=u"",
                                              newline=u"\r\n"),
            "text/tsv", ".tsv")


def format_download_content_delimited(query_result, **opts):
    """Return query_result in a delimited format specified by opts."""
    content = ""
    for sentence in query_result["kwic"]:
        content += format_sentence_delimited(sentence, **opts)
    return content


def format_sentence_delimited(sentence, **opts):
    """Format a single delimited sentence with the delimiter options opts.

    The result contains the following fields:
    - corpus ID (in upper case)
    - corpus position of the start of the Match
    - tokens in left context, separated with spaces
    - tokens in match, separated with spaces
    - tokens in right context, separated with spaces
    - for parallel corpora only, tokens in aligned sentence
    """
    # Match start and end positions in tokens
    match_start = sentence["match"]["start"]
    match_end = sentence["match"]["end"]
    fields = [sentence["corpus"],
              str(sentence["match"]["position"]),
              format_sentence_tokens(sentence["tokens"][:match_start]),
              format_sentence_tokens(sentence["tokens"][match_start:match_end]),
              format_sentence_tokens(sentence["tokens"][match_end:])]
    if "aligned" in sentence:
        for align_key, tokens in sorted(sentence["aligned"].iteritems()):
            fields.append(format_sentence_tokens(tokens))
    return format_delimited_fields(fields, **opts)


def format_sentence_tokens(tokens):
    """Format the tokens of a single sentence."""
    # Allow for None in word
    return u" ".join(token.get("word", "") or "" for token in tokens)


def format_delimited_fields(fields, **opts):
    """Format fields according to the options in opts.

    opts may contain the following keyword arguments:
    - delim: field delimiter (default: ,)
    - quote: quotes surrounding fields (default: ")
    - escape_quote: string to precede a quote with in a field value to
      escape it (default: ")
    - newline: end-of-record string (default: \r\n)
    """
    delim = opts.get("delimiter", u",")
    quote = opts.get("quote", u"\"")
    escape_quote = opts.get("escape_quote", quote)
    newline = opts.get("newline", u"\n")
    return (delim.join((quote + field.replace(quote, escape_quote + quote)
                        + quote)
                       for field in fields)
            + newline)


def print_download_object(obj):
    """Print the downloadable content obj["download_content"]."""
    if "ERROR" in obj:
        print_header("text/plain")
        error = obj["ERROR"]
        print "Error when trying to download results:"
        print error["type"] + ": " + error["value"]
        if "traceback" in error:
            print error["traceback"]
    else:
        print_download_header(obj)
        print obj["download_content"],


def print_download_header(obj):
    """Print header for the downloadable file in obj.

    obj may contain the following keys affecting the output headers:
    - download_content_type => Content-Type (default: text/plain)
    - download_charset => Charset (default: utf-8)
    - download_filename => Content-Disposition filename
    - download_content => Length to Content-Length
    """
    charset = obj.get("download_charset", "utf-8")
    print "Content-Type: " + obj.get("download_content_type", "text/plain")
    print "Charset: " + charset
    # Default filename 
    print ("Content-Disposition: attachment; filename="
           + obj.get("download_filename", "korp_kwic"))
    print "Content-Length: " + str(len(obj["download_content"]))
    # print "Access-Control-Allow-Origin: *"
    # print "Access-Control-Allow-Methods: GET, POST"
    # print "Access-Control-Allow-Headers: Authorization"
    print


if __name__ == "__main__":
    main()
