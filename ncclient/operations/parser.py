import os

from threading import Lock

from ncclient.operations import rpc

from xml.sax.handler import ContentHandler
from lxml import etree
from lxml.builder import E

import logging
logger = logging.getLogger("ncclient.operations.parser")


def __dict_replace(s, d):
    """Replace substrings of a string using a dictionary."""
    for key, value in d.items():
        s = s.replace(key, value)
    return s


def _get_sax_parser_root(xml):
    """
    This function does some validation and rule check of xmlstring
    :param xml: string or object to be used in parsing reply
    :return: lxml object
    """
    if isinstance(xml, etree._Element):
        root = xml
    else:
        root = etree.fromstring(xml)
    return root


def escape(data, entities={}):
    """Escape &, <, and > in a string of data.

    You can escape other strings of data by passing a dictionary as
    the optional entities parameter.  The keys and values must all be
    strings; each key will be replaced with its corresponding value.
    """

    # must do ampersand first
    data = data.replace("&", "&amp;")
    data = data.replace(">", "&gt;")
    data = data.replace("<", "&lt;")
    if entities:
        data = __dict_replace(data, entities)
    return data


def quoteattr(data, entities={}):
    """Escape and quote an attribute value.

    Escape &, <, and > in a string of data, then quote it for use as
    an attribute value.  The \" character will be escaped as well, if
    necessary.

    You can escape other strings of data by passing a dictionary as
    the optional entities parameter.  The keys and values must all be
    strings; each key will be replaced with its corresponding value.
    """
    entities = entities.copy()
    entities.update({'\n': '&#10;', '\r': '&#13;', '\t':'&#9;'})
    data = escape(data, entities)
    if '"' in data:
        if "'" in data:
            data = '"%s"' % data.replace('"', "&quot;")
        else:
            data = "'%s'" % data
    else:
        data = '"%s"' % data
    return data


class SAXParser(ContentHandler):
    def __init__(self, session):
        ContentHandler.__init__(self)
        self._currenttag = None
        self._ignoretag = None
        self._defaulttags = []
        self._session = session
        self._validate_reply_and_sax_tag = False
        self._lock = Lock()
        self._use_filter = False

    def startElement(self, tag, attributes):
        if tag == 'rpc-reply':
            with self._lock:
                listners = list(self._session._listeners)
            rpc_reply_listner = [i for i in listners if
                                 isinstance(i, rpc.RPCReplyListener)]
            rpc_msg_id = attributes._attrs['message-id']
            if rpc_msg_id in rpc_reply_listner[0]._id2rpc:
                rpc_reply_handler = rpc_reply_listner[0]._id2rpc[rpc_msg_id]
                if rpc_reply_handler._filter_xml is not None:
                    self._cur = self._root = _get_sax_parser_root(rpc_reply_handler._filter_xml)
                    self._use_filter = True
                else:
                    # in case last rpc called used sax parsing and error'd out without resetting
                    # use_filer in endElement rpc-reply check
                    self._use_filter = False
        if self._use_filter:
            if self._ignoretag is not None:
                return

            if self._cur == self._root and self._cur.tag == tag:
                node = self._root
            else:
                node = self._cur.find(tag)

            if self._validate_reply_and_sax_tag:
                if tag != self._root.tag:
                    self._write_buffer(tag, format_str='<{}>\n')
                    self._cur = E(tag, self._cur)
                else:
                    self._write_buffer(tag, format_str='<{}{}>', **attributes)
                    self._cur = node
                    self._currenttag = tag
                self._validate_reply_and_sax_tag = False
                self._defaulttags.append(tag)
            elif node is not None:
                self._write_buffer(tag, format_str='<{}{}>', **attributes)
                self._cur = node
                self._currenttag = tag
            elif tag == 'rpc-reply':
                self._write_buffer(tag, format_str='<{}{}>', **attributes)
                self._defaulttags.append(tag)
                self._validate_reply_and_sax_tag = True
            else:
                self._currenttag = None
                self._ignoretag = tag
        else:
            self._write_buffer(tag, format_str='<{}{}>', **attributes)

    def endElement(self, tag):
        if tag == 'rpc-reply':
            self._use_filter = False
        if self._use_filter:
            if self._ignoretag == tag:
                self._ignoretag = None

            if tag in self._defaulttags:
                self._write_buffer(tag, format_str='</{}>\n')

            elif self._cur.tag == tag:
                self._write_buffer(tag, format_str='</{}>\n')
                self._cur = self._cur.getparent()

            self._currenttag = None
        else:
            self._write_buffer(tag, format_str='</{}>')

    def characters(self, content):
        if self._use_filter:
            if self._currenttag is not None:
                self._write_buffer(content, format_str='{}')
        else:
            self._session._buffer.write(str.encode(content))

    def _write_buffer(self, content, format_str, **kwargs):
        self._session._buffer.seek(0, os.SEEK_END)
        attrs = ''
        for (name, value) in kwargs.items():
            attr = ' {}={}'.format(name, quoteattr(value))
            attrs = attrs + attr
        data = format_str.format(content, attrs)
        self._session._buffer.write(str.encode(data))
