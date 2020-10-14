import json, os, re, StringIO, sys, time, traceback
import PIL.Image as Image
from ftplib import FTP
from global_paths import GlobalVar
from shutil import copyfile

# adding util_scripts depending on if it's an executable or if it's running from the wcm_gui
if getattr(sys, 'frozen', False):
    sys.path.append(os.path.join(os.path.dirname(sys.executable), 'resources', 'tools', 'util_scripts'))
else:
    sys.path.append('..')

from global_paths import App as AppPaths
sys.path.append(AppPaths.settings)

class FtpGameList():
    def __init__(self, platform_filter):
        # platform filter to fetch
        self.platform_filter = platform_filter

        # messages
        self.PAUSE_MESSAGE              = 'Press ENTER to continue...'
        self.CONNECTION_ERROR_MESSAGE   = "TIPS: Check your PS3 ip-address in webMan VSH menu (hold SELECT on the XMB)"
        self.TITLE_ID_EXCEPTION_MESSAGE = """Exception: 'get_image' failed during regex operation."""

        # constants
        self.GAME_LIST_DATA_FILE    = os.path.join(AppPaths.application_path, 'game_list_data.json')
        self.NEW_LIST_DATA_FILE     = os.path.join(AppPaths.util_resources, 'game_list_data.json.BAK')

        # ftp settings
        with open(os.path.join(AppPaths.settings, 'ftp_settings.cfg')) as f:
            ftp_settings_file = json.load(f)
            f.close()

        # some PSP-images is found around 20MB into the ISO
        self.ftp_psp_png_offset_kb  = ftp_settings_file['ftp_psp_png_offset_kb']
        self.chunk_size_kb          = ftp_settings_file['ftp_chunk_size_kb']
        self.chunk_size_kb          = ftp_settings_file['ftp_chunk_size_kb']
        self.ps3_lan_ip             = ftp_settings_file['ps3_lan_ip']
        self.ftp_timeout            = ftp_settings_file['ftp_timeout']
        self.ftp_pasv_mode          = ftp_settings_file['ftp_pasv_mode']
        self.ftp_user               = ftp_settings_file['ftp_user']
        self.ftp_password           = ftp_settings_file['ftp_password']
        self.use_mock_data          = False

        self.PSP_ISO_PATH           = '/dev_hdd0/PSPISO/'
        self.PSX_ISO_PATH           = '/dev_hdd0/PSXISO/'
        self.PS2_ISO_PATH           = '/dev_hdd0/PS2ISO/'
        self.PS3_ISO_PATH           = '/dev_hdd0/PS3ISO/'

        # system specific variables
        self.psp_lines   = []
        self.psx_lines   = []
        self.ps2_lines   = []
        self.ps3_lines   = []
        self.all_lines  = []

        # filters and file extensions
        self.file_ext_filter = lambda x: x.upper().endswith(GlobalVar.file_extensions)

        # singular instances
        self.total_lines_count = 0
        self.game_count = 0

        self.ftp = None
        self.data_chunk = None

    def execute(self):
        try:
            print('Connection attempt to ' + self.ps3_lan_ip + ', timeout set to ' + str(self.ftp_timeout) + 's...\n')
            self.ftp = FTP(self.ps3_lan_ip, timeout=self.ftp_timeout)
            self.ftp.set_pasv = self.ftp_pasv_mode
            self.ftp.login(user=self.ftp_user, passwd=self.ftp_password)
            self.ftp.voidcmd('TYPE I')

            if self.platform_filter.lower() == 'all':
                self.ftp.retrlines('NLST ' + self.PSP_ISO_PATH, self.psp_lines.append)
                self.ftp.retrlines('NLST ' + self.PSX_ISO_PATH, self.psx_lines.append)
                self.ftp.retrlines('NLST ' + self.PS2_ISO_PATH, self.ps2_lines.append)
                self.ftp.retrlines('NLST ' + self.PS3_ISO_PATH, self.ps3_lines.append)

            elif self.platform_filter.lower() == 'psp':
                self.ftp.retrlines('NLST ' + self.PSP_ISO_PATH, self.psp_lines.append)

            elif self.platform_filter.lower() == 'psx':
                self.ftp.retrlines('NLST ' + self.PSX_ISO_PATH, self.psx_lines.append)

            elif self.platform_filter.lower() == 'ps2':
                self.ftp.retrlines('NLST ' + self.PS2_ISO_PATH, self.ps2_lines.append)

            elif self.platform_filter.lower() == 'ps3':
                self.ftp.retrlines('NLST ' + self.PS3_ISO_PATH, self.ps3_lines.append)

            # filter out any empty entries
            self.all_lines.append(self.psp_lines)
            self.all_lines.append(self.psx_lines)
            self.all_lines.append(self.ps2_lines)
            self.all_lines.append(self.ps3_lines)

            filtered_platform_list = []
            for p in self.all_lines:
                # filer the lines using the platform filter
                filtered_lines = filter(self.file_ext_filter, p)
                filtered_platform_list.append(filtered_lines)
                self.total_lines_count += len(filtered_lines)

            self.psp_lines = filtered_platform_list[0]
            self.psx_lines = filtered_platform_list[1]
            self.ps2_lines = filtered_platform_list[2]
            self.ps3_lines = filtered_platform_list[3]

            # after retrieving the list of file paths we fetch the actual data
            self.data_chunk = FTPDataHandler(self.ftp, self.total_lines_count)

        except Exception as e:
            error_message = str(e)
            print('Connection error: ' + error_message)
            print(self.CONNECTION_ERROR_MESSAGE)
            print('\n')

            return

        # open a copy of the current gamelist from disk
        with open(self.GAME_LIST_DATA_FILE) as f:
            self.json_game_list_data = json.load(f)

        # open a copy of an empty gamelist from disk
        with open(self.NEW_LIST_DATA_FILE) as f:
            self.new_json_game_list_data = json.load(f)

        # append the platform lists
        if self.platform_filter.lower() == 'all':
            for platform in self.json_game_list_data:
                self.new_platform_list_data = self.list_builder(platform[0:3])
        else:
            platform = self.platform_filter.lower()
            self.new_platform_list_data = self.list_builder(platform)

        # save updated gamelist to disk
        with open(self.GAME_LIST_DATA_FILE, 'w') as newFile:
            json_text = json.dumps(self.json_game_list_data, indent=4, separators=(",", ":"))
            newFile.write(json_text)


    def list_builder(self, platform):
        if 'psp' == platform.lower():
            platform_list   = 'psp_games'
            platform_path   = self.PSP_ISO_PATH
            filtered_platform  = self.psp_lines
        elif 'psx' == platform.lower():
            platform_list   = 'psx_games'
            platform_path   = self.PSX_ISO_PATH
            filtered_platform  = self.psx_lines
        elif 'ps2' == platform.lower():
            platform_list   = 'ps2_games'
            platform_path   = self.PS2_ISO_PATH
            filtered_platform  = self.ps2_lines
        elif 'ps3' == platform.lower():
            platform_list   = 'ps3_games'
            platform_path   = self.PS3_ISO_PATH
            filtered_platform  = self.ps3_lines

        # instantiate variables
        title_id = None
        meta_data_link = None
        icon0 = None
        pic0 = None
        pic1 = None

        for game_filename in filtered_platform:
            game_exist = False

            # check if game exist
            for list_game in self.json_game_list_data[platform_list]:
                if game_filename == list_game['filename']:
                    self.game_count += 1
                    print('DEBUG PROGRESS: ' + "{:.0%}".format(float(self.game_count).__div__(float(self.total_lines_count))) + ' (' + str(self.game_count) + '/' + str(self.total_lines_count) + ')')
                    print('\nDEBUG skipping ' + game_filename + ', already fetched\n')
                    game_exist = True
                    pass

            # if not, add it
            if not game_exist:
                title_id, icon0, pic0, pic1 = self.get_game_data(platform_path, game_filename)
                title = game_filename

                # removes parenthesis & brackets including their content
                title = re.sub(r'\([^)]*\)', '', title)
                title = re.sub(r'\[[^)]*\]', '', title)


                # removes the file extension
                for file_ext in GlobalVar.file_extensions:
                    if game_filename.upper().endswith(file_ext):
                        title = title[0:len(title)-len(file_ext)]
                        break

                # read platform db
                platform_db_file = platform.upper() + '_all_title_ids.json'
                with open(os.path.join(AppPaths.games_metadata, platform_db_file)) as f:
                    self.json_platform_metadata = json.load(f)

                # check for for match the platform game database
                for game in self.json_platform_metadata['games']:
                    # adapt the title_id format for the xml db
                    if platform == 'ps3':
                        title_id = title_id.replace('-', '')

                    if title_id == game['title_id']:
                        if platform == 'psp' or platform == 'psx' or platform == 'ps2':
                            title = game['title'].encode('utf-8').strip()

                            if game['meta_data_link'] is not None:
                                meta_data_link = game['meta_data_link']

                        elif platform == 'ps3':
                            # use the first element for English
                            title = game['locale'][0]['title'].encode('utf-8').strip()

                        break

                # check for duplicates of the same title in the whole list
                for pltfrm in self.json_game_list_data:
                    for game in self.json_game_list_data[pltfrm]:
                        if str(title) == str(game['title']):
                            # check if there are earlier duplicates title + (1), (2) etc
                            dup_title = re.search('\(\d{1,3}\)$', str(title))
                            if dup_title is not None:
                                pre = str(title)[:len(str(title))-3]
                                suf = str(title)[len(str(title))-3:]
                                new_suf = re.sub('\d(?!\d)', lambda x: str(int(x.group(0)) + 1), suf)
                                title = pre + new_suf
                            else:
                                title = str(title) + ' (1)'

                title = title.strip()

                # add game to list of new games
                self.game_count += 1
                print('DEBUG PROGRESS: ' + "{:.0%}".format(float(self.game_count).__div__(float(self.total_lines_count))) + ' (' + str(self.game_count) + '/' + str(self.total_lines_count) + ')')

                self.new_json_game_list_data[platform_list].append({
                    "title_id": title_id,
                    "title": str(title),
                    "platform": platform.upper(),
                    "filename": game_filename,
                    "path": platform_path,
                    "meta_data_link": meta_data_link})

                # also append it to the existing list for next iteration
                self.json_game_list_data[platform_list].append({
                    "title_id": title_id,
                    "title": str(title),
                    "platform": platform.upper(),
                    "filename": game_filename,
                    "path": platform_path,
                    "meta_data_link": meta_data_link})

                print('DEBUG \'' + game_filename + '\' got title ' + str(title) + '\n')
                print("Added '" + str(title) + "' to the list:\n"
                      + 'Platform: ' + platform.upper() + '\n'
                      + 'Filename: ' + game_filename + '\n'
                      + 'Title id: ' + str(title_id) + '\n')

            if title_id is not None:
                # save game build folder data here
                game_folder_name = game_filename[:-4].replace(' ', '_') + '_(' + title_id.replace('-', '') + ')'
                game_build_dir = os.path.join(AppPaths.builds, game_folder_name)

                # making sure the work_dir and pkg directories exists
                if not os.path.exists(os.path.join(game_build_dir, 'work_dir', 'pkg')):
                    os.makedirs(os.path.join(game_build_dir, 'work_dir', 'pkg'))

                # save images to game work folders
                self.image_saver(platform, game_build_dir, [icon0, pic0, pic1])

                # reset game data for next iteration
                title = None
                title_id = None
                meta_data_link = None

        return self.new_json_game_list_data

    def get_game_data(self, platform_path, game_filename):
        title_id = None
        icon = None
        pic0 = None
        pic1 = None

        game_filepath = os.path.join(platform_path, game_filename)
        iso_index = game_filepath.index('ISO/', 0, len(game_filepath))
        platform = game_filepath[iso_index-3: iso_index].lower()

        try:
            title_id, icon, pic0, pic1 = self.data_chunk.ftp_buffer_data(game_filepath, self.chunk_size_kb, 0, self.game_count)

            # make another fetch with rest offset for PSP images
            if platform == 'psp':
                not_used, icon, pic0, pic1 = self.data_chunk.ftp_buffer_data(game_filepath, self.chunk_size_kb, self.ftp_psp_png_offset_kb, self.game_count)

            # PS3 guitar hero games needs a larger chunk to find the PIC1
            if platform == 'ps3' and 'guitar' in game_filename.lower():
                not_used, icon, pic0, pic1 = self.data_chunk.ftp_buffer_data(game_filepath, 6000, 0, self.game_count)

        # retry connection
        except Exception as e:
            print('DEBUG Error: ' + e.message)
            print('Connection timed out, re-connecting in ' + str(self.ftp_timeout) + 's...\n')

            self.make_new_ftp()
            self.data_chunk = FTPDataHandler(self.ftp, self.total_lines_count)

            title_id, icon, pic0, pic1 = self.data_chunk.ftp_buffer_data(game_filepath, self.chunk_size_kb, 0, self.game_count)

            # make another fetch with rest offset for PSP images
            if platform == 'psp':
                title_id, icon, pic0, pic1 = self.data_chunk.ftp_buffer_data(game_filepath, self.chunk_size_kb, self.ftp_psp_png_offset_kb, self.game_count)

        return title_id, icon, pic0, pic1


    def make_new_ftp(self):

        if None is not self.ftp:
            self.ftp.close()
            time.sleep(self.ftp_timeout)

        self.ftp = FTP(self.ps3_lan_ip, timeout=self.ftp_timeout)
        self.ftp.set_pasv=self.ftp_pasv_mode
        self.ftp.login(user='', passwd='')

    def image_saver(self, platform, game_build_dir, images):
        import shutil

        icon0 = images[0]
        pic0 = images[1]
        pic1 = images[2]

        if os.path.isdir(game_build_dir):
            shutil.rmtree(game_build_dir)
            os.makedirs(os.path.join(game_build_dir, 'work_dir', 'pkg'))

        # platforms such as PSP needs rescaling of images
        if(icon0 is not None):
            if platform.upper() == 'PSP':
                t_icon0 = Image.open(os.path.join(AppPaths.application_path, 'resources', 'images', 'pkg', 'default', 'transparent_ICON0.PNG')).convert("RGBA")
                icon0 = icon0.resize((int(icon0.width*2), int(icon0.height*2)), Image.ANTIALIAS)
                x_pos = (t_icon0.width - icon0.width)/2
                y_pos = (t_icon0.height - icon0.height)/2
                t_icon0.paste(icon0, (x_pos, y_pos), icon0)

                t_icon0.save(os.path.join(game_build_dir, 'work_dir', 'pkg', 'ICON0.PNG'))
            else:
                icon0.save(os.path.join(game_build_dir, 'work_dir', 'pkg', 'ICON0.PNG'))

        else:
            icon0 = Image.open(os.path.join(AppPaths.application_path, 'resources', 'images', 'pkg', 'default', platform.upper(), 'ICON0.PNG')).convert("RGBA")
            icon0.save(os.path.join(game_build_dir, 'work_dir', 'pkg', 'ICON0.PNG'))

        if(pic0 is not None):
            if platform.upper() == 'PSP':
                t_pic0 = Image.open(os.path.join(AppPaths.application_path, 'resources', 'images', 'pkg', 'default', 'transparent_PIC0.PNG')).convert("RGBA")
                x_pos = (t_pic0.width - pic0.width)/2
                y_pos = (t_pic0.height - pic0.height)/2
                t_pic0.paste(icon0, (x_pos, y_pos), pic0)

                t_pic0.save(os.path.join(game_build_dir, 'work_dir', 'pkg', 'PIC0.PNG'))
            else:
                pic0.save(os.path.join(game_build_dir, 'work_dir', 'pkg', 'PIC0.PNG'))

        if(pic1 is not None):
            if platform.upper() == 'PSP':
                t_pic1 = Image.open(os.path.join(AppPaths.application_path, 'resources', 'images', 'pkg', 'default', 'transparent_PIC1.PNG')).convert("RGBA")
                pic1 = pic1.resize((int(pic1.width*3), int(pic1.height*3)), Image.ANTIALIAS)
                x_pos = (t_pic1.width - pic1.width)/2
                y_pos = (t_pic1.height - pic1.height)/2
                t_pic1.paste(pic1, (x_pos, y_pos), pic1)

                t_pic1.save(os.path.join(game_build_dir, 'work_dir', 'pkg', 'PIC1.PNG'))
            else:
                pic1.save(os.path.join(game_build_dir, 'work_dir', 'pkg', 'PIC1.PNG'))


