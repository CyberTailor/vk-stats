#!/usr/bin/env python3
# coding=utf-8
# sorry_for_my=english

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
v_number = 2
api_ver = "5.34"

import os
import sys
import csv
import argparse
import tempfile
import zipfile
import json
import gettext
import time
import urllib.error
import socket
from getpass import getpass
from urllib import request
from urllib.parse import urlencode

from vk_api_auth.vk_auth import auth
from gettext_windows import gettext_windows

scriptdir = os.path.abspath(os.path.dirname(__file__))  # directory with this script
# translating strings in _()
lang = gettext_windows.get_language()
translation = gettext.translation("vk_stats", localedir="{}/locale".format(scriptdir), languages=lang)
_ = translation.gettext


def log_write(message, *, to=sys.stdout):
    """
    Writing time and message to standard stream
    :param to: sys.stdout or sys.stderr
    :param message: any object
    """
    current_time = time.strftime("%H:%M:%S")
    print("{}: {}".format(current_time, message), file=to)


def parse_cmd_args():
    """
    Parsing command-line arguments.
    """
    parser = argparse.ArgumentParser(description=_("Computing rating of activity in VK groups. [] = default values"))
    parser.add_argument("wall", help=_("smth where the program will gather stats"))
    parser.add_argument("--version", action="version",
                        version="SysRq VK Stats v{}".format(__version__))
    parser.add_argument("--update", action="store_true",
                        help=_("check for updates"))
    parser.add_argument("--mode", default="posts", choices=["posts", "likers", "liked"],
                        help=_("specify a mode of stats [posts]"))
    parser.add_argument("--export", default="csv", choices=["csv", "txt", "all"],
                        help=_("specify a type of export [CSV]"))
    parser.add_argument("--login", action="store_true",
                        help=_("get access to the VK"))
    parser.add_argument("--posts", type=int, default=0,
                        help=_("set a number of posts to scan [all]"))
    parser.add_argument("--date", default="0/0/0",
                        help=_("the earliest date of post in the yyyy/mm/dd format [0/0/0]"))
    return vars(parser.parse_args())


def upgrade(version):
    """
    Upgrading program
    :param version: version name for VK Stats
    """
    log_write(_("Creating a temporary directory..."))
    tmpdir = tempfile.mktemp(prefix="sysrq-")
    os.mkdir(tmpdir)
    log_write(_("Downloading the new version..."))
    archive_file = "{}/VK_Stats.zip".format(tmpdir)
    request.urlretrieve("https://github.com/CyberTailor/vk-stats/releases/download/{0}/Stats-{0}.zip".format(version),
                        filename=archive_file)
    log_write(_("Unpacking an archive..."))
    archive = zipfile.ZipFile(archive_file)
    archive.extractall(path=scriptdir)  # extract ZIP to script directory
    log_write(_("Exiting..."))
    exit()


def upd_check():
    """
    Checking for updates
    """
    latest_file = request.urlopen(
        "http://net2ftp.ru/node0/CyberTailor@gmail.com/versions.json").read().decode("utf-8")
    latest = json.loads(latest_file)["vk_stats"]
    if latest["number"] > v_number:
        log_write(_("Found the update to version {}!\n\nChangelog:").format(latest["version"]))
        print(request.urlopen(
            "http://net2ftp.ru/node0/CyberTailor@gmail.com/vk_stats.CHANGELOG").read().decode("utf-8"))
        choice = input(_("\nUpgrade? (Y/n)")).lower()
        update_prompt = {"n": False, "not": False, "н": False, "нет": False}.get(choice, True)
        if update_prompt:
            upgrade(version=latest["version"])
        else:
            log_write(_("Passing the update...\n"))
    else:
        log_write(_("You running the latest version\n"))


def login():
    """
    Authorisation in https://vk.com
    :return: access_token for VK
    """
    print(_("If you're afraid of losing the account, then:\n" +
            "\t1) Go to http://vk.cc/3T1J9A\n" +
            "\t2) Login and give permissions to app\n" +
            "\t3) Copy part of an urlbar, which is containing the access_token\n" +
            "\t4) Create a file 'token.txt' and write to one your access token"))
    email = input(_("Your login: "))
    password = getpass(_("Your password: "))
    app_id = 4589594
    token = auth(email, password, app_id, ["stats", "groups", "wall"])[0]
    token_file = open("{}/token.txt".format(scriptdir), mode="w")
    token_file.write(token)
    return token


