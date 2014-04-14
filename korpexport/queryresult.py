#! /usr/bin/python
# -*- coding: utf-8 -*-


from __future__ import absolute_import

import json


class KorpQueryResult(object):

    def __init__(self, query_result):
        if isinstance(query_result, basestring):
            self._query_result = json.loads(query_result)
        else:
            self._query_result = query_result

    def get_sentences(self):
        return self._query_result["kwic"]

    def get_occurring_attrnames(self, keys, struct_name):
        # FIXME: This does not take into account attributes in aligned
        # sentences
        occurring_keys = set()
        for sent in self.get_sentences():
            if isinstance(sent[struct_name], list):
                for item in sent[struct_name]:
                    occurring_keys |= set(item.keys())
            else:
                occurring_keys |= set(sent[struct_name].keys())
        return [key for key in keys if key in occurring_keys]

    def get_sentence_corpus(self, sentence):
        return sentence["corpus"]

    def get_sentence_tokens(self, sentence, start, end):
        return sentence["tokens"][start:end]

    def get_sentence_tokens_match(self, sentence):
        return self.get_sentence_tokens(sentence, sentence["match"]["start"],
                                        sentence["match"]["end"])

    def get_sentence_tokens_left_context(self, sentence):
        return self.get_sentence_tokens(sentence, None,
                                        sentence["match"]["start"])

    def get_sentence_tokens_right_context(self, sentence):
        return self.get_sentence_tokens(sentence, sentence["match"]["end"],
                                        None)

    def get_sentence_match_position(self, sentence):
        return sentence["match"]["position"]

    def get_aligned_sentences(self, sentence):
        return sorted(sentence.get("aligned", {}).iteritems())

    def get_sentence_structs(self, sentence, structnames):
        # Value may be None; convert them to empty strings
        return [(struct, sentence["structs"].get(struct) or "")
                for struct in structnames]

    def get_sentence_struct_values(self, sentence, structnames):
        return [value for name, value in
                self.get_sentence_structs(sentence, structnames)]

    def get_token_attrs(self, token, attrnames):
        return [(attrname, token.get(attrname) or "") for attrname in attrnames]

    def get_token_structs_open(self, token, combine_attrs=False):
        return self._get_token_structs(token, "open", combine_attrs)

    def get_token_structs_close(self, token, combine_attrs=False):
        return self._get_token_structs(token, "close", combine_attrs)

    def _get_token_structs(self, token, struct_type, combine_attrs=False):
        try:
            structs = token["structs"][struct_type]
        except KeyError:
            return []
        if combine_attrs:
            structs = self._combine_struct_attrs(structs, struct_type)
        return structs

    def _combine_struct_attrs(self, structs, struct_type):
        result_structs = []
        for struct in structs:
            if struct_type == "open":
                struct, sp, attrval = struct.partition(" ")
                if not sp:
                    attrval = None
            else:
                attrval = None
            # NOTE: This assumes that element names do not contain
            # underscores.
            struct, _, attrname = struct.partition("_")
            if not result_structs or result_structs[-1][0] != struct:
                result_structs.append((struct, []))
            if attrval is not None:
                result_structs[-1][1].append((attrname, attrval))
        return result_structs

    def is_parallel_corpus(self):
        # FIXME: This does not work if the script gets the query result
        # from frontend instead of redoing the query, since the frontend
        # has processed the corpus names not to contain the vertical bar.
        return "|" in self._query_result["kwic"][0]["corpus"]
