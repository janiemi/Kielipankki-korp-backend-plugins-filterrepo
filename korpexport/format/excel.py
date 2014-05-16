# -*- coding: utf-8 -*-

"""
Format Korp query results as an Excel 97–2003 workbook (XLS).

:Author: Jyrki Niemi <jyrki.niemi@helsinki.fi> for FIN-CLARIN
:Date: 2014
"""


from __future__ import absolute_import

import cStringIO as strio

import xlwt

import korpexport.format.delimited as delimited


__all__ = ['KorpExportFormatterTokensExcel',
           'KorpExportFormatterSentencesExcel']


class KorpExportFormatterExcel(delimited.KorpExportFormatterDelimited):

    """
    Format Korp query results as an Excel 97–2003 workbook (XLS).

    A base class of actual formatters for XLS formats. The class does
    not specify the content of the fields. It assumess that the
    formatted result contains rows separated by newlines and columns
    separated by tabs (before postprocessing). The class overrides
    `_postprocess` to produce the XLS file. The class can be combined
    (via multiple inheritance) with the content formatting classes in
    `korpexport.format.delimited` to produce meaningful output.
    """

    mime_type = "application/vnd.ms-excel"
    filename_extension = ".xls"
    download_charset = None

    def __init__(self, **kwargs):
        super(KorpExportFormatterExcel, self).__init__(**kwargs)

    def _postprocess(self, text):
        """Return an XLS file content of `text`.

        Assumes that `text` contains rows separated by newlines asn
        columns separatedy by tabs.
        """
        # CHECK: Does the encoding parameter work?
        workbook = xlwt.Workbook(encoding="utf-8")
        worksheet = workbook.add_sheet(self._opts.get("title", ""))
        for rownum, row in enumerate(text.split("\n")):
            if row:
                for colnum, value in enumerate(row.split("\t")):
                    worksheet.write(rownum, colnum, value)
        output = strio.StringIO()
        workbook.save(output)
        return output.getvalue()


class KorpExportFormatterSentencesExcel(
    delimited.KorpExportFormatterDelimitedSentence,
    KorpExportFormatterExcel):

    """
    Format Korp query results as an Excel workbook, sentence per row.

    Handle the format type ``sentences_excel`` alias
    ``sentences_xls``.
    """

    formats = ["sentences_excel", "sentences_xls"]

    def __init__(self, **kwargs):
        super(KorpExportFormatterSentencesExcel, self).__init__(**kwargs)


class KorpExportFormatterTokensExcel(
    delimited.KorpExportFormatterDelimitedToken,
    KorpExportFormatterExcel):

    """
    Format Korp query results as an Excel workbook, token per row.

    Handle the format type ``tokens_excel`` alias ``tokens_xls``,
    ``excel``, ``xls``.
    """

    formats = ["tokens_excel", "tokens_xls", "excel", "xls"]

    def __init__(self, **kwargs):
        super(KorpExportFormatterTokensExcel, self).__init__(**kwargs)
