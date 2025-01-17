
![Alt text](https://i.imgur.com/AHBXvnK.png "Optional title")
# ABOUT
Webman Classics Maker is tool for the PS3 that makes PKG shortcuts for ISO files straight to the home menu. It is using web commands  through webMAN-mod to mount and launch the ISOs automatically:
http://www.psx-place.com/threads/webman-mod-web-commands.1508/

This software is under GPLv2 license: https://www.gnu.org/licenses/old-licenses/gpl-2.0.en.html, not to be confused with the GPLv3 license.

# BUILDS
Get the latest build from releases:
https://github.com/Roet-Ivar/Webman-Classics-Maker/releases/

# TOOLS/BINARIES USED

* SCETOOL 0.2.9 (scetool.exe):
https://github.com/naehrwert/scetool

* OpenSCETool (oscetool):
https://github.com/spacemanspiff/oscetool

* PSL1GHT pkgcrypt (python3 version)
https://github.com/lephilousophe/PSL1GHT/tree/use-python3/tools/ps3py

* PARAM_SFO_EDITOR (Aldos PS3 tool collection)
https://www.aldostools.org/

* webMan-mod
https://github.com/aldostools/webMAN-MOD


**Credits goes to all of you guys!**

------------------------------------------------------------------------
# HOW TO USE
1. PS3: Dump your disc-based games (multiman is great for this)
2. PS3: Make sure webMan-mod from aldostools is installed
3. PC: Start Webman Classics Maker application
4. PC: Fetch games-list over FTP
5. PC: Build PKG forwarder for the game you like
6. PS3: Install PKG on PS3 and enjoy disc-images straight from XMB	
---------------------------------------------------------------------------------------------------	
# TROUBLESHOOTING
	
* If you hear three fast beeps: Probably a misspelled path to the ISO, double check it (case sensitive)!
* Games only mounts but doesn't automatically start: the timings on the webcommand are not enough for
your HDD read speeds, see the forum thread for mor info.  	
---------------------------------------------------------------------------------------------------

# Dev environment setup 

* install python3.9+ x86_64 (https://www.python.org/downloads/release/python-390/)
* pip install Pillow (might be bundled in the windows version)
* pip install pyinstaller
* pip install tqdm

**Building the executable**

* Run the pyinstaller-scipts located in:
/Webman-Classics-Maker/resources/tools/util_scripts/_pyinstaller_and_release_scripts/
* Run your new **webman-classics-maker.exe** based on your new changes


# Linux dev environment setup

* sudo apt-get update
* sudo apt-get install python3.9
* sudo apt-get install python3-tk
* sudo apt-get install python-pip
* sudo apt-get install python3.9-dev
* pip install Pillow
* pip install pyinstaller
* pip install tqdm

