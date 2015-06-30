#!/usr/bin/env python3
# coding=utf-8

#   Copyright 2015 Matvey Vyalkov
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

"""
Computing rating of activity in VKontakte groups.
"""
__author__ = "CyberTailor <cybertailor@gmail.com>"
__version__ = '0.6 "Alien Guy"'

import sys
import os
os.devnull = open(os.devnull, mode="w")

import stats
import gettext
import locale

from gi.repository import Gtk

from libs.vk_api_auth.vk_auth import auth
from libs.gettext_windows import gettext_windows

stats.no_console()
lang = gettext_windows.get_language()
locale.setlocale(locale.LC_ALL, "")
if not sys.platform.startswith("win"):
    locale.bindtextdomain("vk_stats", "{}/locale".format(stats.SCRIPTDIR))
translation = gettext.translation("vk_stats", localedir="{}/locale".format(stats.SCRIPTDIR), languages=lang)
_ = translation.gettext


class Handler:
    """
    Handler for GUI
    """
    @staticmethod
    def gtk_main_quit(*args):
        """
        Canceling application.
        :param args: used by GTK+
        """
        Gtk.main_quit(*args)

    @staticmethod
    def destroy(*args):
        """
        Closing a window.
        :param args: used by GTK+
        """
        args[0].destroy()

    @staticmethod
    def logged_destroy(*args):
        """
        Closing the AccountLogged window.
        :param args: used by GTK+
        """
        print(args, file=os.devnull)
        logged_win.destroy()

    @staticmethod
    def process_destroy(*args):
        """
        Closing the Process window.
        :param args: used by GTK+
        """
        print(args, file=os.devnull)
        process_win.destroy()

    @staticmethod
    def latest_destroy(*args):
        """
        Closing the LatestVersion window.
        :param args: used by GTK+
        """
        print(args, file=os.devnull)
        latest_win.destroy()

    @staticmethod
    def update_destroy(*args):
        """
        Closing the FoundUpdate window.
        :param args: used by GTK+
        """
        print(args, file=os.devnull)
        update_win.destroy()

    @staticmethod
    def start(*args):
        """
        Starting.
        :param args: arguments from StatsMain
        """
        group = args[0].get_children()[0].get_children()[1].get_text()
        data = args[0].get_children()[1].get_children()
        date = data[0].get_text()
        posts = int(data[1].get_text())
        export = data[2].get_active_text().lower()
        mode = data[3].get_active_text().lower()
        process_win.show_all()

    @staticmethod
    def authorization(*args):
        """
        Authorization in VKontakte.
        :param args: login and password
        """
        data = args[0].get_children()
        password = data[2].get_text()
        email = data[3].get_text()
        app_id = 4589594
        auth_data = auth(email, password, client_id=app_id, scope=["stats", "groups", "wall"])
        token_file = open("{}/token.txt".format(stats.SCRIPTDIR), mode="w")
        print(*auth_data, sep=",", file=token_file)
        login_win.destroy()
        return auth_data

    @staticmethod
    def login(*args):
        """
        Showing the AccountLogin window.
        :param args: used by GTK+
        """
        print(args, file=os.devnull)
        login_win.show_all()

    @staticmethod
    def apply_update(*args):
        """
        Upgrading
        :param args: used by GTK+
        """
        pass

    @staticmethod
    def update_menu(*args):
        """
        Checking for updates.
        :param args: used by GTK+
        """
        pass

    @staticmethod
    def about_menu(*args):
        """
        Showing the "StatsAbout" window.
        :param args: used by GTK+
        """
        print(args, file=os.devnull)
        about_win.show_all()

    @staticmethod
    def account_menu(*args):
        """
        Logging in to VKontakte.
        :param args: used by GTK+
        """
        print(args, file=os.devnull)
        label = logged_win.get_children()[0].get_children()[0]
        label.set_text(label.get_text().format("{first_name} {last_name}".format(**user_data)))
        logged_win.show_all()

builder = Gtk.Builder()
builder.add_from_file("{}/vk_stats.glade".format(stats.SCRIPTDIR))
builder.connect_signals(Handler())
builder.set_translation_domain("vk_stats")

about_win = builder.get_object("StatsAbout")

logged_win = builder.get_object("AccountLogged")

process_win = builder.get_object("Process")

latest_win = builder.get_object("LatestVersion")

update_win = builder.get_object("FoundUpdate")

login_win = builder.get_object("AccountLogin")

main = builder.get_object("StatsMain")
main.show_all()

if "token.txt" in os.listdir(stats.SCRIPTDIR):
    access_token, user = open("{}/token.txt".format(stats.SCRIPTDIR)).read().split(",")
else:
    Handler.login()
    access_token, user = open("{}/token.txt".format(stats.SCRIPTDIR)).read().split(",")
user_data = stats.call_api("users.get", params={"user_ids": user}, token=access_token)[0]
stats.call_api(method="stats.trackVisitor", params={}, token=access_token)  # needed for tracking you

Gtk.main()