def call_api(method, *, token, params):
    """
    Calling VK API
    :param method: method name from https://vk.com/dev/methods
    :param params: parameters for method (dict)
    :param token: access_token
    :return: result of calling API method
    """
    params.update({"access_token": token, "v": api_ver})
    data = urlencode(params)
    headers = {"Content-length": str(len(data))}
    url = "https://api.vk.com/method/" + method
    req = request.Request(url, data=bytes(data, encoding="utf-8"), headers=headers)
    result = None

    while result is None:
        try:
            result = json.loads(request.urlopen(req, timeout=5).read().decode("utf-8"))
        except (urllib.error.URLError, socket.error) as err:
            log_write(_("Error: {}. Waiting for 10 seconds...").format(err))
            time.sleep(10)
    if "error" in result:
        log_write("VK API: {}".format(result["error"]["error_msg"]), to=sys.stderr)
        exit()
    time.sleep(0.33)
    return result["response"]


def _compare_by_first(sequence):
    return sequence[0]


def percents(el, seq):
    """
    Computing progress for sequence.
    :param el: element
    :param seq: sequence
    :return: number of percents
    """
    return (seq.index(el) + 1) * 100 // len(seq)


class Stats:
    """
    Gathering statistics
    """

    def __init__(self, wall_id, owner_screen_name, *, token, posts_lim=0, date_lim="0/0/0",
                 export="csv", wall_filter="others"):
        self.wall = wall_id
        self.token = token
        self.export = export
        self.screen_name = owner_screen_name
        self.filter = wall_filter

        # limit for posts
        if not posts_lim:
            self.posts_lim = call_api("wall.get", params={"owner_id": self.wall, "count": 1,
                                                          "filter": self.filter}, token=self.token)["count"] - 1
        else:
            self.posts_lim = posts_lim
        log_write(_("limited to {} posts").format(self.posts_lim))

        # date limit
        date_list = date_lim.split("/")
        if not len(date_list) == 3:
            print(_("Incorrect date!"), file=sys.stderr)
            exit()
        if not int("".join(date_list)):
            self.date_lim = None
        else:
            self.date_lim = time.mktime((int(date_list[0]), int(date_list[1]), int(date_list[2]), 0, 0, 0, 0, 0, 0))
            log_write(_("limited to {} date").format(date_lim))

    def _check_limit(self, data):
        if self.date_lim:
            date = data["date"]
            if date < self.date_lim:
                log_write(_("Reached the limit for date."))
                return True
        return False

    def _get_posts_pack(self, *, offset, count):
        if count == 1000:
            data = call_api("execute.wallGetThousand", params={"owner_id": self.wall,
                                                               "offset": offset, "filter": self.filter},
                            token=self.token)
        else:
            data = call_api("wall.get", params={"owner_id": self.wall, "count": count, "offset": offset,
                                                "filter": self.filter}, token=self.token)["items"]
        return data

    def _get_posts(self):
        posts = []
        thousands_range = self.posts_lim // 1000
        thousands_out = self.posts_lim % 1000
        hundreds_range = thousands_out // 100
        hundreds_out = thousands_out % 100
        if hundreds_out:
            hundreds_range += 1
        limit_list = list(range(self.posts_lim))
        offset = 0
        progress = 0

        for post in range(thousands_range):
            if offset > 0:
                if self._check_limit(posts[-1]):
                    return posts
            cur_progress = percents(offset, limit_list)
            if cur_progress > progress:
                progress = cur_progress
                log_write(_("Getting posts: {}%").format(cur_progress))
            posts.extend(self._get_posts_pack(offset=offset, count=1000))
            offset += 1000
        for post in range(hundreds_range):
            if offset > 0:
                if self._check_limit(posts[-1]):
                    return posts
            cur_progress = percents(offset, limit_list)
            if cur_progress > progress:
                progress = cur_progress
                log_write(_("Getting posts: {}%").format(cur_progress))
            posts.extend(self._get_posts_pack(offset=offset, count=100))
            offset += 100
        return posts

    def posts_list(self):
        """
        Making list of posts with senders' IDs and count of likes.
        :return: list of posts
        """
        posts = self._get_posts()
        result = []
        progress = 0

        for data in posts:
            post_id = data["id"]
            from_id = data["from_id"]
            likes = data["likes"]["count"]
            if self._check_limit(data):
                break
            cur_progress = percents(data, posts)
            if cur_progress > progress:
                progress = cur_progress
                log_write(_("Processing posts: {}%").format(cur_progress))
            result.append({"data": (from_id, likes), "id": post_id})
        return result

    def users(self, users_list):
        """
        List of information about users
        :param users_list: list of users' IDs
        """
        result = []
        task = list(range(len(users_list)))
        progress = 0
        did = 0

        while users_list:
            users = ""
            for user in users_list[:1001]:
                users += str(user) + ","
            users = users[:-1]
            cur_progress = percents(did, task)
            if cur_progress > progress:
                log_write(_("Getting list of users: {}%").format(cur_progress))
            data = call_api("users.get", params={"user_ids": users, "fields": "screen_name"}, token=self.token)
            result.extend(data)
            del users_list[:1001]
        return result

    def likers(self):
        """
        Users who liked posts.
        :return: lists of posts and likers
        """
        plist = self.posts_list()
        id_list_orig = [data["id"] for data in plist]
        id_list = id_list_orig.copy()
        result = []

        twenty_five_range = len(id_list) // 25
        twenty_five_out = len(id_list) % 25
        tens_range = twenty_five_out // 10
        tens_out = twenty_five_out % 10
        progress = 0
        did = 0
        task = list(range(len(id_list)))

        for i in range(twenty_five_range):
            cur_progress = percents(did, task)
            if cur_progress > progress:
                progress = cur_progress
                log_write(_("Getting likers: {}%").format(cur_progress))
            count = [id_list.pop() for os._ in range(25)]
            data = call_api("execute.likesGetBigList",
                            params={"wall": self.wall, "posts": ("{}," * 25)[:-1].format(*count)}, token=self.token)
            if data:
                result.extend(data)
            did += 25

        for i in range(tens_range):
            cur_progress = percents(did, task)
            if cur_progress > progress:
                progress = cur_progress
                log_write(_("Getting likers: {}%").format(cur_progress))
            count = [id_list.pop() for os._ in range(10)]
            data = call_api("execute.likesGetBigList",
                            params={"wall": self.wall, "posts": ("{}," * 10)[:-1].format(*count)}, token=self.token)
            if data:
                result.extend(data)
            did += 10

        for i in range(tens_out):
            item = id_list.pop()
            cur_progress = percents(did, task)
            if cur_progress > progress:
                progress = cur_progress
                log_write(_("Getting likers: {}%").format(cur_progress))
            data = call_api("likes.getList", params={"type": "post", "owner_id": self.wall,
                                                     "item_id": item, "count": 1000},
                            token=self.token)["items"]
            if data:
                result.extend(data)
            did += 1
        return id_list_orig, result


