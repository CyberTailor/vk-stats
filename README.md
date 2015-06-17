#SysRq VK Stats
Tool for gathering statistics from VKontakte groups.

##Requirements
* Python >= 3.3

##Usage
`./stats.py <group> [opts]`

`./stats.py --help` - show help

`./stats.py --version` - show version

`./stats.py x --update` - check for updates

##Command-line arguments
###--mode {posts, likers, liked}
**Posts:** count of posts

**Likers:** count of done likes

**Liked:** count of collected likes

###--export {csv, txt, all}
**TXT:** usual text file

**CSV:** ( **C**omma **S**eparated **V**alues ), open it in *MS Excel* or *LibreOffice Calc*

###--posts <number>
Limit for posts.

**Default:** 0

###--date <yyyy/mm/dd>
The earliest date of post.

**Default:** 0/0/0

###--login
Get access to VKontakte.

###--verbose
Verbose output.