import os

from xml.sax.handler import ContentHandler, ErrorHandler
from lxml import etree
from lxml.builder import E

import logging
logger = logging.getLogger("ncclient.operations.rpc")


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


class XMLErrorHandler(ErrorHandler):
    def __init__(self, session):
        self._session = session

    def fatalError(self, exception):
        # self._session._parse10()
        # # self._session._buffer.seek(0)
        print ('Got exception: %s' %self._session._buffer.read().decode('UTF-8'))
        # # self.warning(exception)


class SAXParser(ContentHandler):
    def __init__(self, xml, session):
        ContentHandler.__init__(self)
        self._root = _get_sax_parser_root(xml) if xml is not None else None
        self._cur = self._root
        self._currenttag = None
        self._ignoretag = None
        self._defaulttags = []
        self._session = session
        self._validate_reply_and_sax_tag = False

    # def skippedEntity(self, name):
    #     print ('skipping: %s' %name)
    #
    # def ignorableWhitespace(self, content):
    #     self._session._buffer.write(str.encode(content.strip()))

    def startElement(self, tag, attributes):
        self._write_buffer(tag, format_str='<{}{}>', **attributes)
        # if self._ignoretag is not None:
        #     return
        #
        # if self._cur == self._root and self._cur.tag == tag:
        #     node = self._root
        # else:
        #     node = self._cur.find(tag)
        #
        # if self._validate_reply_and_sax_tag:
        #     if tag != self._root.tag:
        #         self._write_buffer(tag, format_str='<{}>\n')
        #         self._cur = E(tag, self._cur)
        #     else:
        #         self._write_buffer(tag, format_str='<{}{}>', **attributes)
        #         self._cur = node
        #         self._currenttag = tag
        #     self._validate_reply_and_sax_tag = False
        #     self._defaulttags.append(tag)
        # elif node is not None:
        #     self._write_buffer(tag, format_str='<{}{}>', **attributes)
        #     self._cur = node
        #     self._currenttag = tag
        # elif tag == 'rpc-reply':
        #     self._write_buffer(tag, format_str='<{}{}>', **attributes)
        #     self._defaulttags.append(tag)
        #     self._validate_reply_and_sax_tag = True
        # else:
        #     self._currenttag = None
        #     self._ignoretag = tag

    def endElement(self, tag):
        self._write_buffer(tag, format_str='</{}>')
        # if self._ignoretag == tag:
        #     self._ignoretag = None
        #
        # if tag in self._defaulttags:
        #     self._write_buffer(tag, format_str='</{}>\n')
        #
        # elif self._cur.tag == tag:
        #     self._write_buffer(tag, format_str='</{}>\n')
        #     self._cur = self._cur.getparent()
        #
        # self._currenttag = None

    def characters(self, content):
        # print (content)
        self._session._buffer.write(str.encode(content))
        # self._session._parse10()
        # if "]]>]]>" in content:
        #     # self.parser.feed(data[:len(data) - len("]]>]]>") - 1])
        #     self._buffer.seek(0, os.SEEK_END)
        #     self._buffer.write(str.encode("]]>]]>"))
        #     self._parse10()
        # if self._currenttag is not None:
        #     self._write_buffer(content, format_str='{}')

    def _write_buffer(self, content, format_str, **kwargs):
        print (content, format_str, kwargs)
        self._session._buffer.seek(0, os.SEEK_END)
        attrs = ''
        for (name, value) in kwargs.items():
            attr = ' {}={}'.format(name, quoteattr(value))
            attrs = attrs + attr
        data = format_str.format(content, attrs)
        self._session._buffer.write(str.encode(data))
