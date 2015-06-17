#!/bin/bash

# Use this tool to update translations

cd locale/ru/LC_MESSAGES
msgfmt vk_stats.po
mv messages.mo vk_stats.mo
cd ../../..
