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

import sys
import os
os.devnull = open(os.devnull, mode="w")

import stats
import gettext
import locale

from gi.repository import Gtk

from libs.vk_api_auth.vk_auth import auth
from libs.gettext_windows import gettext_windows

lang = gettext_windows.get_language()
locale.setlocale(locale.LC_ALL, "")
if not sys.platform.startswith("win"):
    locale.bindtextdomain("vk_stats", "{}/locale".format(stats.SCRIPTDIR))
translation = gettext.translation("vk_stats", localedir="{}/locale".format(stats.SCRIPTDIR), languages=lang)
_ = translation.gettext


def error(primary=_("Error"), secondary=_("Unknown error")):
    """
    Displaying error
    :param primary: primary (main) text
    :param secondary: secondary (additional) text
    """
    error_win.get_message_area().get_children()[0].set_text(primary)
    error_win.format_secondary_text(secondary)
    error_win.show_all()


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
    def error_destroy(*args):
        """
        Closing the Error window.
        :param args: used by GTK+
        """
        print(args, file=os.devnull)
        error_win.hide()

    @staticmethod
    def about_destroy(*args):
        """
        Closing the StatsAbout window.
        :param args: used by GTK+
        """
        print(args, file=os.devnull)
        about_win.hide()

    @staticmethod
    def logged_destroy(*args):
        """
        Closing the AccountLogged window.
        :param args: used by GTK+
        """
        print(args, file=os.devnull)
        logged_win.hide()

    @staticmethod
    def latest_destroy(*args):
        """
        Closing the LatestVersion window.
        :param args: used by GTK+
        """
        print(args, file=os.devnull)
        latest_win.hide()

    @staticmethod
    def update_destroy(*args):
        """
        Closing the FoundUpdate window.
        :param args: used by GTK+
        """
        print(args, file=os.devnull)
        update_win.hide()

    @staticmethod
    def success_destroy(*args):
        """
        Closing the Successfully window.
        :param args: used by GTK+
        """
        print(args, file=os.devnull)
        success_win.hide()

    @staticmethod
    def start(field):
        """
        Starting.
        :param field: arguments from StatsMain
        """
        data = field.get_children()
        group = data[6].get_text().lower()
        mode = data[4].get_active_text().lower()
        posts = data[1].get_text()
        date = data[0].get_text()
        if not group:
            error(secondary=_("Please, complete a URL of the group."))
        else:
            if not date:
                date = "0/0/0"
            if not posts:
                posts = 0
            else:
                posts = int(posts)
            if mode == _("posts"):
                method = stats.Stats(group, token=access_token, posts_lim=posts, date_lim=date)
            elif mode == _("likes"):
                method = stats.LikedStats(group, token=access_token, posts_lim=posts, date_lim=date)
            else:
                method = stats.LikersStats(group, token=access_token, posts_lim=posts, date_lim=date, wall_filter="all")
            method.stats()

    @staticmethod
    def account_menu(*args):
        """
        Logging in to VKontakte.
        :param args: used by GTK+
        """
        print(args, file=os.devnull)
        label = logged_win.get_child().get_children()[0]
        label.set_text(logged_text.format("{first_name} {last_name}".format(**user_data)))
        logged_win.show_all()

    def authorization(self, field):
        """
        Authorization in VKontakte.
        :param field: login and password
        """
        global access_token, user, user_data
        data = field.get_children()
        password = data[2].get_text()
        email = data[3].get_text()
        app_id = 4589594
        auth_data = auth(email, password, client_id=app_id, scope=["stats", "groups", "wall", "offline"])
        token_file = open("{}/token.txt".format(stats.HOME), mode="w")
        print(*auth_data, sep=",", file=token_file)
        token_file.close()

        access_token, user = auth_data
        user_data = stats.call_api("users.get", params={"user_ids": user}, token=access_token)[0]
        stats.call_api("stats.trackVisitor", params={}, token=access_token)  # needed for tracking you

        login_win.hide()
        if not main.is_visible():
            main.show_all()
        if logged_win.is_visible():
            logged_win.hide()
            self.account_menu()
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
        print(args, file=os.devnull)
        stats.upgrade(version=new_version)
        Gtk.main_quit()

    @staticmethod
    def update_menu(*args):
        """
        Checking for updates.
        :param args: used by GTK+
        """
        print(args, file=os.devnull)
        global new_version
        new_version = stats.upd_check()
        if new_version:
            update_win.format_secondary_text(
                update_win.get_message_area().get_children()[1].get_text().format(new_version))
            update_win.show_all()
        else:
            latest_win.show_all()

    @staticmethod
    def about_menu(*args):
        """
        Showing the "StatsAbout" window.
        :param args: used by GTK+
        """
        print(args, file=os.devnull)
        about_win.show_all()

builder = Gtk.Builder()
builder.add_from_file("{}/vk_stats.glade".format(stats.SCRIPTDIR))
builder.connect_signals(Handler())
builder.set_translation_domain("vk_stats")

about_win = builder.get_object("StatsAbout")

logged_win = builder.get_object("AccountLogged")
logged_text = logged_win.get_child().get_children()[0].get_text()

latest_win = builder.get_object("LatestVersion")

update_win = builder.get_object("FoundUpdate")

login_win = builder.get_object("AccountLogin")

error_win = builder.get_object("Error")

success_win = builder.get_object("Successfully")

main = builder.get_object("StatsMain")
main.show_all()

stats.no_console(error, success_win)

if "token.txt" in os.listdir(stats.HOME):
    access_token, user = open("{}/token.txt".format(stats.HOME)).read().split(",")
    user_data = stats.call_api("users.get", params={"user_ids": user}, token=access_token)[0]
    stats.call_api("stats.trackVisitor", params={}, token=access_token)  # needed for tracking you
else:
    main.hide()
    login_win.show_all()

Gtk.main()