class PostsStats(Stats):
    """
    Gather, make and export statistics for posts
    """

    def gather_stats(self):
        """
        Gathering statistics for posts.
        :return: tuple with user's information and count of posts
        """
        plist = self.posts_list()
        progress = 0

        from_ids = [uid["data"][0] for uid in plist]
        from_ids_unique = list({uid for uid in from_ids})
        from_list = []
        data = self.users(from_ids_unique)

        for user in data:
            if "deactivated" in user:  # if user is deleted or banned
                user["screen_name"] = user["deactivated"].upper()
            posts_from_user = from_ids.count(user["id"])
            cur_progress = percents(user, data)
            if cur_progress > progress:
                progress = cur_progress
                log_write(_("Processing user: {}%").format(cur_progress))
            from_list.append((posts_from_user, user))
        return from_list

    def stats(self):
        """
        Exporting statistics for posts
        """
        posts_data = self.gather_stats()
        posts_data_csv = posts_data.copy()
        if not self.export == "csv":
            log_write(_("Exporting to {}").format("TXT"))
            res_txt = "posts_{}.txt".format(self.screen_name)
            if res_txt in os.listdir("{}/results".format(scriptdir)):
                os.remove("{}/results/{}".format(scriptdir, res_txt))
            txt_file = open("{}/results/{}".format(scriptdir, res_txt), mode="a")
            print(_("STATISTICS FOR POSTS"), file=txt_file)
            while posts_data:
                max_object = max(posts_data, key=_compare_by_first)
                max_index = posts_data.index(max_object)
                max_count = max_object[0]
                user_data = posts_data.pop(max_index)[1]
                user_string = "https://vk.com/{screen_name} ({first_name} {last_name}): {0}".format(max_count,
                                                                                                    **user_data)
                print(user_string, file=txt_file)
        if not self.export == "txt":
            log_write(_("Exporting to {}").format("CSV"))
            res_csv = "posts_{}.csv".format(self.screen_name)
            if res_csv in os.listdir("{}/results".format(scriptdir)):
                os.remove("{}/results/{}".format(scriptdir, res_csv))
            csv_file = open("{}/results/{}".format(scriptdir, res_csv), mode="w", newline="")
            writer = csv.writer(csv_file)
            rows = [["URL", _("Name"), _("Posts")]]
            while posts_data_csv:
                max_object = max(posts_data_csv, key=_compare_by_first)
                max_index = posts_data_csv.index(max_object)
                max_count = max_object[0]
                user_data = max_object[1]
                posts_data_csv.pop(max_index)
                rows.append(["https://vk.com/{screen_name}".format(**user_data),
                             "{first_name} {last_name}".format(**user_data),
                             max_count])
            writer.writerows(rows)