class FTPDataHandler:
    def __init__(self, ftp, total_lines):
        self.ftp_instance = ftp
        self.ftp_instance.voidcmd('TYPE I')
        self.null = None
        self.total_lines = total_lines

    def ftp_buffer_data(self, ftp_filename, chunk_size, rest, game_count):
        icon0 = None
        pic0 = None
        pic1 = None

        iso_index = ftp_filename.index('ISO/', 0, len(ftp_filename))
        platform = ftp_filename[iso_index-3: iso_index].lower()
        filename = ftp_filename[iso_index+4: len(ftp_filename)]
        game_title = ftp_filename[iso_index+4: len(ftp_filename)-4]

        file_size_bytes = self.ftp_instance.size(ftp_filename)
        if file_size_bytes > 0 and file_size_bytes < (chunk_size * 1024):
            chunk_size = (file_size_bytes / 1024) * 0.95
        elif platform.lower() == ('psx', 'ps2'):
            chunk_size = 750

        def fill_buffer(self, received):
            if self.chunk_size <= 0:
                return True
            else:
                self.sio.write(received)
            self.chunk_size -= len(received)


        game_title_id = ''
        self.sio = StringIO.StringIO()
        self.chunk_size = chunk_size * 1024

        offset = max(rest*1024, 0)
        conn = self.ftp_instance.transfercmd('RETR ' + ftp_filename, rest=offset)
        while 1:
            # the buffer size seems a bit random, can't remember why(?)
            try:
                data = conn.recv(1460)
            except Exception as e1:
                error_msg = ''
                if e1.message is not '':
                    error_msg = e1.message
                else:
                    error_msg = repr(e1)
                    # print('DEBUG ERROR traceback: ' + str(traceback.print_exc()))
                    # offset = max(rest*1024, 0)

                print('ERROR when fetching \'' + filename + '\', reason: ' + error_msg)
                print('DEBUG Retrying fetching of \'' + filename + '\'')
                # re-try fetching
                try:
                    conn = self.ftp_instance.transfercmd('RETR ' + ftp_filename, rest=offset)
                except:
                    print('ERROR could not refetch ' + filename + ', skipping')
                    data = None

            # if None: refetch has failed => skip game by breaking the loop
            if data is None:
                game_count += 1
                print('DEBUG PROGRESS: ' + "{:.0%}".format(float(game_count).__div__(float(self.total_lines))) + ' (' + str(game_count) + '/' + str(self.total_lines) + ')')
                break
            else:
                if fill_buffer(self, data):
                    try:
                        conn.close()
                        self.ftp_instance.voidresp()

                    # intended exception: this is thrown when the full data chunk been stored in buffer
                    except Exception as e:
                        # reset values for next round
                        icon0 = None
                        pic0 = None
                        pic1 = None

                        self.data_chunk = self.sio.getvalue()
                        self.sio.close()

                        # try find title_id from beginning of file for all platforms
                        if rest == 0:
                            game_title_id = get_title_id_from_buffer(self, platform, self.data_chunk)

                        # PS3 and PSP are the only platforms that has game art embedded
                        if platform == 'psp' or platform == 'ps3':
                            icon0, pic0, pic1 = get_png_from_buffer(self, platform, filename, self.data_chunk)

                        # Error 451 is normal when closing the conection
                        if '451' not in e.message:
                            print('DEBUG - connection ' + e.message + ' during data fetching of ' + game_title)
                        break

        return game_title_id, icon0, pic0, pic1

