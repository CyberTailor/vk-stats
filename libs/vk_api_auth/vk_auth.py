#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

import http.cookiejar
import urllib.request
import urllib.error
import urllib.parse
from urllib.parse import urlparse
from html.parser import HTMLParser


class FormParser(HTMLParser):
    """
    Parsing forms
    """

    def __init__(self):
        HTMLParser.__init__(self)
        self.url = None
        self.params = {}
        self.in_form = False
        self.form_parsed = False
        self.method = "GET"

    def handle_starttag(self, tag, attrs):
        """
        First form.
        :param tag: name of the form
        :param attrs: names and values
        """
        tag = tag.lower()
        if tag == "form":
            if self.form_parsed:
                raise RuntimeError("Second form on page")
            if self.in_form:
                raise RuntimeError("Already in form")
            self.in_form = True
        if not self.in_form:
            return
        attrs = {name.lower(): value for name, value in attrs}
        if tag == "form":
            self.url = attrs["action"]
            if "method" in attrs:
                self.method = attrs["method"].upper()
        elif tag == "input" and "type" in attrs and "name" in attrs:
            if attrs["type"] in ["hidden", "text", "password"]:
                self.params[attrs["name"]] = attrs["value"] if "value" in attrs else ""

    def handle_endtag(self, tag):
        """
        Last form.
        :param tag: name of the form
        """
        tag = tag.lower()
        if tag == "form":
            if not self.in_form:
                raise RuntimeError("Unexpected end of <form>")
            self.in_form = False
            self.form_parsed = True


def auth(email, password, client_id, scope):
    """

    :param email: login for VK.com
    :param password: password for VK.com
    :param client_id: ID of app
    :param scope: access scopes
    """

    def split_key_value(kv_pair):
        """
        Splitting key-value pair (needed for urlbar parsing)
        :param kv_pair: 'attr=value' string
        :return: (attr, value)
        """
        kv = kv_pair.split("=")
        return kv[0], kv[1]

    # Authorization form
    def auth_user(email, password, client_id, scope, opener):
        """
        Getting access to VKontakte
        :param email: login for VK.com
        :param password: password for VK.com
        :param client_id: ID of app
        :param scope: access scopes
        :param opener: urllib opener
        :return: access_token and ID of user
        """
        access_url = "https://oauth.vk.com/oauth/authorize?redirect_uri=https://oauth.vk.com/blank.html" + \
                     "&response_type=token&client_id={}&scope={}&display=wap".format(client_id, ",".join(scope))
        response = opener.open(access_url)
        doc = response.read()
        parser = FormParser()
        parser.feed(doc.decode("utf-8"))
        parser.close()
        if not parser.form_parsed or parser.url is None or "pass" not in parser.params or "email" not in parser.params:
            raise RuntimeError("Something wrong")
        parser.params["email"] = email
        parser.params["pass"] = password
        if parser.method == "POST":
            response = opener.open(parser.url, bytes(urllib.parse.urlencode(parser.params), encoding="utf-8"))
        else:
            raise NotImplementedError(u"Method '{}'".format(parser.method))
        return response.read(), response.geturl()

    # Permission request form
    def give_access(doc, opener):
        """
        Pressing button to give access.
        :param doc: HTML page
        :param opener: urllib opener
        :return: current URL
        """
        parser = FormParser()
        parser.feed(doc.decode("utf-8"))
        parser.close()
        if not parser.form_parsed or parser.url is None:
            raise RuntimeError("Something wrong")
        if parser.method == "POST":
            response = opener.open(parser.url, bytes(urllib.parse.urlencode(parser.params), encoding="utf-8"))
        else:
            raise NotImplementedError(u"Method '{}'".format(parser.method))
        return response.geturl()

    if not isinstance(scope, list):
        scope = [scope]
    opener = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()),
        urllib.request.HTTPRedirectHandler())
    doc, url = auth_user(email, password, client_id, scope, opener)
    if urlparse(url).path != "/blank.html":
        # Need to give access to requested scope
        url = give_access(doc, opener)
    if urlparse(url).path != "/blank.html":
        raise RuntimeError("Expected success here")
    answer = dict(split_key_value(kv_pair) for kv_pair in urlparse(url).fragment.split("&"))
    if "access_token" not in answer or "user_id" not in answer:
        raise RuntimeError("Missing some values in answer")
    return answer["access_token"], answer["user_id"]
