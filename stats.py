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
Gathering statistics from VKontakte groups.
"""
__author__ = 'CyberTailor <cybertailor@gmail.com>'
__version__ = "0.5"
v_number = 1
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
from datetime import datetime
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


def log_write(message, *, file):
    """
    Writing time and message to file-like object
    :param message: any object
    :param file: object which is supporting write method
    """
    current_time = time.strftime("%H:%M:%S")
    print("{}: {}".format(current_time, message), file=file)
    file.flush()


def parse_cmd_args():
    """
    Parsing command-line arguments.
    """
    parser = argparse.ArgumentParser(description=_("Gathering stats from VKontakte groups."))
    parser.add_argument("group", help=_("group in which the program will gather stats"))
    parser.add_argument("--version", action="version",
                        version="SysRq VK Stats v{}".format(__version__))
    parser.add_argument("--update", action="store_true",
                        help=_("check for updates"))
    parser.add_argument("--mode", default="posts", choices=["posts", "likers", "liked"],
                        help=_("specify stats mode"))
    parser.add_argument("--export", default="csv", choices=["csv", "txt", "all"],
                        help=_("specify export type"))
    parser.add_argument("--login", action="store_true",
                        help=_("get access to vk.com"))
    parser.add_argument("--posts", type=int, default=0,
                        help=_("set number of posts to scan"))
    parser.add_argument("--date", default="0/0/0",
                        help=_("the earliest date of post in yyyy/mm/dd format"))
    parser.add_argument("--verbose", action="store_true", help=_("verbose output"))
    return vars(parser.parse_args())


def upgrade(version):
    """
    Upgrading program
    :param version: version name for VK Stats
    """
    print(_("Creating temporary directory..."))
    tmpdir = tempfile.mktemp(prefix="sysrq-")
    os.mkdir(tmpdir)
    print(_("Downloading new version..."))
    archive_file = "{}/VK_Stats.zip".format(tmpdir)
    request.urlretrieve("https://github.com/CyberTailor/vk-stats/releases/download/{0}/Stats-{0}.zip".format(version),
                        filename=archive_file)
    print(_("Unpacking archive..."))
    archive = zipfile.ZipFile(archive_file)
    archive.extractall(path=scriptdir)  # extract ZIP to script directory
    print(_("Exiting..."))
    exit()


def upd_check():
    """
    Checking for updates
    """
    latest_file = request.urlopen(
        "http://net2ftp.ru/node0/CyberTailor@gmail.com/versions.json").read().decode("utf-8")
    latest = json.loads(latest_file)["vk_stats"]
    if latest["number"] > v_number:
        print(_("Found update to version {}!\n\nChangelog:").format(latest["version"]))
        print(request.urlopen(
            "http://net2ftp.ru/node0/CyberTailor@gmail.com/vk_stats.CHANGELOG").read().decode("utf-8"))
        choice = input(_("\nUpgrade? (Y/n)")).lower()
        update_prompt = {"n": False, "not": False, "н": False, "нет": False}.get(choice, True)
        if update_prompt:
            upgrade(version=latest["version"])
        else:
            print(_("Passing update...\n"))
    else:
        print(_("You running latest version\n"))


def login():
    """
    Authorisation in https://vk.com
    :return: access_token for VK
    """
    print(_("If you're afraid of losing an account, then:\n" +
            "\t1) Go to http://vk.cc/3T1J9A\n" +
            "\t2) Login and give permissions to app\n" +
            "\t3) Copy part of urlbar, which is containing access_token\n" +
            "\t4) Create file 'token.txt' and write to one your access token"))
    email = input(_("Your login: "))
    password = getpass(_("Your password: "))
    app_id = 4589594
    token = auth(email, password, app_id, ["stats", "groups", "wall"])[0]
    token_file = open("{}/token.txt".format(scriptdir), mode="w")
    token_file.write(token)
    return token


def call_api(method, params, token):
    """
    Calling VK API
    :param method: method name from https://vk.com/dev/methods
    :param params: parameters for method
    :param token: access_token
    :return: result of calling API method
    """
    params.append(("access_token", token))
    params.append(("v", api_ver))
    url = "https://api.vk.com/method/{}?{}".format(method, urlencode(params))
    try:
        result = json.loads(request.urlopen(url, timeout=5).read().decode("utf-8"))
    except urllib.error.URLError:
        time.sleep(10)
        result = json.loads(request.urlopen(url, timeout=5).read().decode("utf-8"))
    if "error" in result:
        print("VK API:", result["error"]["error_msg"], file=sys.stderr)
        exit()
    time.sleep(0.4)
    return result["response"]


def compare_by_first(sequence):
    """
    Used for 'key' in max() function.
    For example: max([(1, {"a": 1, "b": 2}), (1, {"x": 8, "y": 9})], key=compare_by_first)
    :param sequence:
    :return: first element
    """
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

    def __init__(self, group_id, *, token, posts_lim=0, date_lim="0/0/0", log_file=sys.stdout,
                 export="csv", wall_filter="others"):
        self.group_id = group_id
        self.log_file = log_file
        self.token = token
        self.export = export
        self.screen_name = call_api(method="groups.getById",
                                    params=[("group_id", group_id)], token=access_token)[0]["screen_name"]
        self.wall = "-{}".format(self.group_id)
        self.filter = wall_filter

        # limit for posts
        if not posts_lim:
            self.posts_lim = call_api("wall.get", params=[("owner_id", self.wall), ("count", 1),
                                                          ("filter", self.filter)], token=self.token)["count"] - 1
        else:
            self.posts_lim = posts_lim
        log_write(_("limited to {} posts").format(self.posts_lim), file=self.log_file)

        # date limit
        date_list = date_lim.split("/")
        if not len(date_list) == 3:
            print(_("Incorrect date!"), file=sys.stderr)
            exit()
        if not int("".join(date_list)):
            self.date_lim = None
        else:
            self.date_lim = time.mktime((int(date_list[0]), int(date_list[1]), int(date_list[2]), 0, 0, 0, 0, 0, 0))
            log_write(_("limited to {} date").format(date_lim), file=self.log_file)

    def posts_list(self):
        """
        Making list of posts with senders' IDs and count of likes.
        :return: list of posts
        """
        posts = []
        result = []
        thousands_range = self.posts_lim // 1000
        thousands_out = self.posts_lim % 1000
        hundreds_range = thousands_out // 100
        hundreds_out = thousands_out % 100
        tens_range = hundreds_out // 10
        tens_out = hundreds_out % 10
        offset = 0

        for post in range(thousands_range):
            data = call_api("execute.wallGetThousand", params=[("owner_id", self.wall),
                                                               ("offset", offset), ("filter", self.filter)],
                            token=self.token)
            posts.extend(data)
            offset += 1000
        if thousands_out:
            for post in range(hundreds_range):
                data = call_api("wall.get", params=[("owner_id", self.wall), ("count", 100), ("offset", offset),
                                                    ("filter", self.filter)], token=self.token)["items"]
                posts.extend(data)
                offset += 100
        if hundreds_out:
            for post in range(tens_range):
                data = call_api("wall.get", params=[("owner_id", self.wall), ("count", 10), ("offset", offset),
                                                    ("filter", self.filter)], token=self.token)["items"]
                posts.extend(data)
                offset += 10
        if tens_out:
            for post in range(tens_out):
                data = call_api("wall.get", params=[("owner_id", self.wall), ("count", 1), ("offset", offset),
                                                    ("filter", self.filter)], token=self.token)["items"][0]
                posts.append(data)
                offset += 1

        for data in posts:
            post_id = data["id"]
            from_id = data["from_id"]
            likes = data["likes"]["count"]
            date = data["date"]
            human_date = time.strftime("%Y/%m/%d", datetime.fromtimestamp(date).timetuple())
            if self.date_lim:
                if date < self.date_lim:
                    break
            log_write(_("[{}%] post https://vk.com/wall{}_{}:\n" +
                        "\tfrom: https://vk.com/id{}\n" +
                        "\tlikes: {}\n" +
                        "\tdate (yyyy/mm/dd): {}").format(percents(data, posts), self.wall, post_id, from_id,
                                                          likes, human_date),
                      file=self.log_file)
            result.append({"data": (from_id, likes), "id": post_id})
        self.log_file.flush()
        return result

    def likers(self):
        """
        People who did likes.
        :return: list of dictionaries {post id: list of likes}
        """
        plist = self.posts_list()
        id_list = [data["id"] for data in plist]
        result = []

        for post_data, post_id in zip(plist, id_list):
            if post_data["data"][1]:
                likes_data = call_api("likes.getList", params=[("type", "post"), ("owner_id", self.wall),
                                                               ("item_id", post_id), ("count", 1000)], token=self.token)
                log_write(_("[{}%] post https://vk.com/wall{}_{} :\n" +
                            "\tlikes: {}\n" +
                            "\tlikers: {}").format(percents(post_id, id_list), self.wall, post_id, likes_data["count"],
                                                   str(["https://vk.com/id" + str(user) for user in
                                                        likes_data["items"]])[1:-1]),
                          file=self.log_file)
                if likes_data["count"] < 1000:
                    result.append({post_id: likes_data["items"]})
                else:
                    likes_list = []

                    thousands_range = likes_data["count"] // 1000
                    thousands_out = likes_data["count"] % 1000
                    hundreds_range = thousands_out // 100
                    hundreds_out = thousands_out % 100
                    tens_range = hundreds_out // 10
                    tens_out = hundreds_out % 10
                    offset = 0

                    for post in range(thousands_range):
                        data = call_api("likes.getList", params=[("type", "post"), ("owner_id", self.wall),
                                                                 ("item_id", post_id), ("offset", offset),
                                                                 ("count", 1000)],
                                        token=self.token)["items"]
                        likes_list.extend(data)
                        offset += 1000
                    if thousands_out:
                        for post in range(hundreds_range):
                            data = call_api("likes.getList", params=[("type", "post"), ("owner_id", self.wall),
                                                                     ("item_id", post_id), ("offset", offset),
                                                                     ("count", 100)],
                                            token=self.token)["items"]
                            likes_list.extend(data)
                            offset += post * 100
                    if hundreds_out:
                        for post in range(tens_range):
                            data = call_api("likes.getList", params=[("type", "post"), ("owner_id", self.wall),
                                                                     ("item_id", post_id), ("offset", offset),
                                                                     ("count", 10)],
                                            token=self.token)["items"]
                            likes_list.extend(data)
                            offset += 10
                    if tens_out:
                        for post in range(tens_out):
                            data = call_api("likes.getList", params=[("type", "post"), ("owner_id", self.wall),
                                                                     ("item_id", post_id), ("offset", offset),
                                                                     ("count", 1)],
                                            token=self.token)["items"]
                            likes_list.extend(data)
                            offset += 1
                    result.append({post_id: likes_list})
        return plist, result


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

        from_ids = [uid["data"][0] for uid in plist]
        from_ids_unique = list({uid for uid in from_ids})
        from_list = []
        for uid in from_ids_unique:
            data = call_api("users.get", params=[("user_ids", uid), ("fields", "screen_name")], token=self.token)[0]
            if "deactivated" in data:  # if user is deleted
                data["screen_name"] = data["deactivated"].upper()
            posts_from_user = from_ids.count(uid)
            log_write(
                _(
                    "[{}%] user {}:\n" +
                    "\tposts: {}\n" +
                    "\tURL: https://vk.com/{screen_name}\n" +
                    "\tname: {first_name} {last_name}").format(percents(uid, from_ids_unique), uid, posts_from_user,
                                                               **data), file=self.log_file)
            from_list.append((posts_from_user, data))
        return from_list

    def stats(self):
        """
        Exporting statistics for posts
        """
        posts_data = self.gather_stats()
        posts_data_csv = posts_data.copy()
        if not self.export == "csv":
            log_write(_("Exporting to {}").format("TXT"), file=self.log_file)
            res_txt = "posts_{}.txt".format(self.screen_name)
            if res_txt in os.listdir("{}/results".format(scriptdir)):
                os.remove("{}/results/{}".format(scriptdir, res_txt))
            txt_file = open("{}/results/{}".format(scriptdir, res_txt), mode="a")
            print(_("STATISTICS FOR POSTS"), file=txt_file)
            while posts_data:
                max_object = max(posts_data, key=compare_by_first)
                max_index = posts_data.index(max_object)
                max_count = max_object[0]
                user_data = posts_data.pop(max_index)[1]
                user_string = "https://vk.com/{screen_name} ({first_name} {last_name}): {0}".format(max_count,
                                                                                                    **user_data)
                log_write(_("Wrote: {}").format(user_string), file=self.log_file)
                print(user_string, file=txt_file)
        if not self.export == "txt":
            log_write(_("Exporting to {}").format("CSV"), file=self.log_file)
            res_csv = "posts_{}.csv".format(self.screen_name)
            if res_csv in os.listdir("{}/results".format(scriptdir)):
                os.remove("{}/results/{}".format(scriptdir, res_csv))
            csv_file = open("{}/results/{}".format(scriptdir, res_csv), mode="w", newline="")
            writer = csv.writer(csv_file)
            rows = [["URL", _("Name"), _("Posts")]]
            while posts_data_csv:
                max_object = max(posts_data_csv, key=compare_by_first)
                max_index = posts_data_csv.index(max_object)
                max_count = max_object[0]
                user_data = max_object[1]
                posts_data_csv.pop(max_index)
                rows.append(["https://vk.com/{screen_name}".format(**user_data),
                             "{first_name} {last_name}".format(**user_data),
                             max_count])
                log_write(_("Wrote: {}").format("https://vk.com/{screen_name},".format(**user_data) +
                                                "{first_name} {last_name},".format(**user_data) +
                                                str(max_count)), file=self.log_file)
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

        data = [val["data"] for val in plist]
        users = {val[0]: 0 for val in data}
        result = []
        for user, likes in data:
            users[user] += likes
        for user, likes in users.items():
            user_info = call_api("users.get", params=[("user_ids", user), ("fields", "screen_name")],
                                 token=self.token)[0]
            if "deactivated" in user_info:
                user_info["screen_name"] = user_info["deactivated"].upper()
            log_write(
                _(
                    "[{}%] user {}:\n" +
                    "\tlikes: {}\n" +
                    "\tURL: https://vk.com/{screen_name}\n" +
                    "\tname: {first_name} {last_name}").format(percents((user, likes), list(users.items())),
                                                               user, likes, **user_info), file=self.log_file)
            result.append((likes, user_info))
        return result

    def stats(self):
        """
        Exporting statistics for likes
        """
        likes_data = self.gather_stats()
        likes_data_csv = likes_data.copy()
        if not self.export == "csv":
            log_write(_("Exporting to {}").format("TXT"), file=self.log_file)
            res_txt = "liked_{}.txt".format(self.screen_name)
            if res_txt in os.listdir("{}/results".format(scriptdir)):
                os.remove("{}/results/{}".format(scriptdir, res_txt))
            txt_file = open("{}/results/{}".format(scriptdir, res_txt), mode="a")
            print(_("STATISTICS FOR LIKES"), file=txt_file)
            while likes_data:
                max_object = max(likes_data, key=compare_by_first)
                max_count = max_object[0]
                if max_count:
                    max_index = likes_data.index(max_object)
                    user_data = likes_data.pop(max_index)[1]
                    user_string = "https://vk.com/{screen_name} ({first_name} {last_name}): {0}".format(max_count,
                                                                                                        **user_data)
                    log_write(_("Wrote: {}").format(user_string), file=self.log_file)
                    print(user_string, file=txt_file)
                else:
                    break
        if not self.export == "txt":
            log_write(_("Exporting to {}").format("CSV"), file=self.log_file)
            res_csv = "liked_{}.csv".format(self.screen_name)
            if res_csv in os.listdir("{}/results".format(scriptdir)):
                os.remove("{}/results/{}".format(scriptdir, res_csv))
            csv_file = open("{}/results/{}".format(scriptdir, res_csv), mode="w", newline="")
            writer = csv.writer(csv_file)
            rows = [["URL", _("Name"), _("Likes")]]
            while likes_data_csv:
                max_object = max(likes_data_csv, key=compare_by_first)
                max_count = max_object[0]
                if max_count:
                    max_index = likes_data_csv.index(max_object)
                    user_data = likes_data_csv.pop(max_index)[1]
                    rows.append(["https://vk.com/{screen_name}".format(**user_data),
                                 "{first_name} {last_name}".format(**user_data),
                                 max_count])
                    log_write(_("Wrote: {}").format("https://vk.com/{screen_name},".format(**user_data) +
                                                    "{first_name} {last_name},".format(**user_data) +
                                                    str(max_count)), file=self.log_file)
                else:
                    break
            writer.writerows(rows)
            self.log_file.flush()


class LikersStats(Stats):
    """
    Gather, make and export statistics for likers
    """

    def gather_stats(self):
        """
        Gathering statistics for likers.
        :return: dictionary with user's information and general count of likes
        """
        likers_data = self.likers()[1]
        likers_list = []
        for post in likers_data:
            likers_list.extend(list(post.values())[0])
        likers_unique = list({user for user in likers_list})
        result = []
        for uid in likers_unique:
            data = call_api("users.get", params=[("user_ids", uid), ("fields", "screen_name")], token=self.token)[0]
            if "deactivated" in data:
                data["screen_name"] = data["deactivated"].upper()
            likes_from_user = likers_list.count(uid)
            log_write(
                _(
                    "[{}%] user {}:\n" +
                    "\tlikes: {}\n" +
                    "\tURL: https://vk.com/{screen_name}\n" +
                    "\tname: {first_name} {last_name}").format(percents(uid, likers_unique), uid,
                                                               likes_from_user, **data), file=self.log_file)
            result.append((likes_from_user, data))
        return result

    def stats(self):
        """
        Exporting statistics for posts
        """
        likers_data = self.gather_stats()
        likers_data_csv = likers_data.copy()
        if not self.export == "csv":
            log_write(_("Exporting to {}").format("TXT"), file=self.log_file)
            res_txt = "likers_{}.txt".format(self.screen_name)
            if res_txt in os.listdir("{}/results".format(scriptdir)):
                os.remove("{}/results/{}".format(scriptdir, res_txt))
            txt_file = open("{}/results/{}".format(scriptdir, res_txt), mode="a")
            print(_("STATISTICS FOR LIKERS"), file=txt_file)
            while likers_data:
                max_object = max(likers_data, key=compare_by_first)
                max_index = likers_data.index(max_object)
                max_count = max_object[0]
                user_data = likers_data.pop(max_index)[1]
                user_string = "https://vk.com/{screen_name} ({first_name} {last_name}): {0}".format(max_count,
                                                                                                    **user_data)
                log_write(_("Wrote: {}").format(user_string), file=self.log_file)
                print(user_string, file=txt_file)
        if not self.export == "txt":
            log_write(_("Exporting to {}").format("CSV"), file=self.log_file)
            res_csv = "likers_{}.csv".format(self.screen_name)
            if res_csv in os.listdir("{}/results".format(scriptdir)):
                os.remove("{}/results/{}".format(scriptdir, res_csv))
            csv_file = open("{}/results/{}".format(scriptdir, res_csv), mode="w", newline="")
            writer = csv.writer(csv_file)
            rows = [["URL", _("Name"), _("Likes")]]
            while likers_data_csv:
                max_object = max(likers_data_csv, key=compare_by_first)
                max_index = likers_data_csv.index(max_object)
                max_count = max_object[0]
                user_data = max_object[1]
                likers_data_csv.pop(max_index)
                rows.append(["https://vk.com/{screen_name}".format(**user_data),
                             "{first_name} {last_name}".format(**user_data),
                             max_count])
                log_write(_("Wrote: {}").format("https://vk.com/{screen_name},".format(**user_data) +
                                                "{first_name} {last_name},".format(**user_data) +
                                                str(max_count)), file=self.log_file)
            writer.writerows(rows)


if __name__ == "__main__":
    args = parse_cmd_args()
    if args["update"]:
        upd_check()

    if "token.txt" not in os.listdir(scriptdir) or args["login"]:
        access_token = login()
    else:
        access_token = open("token.txt").read()

    call_api(method="stats.trackVisitor", params=[], token=access_token)  # needed for stats gathering

    group_data = call_api(method="groups.getById",
                          params=[("group_id", args["group"].split("/")[-1])], token=access_token)[0]
    group = group_data["id"]
    group_name = group_data["screen_name"]
    group_title = group_data["name"]

    if "stats.log" in os.listdir("{}/logs".format(scriptdir)):
        os.remove("{}/logs/stats.log".format(scriptdir))
    log_file_main = "{}/logs/stats.log".format(scriptdir)
    log = sys.stdout if args["verbose"] else open(log_file_main, mode="a")

    if not args["verbose"]:
        print(_("STARTED GATHERING STATS FROM '{}'").format(group_title.upper()))
    log_write(_("STATISTICS MODE: {}").format(args["mode"].upper()), file=log)
    log_write(_("STARTED GATHERING STATS FROM '{}'").format(group_title.upper()), file=log)

    if args["mode"] == "posts":
        stats = PostsStats(group, token=access_token, posts_lim=args["posts"],
                           date_lim=args["date"], log_file=log, export=args["export"])
    elif args["mode"] == "liked":
        stats = LikedStats(group, token=access_token, posts_lim=args["posts"],
                           date_lim=args["date"], log_file=log, export=args["export"])
    else:
        stats = LikersStats(group, token=access_token, posts_lim=args["posts"],
                            date_lim=args["date"], log_file=log, export=args["export"], wall_filter="all")

    stats.stats()

    log_write(_("SUCCESSFUL!"), file=log)
    if not args["verbose"]:
        print(_("SUCCESSFUL!"))