def get_png_from_buffer(self, platform, game_name, buffer_data):
    self.platform = platform
    self.data = buffer_data

    try:
        self.has_icon0 = False
        self.has_pic0 = False
        self.has_pic1 = False
        self.image_duplicate = False

        self.icon0_image = None
        self.pic0_image = None
        self.pic1_image = None
        self.image_name = None

        # these byte sequences are standard start and end of PNGs
        def png_finder(data, image_name):
            index_png_start = data.find(b'\x89\x50\x4E\x47\x0D\x0A\x1A\x0A')
            index_png_end = data.find(b'\x00\x00\x00\x00\x49\x45\x4E\x44', index_png_start)

            self.image_duplicate = False
            self.image_name = image_name
            if index_png_start != -1:
                if index_png_end != -1:
                    import PIL.Image as Image
                    import io

                    png_byte_array = data[index_png_start:index_png_end+8]
                    tmp_image = Image.open(io.BytesIO(png_byte_array)).convert("RGBA")
                    self.img_name = None

                    if self.platform == 'psp':
                        # icon image PSP
                        if tmp_image.size == (144, 80):
                            self.img_name = 'ICON0.PNG'
                            if not self.has_icon0:
                                self.icon0_image = tmp_image
                                self.has_icon0 = True

                        # this is background image PSP
                        elif tmp_image.size == (480, 272):
                            self.img_name = 'PIC1.PNG'
                            if not self.has_pic1:
                                self.pic1_image = tmp_image
                                self.has_pic1 = True


                    elif self.platform == 'ps3':
                        # icon image PS3
                        if tmp_image.size == (320, 176):
                            self.img_name = 'ICON0.PNG'
                            if not self.has_icon0:
                                self.icon0_image = tmp_image
                                self.has_icon0 = True


                        # when multiple pic0 we pic the first for English
                        elif tmp_image.size == (1000, 560):
                            self.img_name = 'PIC0.PNG'
                            if not self.has_pic0:
                                self.pic0_image = tmp_image
                                self.has_pic0 = True


                        # this is background image PS3
                        elif tmp_image.size == (1920, 1080):
                            self.img_name = 'PIC1.PNG'
                            if not self.has_pic1:
                                self.pic1_image = tmp_image
                                self.has_pic1 = True

                    if self.img_name is not None:
                        # crop data for next iteration
                        self.data = data[index_png_end:len(data)-1]
                        return True

                return False

        while png_finder(self.data, self.image_name):
            print('DEBUG Found ' + self.img_name + ' for  \'' + game_name + '\'')

        return self.icon0_image, self.pic0_image, self.pic1_image

    except Exception as e:
        print('ERROR: get_png_from_buffer - ' + e.message)
        return self.icon0_image, self.pic0_image, self.pic1_image


def get_title_id_from_buffer(self, platform, buffer_data):
    game_id = ''
    try:
        # psx and ps2
        if platform == 'psx' or platform == 'ps2':
            for m in re.finditer("""\w{4}\_\d{3}\.\d{2}""", buffer_data):
                if m is not None:
                    game_id = str(m.group(0)).strip()
                    game_id = game_id.replace('_', '-')
                    game_id = game_id.replace('.', '')

        elif platform == 'ps3':
            for m in re.finditer("""\w{4}-\d{5} """, buffer_data):
                if m is not None:
                    game_id = str(m.group(0)).strip()

        elif platform == 'psp':
            for m in re.finditer("""\w{4}-\d{5}\|""", buffer_data):
                game_id = str(m.group(0)).strip()
                game_id = game_id[0:len(game_id)-1]

    except Exception:
        print('Error in get_id_from_buffer: ' + self.TITLE_ID_EXCEPTION_MESSAGE)
    finally:
        return game_id
