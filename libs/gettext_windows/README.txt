Module gettext_windows.py
-------------------------
This module helps to use standard Python gettext.py library on Windows.
It obtains user language code suitable for gettext from current Windows 
settings.

The module provides 2 functions: setup_env and get_language.

You may use setup_env before initializing gettext functions.

Or you can use get_language to get the list of language codes suitable
to pass them to gettext.find or gettext.translation function.

Usage example #1:

import gettext, gettext_windows
gettext_windows.setup_env()
gettext.install('myapp')

Usage example #2:

import gettext, gettext_windows
lang = gettext_windows.get_language()
translation = gettext.translation('myapp', languages=lang)
_ = translation.gettext
