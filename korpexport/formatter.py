#! /usr/bin/python
# -*- coding: utf-8 -*-


# TODO: 
# kwargs/format_args to all _format methods; sensible defaults for all options


from __future__ import absolute_import

import time
import string
import re

import korpexport.queryresult as qr

__all__ = ["KorpExportFormatter"]


class _PartialStringFormatter(string.Formatter):

    """A string formatter handling missing keys

    A string formatter that outputs an empty (or other specified)
    string when a format key would cause a KeyError or AttributeError.

    Adapted from
    http://stackoverflow.com/questions/20248355/how-to-get-python-to-gracefully-format-none-and-non-existing-fields
    https://gist.github.com/navarroj/7689682
    """

    def __init__(self, missing=""):
        self.missing = missing

    def get_field(self, field_name, args, kwargs):
        # Handle missing fields
        try:
            return super(_PartialStringFormatter, self).get_field(
                field_name, args, kwargs)
        except (KeyError, AttributeError):
            return None, field_name

    def format_field(self, value, spec):
        if value is None:
            return self.missing
        else:
            return super(_PartialStringFormatter, self).format_field(
                value, spec)


class _KorpExportFormatterMetaclass(type):

    def __init__(self, classname, bases, attrs):
        super(_KorpExportFormatterMetaclass, self).__init__(classname, bases,
                                                            attrs)
        self._make_option_defaults(bases)

    def _make_option_defaults(self, base_classes):
        new_option_defaults = {}
        for cls in list(base_classes) + [self]:
            try:
                new_option_defaults.update(cls._option_defaults)
            except AttributeError:
                pass
        self._option_defaults = new_option_defaults