class LikedStats(Stats):
    """
    Gather, make and export statistics for liked posts
    """

    def gather_stats(self):
        """
        Gathering statistics for liked posts.
        :return: dictionary with user's information and general count of likes
        """
        plist = self.posts_list()
        progress = 0

        data = [val["data"] for val in plist]
        users = {val[0]: 0 for val in data}
        result = []
        for user, likes in data:
            users[user] += likes
        items_list = list(users.items())
        users_list = [key[0] for key in items_list]
        likes_list = [key[1] for key in items_list]

        users_data = self.users(users_list)
        for user, likes in zip(users_data, likes_list):
            if "deactivated" in user:
                user["screen_name"] = user["deactivated"].upper()
            cur_progress = percents(likes, likes_list)
            if cur_progress > progress:
                progress = cur_progress
                log_write(_("Processing user: {}%").format(cur_progress))
            result.append((likes, user))
        return result

    def stats(self):
        """
        Exporting statistics for likes
        """
        likes_data = self.gather_stats()
        likes_data_csv = likes_data.copy()
        if not self.export == "csv":
            log_write(_("Exporting to {}").format("TXT"))
            res_txt = "liked_{}.txt".format(self.screen_name)
            if res_txt in os.listdir("{}/results".format(scriptdir)):
                os.remove("{}/results/{}".format(scriptdir, res_txt))
            txt_file = open("{}/results/{}".format(scriptdir, res_txt), mode="a")
            print(_("STATISTICS FOR LIKES"), file=txt_file)
            while likes_data:
                max_object = max(likes_data, key=_compare_by_first)
                max_count = max_object[0]
                if max_count:
                    max_index = likes_data.index(max_object)
                    user_data = likes_data.pop(max_index)[1]
                    user_string = "https://vk.com/{screen_name} ({first_name} {last_name}): {0}".format(max_count,
                                                                                                        **user_data)
                    print(user_string, file=txt_file)
                else:
                    break
        if not self.export == "txt":
            log_write(_("Exporting to {}").format("CSV"))
            res_csv = "liked_{}.csv".format(self.screen_name)
            if res_csv in os.listdir("{}/results".format(scriptdir)):
                os.remove("{}/results/{}".format(scriptdir, res_csv))
            csv_file = open("{}/results/{}".format(scriptdir, res_csv), mode="w", newline="")
            writer = csv.writer(csv_file)
            rows = [["URL", _("Name"), _("Likes")]]
            while likes_data_csv:
                max_object = max(likes_data_csv, key=_compare_by_first)
                max_count = max_object[0]
                if max_count:
                    max_index = likes_data_csv.index(max_object)
                    user_data = likes_data_csv.pop(max_index)[1]
                    rows.append(["https://vk.com/{screen_name}".format(**user_data),
                                 "{first_name} {last_name}".format(**user_data),
                                 max_count])
                else:
                    break
            writer.writerows(rows)


class LikersStats(Stats):
    """
    Gather, make and export statistics for likers
    """

    def gather_stats(self):
        """
        Gathering statistics for likers.
        :return: dictionary with user's information and general count of likes
        """
        likers_data = self.likers()
        likers = likers_data[1]
        likers_unique = list({uid for uid in likers})
        result = []
        progress = 0
        did = 0
        task = list(range(len(likers_unique)))

        users_data = self.users(likers_unique)

        for liker in users_data:
            cur_progress = percents(did, task)
            count = likers.count(liker["id"])
            if "deactivated" in liker:
                liker["screen_name"] = liker["deactivated"].upper()
            if cur_progress > progress:
                progress = cur_progress
                log_write(_("Processing user: {}%").format(cur_progress))
            result.append((count, liker))
            did += 1
        return result

    def stats(self):
        """
        Exporting statistics for posts
        """
        likers_data = self.gather_stats()
        likers_data_csv = likers_data.copy()
        if not self.export == "csv":
            log_write(_("Exporting to {}").format("TXT"))
            res_txt = "likers_{}.txt".format(self.screen_name)
            if res_txt in os.listdir("{}/results".format(scriptdir)):
                os.remove("{}/results/{}".format(scriptdir, res_txt))
            txt_file = open("{}/results/{}".format(scriptdir, res_txt), mode="a")
            print(_("STATISTICS FOR LIKERS"), file=txt_file)
            while likers_data:
                max_object = max(likers_data, key=_compare_by_first)
                max_index = likers_data.index(max_object)
                max_count = max_object[0]
                user_data = likers_data.pop(max_index)[1]
                user_string = "https://vk.com/{screen_name} ({first_name} {last_name}): {0}".format(max_count,
                                                                                                    **user_data)
                print(user_string, file=txt_file)
        if not self.export == "txt":
            log_write(_("Exporting to {}").format("CSV"))
            res_csv = "likers_{}.csv".format(self.screen_name)
            if res_csv in os.listdir("{}/results".format(scriptdir)):
                os.remove("{}/results/{}".format(scriptdir, res_csv))
            csv_file = open("{}/results/{}".format(scriptdir, res_csv), mode="w", newline="")
            writer = csv.writer(csv_file)
            rows = [["URL", _("Name"), _("Likes")]]
            while likers_data_csv:
                max_object = max(likers_data_csv, key=_compare_by_first)
                max_index = likers_data_csv.index(max_object)
                max_count = max_object[0]
                user_data = max_object[1]
                likers_data_csv.pop(max_index)
                rows.append(["https://vk.com/{screen_name}".format(**user_data),
                             "{first_name} {last_name}".format(**user_data),
                             max_count])
            writer.writerows(rows)


if __name__ == "__main__":
    args = parse_cmd_args()
    if args["update"]:
        upd_check()

    if "token.txt" not in os.listdir(scriptdir) or args["login"]:
        access_token = login()
    else:
        access_token = open("token.txt").read()

    call_api(method="stats.trackVisitor", params={}, token=access_token)  # needed for stats gathering

    wall_data = call_api("utils.resolveScreenName", params={"screen_name": args["wall"].split("/")[-1]},
                         token=access_token)
    wall_type = wall_data["type"]
    obj_id = wall_data["object_id"]

    if wall_type == "group":
        group_data = call_api(method="groups.getById", params={"group_ids": obj_id}, token=access_token)[0]
        wall = "-{}".format(group_data["id"])
        screen_name = group_data["screen_name"]
        title = group_data["name"]
    else:
        profile = call_api(method="users.get", params={"user_ids": obj_id, "fields": "screen_name"},
                           token=access_token)[0]
        wall = profile["id"]
        screen_name = profile["screen_name"]
        title = "{first_name} {last_name}".format(**profile)

    log_write(_("STARTED GATHERING STATS FROM '{}'").format(title.upper()))

    if args["mode"] == "posts":
        stats = PostsStats(wall, screen_name, token=access_token, posts_lim=args["posts"],
                           date_lim=args["date"], export=args["export"])
    elif args["mode"] == "liked":
        stats = LikedStats(wall, screen_name, token=access_token, posts_lim=args["posts"],
                           date_lim=args["date"], export=args["export"])
    else:
        stats = LikersStats(wall, screen_name, token=access_token, posts_lim=args["posts"],
                            date_lim=args["date"], export=args["export"], wall_filter="all")

    stats.stats()

    log_write(_("SUCCESSFUL!"))