class KorpExportFormatter(object):

    __metaclass__ = _KorpExportFormatterMetaclass

    formats = []
    download_charset = "utf-8"
    mime_type = "application/unknown"
    structured_format = False
    filename_extension = ""

    _option_defaults = {
        "list_valued_opts": [
            "infoitems",
            "params",
            "sentence_fields",
            "token_fields"
            ],
        "newline": "\n",
        "show_info": "True",
        "show_field_headings": "True",
        "content_format": u"{info}{sentence_field_headings}{sentences}",
        "infoitems_format": "{title}{infoitems}\n",
        "infoitems": "date,korp_url,params,hitcount",
        "infoitem_labels": {
            "date": "Date",
            "params": "Query parameters",
            "hitcount": "Total hits",
            "korp_url": "Korp URL",
            "korp_server_url": "Korp server URL"
            },
        "infoitem_format": u"{label}:{sp_or_nl}{value}",
        "infoitem_sep": "\n",
        "title_format": u"{title}\n",
        "title": "Korp search results",
        "date_format": "%Y-%m-%d %H:%M:%S",
        "hitcount_format": u"{hitcount}",
        "params_format": u"{params}",
        "params": "corpus,cqp,defaultcontext,defaultwithin,sort,start,end",
        "param_labels": {
            "corpus": "corpora",
            "cqp": "CQP query",
            "defaultcontext": "context",
            "defaultwithin": "within",
            "sort": "sorting"
            },
        "param_format": u"{label}: {value}", 
        "param_sep": "; ",
        "field_headings_format": u"{field_headings}\n",
        "sentence_format": (u"{info}: {left_context}"
                            u"{match_open}{match}{match_close}"
                            u"{right_context}\n"),
        "sentence_sep": u"",
        "sentence_info_format": u"{corpus} {match_pos}",
        "sentence_fields": "",
        "sentence_field_labels": {
            "match_pos": "match position",
            "left_context": "left context",
            "right_context": "right context",
            "aligned_text": "aligned text"
            },
        "sentence_field_format": u"{value}",
        "sentence_field_sep": "",
        "aligned_format": u"{sentence}",
        "aligned_sep": u" | ",
        "struct_format": u"{name}: {value}",
        "struct_sep": u"; ",
        "token_format": u"{word}[{attrs}]",
        "token_noattrs_format": u"{word}",
        "token_sep": u" ",
        "word_format": u"{word}",
        "token_fields": "word,*attrs",
        "token_field_labels": {
            "match_mark": "match"
            },
        "token_field_format": u"{value}",
        "token_field_sep": ";",
        "attr_format": u"{value}",
        "attr_sep": u";",
        "token_struct_open_format": u"",
        "token_struct_close_format": u"",
        "token_struct_open_sep": "",
        "token_struct_close_sep": "",
        "combine_token_structs": "False",
        "match_open": u"",
        "match_close": u"",
        "match_marker": u"*",
        }

    _formatter = _PartialStringFormatter("[none]")

    def __init__(self, format_name, options=None):
        self._format_name = format_name
        self._opts = {}
        self._opts.update(self.__class__._option_defaults)
        self._opts.update(options or {})
        self._query_params = {}
        self._query_result = {}

    def get_options(self):
        return self._opts

    def get_option_bool(self, optname):
        return (self._opts[optname].lower()
                not in ["false", "no", "off", "0", ""])

    def get_option_int(self, optname):
        value = None
        try:
            value = int(self._opts[optname])
        except (ValueError, TypeError):
            value = int(self._option_defaults[optname])
        return value

    def make_download_content(self, query_result, query_params=None,
                              options=None):
        self._query_result = query_result
        self._query_params = query_params or {}
        self._opts.update(options or {})
        self._adjust_opts()
        self._init_infoitems()
        return self._convert_newlines(self._postprocess(self._format_content()))

    def _adjust_opts(self):
        self._make_opt_lists()

    def _make_opt_lists(self):

        def adjust_item(item):
            if item.startswith("*"):
                return self._opts.get(item[1:], [])
            elif item == "?aligned_text":
                return ([item[1:]] if qr.is_parallel_corpus(self._query_result)
                        else [])
            else:
                return [item]

        for optkey in self._opts.get("list_valued_opts", []):
            if isinstance(self._opts.get(optkey), basestring):
                self._opts[optkey] = self._opts.get(optkey, "").split(",")
                adjusted_list = []
                for item in self._opts[optkey]:
                    adjusted_list.extend(adjust_item(item))
                self._opts[optkey] = adjusted_list

    def _init_infoitems(self):
        self._infoitems = dict(
            params=self._format_params(),
            # Also allow format references {param[name]}
            param=self._query_params,
            date=self._format_date(),
            hitcount=self._format_hitcount(),
            sentence_field_headings=self._format_field_headings("sentence"),
            token_field_headings=self._format_field_headings("token"),
            title=self._format_title(),
            korp_url=self._opts.get("korp_url"),
            korp_server_url=self._opts.get("korp_server_url"))

    def _convert_newlines(self, text):
        if self._opts["newline"] != "\n":
            return text.replace("\n", self._opts["newline"])
        else:
            return text

    def _postprocess(self, text):
        return text

    def _get_sentence_structs(self, sentence, all_structs=False):
        return qr.get_sentence_structs(
            sentence, None if all_structs else self._opts.get("structs", []))

    def _get_formatted_sentence_structs(self, sentence):
        return dict([(key, self._format_struct((key, val)))
                     for (key, val)
                     in self._get_sentence_structs(sentence, all_structs=True)])

    def _get_token_attrs(self, token, all_attrs=False):
        return qr.get_token_attrs(
            token, None if all_attrs else self._opts.get("attrs", []))

    def _format_item(self, item_type, **kwargs):
        return self._formatter.format(self._opts[item_type + "_format"],
                                      **kwargs)

    def _format_list(self, item_type, list_, format_fn=None, **kwargs):
        format_fn = format_fn or getattr(self, "_format_" + item_type)
        skip_re = self._opts.get(item_type + "_skip")
        if skip_re:
            skip_re = re.compile(r"^" + skip_re + r"$", re.UNICODE)
        return self._opts[item_type + "_sep"].join(
            formatted_elem for elem in list_
            for formatted_elem in [format_fn(elem, **kwargs)]
            if not (skip_re and skip_re.match(formatted_elem)))

    def _format_label_list_item(self, item_type, key, value):
        return self._format_item(
            item_type,
            key=key,
            label=self._opts[item_type + "_labels"].get(key, key),
            value=value,
            sp_or_nl="\n" if "\n" in unicode(value) else " ")

    def _format_field_headings(self, item_type):
        if not self.get_option_bool("show_field_headings"):
            return ""
        fields = self._opts.get(item_type + "_fields")
        if fields:
            headings = self._format_list(
                item_type + "_field",
                fields,
                lambda item, **kwargs: (
                    self._format_label_list_item(
                        item_type + "_field", item,
                        self._opts[item_type + "_field_labels"]
                        .get(item, item))))
        else:
            headings = ""
        return self._format_item("field_headings", field_headings=headings)

    # def _format_part(self, format_name, arg_fn_args, **format_arg_fns):
    #     # An untested, unused formatting function with a kind of lazy
    #     # evaluation of format arguments: only those arguments are
    #     # evaluated which occur in the format string.
    #     format_str = self._opts[format_name + "_format"]

    #     def make_format_arg_value(arg_name, arg_fn):
    #         return (arg_fn(*arg_fn_args) if "{" + arg_name + "}" in format_str
    #                 else "")

    #     format_args = [(name, make_format_arg_value(name, format_arg_fn))
    #                    for (name, format_arg_fn)
    #                    in format_arg_fns.iteritems()]
    #     return self._format_item(format_name, **format_args)

    def _format_content(self):
        return self._format_item(
            "content",
            info=self._format_infoitems(),
            sentences=self._format_sentences(),
            **self._infoitems)

    def _format_infoitems(self):
        if self.get_option_bool("show_info"):
            return self._format_item(
                "infoitems",
                infoitems=self._format_infoitem_fields(),
                **self._infoitems)
        else:
            return ""

    def _format_infoitem_fields(self, **format_args):
        return self._format_list(
            "infoitem",
            self._opts.get("infoitems", []),
            **format_args)

    def _format_infoitem(self, key, **format_args):
        try:
            value = getattr(self, "_format_" + key)()
        except AttributeError:
            value = self._opts.get(key)
        return self._format_label_list_item(
            "infoitem", key, value)

    def _format_title(self):
        title = title=self._opts.get("title")
        if title is None:
            return ""
        else:
            return self._format_item("title", title=title)

    def _format_date(self):
        return time.strftime(self._opts["date_format"])

    def _format_hitcount(self):
        return self._format_item("hitcount",
                                 hitcount=qr.get_hitcount(self._query_result))

    def _format_params(self):
        # Allow format references {name} as well as {param[name]}
        return self._format_item(
            "params",
            param=self._query_params,
            params=self._format_param_fields(),
            **self._query_params)

    def _format_param_fields(self, **format_args):
        return self._format_list(
            "param",
            self._opts.get("params", []),
            **format_args)

    def _format_param(self, key, **format_args):
        return self._format_label_list_item(
            "param", key, self._query_params.get(key))

    def _format_sentences(self):
        return self._format_list(
            "sentence", qr.get_sentences(self._query_result))

    def _format_sentence(self, sentence, **kwargs):
        struct = self._get_formatted_sentence_structs(sentence)
        format_args = dict(
            corpus=qr.get_sentence_corpus(sentence),
            match_pos=qr.get_sentence_match_position(sentence),
            tokens=self._format_tokens(
                qr.get_sentence_tokens_all(sentence)),
            match=self._format_tokens(
                qr.get_sentence_tokens_match(sentence),
                match_mark=self._opts.get("match_marker", "")),
            match_open=self._opts["match_open"],
            match_close=self._opts["match_close"],
            left_context=self._format_tokens(
                qr.get_sentence_tokens_left_context(sentence)),
            right_context=self._format_tokens(
                qr.get_sentence_tokens_right_context(sentence)),
            aligned=self._format_aligned_sentences(sentence),
            structs=self._format_structs(sentence),
            struct=struct,
            arg=kwargs)
        # Allow direct format references to struct names (unformatted
        # values)
        format_args.update(dict(self._get_sentence_structs(sentence)))
        format_args.update(self._infoitems)
        format_args.update(dict(info=self._format_item("sentence_info",
                                                       **format_args)))
        return self._format_item(
            "sentence",
            fields=self._format_list("sentence_field",
                                     self._opts.get("sentence_fields", []),
                                     **format_args),
            **format_args)

    def _format_sentence_field(self, key, **format_args):
        value = format_args.get(key)
        if value is None:
            value = format_args.get("struct", {}).get(key, "")
        return self._format_label_list_item("sentence_field", key, value)

    def _format_aligned_sentences(self, sentence):
        return self._format_list("aligned",
                                 qr.get_aligned_sentences(sentence),
                                 self._format_aligned_sentence)

    def _format_aligned_sentence(self, aligned_sentence, **kwargs):
        align_key, sentence = aligned_sentence
        return self._format_item("aligned",
                                 align_key=align_key, sentence=sentence)

    def _format_structs(self, sentence):
        return self._format_list("struct",
                                 self._get_sentence_structs(sentence))

    def _format_struct(self, struct):
        return self._format_item("struct", name=struct[0], value=struct[1])

    def _format_tokens(self, tokens, **kwargs):
        """Format the tokens of a single sentence."""
        return self._format_list("token", tokens, **kwargs)

    def _format_token(self, token, **kwargs):
        """Format a single token, possibly with attributes."""
        # Allow for None in word (but where do they come from?)
        word = self._format_item("word", word=(token.get("word") or ""))
        if (self._opts.get("attrs") or self.structured_format
            or len(self._opts.get("token_fields")) > 1):
            format_name = "token"
        else:
            format_name = "token_noattrs"
        format_args = dict(
            word=word,
            attrs=self._format_token_attrs(token),
            structs_open=self._format_token_structs_open(token),
            structs_close=self._format_token_structs_close(token))
        # Allow direct format references to attr names
        format_args.update(dict(self._get_token_attrs(token)))
        format_args.update(kwargs)
        result = self._format_item(
            format_name,
            fields=self._format_list("token_field",
                                     self._opts.get("token_fields", []),
                                     **format_args),
            **format_args)
        return result

    def _format_token_field(self, key, **format_args):
        return self._format_label_list_item(
            "token_field", key,
            (format_args.get(key)
             or format_args.get("attr", {}).get(key, "")
             or format_args.get("struct", {}).get(key, "")))

    def _format_token_attrs(self, token):
        """Format the attributes of a token."""
        return self._format_list(
            "attr", self._get_token_attrs(token), self._format_token_attr)

    def _format_token_attr(self, attr_name_value):
        attrname, value = attr_name_value
        return self._format_item("attr", name=attrname, value=(value or ""))

    def _format_token_structs_open(self, token):
        combine = self.get_option_bool("combine_token_structs")
        return self._format_list(
            "token_struct_open",
            qr.get_token_structs_open(token, combine))

    def _format_token_struct_open(self, struct):
        if self.get_option_bool("combine_token_structs"):
            structname, attrlist = struct
            attrstr = self._format_token_struct_attrs(attrlist)
            format_name = (
                "token_struct_open_" + ("attrs" if attrstr else "noattrs"))
            return self._format_item(format_name,
                                     name=structname, attrs=attrstr)
        else:
            return self._format_item("token_struct_open", name=struct)

    def _format_token_struct_attrs(self, attrs):
        return self._format_list("token_struct_attr", attrs)

    def _format_token_struct_attr(self, attr):
        name, value = attr
        return self._format_item("token_struct_attr", name=name, value=value)

    def _format_token_structs_close(self, token):
        return self._format_list(
            "token_struct_close",
            qr.get_token_structs_close(
                token, self.get_option_bool("combine_token_structs")))

    def _format_token_struct_close(self, struct):
        if self.get_option_bool("combine_token_structs"):
            struct, _ = struct
        return self._format_item("token_struct_close", name=struct)
